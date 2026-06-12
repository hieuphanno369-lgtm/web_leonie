"""Pure helpers for the ML Studio Auto-EDA feature (unit-testable, no FastAPI)."""
from __future__ import annotations

import numpy as np
import polars as pl

_DATE_HINTS = ("date", "time", "ngay", "thang", "ngày", "tháng")


def infer_role(name: str, s: pl.Series, nunq: int, n: int, is_num: bool) -> str:
    low = name.lower()
    if s.dtype in (pl.Date, pl.Datetime) or any(h in low for h in _DATE_HINTS):
        return "date"
    if "id" in low and nunq > n * 0.9:
        return "id"
    if nunq <= 2:
        return "flag"
    if is_num:
        return "metric"
    # A fully-unique NON-numeric column (a code/key) reads as an id; a fully-unique
    # numeric column is a measure ("amount"), so this check comes after numeric→metric.
    if n > 0 and nunq == n:
        return "id"
    return "dimension"


def profile_columns(df: pl.DataFrame) -> list[dict]:
    n = df.height
    out: list[dict] = []
    for name in df.columns:
        s = df[name]
        nulls = int(s.null_count())
        nunq = int(s.n_unique())
        is_num = s.dtype.is_numeric()
        col = {
            "name": name,
            "dtype": str(s.dtype),
            "role": infer_role(name, s, nunq, n, is_num),
            "cardinality": nunq,
            "null_pct": round(100.0 * nulls / n, 2) if n else 0.0,
            "is_constant": nunq <= 1,
            "samples": [str(v) for v in s.drop_nulls().head(3).to_list()],
        }
        if is_num and s.drop_nulls().len():
            col["min"] = float(s.min())
            col["max"] = float(s.max())
        out.append(col)
    return out


def correlation_matrix(df: pl.DataFrame, max_cols: int = 12) -> dict:
    """Pairwise Pearson correlation over numeric columns.

    Excludes all-null and constant columns. Returns columns/matrix (with None for
    pairs lacking >=3 overlapping non-null rows) and the excluded-columns note.
    """
    numeric = [c for c in df.columns if df[c].dtype.is_numeric()]
    cols: list[str] = []
    excluded: list[dict] = []
    series: dict[str, np.ndarray] = {}
    for c in numeric[:max_cols]:
        s = df[c]
        if s.null_count() == len(s):
            excluded.append({"name": c, "reason": "all_null"})
            continue
        if s.n_unique() <= 1:
            excluded.append({"name": c, "reason": "constant"})
            continue
        cols.append(c)
        series[c] = s.cast(pl.Float64).to_numpy()

    size = len(cols)
    matrix: list[list[float | None]] = [[None] * size for _ in range(size)]
    for i in range(size):
        for j in range(i, size):
            if i == j:
                matrix[i][j] = 1.0
                continue
            a, b = series[cols[i]], series[cols[j]]
            mask = ~(np.isnan(a) | np.isnan(b))
            if int(mask.sum()) < 3:
                r = None
            else:
                with np.errstate(invalid="ignore"):
                    r = float(np.corrcoef(a[mask], b[mask])[0, 1])
                if np.isnan(r):
                    r = None
            matrix[i][j] = r
            matrix[j][i] = r
    return {"columns": cols, "matrix": matrix, "excluded_columns": excluded}


def _skew(arr: np.ndarray) -> float:
    arr = arr[~np.isnan(arr)]
    if arr.size < 3:
        return 0.0
    m, sd = arr.mean(), arr.std()
    if sd == 0:
        return 0.0
    return float((((arr - m) / sd) ** 3).mean())


def _bins(arr: np.ndarray, n_bins: int = 20) -> list[dict]:
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return []
    counts, edges = np.histogram(arr, bins=n_bins)
    return [
        {"x0": float(edges[i]), "x1": float(edges[i + 1]), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def numeric_distributions(
    df: pl.DataFrame, cols: list[str], log_transform: str = "auto", n_bins: int = 20,
) -> list[dict]:
    """Histogram + summary stats per numeric column. log_transform: auto|on|off."""
    out: list[dict] = []
    for c in cols:
        if c not in df.columns or not df[c].dtype.is_numeric():
            continue
        arr = df[c].cast(pl.Float64).to_numpy()
        clean = arr[~np.isnan(arr)]
        if clean.size == 0:
            continue
        skew = _skew(arr)
        want_log = log_transform == "on" or (log_transform == "auto" and skew > 1.0)
        log_applied = bool(want_log and clean.min() >= 0)
        bins_arr = np.log1p(arr) if log_applied else arr
        out.append({
            "column": c,
            "bins": _bins(bins_arr, n_bins),
            "skew": round(skew, 3),
            "log_applied": log_applied,
            "mean": float(clean.mean()),
            "median": float(np.median(clean)),
            "std": float(clean.std()),
            "min": float(clean.min()),
            "max": float(clean.max()),
        })
    return out


def segment_breakdown(
    df: pl.DataFrame, seg_col: str, metric_cols: list[str],
    top_n: int = 10, sample_n: int = 2000,
) -> dict:
    """Group-by `seg_col`: count + per-metric sum/mean for the top_n biggest groups.

    Scatter uses the first two metrics; points sampled to <= sample_n.
    """
    metrics = [m for m in metric_cols if m in df.columns and df[m].dtype.is_numeric()]
    aggs = [pl.len().alias("count")]
    for m in metrics:
        aggs.append(pl.col(m).sum().alias(f"{m}_sum"))
        aggs.append(pl.col(m).mean().alias(f"{m}_mean"))
    grouped = df.group_by(seg_col).agg(aggs).sort("count", descending=True).head(top_n)

    table: list[dict] = []
    for row in grouped.iter_rows(named=True):
        rec = {"segment": str(row[seg_col]), "count": int(row["count"])}
        for m in metrics:
            rec[f"{m}_sum"] = float(row[f"{m}_sum"]) if row[f"{m}_sum"] is not None else 0.0
            rec[f"{m}_mean"] = float(row[f"{m}_mean"]) if row[f"{m}_mean"] is not None else 0.0
        table.append(rec)

    scatter: dict = {"x_col": None, "y_col": None, "points": []}
    if len(metrics) >= 2:
        xc, yc = metrics[0], metrics[1]
        sub = df.select([seg_col, xc, yc]).drop_nulls()
        if sub.height > sample_n:
            sub = sub.sample(n=sample_n, seed=42)
        scatter = {
            "x_col": xc, "y_col": yc,
            "points": [
                {"x": float(r[xc]), "y": float(r[yc]), "group": str(r[seg_col])}
                for r in sub.iter_rows(named=True)
            ],
        }
    return {"table": table, "scatter": scatter}


def derive_rule_insights(
    profile: list[dict], corr: dict, distributions: list[dict],
    segments: dict, total_rows: int, max_insights: int = 5,
) -> list[dict]:
    """Rule-based Finding -> So-what -> Action insights (AI-free fallback)."""
    out: list[dict] = []

    # 1. Highest-null column.
    nullable = [c for c in profile if c.get("null_pct", 0) > 0]
    if nullable:
        worst = max(nullable, key=lambda c: c["null_pct"])
        if worst["null_pct"] >= 20:
            out.append({
                "finding": f"Cột '{worst['name']}' thiếu {worst['null_pct']:.0f}% dữ liệu.",
                "so_what": "Phân tích/biểu đồ trên cột này dễ sai lệch, mẫu hữu dụng bị thu nhỏ.",
                "action": f"Bổ sung nguồn cho '{worst['name']}' hoặc loại khỏi báo cáo nếu không cứu được.",
                "severity": "high" if worst["null_pct"] >= 50 else "medium",
            })

    # 2. Strongest correlation pair.
    cols, mat = corr.get("columns", []), corr.get("matrix", [])
    best = None
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = mat[i][j]
            if r is None:
                continue
            if best is None or abs(r) > abs(best[2]):
                best = (cols[i], cols[j], r)
    if best and abs(best[2]) >= 0.7:
        direction = "cùng chiều" if best[2] > 0 else "ngược chiều"
        out.append({
            "finding": f"'{best[0]}' và '{best[1]}' tương quan {direction} mạnh (r={best[2]:.2f}).",
            "so_what": "Hai chỉ số gắn chặt — có thể trùng thông tin hoặc một bên dự báo bên kia.",
            "action": f"Dùng '{best[0]}' để giải thích/forecast '{best[1]}', tránh đếm trùng khi báo cáo.",
            "severity": "medium",
        })

    # 3. Most skewed metric.
    skewed = [d for d in distributions if abs(d.get("skew", 0)) >= 1.0]
    if skewed:
        s = max(skewed, key=lambda d: abs(d["skew"]))
        out.append({
            "finding": f"'{s['column']}' lệch mạnh (skew={s['skew']:.1f}); trung vị {s['median']:.0f} so với trung bình {s['mean']:.0f}.",
            "so_what": "Vài giá trị lớn kéo trung bình lên — dùng trung bình sẽ hiểu sai 'điển hình'.",
            "action": f"Báo cáo theo trung vị/percentile cho '{s['column']}', xem lại nhóm giá trị cực đại.",
            "severity": "medium",
        })

    # 4. Dominant segment.
    table = segments.get("table", [])
    if table and total_rows:
        top = table[0]
        share = 100.0 * top["count"] / total_rows
        if share >= 40:
            out.append({
                "finding": f"Nhóm '{top['segment']}' chiếm {share:.0f}% số dòng.",
                "so_what": "Dữ liệu tập trung một nhóm — kết luận chung dễ bị nhóm này chi phối.",
                "action": f"Phân tích riêng '{top['segment']}' và phần còn lại; cân nhắc chuẩn hóa theo nhóm.",
                "severity": "medium",
            })

    # 5. Constant columns.
    consts = [c["name"] for c in profile if c.get("is_constant")]
    if consts:
        out.append({
            "finding": f"{len(consts)} cột chỉ có một giá trị: {', '.join(consts[:3])}.",
            "so_what": "Cột hằng số không mang thông tin phân tích.",
            "action": "Loại các cột này khỏi mô hình/biểu đồ để giảm nhiễu.",
            "severity": "low",
        })

    # Guarantee at least one insight.
    if not out:
        out.append({
            "finding": f"Dữ liệu có {total_rows} dòng, {len(profile)} cột, chất lượng cơ bản ổn.",
            "so_what": "Không phát hiện vấn đề null/lệch/tập trung nổi bật ở mức cảnh báo.",
            "action": "Tiến hành phân tích chuyên sâu theo câu hỏi nghiệp vụ cụ thể.",
            "severity": "low",
        })
    return out[:max_insights]
