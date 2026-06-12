"""Pure helpers for the ML Studio multi-file Merge feature.

No FastAPI/DB imports here — keep this unit-testable with plain polars.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import polars as pl

SemanticType = Literal["phone", "email", "date", "number", "category", "text"]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DATE_FMTS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")


def normalize_field(name) -> str:
    """Canonical key for matching a field name across files.

    Lowercase (casefold), collapse internal whitespace, strip a trailing colon.
    """
    s = str(name).strip().casefold()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(":").strip()
    return s


def clean_phone(v) -> str | None:
    """VN phone normalize: keep digits, take last 9, prefix '0'.

    Returns None when fewer than 9 digits remain (treated as invalid/null).
    """
    if v is None:
        return None
    digits = re.sub(r"\D", "", str(v))
    if len(digits) >= 9:
        return "0" + digits[-9:]
    return None


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _is_email(s: str) -> bool:
    return bool(EMAIL_RE.match(s.strip()))


def _is_phone(s: str) -> bool:
    # A digit-ish token, but never an email (rule 2 in spec §5.2).
    if _is_email(s):
        return False
    return 9 <= len(_digits(s)) <= 15


def _parse_date(s: str) -> datetime | None:
    s = s.strip()
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _is_date(s: str) -> bool:
    return _parse_date(s) is not None


def _to_number(s):
    # MVP: strip '.', ',', spaces (treated as thousands separators) then float.
    # Decimals are NOT preserved by design (spec §6); V2 = locale-aware parsing.
    t = str(s).strip().replace(" ", "").replace(",", "").replace(".", "")
    if t in ("", "+", "-"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _is_number(s: str) -> bool:
    return _to_number(s) is not None


def normalize_value(v, t: SemanticType) -> str | None:
    """Canonicalize a single cell for semantic type `t`. None == drop/invalid."""
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    if t == "phone":
        return clean_phone(s)
    if t == "email":
        return s.lower() or None
    if t == "date":
        d = _parse_date(s)
        return d.strftime("%Y-%m-%d") if d else None
    if t == "number":
        f = _to_number(s)
        if f is None:
            return None
        return str(int(f)) if f.is_integer() else str(f)
    if t == "category":
        return re.sub(r"\s+", " ", s) or None
    # text
    return s or None


def is_valid(v, t: SemanticType) -> bool:
    """Post-normalize validity for type `t`."""
    nv = normalize_value(v, t)
    if nv is None:
        return False
    if t == "email":
        return _is_email(nv)
    return nv != ""


def _infer_type(values: list[str]) -> tuple[SemanticType, float]:
    """Pick the highest-priority type clearing the 0.70 threshold (spec §5.2)."""
    n = len(values)
    if n == 0:
        return ("text", 1.0)

    def frac(pred) -> float:
        return sum(1 for v in values if pred(v)) / n

    fe = frac(_is_email)
    if fe >= 0.70:
        return ("email", fe)
    fp = frac(_is_phone)
    if fp >= 0.70:
        return ("phone", fp)
    fd = frac(_is_date)
    if fd >= 0.70:
        return ("date", fd)
    fn = frac(_is_number)
    if fn >= 0.70:
        return ("number", fn)
    distinct = len(set(values))
    mean_len = sum(len(v) for v in values) / n
    # Fallthrough: no strong type cleared 0.70. Low-cardinality + short values
    # become "category"; everything else (incl. mixed sub-threshold columns)
    # becomes "text". This is profiling metadata only — the user can override
    # the inferred type in the wizard.
    if distinct <= max(20, 0.05 * n) and mean_len <= 20:
        return ("category", 1.0)
    return ("text", 1.0)


@dataclass
class ColumnProfile:
    file: str
    name: str
    norm: str
    inferred_type: SemanticType
    confidence: float
    samples: list[str]
    non_null: int
    distinct: int
    fill_rate: float


def profile_columns(
    frames: list[pl.DataFrame], filenames: list[str], *, sample: int = 500,
) -> list[ColumnProfile]:
    """Profile every (file, column): sample non-null values → infer type."""
    out: list[ColumnProfile] = []
    for df, fname in zip(frames, filenames):
        rows = df.height or 1
        for col in df.columns:
            series = df[col].cast(pl.Utf8, strict=False).drop_nulls()
            vals = [s for s in (str(x).strip() for x in series.to_list()) if s != ""]
            non_null = len(vals)
            distinct = len(set(vals))
            itype, conf = _infer_type(vals[:sample])
            seen: list[str] = []
            for x in vals:
                if x not in seen:
                    seen.append(x)
                if len(seen) >= 5:
                    break
            out.append(ColumnProfile(
                file=fname, name=col, norm=normalize_field(col),
                inferred_type=itype, confidence=round(conf, 3),
                samples=seen, non_null=non_null, distinct=distinct,
                fill_rate=round(non_null / rows, 3),
            ))
    return out


_STRONG_TYPES = {"phone", "email", "date"}


def _name_sim(a: str, b: str) -> float:
    """Normalized-name similarity in 0..1 (equal / substring / token Jaccard)."""
    if a == b:
        return 1.0
    if a and b and (a in b or b in a):
        return 0.8
    ta, tb = set(a.split()), set(b.split())
    if ta and tb:
        return len(ta & tb) / len(ta | tb)
    return 0.0


def _cluster_by_name(cols: list[ColumnProfile]) -> list[list[ColumnProfile]]:
    """Union-find clusters of columns whose names are similar (>= 0.5)."""
    parent = list(range(len(cols)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if _name_sim(cols[i].norm, cols[j].norm) >= 0.5:
                union(i, j)
    groups: dict[int, list[ColumnProfile]] = {}
    for idx in range(len(cols)):
        groups.setdefault(find(idx), []).append(cols[idx])
    return list(groups.values())


@dataclass
class FieldGroupSuggestion:
    canonical: str
    members: list[str]
    inferred_type: SemanticType
    confidence: float
    reason: str  # "name" | "type" | "name+type"


def suggest_groups(profiles: list[ColumnProfile]) -> list[FieldGroupSuggestion]:
    """Propose canonical groups of columns to unify (spec §5.3). Proposals only."""
    by_type: dict[SemanticType, list[ColumnProfile]] = {}
    for p in profiles:
        by_type.setdefault(p.inferred_type, []).append(p)

    suggestions: list[FieldGroupSuggestion] = []
    for t, cols in by_type.items():
        if t in _STRONG_TYPES:
            # Strong types unify regardless of name ("value giống nhau, tên khác").
            clusters = [cols] if len(cols) >= 2 else []
        else:
            clusters = [c for c in _cluster_by_name(cols) if len(c) >= 2]

        for cluster in clusters:
            names = [c.name for c in cluster]
            norms = [c.norm for c in cluster]
            sims = [
                _name_sim(norms[i], norms[j])
                for i in range(len(norms)) for j in range(i + 1, len(norms))
            ]
            name_sim = sum(sims) / len(sims) if sims else 0.0
            if t in _STRONG_TYPES:
                reason = "name+type" if name_sim >= 0.5 else "type"
            else:
                reason = "name"
            suggestions.append(FieldGroupSuggestion(
                canonical=cluster[0].name,
                members=names,
                inferred_type=t,
                confidence=round(0.5 * name_sim + 0.5, 3),  # type_agreement=1.0
                reason=reason,
            ))
    return suggestions


def common_fields(schemas: list[list[str]], threshold: float = 1.0) -> list[str]:
    """Fields present in >= `threshold` fraction of schemas (by normalized name).

    threshold=1.0 -> strict intersection (present in every file).
    Returns the first-seen DISPLAY name for each qualifying field, in first-seen order.
    """
    if not schemas:
        return []
    n = len(schemas)
    counts: dict[str, int] = {}
    display: dict[str, str] = {}
    order: list[str] = []
    for schema in schemas:
        seen: set[str] = set()
        for col in schema:
            key = normalize_field(col)
            if key in seen:
                continue
            seen.add(key)
            if key not in counts:
                counts[key] = 0
                display[key] = col
                order.append(key)
            counts[key] += 1
    need = threshold * n - 1e-9
    return [display[k] for k in order if counts[k] >= need]


@dataclass
class MergeSummary:
    total_raw: int                          # Σ file row counts (after union)
    valid_format: int                       # rows with a valid dedup key
    null_or_wrong: int                      # total_raw - valid_format
    distinct: int                           # unique valid keys (coalesced rows)
    dup_removed_clean: int                  # valid_format - distinct
    dup_removed_raw: int                    # total_raw - distinct
    complete: int                           # distinct rows with all required non-null
    incomplete: int                         # distinct - complete
    rejected: int                           # == null_or_wrong
    per_field_fill_rate: dict[str, float]   # per selected col: non-null / distinct
    per_file_contribution: dict[str, int]   # valid rows contributed per file


_SRC = "__src__"  # private provenance column, never user-selectable


def align_and_merge(
    frames: list[pl.DataFrame],
    selected: list[str],
    alias_map: dict[str, str] | None = None,
    *,
    filenames: list[str] | None = None,
    field_groups: dict[str, list[str]] | None = None,
    semantic_types: dict[str, "SemanticType"] | None = None,
    dedup_key: str | None = None,
    required_fields: list[str] | None = None,
    coalesce: bool = True,
    drop_invalid_key: bool = True,
    trim: bool = True,
) -> tuple[pl.DataFrame, pl.DataFrame, MergeSummary]:
    """Union → clean (per semantic type) → coalesce-dedup → metrics.

    Returns (clean, rejected, summary). `filenames` (optional, additive) feeds
    `per_file_contribution`; defaults to positional `file_0..N` labels.
    """
    alias_map = alias_map or {}
    field_groups = field_groups or {}
    semantic_types = semantic_types or {}
    required_fields = required_fields or []
    selected_set = set(selected)
    if filenames is None or len(filenames) != len(frames):
        filenames = [f"file_{i}" for i in range(len(frames))]

    # canonical resolution: field_groups member (raw or normalized) -> canonical
    member_to_canon: dict[str, str] = {}
    for canon, members in field_groups.items():
        for m in members:
            member_to_canon[m] = canon
            member_to_canon[normalize_field(m)] = canon
    sel_norm = {normalize_field(s): s for s in selected}

    aligned: list[pl.DataFrame] = []
    for df, fname in zip(frames, filenames):
        rename: dict[str, str] = {}
        used: set[str] = set()
        for c in df.columns:
            tgt = (alias_map.get(c)
                   or member_to_canon.get(c)
                   or member_to_canon.get(normalize_field(c))
                   or sel_norm.get(normalize_field(c)))
            if tgt and tgt in selected_set and tgt not in used:
                rename[c] = tgt
                used.add(tgt)
        d = df.rename(rename) if rename else df
        d = d.select([c for c in selected if c in d.columns])
        for c in selected:
            if c not in d.columns:
                d = d.with_columns(pl.lit(None).alias(c))
        d = d.select(selected)
        d = d.with_columns([pl.col(c).cast(pl.Utf8, strict=False) for c in selected])
        d = d.with_columns(pl.lit(fname).alias(_SRC))
        aligned.append(d)

    if aligned:
        merged = pl.concat(aligned, how="diagonal_relaxed")
    else:
        merged = pl.DataFrame({c: [] for c in [*selected, _SRC]})
    total_raw = merged.height

    if trim and total_raw:
        merged = merged.with_columns([pl.col(c).str.strip_chars() for c in selected])
        merged = merged.with_columns([
            pl.when(pl.col(c) == "").then(None).otherwise(pl.col(c)).alias(c)
            for c in selected
        ])

    for c in selected:
        t = semantic_types.get(c)
        if t:
            merged = merged.with_columns(
                pl.col(c).map_elements(lambda v, _t=t: normalize_value(v, _t),
                                       return_dtype=pl.Utf8).alias(c)
            )

    other_cols = [c for c in selected if c != dedup_key]

    def _contrib(frame: pl.DataFrame) -> dict[str, int]:
        out = {fn: 0 for fn in filenames}
        if frame.height:
            for r in frame.group_by(_SRC).len().iter_rows(named=True):
                out[r[_SRC]] = int(r["len"])
        return out

    if dedup_key and dedup_key in selected_set:
        ktype = semantic_types.get(dedup_key, "text")
        valid_mask = merged[dedup_key].map_elements(
            lambda v, _t=ktype: is_valid(v, _t), return_dtype=pl.Boolean).fill_null(False)
        valid_df = merged.filter(valid_mask)
        rejected = merged.filter(~valid_mask).select(selected)
        valid_format = valid_df.height
        distinct = int(valid_df[dedup_key].n_unique()) if valid_format else 0
        per_file = _contrib(valid_df)
        if coalesce:
            clean_distinct = (
                valid_df.group_by(dedup_key, maintain_order=True)
                .agg([pl.col(c).drop_nulls().first().alias(c) for c in other_cols])
                .select(selected)
            )
        else:
            clean_distinct = valid_df.unique(
                subset=[dedup_key], keep="first", maintain_order=True).select(selected)
    else:
        valid_format = total_raw
        distinct = total_raw
        clean_distinct = merged.select(selected)
        rejected = merged.head(0).select(selected)
        per_file = _contrib(merged)

    null_or_wrong = total_raw - valid_format
    dup_removed_clean = valid_format - distinct
    dup_removed_raw = total_raw - distinct

    req = [c for c in required_fields if c in selected_set]
    if req and clean_distinct.height:
        mask = pl.all_horizontal([pl.col(c).is_not_null() for c in req])
        complete = int(clean_distinct.select(mask.alias("_c"))["_c"].sum())
    else:
        complete = clean_distinct.height
    incomplete = distinct - complete

    h = clean_distinct.height or 1
    fill = {c: round(int(clean_distinct[c].is_not_null().sum()) / h, 3) for c in selected}

    clean = clean_distinct
    if not drop_invalid_key and rejected.height:
        clean = pl.concat([clean_distinct, rejected], how="diagonal_relaxed")
        rejected = rejected.head(0)

    summary = MergeSummary(
        total_raw=total_raw, valid_format=valid_format, null_or_wrong=null_or_wrong,
        distinct=distinct, dup_removed_clean=dup_removed_clean,
        dup_removed_raw=dup_removed_raw, complete=complete, incomplete=incomplete,
        rejected=null_or_wrong, per_field_fill_rate=fill,
        per_file_contribution=per_file,
    )
    return clean, rejected, summary
