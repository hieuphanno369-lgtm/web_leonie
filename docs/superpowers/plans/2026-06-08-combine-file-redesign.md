# Combine file — Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the phone-centric "Gộp file" tab with a generic, value-aware
"Combine file" 4-step wizard that profiles each column's semantic type, suggests
unifying differently-named columns that hold similar values, and produces the
notebook-grade outcome (8 metrics + both dup definitions + fill-rate + per-file).

**Architecture:** Backend `analytics/merge.py` gains a pure value-aware engine
(`profile_columns`, `suggest_groups`, `normalize_value`/`is_valid`) and a v2
`align_and_merge` that returns `(clean, rejected, summary)` with a rich
`MergeSummary`. `routers/ml.py` extends `/merge/stage` (profiles+suggestions),
`/merge/run` (new options + `dry_run` preview), and adds
`/merge/{sid}/rejected.csv`. The frontend splits `MlMergeView` into a
`components/ml/merge/` wizard; the tab is renamed and moved before Auto-EDA.

**Tech Stack:** Backend — Python, Polars, FastAPI, pytest. Frontend — React 19,
TypeScript ~5.7, Vite 6, Tailwind 3.4, lucide-react. Source spec:
`docs/superpowers/specs/2026-06-08-combine-file-redesign-design.md`.

---

## Conventions & gotchas (read before starting)

- **Working tree:** implement in the worktree on branch
  `claude/beautiful-curran-085809`. Commit after every green task.
- **Backend tests:** `cd backend ; uv run pytest -q` (uv auto-syncs `.venv` in
  the worktree on first run — first invocation may be slow; that is expected).
- **Frontend gate:** there is **no JS unit runner** in this repo. The frontend
  "test" is a clean `cd frontend ; npm run build` (= `tsc -b && vite build`).
  If the worktree has no `node_modules`, run `cd frontend ; npm install` **once**
  before the first frontend task (it lives only in MAIN otherwise).
- **Name collision:** `routers/ml.py` already imports `profile_columns` from
  `analytics.eda`. The new merge profiler is imported **aliased**
  (`profile_columns as profile_merge_columns`). Never shadow the eda import.
- **Number cleaning caveat (per spec §6):** `normalize_value(v,"number")` strips
  `.`, `,`, and spaces then parses as float. This intentionally treats `.`/`,`
  as thousands separators (e.g. `"1.234" → "1234"`); decimals are **not**
  preserved in MVP. Keep the documenting comment in the code.
- **Delivery (spec §12):** do **all** work + verification in the worktree, then
  do a **single** FF-merge into local `master` at the very end (Phase G) so the
  MAIN dev server never sees a half-built backend. **NEVER push** — `master`
  history contains live secrets. `.env` stays untracked.
- **Commit attribution:** end each commit message with the Co-Authored-By line
  the harness requires.

---

## File Structure

**Backend — modify:**
- `backend/analytics/merge.py` — add engine (`SemanticType`, value helpers,
  `normalize_value`/`is_valid`, `_infer_type`, `ColumnProfile`,
  `profile_columns`, `FieldGroupSuggestion`, `suggest_groups`); rewrite
  `MergeSummary` (rich) and `align_and_merge` (v2, 3-tuple). Keep
  `normalize_field`, `clean_phone`, `common_fields` unchanged.
- `backend/routers/ml.py` — extend `MergeStageOut`, `MergeOptions`, `MergeRunIn`,
  `MergeSummaryOut`, `MergeRunOut`; rewrite `merge_stage`/`merge_run` bodies; add
  `merge_rejected` download route; fix the merge import line.
- `backend/tests/test_merge.py` — update existing cases to the v2 API; add engine
  tests + the notebook-numbers fixture test.

**Frontend — create (`frontend/src/components/ml/merge/`):**
- `MergeWizard.tsx` — step state machine (1..4), session, api orchestration.
- `MergeStepUpload.tsx` — B1 dropzone + staged-file list.
- `MergeFieldGroups.tsx` — B2 common/per-file groups + provenance + include toggles.
- `MergeUnifySuggestions.tsx` — B2 suggestion cards (accept/split).
- `MergeTypePicker.tsx` — B2 per-canonical type confirm + samples.
- `MergeCleanStep.tsx` — B3 key, required fields, toggles.
- `MergePreview.tsx` — B4 preview table.
- `MergeOutcome.tsx` — B4 8 metrics + fill-rate + per-file + exports.

**Frontend — modify:**
- `frontend/src/types.ts` — add `SemanticType`, `ColumnProfile`,
  `FieldGroupSuggestion`; extend `MergeStageResult`, `MergeOptions`,
  `MergeSummary`, `MergeRunResult`.
- `frontend/src/api/ml.ts` — extend `runMerge` (new options + `dryRun`); add
  `downloadRejected`.
- `frontend/src/components/ml/MlResultTabs.tsx` — rename + reorder the merge tab;
  render `MergeWizard` instead of `MlMergeView`.

**Frontend — delete (absorbed):**
- `frontend/src/components/ml/MlMergeView.tsx`
- `frontend/src/components/ml/MlMergeChips.tsx`
- `frontend/src/components/ml/MlMergeSummary.tsx`

`MlMergeDropzone.tsx` is **kept** and reused by `MergeStepUpload`.

---

# Phase A — Backend value-aware engine

### Task A1: `normalize_value` + `is_valid` (6 semantic types)

**Files:**
- Modify: `backend/analytics/merge.py`
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing tests** — append to `backend/tests/test_merge.py`:

```python
from analytics.merge import normalize_value, is_valid


def test_normalize_value_phone_lenient():
    assert normalize_value("0987.654.321", "phone") == "0987654321"
    assert normalize_value("84987654321", "phone") == "0987654321"
    assert normalize_value("123", "phone") is None
    assert is_valid("84987654321", "phone") is True
    assert is_valid("123", "phone") is False


def test_normalize_value_email_trims_lowercases():
    assert normalize_value("  Foo@Bar.COM ", "email") == "foo@bar.com"
    assert is_valid("Foo@Bar.com", "email") is True
    assert is_valid("not-an-email", "email") is False


def test_normalize_value_date_to_iso():
    assert normalize_value("31/12/2024", "date") == "2024-12-31"
    assert normalize_value("2024-01-05", "date") == "2024-01-05"
    assert normalize_value("05-06-2024", "date") == "2024-06-05"
    assert normalize_value("nope", "date") is None
    assert is_valid("31/12/2024", "date") is True


def test_normalize_value_number_strips_separators():
    # MVP rule: '.', ',', spaces are thousands separators (decimals not kept).
    assert normalize_value("1.234", "number") == "1234"
    assert normalize_value("1,234", "number") == "1234"
    assert normalize_value("12 345", "number") == "12345"
    assert normalize_value("abc", "number") is None
    assert is_valid("12 345", "number") is True


def test_normalize_value_category_and_text():
    assert normalize_value("  Ha   Noi ", "category") == "Ha Noi"
    assert normalize_value("  free   text ", "text") == "free   text"
    assert is_valid("", "category") is False
    assert is_valid("  ", "text") is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "normalize_value or is_valid" -q`
Expected: FAIL — `ImportError: cannot import name 'normalize_value'`.

- [ ] **Step 3: Implement the engine value layer** — in `backend/analytics/merge.py`,
add the imports at the top (after `import re`) and the value helpers after
`clean_phone`:

```python
from datetime import datetime
from typing import Literal

SemanticType = Literal["phone", "email", "date", "number", "category", "text"]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DATE_FMTS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _is_email(s: str) -> bool:
    return bool(EMAIL_RE.match(s.strip()))


def _is_phone(s: str) -> bool:
    # A digit-ish token, but never an email (rule 2 in spec §5.2).
    if _is_email(s):
        return False
    return 9 <= len(_digits(s)) <= 15


def _parse_date(s: str):
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "normalize_value or is_valid" -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/merge.py backend/tests/test_merge.py
git commit -m "feat(merge): generic per-type normalize_value/is_valid engine"
```

---

### Task A2: column profiling + type inference

**Files:**
- Modify: `backend/analytics/merge.py`
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing tests** — append to `backend/tests/test_merge.py`:

```python
from analytics.merge import profile_columns, ColumnProfile


def test_profile_columns_infers_types_and_samples():
    f1 = pl.DataFrame({
        "SĐT":   ["0987654321", "0912345678", "84900000000"],
        "Email": ["a@x.com", "b@y.com", "c@z.com"],
        "Ngày":  ["01/02/2024", "2024-03-04", "05-06-2024"],
        "Tỉnh":  ["Hà Nội", "Hà Nội", "Đà Nẵng"],
    })
    profs = profile_columns([f1], ["f1.csv"])
    by_name = {p.name: p for p in profs}
    assert by_name["SĐT"].inferred_type == "phone"
    assert by_name["Email"].inferred_type == "email"
    assert by_name["Ngày"].inferred_type == "date"
    assert by_name["Tỉnh"].inferred_type == "category"
    p = by_name["SĐT"]
    assert isinstance(p, ColumnProfile)
    assert p.file == "f1.csv"
    assert p.non_null == 3 and p.distinct == 3
    assert 0.0 < p.confidence <= 1.0
    assert len(p.samples) <= 5 and len(p.samples) >= 1


def test_profile_columns_fill_rate_and_text_fallback():
    f1 = pl.DataFrame({"note": ["hello world this is free text", None, "another distinct sentence"]})
    profs = profile_columns([f1], ["n.csv"])
    p = profs[0]
    assert p.inferred_type == "text"
    assert p.non_null == 2
    assert p.fill_rate == round(2 / 3, 3)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "profile_columns" -q`
Expected: FAIL — `ImportError: cannot import name 'profile_columns'`.

- [ ] **Step 3: Implement inference + profiling** — in `backend/analytics/merge.py`,
add after `is_valid` (uses `@dataclass`, already imported at top of file):

```python
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
    if distinct <= max(20, 0.05 * n) and mean_len <= 30:
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "profile_columns" -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/merge.py backend/tests/test_merge.py
git commit -m "feat(merge): value-based column profiling + semantic type inference"
```

---

### Task A3: `suggest_groups` (value-aware unification proposals)

**Files:**
- Modify: `backend/analytics/merge.py`
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing tests** — append to `backend/tests/test_merge.py`:

```python
from analytics.merge import suggest_groups, FieldGroupSuggestion


def test_suggest_groups_unifies_phone_columns_under_different_names():
    # Three differently-named columns that all hold phone values (the core
    # "value giống nhau, tên khác" case) → one canonical group.
    f1 = pl.DataFrame({"SĐT": ["0987654321", "0912345678"]})
    f2 = pl.DataFrame({"Mobile": ["0900000001", "0900000002"]})
    f3 = pl.DataFrame({"Liên hệ": ["0900000003", "0900000004"]})
    profs = profile_columns([f1, f2, f3], ["a", "b", "c"])
    sugg = suggest_groups(profs)
    phone_groups = [s for s in sugg if s.inferred_type == "phone"]
    assert len(phone_groups) == 1
    g = phone_groups[0]
    assert isinstance(g, FieldGroupSuggestion)
    assert set(g.members) == {"SĐT", "Mobile", "Liên hệ"}
    assert g.reason in ("type", "name+type")


def test_suggest_groups_clusters_similar_names_for_generic_types():
    f1 = pl.DataFrame({"Tỉnh thành": ["Hà Nội", "Đà Nẵng", "Huế"]})
    f2 = pl.DataFrame({"Tỉnh": ["Hà Nội", "HCM", "Cần Thơ"]})
    profs = profile_columns([f1, f2], ["a", "b"])
    sugg = suggest_groups(profs)
    cat = [s for s in sugg if s.inferred_type == "category"]
    assert len(cat) == 1
    assert set(cat[0].members) == {"Tỉnh thành", "Tỉnh"}
    assert cat[0].reason == "name"


def test_suggest_groups_ignores_singletons():
    f1 = pl.DataFrame({"only": ["unique long free text value here", "another one entirely"]})
    profs = profile_columns([f1], ["a"])
    assert suggest_groups(profs) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "suggest_groups" -q`
Expected: FAIL — `ImportError: cannot import name 'suggest_groups'`.

- [ ] **Step 3: Implement clustering + suggestions** — in `backend/analytics/merge.py`,
add after `profile_columns`:

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "suggest_groups" -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/merge.py backend/tests/test_merge.py
git commit -m "feat(merge): suggest_groups — propose unifying same-value differently-named columns"
```

---

# Phase B — Backend merge v2 (`align_and_merge`)

### Task B1: rich `MergeSummary` + v2 `align_and_merge` (3-tuple, coalesce, generic clean)

**Files:**
- Modify: `backend/analytics/merge.py` (replace `MergeSummary` and `align_and_merge`)
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing tests** — append to `backend/tests/test_merge.py`:

```python
from analytics.merge import align_and_merge as merge_v2


def test_merge_v2_returns_clean_rejected_summary_and_coalesces():
    # Same phone under two names; one row complete, its duplicate fills the gap.
    f1 = pl.DataFrame({"SĐT": ["0987654321", "0912345678", ""],
                       "Tên":  ["An", None, "Z"],
                       "Email": ["an@x.com", None, None]})
    f2 = pl.DataFrame({"Phone": ["84987654321"],
                       "Tên":   [None],
                       "Email": ["an2@x.com"]})
    clean, rejected, summary = merge_v2(
        [f1, f2], selected=["SĐT", "Tên", "Email"],
        filenames=["f1", "f2"],
        field_groups={"SĐT": ["SĐT", "Phone"]},
        semantic_types={"SĐT": "phone", "Email": "email", "Tên": "text"},
        dedup_key="SĐT", required_fields=["Tên", "Email"],
        coalesce=True, drop_invalid_key=True,
    )
    # 4 raw rows; "" phone is invalid -> rejected; 0987654321 appears 3x (f1 + f2)
    assert summary.total_raw == 4
    assert summary.null_or_wrong == 1
    assert summary.valid_format == 3
    assert summary.distinct == 2                 # 0987654321, 0912345678
    assert summary.dup_removed_clean == 1        # 3 valid - 2 distinct
    assert summary.dup_removed_raw == 2          # 4 raw - 2 distinct
    assert summary.rejected == 1
    assert clean.height == 2
    assert rejected.height == 1
    # Coalesce: the 0987654321 group fills Tên="An" (from f1 row 1).
    row = clean.filter(pl.col("SĐT") == "0987654321").to_dicts()[0]
    assert row["Tên"] == "An" and row["Email"] == "an@x.com"
    # complete = groups with Tên AND Email non-null after coalesce.
    assert summary.complete == 1
    assert summary.incomplete == 1
    assert set(summary.per_file_contribution) == {"f1", "f2"}
    assert "Email" in summary.per_field_fill_rate


def test_merge_v2_keeps_invalid_when_not_dropping():
    f1 = pl.DataFrame({"phone": ["0987654321", ""], "name": ["A", "B"]})
    clean, rejected, summary = merge_v2(
        [f1], selected=["phone", "name"], filenames=["f"],
        semantic_types={"phone": "phone"}, dedup_key="phone",
        drop_invalid_key=False,
    )
    assert clean.height == 2          # 1 valid distinct + 1 invalid kept
    assert rejected.height == 0
    assert summary.null_or_wrong == 1


def test_merge_v2_no_key_passthrough():
    f1 = pl.DataFrame({"a": ["1", "2"], "b": ["x", "y"]})
    clean, rejected, summary = merge_v2(
        [f1], selected=["a", "b"], filenames=["f"], required_fields=["b"],
    )
    assert clean.height == 2
    assert summary.distinct == 2
    assert summary.complete == 2
    assert summary.dup_removed_raw == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "merge_v2" -q`
Expected: FAIL — `TypeError` (old `align_and_merge` returns a 2-tuple / rejects
the new kwargs).

- [ ] **Step 3: Replace `MergeSummary` and `align_and_merge`** — in
`backend/analytics/merge.py`, delete the **entire** existing `MergeSummary`
dataclass (lines defining `total_raw/valid/nulls/...`) and the **entire**
existing `align_and_merge` function, and replace both with:

```python
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
            lambda v, _t=ktype: is_valid(v, _t), return_dtype=pl.Boolean)
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "merge_v2" -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/merge.py backend/tests/test_merge.py
git commit -m "feat(merge): align_and_merge v2 — coalesce dedup, rich summary, (clean,rejected,summary)"
```

---

### Task B2: reproduce the notebook numbers from a synthetic fixture

**Files:**
- Test: `backend/tests/test_merge.py`

This validates the metric math end-to-end against the gold numbers
`3483 / 3293 / 190 / 551 / 361 / 2932 / 612 / 2320` (spec §7.4, §11). The fixture
is generated deterministically so the counts are exact.

- [ ] **Step 1: Write the failing test** — append to `backend/tests/test_merge.py`:

```python
def _notebook_fixture():
    """Two frames engineered to reproduce the notebook's 8 gold metrics.

    612 complete groups + 361 duplicates of the first 361 of them (in file1),
    2320 incomplete groups (email missing) + 190 invalid-phone rows (in file2).
      total_raw      = 612 + 361 + 2320 + 190 = 3483
      valid_format   = 612 + 361 + 2320       = 3293
      null_or_wrong  = 190
      distinct       = 612 + 2320             = 2932   (361 dups reuse phones)
      dup_clean      = 3293 - 2932 = 361
      dup_raw        = 3483 - 2932 = 551
      complete       = 612    incomplete = 2932 - 612 = 2320
    """
    def phone(i: int) -> str:
        return f"09{i:08d}"          # 10 digits, valid, distinct per i

    file1 = []
    for i in range(612):             # complete groups
        file1.append({"phone": phone(i), "name": f"N{i}", "email": f"u{i}@x.com"})
    for i in range(361):             # duplicates of first 361 complete groups
        file1.append({"phone": phone(i), "name": f"N{i}", "email": f"u{i}@x.com"})

    file2 = []
    for i in range(612, 612 + 2320):  # incomplete groups (email missing)
        file2.append({"phone": phone(i), "name": f"N{i}", "email": None})
    for i in range(190):              # invalid phones (rejected)
        file2.append({"phone": "123", "name": f"bad{i}", "email": None})

    return pl.DataFrame(file1), pl.DataFrame(file2)


def test_align_and_merge_reproduces_notebook_numbers():
    f1, f2 = _notebook_fixture()
    clean, rejected, s = merge_v2(
        [f1, f2], selected=["phone", "name", "email"],
        filenames=["file1.xlsx", "file2.xlsx"],
        semantic_types={"phone": "phone", "name": "text", "email": "email"},
        dedup_key="phone", required_fields=["name", "email"],
        coalesce=True, drop_invalid_key=True,
    )
    assert s.total_raw == 3483
    assert s.valid_format == 3293
    assert s.null_or_wrong == 190
    assert s.distinct == 2932
    assert s.dup_removed_clean == 361
    assert s.dup_removed_raw == 551
    assert s.complete == 612
    assert s.incomplete == 2320
    assert clean.height == 2932
    assert rejected.height == 190
    assert s.per_file_contribution == {"file1.xlsx": 973, "file2.xlsx": 2320}
    assert s.per_field_fill_rate["phone"] == 1.0
    assert s.per_field_fill_rate["email"] == round(612 / 2932, 3)
```

- [ ] **Step 2: Run to verify it fails, then passes**

Run: `cd backend ; uv run pytest tests/test_merge.py::test_align_and_merge_reproduces_notebook_numbers -v`
Expected: PASS immediately (the v2 engine from B1 already implements the math).
If any count is off, **do not edit the test** — fix the metric math in
`align_and_merge` until the gold numbers match.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_merge.py
git commit -m "test(merge): reproduce notebook gold metrics (3483/3293/190/551/361/2932/612/2320)"
```

---

### Task B3: migrate the legacy `align_and_merge`/summary tests to v2

The original `test_merge.py` had 5 `align_and_merge` cases and 2 API cases using
the removed `phone_cols`/`drop_null_key` args, the 2-tuple return, and the old
`MergeSummary` field names. They will now fail to import / assert. Update them.

**Files:**
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Run the legacy cases to confirm they now fail**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "test_align_and_merge_unions or test_align_and_merge_dedup or test_align_and_merge_complete or test_align_and_merge_keeps" -q`
Expected: FAIL — `ValueError: too many values to unpack` / unexpected kwargs.

- [ ] **Step 2: Rewrite the four legacy `align_and_merge` cases** — in
`backend/tests/test_merge.py`, replace the bodies of these four tests
(`test_align_and_merge_unions_and_aligns_by_normalized_name`,
`test_align_and_merge_dedup_and_phone_clean`,
`test_align_and_merge_complete_records`,
`test_align_and_merge_keeps_null_keys_when_not_dropping`) with:

```python
def test_align_and_merge_unions_and_aligns_by_normalized_name():
    f1 = pl.DataFrame({"Phone": ["0987654321"], "Name": ["A"]})
    f2 = pl.DataFrame({"phone ": ["0912345678"], "Product": ["X"]})
    clean, _rej, summary = align_and_merge(
        [f1, f2], selected=["Phone", "Name", "Product"],
    )
    assert clean.columns == ["Phone", "Name", "Product"]
    assert clean.height == 2
    assert clean["Name"].to_list() == ["A", None]
    assert clean["Product"].to_list() == [None, "X"]
    assert summary.total_raw == 2


def test_align_and_merge_dedup_and_phone_clean():
    f1 = pl.DataFrame({"phone": ["0987.654.321", "0987654321", None],
                       "name": ["A", "B", "C"]})
    f2 = pl.DataFrame({"phone": ["84987654321"], "name": ["D"]})
    clean, _rej, summary = align_and_merge(
        [f1, f2], selected=["phone", "name"],
        semantic_types={"phone": "phone"}, dedup_key="phone",
        drop_invalid_key=True,
    )
    assert summary.total_raw == 4
    assert summary.null_or_wrong == 1
    assert summary.valid_format == 3
    assert summary.distinct == 1
    assert summary.dup_removed_clean == 2
    assert clean.height == 1
    assert clean["phone"].to_list() == ["0987654321"]


def test_align_and_merge_complete_records():
    f1 = pl.DataFrame({"phone": ["0987654321", "0912345678"],
                       "name": ["A", None], "age": ["5", "6"]})
    clean, _rej, summary = align_and_merge(
        [f1], selected=["phone", "name", "age"],
        semantic_types={"phone": "phone"}, dedup_key="phone",
        required_fields=["name", "age"],
    )
    assert summary.complete == 1
    assert isinstance(summary, MergeSummary)


def test_align_and_merge_keeps_null_keys_when_not_dropping():
    f1 = pl.DataFrame({"phone": ["0987654321", None], "name": ["A", "B"]})
    clean, _rej, summary = align_and_merge(
        [f1], selected=["phone", "name"],
        semantic_types={"phone": "phone"}, dedup_key="phone",
        drop_invalid_key=False,
    )
    assert clean.height == 2
    assert summary.null_or_wrong == 1
```

- [ ] **Step 3: Run to verify they pass**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "test_align_and_merge_unions or test_align_and_merge_dedup or test_align_and_merge_complete or test_align_and_merge_keeps" -q`
Expected: PASS (4 tests). (The 2 API cases `test_merge_run_registers_dataset`
and `test_merge_stage_returns_common_fields` are updated in Phase C.)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_merge.py
git commit -m "test(merge): migrate legacy align_and_merge cases to v2 API"
```

---

# Phase C — Backend endpoints (`routers/ml.py`)

### Task C1: extend `/merge/stage` with profiles + suggestions

**Files:**
- Modify: `backend/routers/ml.py` (import line ~28; `MergeStageOut` ~426;
  `merge_stage` return ~483)
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing test** — in `backend/tests/test_merge.py`,
replace `test_merge_stage_returns_common_fields` with:

```python
def test_merge_stage_returns_common_fields_profiles_suggestions(client):
    resp = client.post(
        "/api/ml/merge/stage",
        files=[
            ("files", ("a.csv", io.BytesIO(CSV_A), "text/csv")),
            ("files", ("b.csv", io.BytesIO(CSV_B), "text/csv")),
        ],
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["session_id"]
    assert len(d["files"]) == 2
    assert set(normalize_field(f) for f in d["common_fields"]) == {"phone", "name"}
    assert "Age" in d["all_fields"] and "Product" in d["all_fields"]
    # NEW: profiles for every (file, column) + value-aware suggestions.
    assert any(p["name"] == "Phone" and p["inferred_type"] == "phone" for p in d["profiles"])
    assert isinstance(d["suggestions"], list)
    # Phone present in both files -> a unify suggestion of type "phone".
    assert any(s["inferred_type"] == "phone" for s in d["suggestions"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py::test_merge_stage_returns_common_fields_profiles_suggestions -v`
Expected: FAIL — `KeyError: 'profiles'`.

- [ ] **Step 3a: Fix the merge import** — in `backend/routers/ml.py`, replace
line 28:

```python
from analytics.merge import common_fields, align_and_merge
```

with (alias avoids colliding with the `profile_columns` already imported from
`analytics.eda` on line 29):

```python
from analytics.merge import (
    common_fields, align_and_merge,
    profile_columns as profile_merge_columns, suggest_groups,
    ColumnProfile, FieldGroupSuggestion,
)
```

- [ ] **Step 3b: Extend `MergeStageOut`** — replace the `MergeStageOut` class
(currently lines ~426-430) with:

```python
class ColumnProfileOut(BaseModel):
    file: str
    name: str
    norm: str
    inferred_type: str
    confidence: float
    samples: list[str]
    non_null: int
    distinct: int
    fill_rate: float


class FieldGroupSuggestionOut(BaseModel):
    canonical: str
    members: list[str]
    inferred_type: str
    confidence: float
    reason: str


class MergeStageOut(BaseModel):
    session_id: str
    files: list[MergeFileSchema]
    common_fields: list[str]
    all_fields: list[str]
    profiles: list[ColumnProfileOut]
    suggestions: list[FieldGroupSuggestionOut]
```

- [ ] **Step 3c: Populate them in `merge_stage`** — in `merge_stage`, replace the
final `return MergeStageOut(...)` block (currently lines ~483-488) with:

```python
    frames = [pl.read_parquet(sdir / m["parquet"]) for m in manifest]
    fnames = [m["filename"] for m in manifest]
    profiles = profile_merge_columns(frames, fnames)
    suggestions = suggest_groups(profiles)
    return MergeStageOut(
        session_id=sid,
        files=[MergeFileSchema(filename=m["filename"], fields=m["fields"]) for m in manifest],
        common_fields=common_fields(schemas),
        all_fields=seen,
        profiles=[ColumnProfileOut(**p.__dict__) for p in profiles],
        suggestions=[FieldGroupSuggestionOut(**g.__dict__) for g in suggestions],
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py::test_merge_stage_returns_common_fields_profiles_suggestions -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_merge.py
git commit -m "feat(merge): /merge/stage returns column profiles + unify suggestions"
```

---

### Task C2: extend `/merge/run` (new options + `dry_run` preview + rejected persistence)

**Files:**
- Modify: `backend/routers/ml.py` (`MergeOptions` ~491; `MergeRunIn` ~498;
  `MergeSummaryOut` ~505; `MergeRunOut` ~514; `merge_run` body ~519-562)
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing tests** — in `backend/tests/test_merge.py`,
replace `test_merge_run_registers_dataset` with the two tests below:

```python
def test_merge_run_registers_dataset(client):
    stage = client.post(
        "/api/ml/merge/stage",
        files=[
            ("files", ("a.csv", io.BytesIO(CSV_A), "text/csv")),
            ("files", ("b.csv", io.BytesIO(CSV_B), "text/csv")),
        ],
    ).json()
    resp = client.post("/api/ml/merge/run", json={
        "session_id": stage["session_id"],
        "selected_fields": ["Phone", "Name"],
        "alias_map": {},
        "options": {"dedup_key": "Phone", "drop_invalid_key": True, "trim": True,
                    "semantic_types": {"Phone": "phone"},
                    "field_groups": {"Phone": ["Phone", "phone"]},
                    "required_fields": ["Name"], "coalesce": True},
        "dry_run": False,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["summary"]["total_raw"] == 4
    assert d["summary"]["distinct"] == 3
    assert d["summary"]["dup_removed_clean"] == 1
    assert d["dataset"] is not None
    assert d["rejected_url"]
    fid = d["dataset"]["file_id"]
    assert d["dataset"]["rows"] == 3
    q = client.post("/api/ml/query", json={
        "file_id": fid, "sql": "SELECT COUNT(*) AS n FROM data",
    })
    assert q.status_code == 200
    assert q.json()["rows"][0][0] == 3


def test_merge_run_dry_run_returns_preview_no_dataset(client):
    stage = client.post(
        "/api/ml/merge/stage",
        files=[("files", ("a.csv", io.BytesIO(CSV_A), "text/csv"))],
    ).json()
    resp = client.post("/api/ml/merge/run", json={
        "session_id": stage["session_id"],
        "selected_fields": ["Phone", "Name", "Age"],
        "options": {"dedup_key": "Phone", "semantic_types": {"Phone": "phone"}},
        "dry_run": True,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["dataset"] is None
    assert isinstance(d["preview"], list) and len(d["preview"]) >= 1
    assert "Phone" in d["preview"][0]
    assert d["summary"]["total_raw"] == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "merge_run" -q`
Expected: FAIL — `KeyError: 'rejected_url'` / dry-run preview missing.

- [ ] **Step 3a: Replace `MergeOptions`, `MergeRunIn`, `MergeSummaryOut`,
`MergeRunOut`** (currently lines ~491-516) with:

```python
class MergeOptions(BaseModel):
    dedup_key: str | None = None
    drop_invalid_key: bool = True
    trim: bool = True
    semantic_types: dict[str, str] = {}
    field_groups: dict[str, list[str]] = {}
    required_fields: list[str] = []
    coalesce: bool = True


class MergeRunIn(BaseModel):
    session_id: str
    selected_fields: list[str]
    alias_map: dict[str, str] = {}
    options: MergeOptions = MergeOptions()
    dry_run: bool = False


class MergeSummaryOut(BaseModel):
    total_raw: int
    valid_format: int
    null_or_wrong: int
    distinct: int
    dup_removed_clean: int
    dup_removed_raw: int
    complete: int
    incomplete: int
    rejected: int
    per_field_fill_rate: dict[str, float]
    per_file_contribution: dict[str, int]


class MergeRunOut(BaseModel):
    summary: MergeSummaryOut
    dataset: DatasetInfo | None = None
    preview: list[dict] | None = None
    rejected_url: str | None = None
```

- [ ] **Step 3b: Rewrite the `merge_run` body** — replace the whole function body
of `merge_run` (currently lines ~520-562, from `sdir = ...` through the
`return MergeRunOut(...)`) with:

```python
    sdir = MERGE_SESSIONS_DIR / body.session_id
    manifest_path = sdir / "_session.json"
    if not manifest_path.exists():
        raise HTTPException(404, "Merge session not found")
    if not body.selected_fields:
        raise HTTPException(400, "No fields selected")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames = [pl.read_parquet(sdir / m["parquet"]) for m in manifest]
    fnames = [m["filename"] for m in manifest]

    o = body.options
    clean, rejected, summary = align_and_merge(
        frames, body.selected_fields, body.alias_map,
        filenames=fnames,
        field_groups=o.field_groups,
        semantic_types=o.semantic_types,
        dedup_key=o.dedup_key,
        required_fields=o.required_fields,
        coalesce=o.coalesce,
        drop_invalid_key=o.drop_invalid_key,
        trim=o.trim,
    )
    summary_out = MergeSummaryOut(**summary.__dict__)

    if body.dry_run:
        preview = clean.head(30).to_dicts()
        return MergeRunOut(summary=summary_out, preview=preview)

    # Persist rejected rows for the audit download.
    rejected.write_csv(sdir / "rejected.csv")

    out_name = "merged.parquet"
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO uploaded_files (filename, filepath, rows, cols) VALUES (?,?,0,0)",
        (out_name, ""),
    )
    file_id = conn.execute(
        "SELECT file_id FROM uploaded_files WHERE rowid=?", (cur.lastrowid,)
    ).fetchone()[0]
    dest = UPLOADS_DIR / f"{file_id}_{out_name}"
    clean.write_parquet(dest)
    rows, cols = clean.shape
    conn.execute(
        "UPDATE uploaded_files SET filepath=?, rows=?, cols=? WHERE file_id=?",
        (str(dest), rows, cols, file_id),
    )
    conn.commit()
    conn.close()

    cols_info = [ColumnInfo(name=c, dtype=str(clean[c].dtype)) for c in clean.columns]
    return MergeRunOut(
        summary=summary_out,
        dataset=DatasetInfo(file_id=file_id, filename=out_name,
                            rows=rows, cols=cols, columns=cols_info),
        rejected_url=f"/api/ml/merge/{body.session_id}/rejected.csv",
    )
```

Note: the alias map lives on `body.alias_map` (top-level of `MergeRunIn`), not
inside `body.options`. The wizard sends `{}` for it (unification is driven by
`field_groups` instead), but the param is kept for API compatibility.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "merge_run" -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_merge.py
git commit -m "feat(merge): /merge/run new options + dry_run preview + rejected persistence"
```

---

### Task C3: `GET /merge/{session_id}/rejected.csv`

**Files:**
- Modify: `backend/routers/ml.py` (add route next to `merge_delete` ~565)
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing test** — append to `backend/tests/test_merge.py`:

```python
def test_merge_rejected_csv_download(client):
    # CSV_B's 0900000000 is fine; craft a file with an invalid phone to reject.
    csv_bad = b"Phone,Name\n0987654321,Alice\n12,Bad\n"
    stage = client.post(
        "/api/ml/merge/stage",
        files=[("files", ("c.csv", io.BytesIO(csv_bad), "text/csv"))],
    ).json()
    sid = stage["session_id"]
    run = client.post("/api/ml/merge/run", json={
        "session_id": sid,
        "selected_fields": ["Phone", "Name"],
        "options": {"dedup_key": "Phone", "semantic_types": {"Phone": "phone"},
                    "drop_invalid_key": True},
        "dry_run": False,
    })
    assert run.json()["summary"]["null_or_wrong"] == 1
    rej = client.get(f"/api/ml/merge/{sid}/rejected.csv")
    assert rej.status_code == 200
    assert rej.headers["content-type"].startswith("text/csv")
    assert b"Bad" in rej.content


def test_merge_rejected_csv_missing_is_404(client):
    assert client.get("/api/ml/merge/nope/rejected.csv").status_code == 404
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k "rejected_csv" -q`
Expected: FAIL — 404 for the valid session (route does not exist yet).

- [ ] **Step 3: Add the route** — in `backend/routers/ml.py`, immediately after
the `merge_delete` function (~line 569), add:

```python
@router.get("/merge/{session_id}/rejected.csv")
def merge_rejected(session_id: str):
    path = MERGE_SESSIONS_DIR / session_id / "rejected.csv"
    if not path.exists():
        raise HTTPException(404, "No rejected rows for this session")
    return Response(
        content=path.read_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="rejected.csv"'},
    )
```

(`Response` is already imported on line 16.)

- [ ] **Step 4: Run to verify it passes, then run the whole merge suite**

Run: `cd backend ; uv run pytest tests/test_merge.py -q`
Expected: PASS (all merge tests green — engine + endpoints + notebook fixture).

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_merge.py
git commit -m "feat(merge): GET /merge/{sid}/rejected.csv audit download"
```

---

# Phase D — Frontend types + API client

### Task D1: extend `types.ts`

**Files:**
- Modify: `frontend/src/types.ts` (Merge block, lines ~277-310)

- [ ] **Step 1: Replace the `// ─── ML Merge ───` block** (from
`export interface MergeFileSchema` through `export interface MergeRunResult`)
with:

```ts
// ─── ML Merge ─────────────────────────────────────────────────────────────────

export type SemanticType = 'phone' | 'email' | 'date' | 'number' | 'category' | 'text'

export interface MergeFileSchema {
  filename: string
  fields: string[]
}

export interface ColumnProfile {
  file: string
  name: string
  norm: string
  inferred_type: SemanticType
  confidence: number
  samples: string[]
  non_null: number
  distinct: number
  fill_rate: number
}

export interface FieldGroupSuggestion {
  canonical: string
  members: string[]
  inferred_type: SemanticType
  confidence: number
  reason: 'name' | 'type' | 'name+type'
}

export interface MergeStageResult {
  session_id: string
  files: MergeFileSchema[]
  common_fields: string[]
  all_fields: string[]
  profiles: ColumnProfile[]
  suggestions: FieldGroupSuggestion[]
}

export interface MergeOptions {
  dedup_key: string | null
  drop_invalid_key: boolean
  trim: boolean
  semantic_types: Record<string, SemanticType>
  field_groups: Record<string, string[]>
  required_fields: string[]
  coalesce: boolean
}

export interface MergeSummary {
  total_raw: number
  valid_format: number
  null_or_wrong: number
  distinct: number
  dup_removed_clean: number
  dup_removed_raw: number
  complete: number
  incomplete: number
  rejected: number
  per_field_fill_rate: Record<string, number>
  per_file_contribution: Record<string, number>
}

export interface MergeRunResult {
  summary: MergeSummary
  dataset?: DatasetInfo
  preview?: Record<string, string | null>[]
  rejected_url?: string
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend ; npx tsc -b`
Expected: errors only in `api/ml.ts` / old merge components that still use the
old shape (fixed in D2 / F1). No errors **inside** `types.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts
git commit -m "feat(merge): frontend types — profiles, suggestions, extended options/summary"
```

---

### Task D2: extend `api/ml.ts`

**Files:**
- Modify: `frontend/src/api/ml.ts` (`runMerge` ~265-274; add `downloadRejected`)

- [ ] **Step 1: Replace `runMerge`** (lines ~265-274) with a version that takes
the new options and a `dryRun` flag:

```ts
export async function runMerge(
  sessionId: string, selectedFields: string[],
  aliasMap: Record<string, string>, options: MergeOptions, dryRun = false,
): Promise<MergeRunResult> {
  const { data } = await client.post<MergeRunResult>('/ml/merge/run', {
    session_id: sessionId, selected_fields: selectedFields,
    alias_map: aliasMap, options, dry_run: dryRun,
  }, { timeout: 120_000 })
  return data
}
```

- [ ] **Step 2: Add `downloadRejected`** after `deleteMergeSession` (~line 278):

```ts
export async function downloadRejected(sessionId: string): Promise<void> {
  const { data } = await client.get(`/ml/merge/${sessionId}/rejected.csv`, { responseType: 'blob' })
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: 'text/csv' }))
  const a = document.createElement('a'); a.href = url; a.download = 'rejected.csv'; a.click()
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend ; npx tsc -b`
Expected: remaining errors only in the old `MlMergeView`/`MlMergeChips`/
`MlMergeSummary` (deleted in F1). `api/ml.ts` itself compiles.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/ml.ts
git commit -m "feat(merge): api client — runMerge dry_run + downloadRejected"
```

---

# Phase E — Frontend wizard + step components

> All components live in `frontend/src/components/ml/merge/`. UI strings are
> Vietnamese inline (matching the old `MlMergeView` convention; `MSG` is reserved
> for errors/empty-states). Verification for every Phase E task is
> `cd frontend ; npx tsc -b` (the component compiles even before it is wired in,
> because `MergeWizard` — built last — imports them). To get a clean tsc before
> `MergeWizard` exists, **build E1–E6 then E7 in order**; tsc on an unimported
> component still type-checks it.

### Task E1: `MergeStepUpload.tsx` (B1)

**Files:**
- Create: `frontend/src/components/ml/merge/MergeStepUpload.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { X } from 'lucide-react'
import type { MergeStageResult } from '../../../types'
import MlMergeDropzone from '../MlMergeDropzone'

interface Props {
  stage: MergeStageResult | null
  busy: boolean
  onFiles: (files: File[]) => void
  onRemove: (filename: string) => void
  onNext: () => void
}

export default function MergeStepUpload({ stage, busy, onFiles, onRemove, onNext }: Props) {
  const files = stage?.files ?? []
  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">
        Tải lên nhiều file (CSV/XLSX) lệch schema. Công cụ sẽ đọc giá trị, đoán loại
        từng cột và gợi ý gộp các cột cùng loại nhưng khác tên.
      </p>

      <MlMergeDropzone onFiles={onFiles} busy={busy} />

      {files.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-wide text-gray-600">
            {files.length} file đã tải
          </p>
          {files.map(f => (
            <div key={f.filename}
              className="flex items-center justify-between gap-2 rounded-md bg-white/5 border border-white/5 px-3 py-2">
              <span className="text-xs text-gray-200 truncate">{f.filename}</span>
              <span className="text-[10px] text-gray-500 flex-shrink-0">{f.fields.length} cột</span>
              <button onClick={() => onRemove(f.filename)} title="Bỏ file"
                className="text-gray-500 hover:text-danger flex-shrink-0">
                <X size={13} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-end">
        <button onClick={onNext} disabled={busy || files.length === 0}
          className="rounded-md bg-data px-4 py-2 text-xs font-medium text-black disabled:opacity-40">
          Tiếp tục →
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend ; npx tsc -b`
Expected: no error in `MergeStepUpload.tsx` (only pre-existing old-component errors remain).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/merge/MergeStepUpload.tsx
git commit -m "feat(merge): B1 upload step (dropzone + staged-file list)"
```

---

### Task E2: `MergeFieldGroups.tsx` (B2 — common / per-file groups)

**Files:**
- Create: `frontend/src/components/ml/merge/MergeFieldGroups.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { MergeStageResult } from '../../../types'

interface Props {
  stage: MergeStageResult
  included: string[]
  onToggle: (field: string) => void
}

// Count how many files contain a field (by raw name) + which files.
function filesFor(stage: MergeStageResult, field: string): string[] {
  return stage.files.filter(f => f.fields.includes(field)).map(f => f.filename)
}

export default function MergeFieldGroups({ stage, included, onToggle }: Props) {
  const n = stage.files.length
  const common = new Set(stage.common_fields)
  const commonFields = stage.all_fields.filter(f => common.has(f))
  const individual = stage.all_fields.filter(f => !common.has(f))

  const Row = ({ field }: { field: string }) => {
    const owners = filesFor(stage, field)
    return (
      <label title={owners.join(', ')}
        className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-white/5 cursor-pointer">
        <input type="checkbox" checked={included.includes(field)} onChange={() => onToggle(field)} />
        <span className="text-xs text-gray-200 truncate flex-1">{field}</span>
        <span className="text-[10px] text-gray-500 flex-shrink-0">{owners.length}/{n} file</span>
      </label>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">
          Field chung (mọi file)
        </p>
        <div className="rounded-lg border border-white/5 bg-white/5 p-1">
          {commonFields.length === 0
            ? <p className="text-[11px] text-gray-600 px-2 py-2">Không có field chung</p>
            : commonFields.map(f => <Row key={f} field={f} />)}
        </div>
      </div>
      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">
          Field riêng lẻ
        </p>
        <div className="rounded-lg border border-white/5 bg-white/5 p-1 max-h-72 overflow-y-auto">
          {individual.length === 0
            ? <p className="text-[11px] text-gray-600 px-2 py-2">Tất cả field đều chung</p>
            : individual.map(f => <Row key={f} field={f} />)}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend ; npx tsc -b`
Expected: no error in `MergeFieldGroups.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/merge/MergeFieldGroups.tsx
git commit -m "feat(merge): B2 common/per-file field groups with provenance badges"
```

---

### Task E3: `MergeUnifySuggestions.tsx` (B2 — suggestion cards)

**Files:**
- Create: `frontend/src/components/ml/merge/MergeUnifySuggestions.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { Check, Split, Sparkles } from 'lucide-react'
import type { FieldGroupSuggestion } from '../../../types'

interface Props {
  suggestions: FieldGroupSuggestion[]
  accepted: Record<string, string[]>   // canonical -> members (accepted groups)
  onAccept: (s: FieldGroupSuggestion) => void
  onSplit: (canonical: string) => void
}

const REASON_LABEL: Record<string, string> = {
  type: 'gộp theo loại giá trị',
  name: 'gộp theo tên cột',
  'name+type': 'tên + loại giống nhau',
}

export default function MergeUnifySuggestions({ suggestions, accepted, onAccept, onSplit }: Props) {
  if (suggestions.length === 0) {
    return <p className="text-[11px] text-gray-600">Không có gợi ý gộp cột.</p>
  }
  return (
    <div className="space-y-2">
      <p className="text-[11px] uppercase tracking-wide text-gray-600 flex items-center gap-1">
        <Sparkles size={12} /> Gợi ý gộp cột
      </p>
      {suggestions.map(s => {
        const isAccepted = !!accepted[s.canonical]
        return (
          <div key={s.canonical}
            className="rounded-lg border border-white/10 bg-white/5 p-2.5 space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-gray-100">{s.canonical}</span>
              <span className="badge bg-analytics/15 text-analytics">{s.inferred_type}</span>
            </div>
            <p className="text-[11px] text-gray-400">
              {s.members.join(' · ')} — {REASON_LABEL[s.reason] ?? s.reason}
              <span className="text-gray-600"> ({Math.round(s.confidence * 100)}%)</span>
            </p>
            <div className="flex gap-1.5">
              {isAccepted ? (
                <button onClick={() => onSplit(s.canonical)}
                  className="flex items-center gap-1 rounded bg-white/5 px-2 py-1 text-[11px] text-gray-300 hover:bg-white/10">
                  <Split size={11} /> Tách lại
                </button>
              ) : (
                <button onClick={() => onAccept(s)}
                  className="flex items-center gap-1 rounded bg-data/20 px-2 py-1 text-[11px] text-data hover:bg-data/30">
                  <Check size={11} /> Đồng ý gộp
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend ; npx tsc -b`
Expected: no error in `MergeUnifySuggestions.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/merge/MergeUnifySuggestions.tsx
git commit -m "feat(merge): B2 unify-suggestion cards (accept/split)"
```

---

### Task E4: `MergeTypePicker.tsx` (B2 — per-canonical type confirm + samples)

**Files:**
- Create: `frontend/src/components/ml/merge/MergeTypePicker.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { SemanticType, ColumnProfile } from '../../../types'

const TYPES: SemanticType[] = ['phone', 'email', 'date', 'number', 'category', 'text']

interface Props {
  included: string[]                          // canonical fields user is keeping
  semanticTypes: Record<string, SemanticType>
  samplesFor: (field: string) => string[]     // resolved from profiles
  onChange: (field: string, t: SemanticType) => void
}

export default function MergeTypePicker({ included, semanticTypes, samplesFor, onChange }: Props) {
  if (included.length === 0) {
    return <p className="text-[11px] text-gray-600">Chọn field để xác nhận loại dữ liệu.</p>
  }
  return (
    <div className="space-y-2">
      <p className="text-[11px] uppercase tracking-wide text-gray-600">
        Xác nhận loại dữ liệu
      </p>
      {included.map(f => {
        const samples = samplesFor(f).slice(0, 4)
        return (
          <div key={f} className="rounded-lg border border-white/5 bg-white/5 p-2.5">
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-xs font-medium text-gray-100 truncate">{f}</span>
              <select
                value={semanticTypes[f] ?? 'text'}
                onChange={e => onChange(f, e.target.value as SemanticType)}
                className="input-base text-[11px] py-1 px-2 w-28">
                {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            {samples.length > 0 && (
              <p className="text-[10px] text-gray-500 truncate">vd: {samples.join(' · ')}</p>
            )}
          </div>
        )
      })}
    </div>
  )
}

export type { ColumnProfile }
```

- [ ] **Step 2: Type-check**

Run: `cd frontend ; npx tsc -b`
Expected: no error in `MergeTypePicker.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/merge/MergeTypePicker.tsx
git commit -m "feat(merge): B2 per-canonical semantic-type confirm + value samples"
```

---

### Task E5: `MergeCleanStep.tsx` (B3 — key, required fields, toggles)

**Files:**
- Create: `frontend/src/components/ml/merge/MergeCleanStep.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { SemanticType } from '../../../types'

interface Props {
  included: string[]
  semanticTypes: Record<string, SemanticType>
  dedupKey: string | null
  requiredFields: string[]
  dropInvalidKey: boolean
  coalesce: boolean
  onDedupKey: (k: string | null) => void
  onToggleRequired: (f: string) => void
  onDropInvalidKey: (v: boolean) => void
  onCoalesce: (v: boolean) => void
}

export default function MergeCleanStep({
  included, semanticTypes, dedupKey, requiredFields,
  dropInvalidKey, coalesce, onDedupKey, onToggleRequired,
  onDropInvalidKey, onCoalesce,
}: Props) {
  return (
    <div className="space-y-4 max-w-xl">
      <div>
        <label className="block text-[11px] uppercase tracking-wide text-gray-600 mb-1">
          Khóa loại trùng (dedup key)
        </label>
        <select
          value={dedupKey ?? ''}
          onChange={e => onDedupKey(e.target.value || null)}
          className="input-base text-xs py-1.5">
          <option value="">— không loại trùng —</option>
          {included.map(f => (
            <option key={f} value={f}>{f} ({semanticTypes[f] ?? 'text'})</option>
          ))}
        </select>
        <p className="text-[10px] text-gray-600 mt-1">
          Các dòng cùng khóa sẽ được gộp lại, lấy giá trị đầy đủ nhất ở mỗi cột.
        </p>
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1">
          Field bắt buộc (để tính “đủ thông tin”)
        </p>
        <div className="rounded-lg border border-white/5 bg-white/5 p-1">
          {included.map(f => (
            <label key={f} className="flex items-center gap-2 px-2 py-1.5 hover:bg-white/5 rounded cursor-pointer">
              <input type="checkbox" checked={requiredFields.includes(f)}
                onChange={() => onToggleRequired(f)} />
              <span className="text-xs text-gray-200">{f}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-xs text-gray-400">
          <input type="checkbox" checked={coalesce} onChange={e => onCoalesce(e.target.checked)} />
          Gộp dòng trùng, lấp ô trống từ bản trùng (coalesce)
        </label>
        <label className="flex items-center gap-2 text-xs text-gray-400">
          <input type="checkbox" checked={dropInvalidKey} onChange={e => onDropInvalidKey(e.target.checked)} />
          Bỏ dòng có khóa rỗng / sai định dạng
        </label>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend ; npx tsc -b`
Expected: no error in `MergeCleanStep.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/merge/MergeCleanStep.tsx
git commit -m "feat(merge): B3 clean & dedup controls (key, required fields, toggles)"
```

---

### Task E6: `MergePreview.tsx` + `MergeOutcome.tsx` (B4)

**Files:**
- Create: `frontend/src/components/ml/merge/MergePreview.tsx`
- Create: `frontend/src/components/ml/merge/MergeOutcome.tsx`

- [ ] **Step 1: Create `MergePreview.tsx`**

```tsx
interface Props {
  rows: Record<string, string | null>[]
}

export default function MergePreview({ rows }: Props) {
  if (rows.length === 0) {
    return <p className="text-[11px] text-gray-600">Không có dòng nào để xem trước.</p>
  }
  const cols = Object.keys(rows[0])
  return (
    <div className="rounded-lg border border-white/5 overflow-auto max-h-72">
      <table className="w-full text-[11px]">
        <thead className="sticky top-0 bg-[#1a1a1a]">
          <tr>
            {cols.map(c => (
              <th key={c} className="text-left px-2.5 py-1.5 text-gray-400 font-medium border-b border-white/5">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-white/5">
              {cols.map(c => (
                <td key={c} className="px-2.5 py-1 text-gray-300 truncate max-w-[200px]">
                  {r[c] ?? <span className="text-gray-700">∅</span>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 2: Create `MergeOutcome.tsx`**

```tsx
import { Download, FileWarning } from 'lucide-react'
import type { MergeSummary } from '../../../types'

interface Props {
  summary: MergeSummary
  onDownloadRejected: () => void
}

function Metric({ label, value, hint, tone = 'default' }:
  { label: string; value: number; hint?: string; tone?: 'default' | 'good' | 'warn' }) {
  const color = tone === 'good' ? 'text-success' : tone === 'warn' ? 'text-amber-400' : 'text-white'
  return (
    <div className="rounded-lg bg-white/5 border border-white/5 px-3 py-2.5">
      <p className={`text-lg font-semibold ${color}`}>{value.toLocaleString('vi-VN')}</p>
      <p className="text-[11px] text-gray-400 leading-tight">{label}</p>
      {hint && <p className="text-[10px] text-gray-600 mt-0.5">{hint}</p>}
    </div>
  )
}

export default function MergeOutcome({ summary: s, onDownloadRejected }: Props) {
  const fill = Object.entries(s.per_field_fill_rate)
  const files = Object.entries(s.per_file_contribution)
  const maxContrib = Math.max(1, ...files.map(([, v]) => v))
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Metric label="Tổng thu thập" value={s.total_raw} />
        <Metric label="Hợp lệ định dạng" value={s.valid_format} tone="good" />
        <Metric label="Null / sai" value={s.null_or_wrong} tone="warn" />
        <Metric label="Distinct" value={s.distinct} />
        <Metric label="Trùng đã loại (sạch)" value={s.dup_removed_clean} hint="hợp lệ − distinct" />
        <Metric label="Trùng đã loại (thô)" value={s.dup_removed_raw} hint="tổng − distinct" />
        <Metric label="Đủ thông tin" value={s.complete} tone="good" />
        <Metric label="Thiếu thông tin" value={s.incomplete} tone="warn" />
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">Tỷ lệ điền theo cột</p>
        <div className="space-y-1">
          {fill.map(([col, rate]) => (
            <div key={col} className="flex items-center gap-2">
              <span className="text-[11px] text-gray-400 w-28 truncate">{col}</span>
              <div className="flex-1 h-2 rounded bg-white/5 overflow-hidden">
                <div className="h-full bg-data" style={{ width: `${Math.round(rate * 100)}%` }} />
              </div>
              <span className="text-[10px] text-gray-500 w-10 text-right">{Math.round(rate * 100)}%</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">Đóng góp theo file (dòng hợp lệ)</p>
        <div className="space-y-1">
          {files.map(([file, count]) => (
            <div key={file} className="flex items-center gap-2">
              <span className="text-[11px] text-gray-400 w-36 truncate" title={file}>{file}</span>
              <div className="flex-1 h-2 rounded bg-white/5 overflow-hidden">
                <div className="h-full bg-analytics" style={{ width: `${Math.round((count / maxContrib) * 100)}%` }} />
              </div>
              <span className="text-[10px] text-gray-500 w-12 text-right">{count.toLocaleString('vi-VN')}</span>
            </div>
          ))}
        </div>
      </div>

      {s.rejected > 0 && (
        <button onClick={onDownloadRejected}
          className="flex items-center gap-1.5 rounded-md bg-white/5 border border-white/10 px-3 py-2 text-xs text-amber-400 hover:bg-white/10">
          <FileWarning size={13} /> Tải bản bị loại ({s.rejected.toLocaleString('vi-VN')} dòng)
          <Download size={12} />
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend ; npx tsc -b`
Expected: no error in `MergePreview.tsx` / `MergeOutcome.tsx`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ml/merge/MergePreview.tsx frontend/src/components/ml/merge/MergeOutcome.tsx
git commit -m "feat(merge): B4 preview table + outcome (8 metrics, fill-rate, per-file, rejected export)"
```

---

### Task E7: `MergeWizard.tsx` (orchestrator)

**Files:**
- Create: `frontend/src/components/ml/merge/MergeWizard.tsx`

- [ ] **Step 1: Create the orchestrator**

```tsx
import { useMemo, useState } from 'react'
import type {
  DatasetInfo, MergeStageResult, MergeRunResult, SemanticType, FieldGroupSuggestion,
} from '../../../types'
import { stageMerge, runMerge, downloadRejected } from '../../../api/ml'
import MergeStepUpload from './MergeStepUpload'
import MergeFieldGroups from './MergeFieldGroups'
import MergeUnifySuggestions from './MergeUnifySuggestions'
import MergeTypePicker from './MergeTypePicker'
import MergeCleanStep from './MergeCleanStep'
import MergePreview from './MergePreview'
import MergeOutcome from './MergeOutcome'

interface Props { onDatasetCreated: (d: DatasetInfo) => void }

const STEPS = ['Tải file', 'Gộp & loại', 'Làm sạch', 'Xem & tạo']

function errMsg(e: unknown): string {
  return (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Có lỗi xảy ra'
}

export default function MergeWizard({ onDatasetCreated }: Props) {
  const [step, setStep]       = useState(1)
  const [stage, setStage]     = useState<MergeStageResult | null>(null)
  const [included, setIncluded] = useState<string[]>([])
  const [fieldGroups, setFieldGroups] = useState<Record<string, string[]>>({})
  const [semanticTypes, setSemanticTypes] = useState<Record<string, SemanticType>>({})
  const [dedupKey, setDedupKey] = useState<string | null>(null)
  const [requiredFields, setRequiredFields] = useState<string[]>([])
  const [dropInvalidKey, setDropInvalidKey] = useState(true)
  const [coalesce, setCoalesce] = useState(true)
  const [dry, setDry]         = useState<MergeRunResult | null>(null)
  const [busy, setBusy]       = useState(false)
  const [error, setError]     = useState('')

  // field name (raw or canonical) -> inferred type & samples, from profiles
  const profByName = useMemo(() => {
    const m: Record<string, { type: SemanticType; samples: string[] }> = {}
    stage?.profiles.forEach(p => {
      if (!m[p.name]) m[p.name] = { type: p.inferred_type, samples: p.samples }
    })
    return m
  }, [stage])

  function samplesFor(field: string): string[] {
    if (profByName[field]) return profByName[field].samples
    const members = fieldGroups[field]
    if (members) for (const mem of members) if (profByName[mem]) return profByName[mem].samples
    return []
  }

  async function handleFiles(files: File[]) {
    setBusy(true); setError('')
    try {
      const r = await stageMerge(files, stage?.session_id)
      setStage(r)
      setIncluded(r.common_fields)
      // seed semantic types from profiles (first profile per name wins)
      const st: Record<string, SemanticType> = {}
      r.profiles.forEach(p => { if (!st[p.name]) st[p.name] = p.inferred_type })
      setSemanticTypes(st)
    } catch (e) { setError(errMsg(e)) } finally { setBusy(false) }
  }

  function handleRemove(filename: string) {
    if (!stage) return
    setStage({ ...stage, files: stage.files.filter(f => f.filename !== filename) })
  }

  function toggleInclude(f: string) {
    setIncluded(s => s.includes(f) ? s.filter(x => x !== f) : [...s, f])
  }

  function acceptSuggestion(s: FieldGroupSuggestion) {
    setFieldGroups(g => ({ ...g, [s.canonical]: s.members }))
    setSemanticTypes(t => ({ ...t, [s.canonical]: s.inferred_type }))
    setIncluded(inc => {
      const without = inc.filter(f => !s.members.includes(f))
      return without.includes(s.canonical) ? without : [...without, s.canonical]
    })
  }

  function splitSuggestion(canonical: string) {
    setFieldGroups(g => { const n = { ...g }; delete n[canonical]; return n })
    setIncluded(inc => inc.filter(f => f !== canonical))
  }

  function toggleRequired(f: string) {
    setRequiredFields(s => s.includes(f) ? s.filter(x => x !== f) : [...s, f])
  }

  function buildOptions() {
    return {
      dedup_key: dedupKey, drop_invalid_key: dropInvalidKey, trim: true,
      semantic_types: semanticTypes, field_groups: fieldGroups,
      required_fields: requiredFields, coalesce,
    }
  }

  async function runDry() {
    if (!stage) return
    setBusy(true); setError('')
    try {
      const r = await runMerge(stage.session_id, included, {}, buildOptions(), true)
      setDry(r)
    } catch (e) { setError(errMsg(e)) } finally { setBusy(false) }
  }

  async function createDataset() {
    if (!stage) return
    setBusy(true); setError('')
    try {
      const r = await runMerge(stage.session_id, included, {}, buildOptions(), false)
      if (r.dataset) onDatasetCreated(r.dataset)
    } catch (e) { setError(errMsg(e)) } finally { setBusy(false) }
  }

  function goTo(next: number) {
    setError('')
    if (next === 4) { setStep(4); runDry() } else setStep(next)
  }

  return (
    <div className="p-4 max-w-4xl space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-gray-200 mb-1">Combine file</h2>
        <div className="flex gap-1.5">
          {STEPS.map((label, i) => (
            <div key={label}
              className={`flex-1 text-center text-[11px] py-1 rounded ${
                step === i + 1 ? 'bg-data/20 text-data' : 'bg-white/5 text-gray-500'}`}>
              {i + 1}. {label}
            </div>
          ))}
        </div>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {step === 1 && (
        <MergeStepUpload stage={stage} busy={busy}
          onFiles={handleFiles} onRemove={handleRemove} onNext={() => goTo(2)} />
      )}

      {step === 2 && stage && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <MergeFieldGroups stage={stage} included={included} onToggle={toggleInclude} />
            <MergeUnifySuggestions
              suggestions={stage.suggestions} accepted={fieldGroups}
              onAccept={acceptSuggestion} onSplit={splitSuggestion} />
          </div>
          <MergeTypePicker included={included} semanticTypes={semanticTypes}
            samplesFor={samplesFor}
            onChange={(f, t) => setSemanticTypes(s => ({ ...s, [f]: t }))} />
          <div className="flex justify-between">
            <button onClick={() => goTo(1)} className="text-xs text-gray-500 hover:text-gray-300">← Quay lại</button>
            <button onClick={() => goTo(3)} disabled={included.length === 0}
              className="rounded-md bg-data px-4 py-2 text-xs font-medium text-black disabled:opacity-40">
              Tiếp tục →
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <MergeCleanStep included={included} semanticTypes={semanticTypes}
            dedupKey={dedupKey} requiredFields={requiredFields}
            dropInvalidKey={dropInvalidKey} coalesce={coalesce}
            onDedupKey={setDedupKey} onToggleRequired={toggleRequired}
            onDropInvalidKey={setDropInvalidKey} onCoalesce={setCoalesce} />
          <div className="flex justify-between">
            <button onClick={() => goTo(2)} className="text-xs text-gray-500 hover:text-gray-300">← Quay lại</button>
            <button onClick={() => goTo(4)}
              className="rounded-md bg-data px-4 py-2 text-xs font-medium text-black">
              Xem trước →
            </button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="space-y-4">
          {busy && <p className="text-xs text-gray-500">Đang tính toán…</p>}
          {dry && (
            <>
              <MergeOutcome summary={dry.summary}
                onDownloadRejected={() => stage && downloadRejected(stage.session_id)} />
              <div>
                <p className="text-[11px] uppercase tracking-wide text-gray-600 mb-1.5">Xem trước (30 dòng)</p>
                <MergePreview rows={dry.preview ?? []} />
              </div>
            </>
          )}
          <div className="flex justify-between">
            <button onClick={() => goTo(3)} className="text-xs text-gray-500 hover:text-gray-300">← Quay lại</button>
            <button onClick={createDataset} disabled={busy || !dry}
              className="rounded-md bg-success px-4 py-2 text-xs font-medium text-black disabled:opacity-40">
              {busy ? 'Đang tạo…' : 'Tạo dataset'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
```

Note: the rejected download in step 4 uses the session id (not `rejected_url`)
because the audit file is only written on the **non-dry** run; offer it after
"Tạo dataset" or rely on the metric card — if a user clicks before creating, the
backend returns 404 and `downloadRejected` no-ops on the blob. (Acceptable for
MVP; the button is primarily meaningful post-create.)

- [ ] **Step 2: Type-check**

Run: `cd frontend ; npx tsc -b`
Expected: no error in `MergeWizard.tsx` (old `MlMergeView` errors may still show
until F1).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/merge/MergeWizard.tsx
git commit -m "feat(merge): MergeWizard orchestrator (4-step state machine + dry-run preview)"
```

---

# Phase F — Wire-up + cleanup

### Task F1: rename/reorder tab, swap in `MergeWizard`, delete old components

**Files:**
- Modify: `frontend/src/components/ml/MlResultTabs.tsx`
- Delete: `frontend/src/components/ml/MlMergeView.tsx`,
  `MlMergeChips.tsx`, `MlMergeSummary.tsx`

- [ ] **Step 1: Update `MlResultTabs.tsx`** — apply these three edits:

(a) Replace the import line (line 8):

```tsx
import MlMergeView    from './MlMergeView'
```
with:
```tsx
import MergeWizard    from './merge/MergeWizard'
```

(b) Reorder + rename the `TABS` array (lines 25-33) so `merge` is labelled
`'Combine file'` and sits just before `eda`:

```tsx
const TABS: { key: Tab; label: string; Icon: React.ElementType }[] = [
  { key: 'table',    label: 'Table',        Icon: Table        },
  { key: 'charts',   label: 'Charts',       Icon: BarChart2    },
  { key: 'stats',    label: 'Stats',        Icon: FlaskConical },
  { key: 'forecast', label: 'Forecast',     Icon: TrendingUp   },
  { key: 'cohort',   label: 'Cohort',       Icon: Users        },
  { key: 'merge',    label: 'Combine file', Icon: Combine      },
  { key: 'eda',      label: 'Auto-EDA',     Icon: Telescope    },
]
```

(c) Replace the merge render (line 105):

```tsx
          <MlMergeView onDatasetCreated={onDatasetCreated} />
```
with:
```tsx
          <MergeWizard onDatasetCreated={onDatasetCreated} />
```

- [ ] **Step 2: Delete the absorbed components**

```bash
git rm frontend/src/components/ml/MlMergeView.tsx frontend/src/components/ml/MlMergeChips.tsx frontend/src/components/ml/MlMergeSummary.tsx
```

- [ ] **Step 3: Full frontend build (the real gate)**

Run: `cd frontend ; npm run build`
Expected: `✓ built in …s`, exit 0. No TypeScript errors. (A pre-existing
chunk-size >500 kB warning for SqlSandbox/vsc-dark-plus is unrelated and fine.)

If tsc reports an unused import (e.g. `Upload`/`Combine` in `MlResultTabs.tsx`
still referenced by `EmptyStudio`), leave `Combine` imported (still used by the
tab) — only remove an import the compiler flags as unused.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ml/MlResultTabs.tsx
git commit -m "feat(merge): rename tab to Combine file (before Auto-EDA), wire MergeWizard, remove old merge UI"
```

---

# Phase G — Full verification + delivery

### Task G1: backend suite, frontend build, FF-merge to MAIN (no push)

**Files:** none (verification + delivery)

- [ ] **Step 1: Run the entire backend suite**

Run: `cd backend ; uv run pytest -q`
Expected: the merge suite is fully green. Total pass count rises by the new
engine/endpoint tests. Pre-existing unrelated failures
(`test_sql_sandbox.py` — the vina_brew fixture gap noted in project memory) may
remain; confirm **no new** failures originate from `test_merge.py` or from the
`align_and_merge`/`MergeSummary` rename rippling into other modules. If any other
test imports `MergeSummary` old fields, fix that consumer.

- [ ] **Step 2: Confirm the frontend build is clean**

Run: `cd frontend ; npm run build`
Expected: exit 0, `✓ built`.

- [ ] **Step 3: Deliver to MAIN via fast-forward merge (NO push)**

The MAIN working tree is `D:\assitant_tools\tools_performance\08_Projects\leonie`
and runs the dev server. FF-merge the worktree branch into local `master`:

```bash
git -C "D:/assitant_tools/tools_performance/08_Projects/leonie" merge --ff-only claude/beautiful-curran-085809
```

Expected: `Fast-forward` (works because `master` has not diverged from the
branch base). If git refuses (master moved), STOP and report — do not force.

- [ ] **Step 4: Confirm MAIN build once more (node_modules lives in MAIN)**

Run: `cd "D:/assitant_tools/tools_performance/08_Projects/leonie/frontend" ; npm run build`
Expected: exit 0, `✓ built`.

- [ ] **Step 5: Do NOT push.** Leave `master` local. Report the delivered commit
range and that nothing was pushed (per spec §12 — secrets in `master` history).

---

## Notes on spec coverage

- **§5 value-aware engine** → Tasks A1–A3 (`normalize_value`/`is_valid`,
  `profile_columns` + inference, `suggest_groups`).
- **§6 cleaning table** → A1 `normalize_value`/`is_valid` per type; the phone
  branch reuses `clean_phone` unchanged (notebook phones reproduce).
- **§7 merge/dedup/metrics** → B1 (`align_and_merge` v2 + rich `MergeSummary`,
  coalesce, per-field/per-file) and B2 (exact gold numbers).
- **§4.2 / §9 endpoints** → C1 (stage profiles+suggestions), C2 (run options +
  `dry_run` + rejected persistence), C3 (rejected.csv).
- **§4.3 / §8 wizard** → E1–E7 + the step components; **§10 tab** → F1.
- **§11 testing** → backend pytest throughout; frontend `npm run build` (no JS
  unit runner in this repo).
- **§12 delivery** → G1 (FF-merge to local `master`, no push).
- **Deviations documented:** (1) `align_and_merge` gains an optional `filenames`
  param to source `per_file_contribution` (spec §4.1 omitted it but §7 requires
  it); (2) `profile_columns` imported aliased to avoid the existing
  `analytics.eda.profile_columns` import; (3) number cleaning treats `.`/`,` as
  thousands separators per the literal §6 rule (decimals not preserved — MVP).
- **V2 deferred (not in this plan):** Jaccard value-overlap for generic types,
  composite/keep-latest dedup, extra semantic types, saved templates.
