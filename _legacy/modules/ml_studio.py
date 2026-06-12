# modules/ml_studio.py
"""
ML STUDIO — Streamlit UI orchestrator.
Renders the current pipeline step and handles confirm gates.
Called from app.py when ds_view == "⚗ ML STUDIO".
"""

import io
import json
import os
import pickle
import time
from datetime import datetime
from pathlib import Path

import polars as pl
import streamlit as st

import polars.selectors as cs

from modules.ai_client import call_ai
from modules.ml_pipeline.ai_recommender import recommend
from modules.ml_pipeline.cleaner import run_clean
from modules.ml_pipeline.eda import run_eda
from modules.ml_pipeline.feature_selector import compute_feature_importance
from modules.ml_pipeline.header_detector import detect_header
from modules.ml_pipeline.notebook_gen import generate_notebook
from modules.ml_pipeline.result_plotter import get_figures_for_algo, get_result_figures
from modules.ml_pipeline.trainer import train_model

_SESSIONS_DIR = Path("data/ml_sessions")


# ── Cached file parsers ───────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_read_raw(file_bytes: bytes, filename: str) -> pl.DataFrame:
    """Parse uploaded file to raw string DataFrame (no header). Cached per file bytes."""
    if filename.endswith(".xlsx"):
        import pandas as pd
        pdf = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=str)
        return pl.from_pandas(pdf).fill_null("").cast(pl.Utf8)
    return pl.read_csv(
        io.BytesIO(file_bytes),
        has_header=False,
        infer_schema_length=0,
        encoding="utf8-lossy",
    )


@st.cache_data(show_spinner=False)
def _cached_read_with_header(
    file_bytes: bytes, filename: str, header_row: int, skip_rows: int
) -> pl.DataFrame:
    """Parse uploaded file with detected header. Cached per (file bytes, header config)."""
    if filename.endswith(".xlsx"):
        import pandas as pd
        pdf = pd.read_excel(io.BytesIO(file_bytes), header=header_row, dtype=str)
        return pl.from_pandas(pdf)
    return pl.read_csv(
        io.BytesIO(file_bytes),
        skip_rows=skip_rows,
        has_header=True,
        infer_schema_length=500,
        encoding="utf8-lossy",
    )


CHART_SAMPLE_SIZE = 50_000  # rows — sample threshold for plotly charts


@st.cache_data(show_spinner=False)
def _cached_run_eda(df: pl.DataFrame) -> dict:
    """Run full EDA profiling on df. Cached per DataFrame content (Streamlit hashes it)."""
    return run_eda(df)


def _get_chart_df(df: pl.DataFrame) -> tuple:
    """Return (df_for_charts, was_sampled). Samples to CHART_SAMPLE_SIZE if df is larger."""
    if df.height > CHART_SAMPLE_SIZE:
        return df.sample(CHART_SAMPLE_SIZE, seed=42), True
    return df, False


def _sh(icon: str, title: str, color: str = "#00d4ff", anim: str = "pulse", subtitle: str = ""):
    """Render a section header matching the project's IT style."""
    sub = (
        f'<div style="font-size:9px;color:#3d5a6b;letter-spacing:.18em;'
        f'margin-top:1px;font-family:\'JetBrains Mono\',monospace">{subtitle}</div>'
    ) if subtitle else ""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:9px;padding:2px 0 8px;">'
        f'<span class="anim-{anim}" style="color:{color};font-size:22px;line-height:1">{icon}</span>'
        f'<div>'
        f'<div style="font-size:13px;font-weight:700;color:#e6edf3;letter-spacing:.07em;'
        f'font-family:\'JetBrains Mono\',monospace">{title}</div>'
        f'{sub}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _init_state():
    if "ml_pipeline" not in st.session_state:
        st.session_state["ml_pipeline"] = {"step": 0}


def _state() -> dict:
    return st.session_state["ml_pipeline"]


def _set(key, value):
    st.session_state["ml_pipeline"][key] = value


def _advance():
    st.session_state["ml_pipeline"]["step"] += 1
    st.rerun()


def _go_back():
    st.session_state["ml_pipeline"]["step"] -= 1
    st.rerun()


def _reset():
    st.session_state["ml_pipeline"] = {"step": 0}
    st.rerun()


def _step0_upload():
    _sh("⬡", "UPLOAD DATASET", color="#00d4ff", anim="scan", subtitle="STEP 0 // CSV OR XLSX")
    uploaded = st.file_uploader("CSV or Excel (.xlsx)", type=["csv", "xlsx"])
    if uploaded is None:
        return

    try:
        raw_bytes = uploaded.getvalue()  # idempotent; safe to call multiple times
        df_raw = _cached_read_raw(raw_bytes, uploaded.name)
    except Exception as e:
        st.error(f"Cannot read file: {e}")
        return

    st.write("**Preview (raw):**")
    st.dataframe(df_raw.head(5).to_pandas(), use_container_width=True)

    _set("df_raw_bytes", raw_bytes)
    _set("filename", uploaded.name)
    _set("df_raw", df_raw)

    detection = detect_header(df_raw)
    _set("detection", detection)
    _advance()


def _step1_header():
    _sh("◎", "HEADER DETECTION", color="#00d4ff", anim="pulse", subtitle="GATE ① // AUTO-DETECT REAL HEADER ROW")
    s = _state()
    df_raw: pl.DataFrame = s["df_raw"]
    detection: dict = s["detection"]

    for w in detection.get("warnings", []):
        st.warning(w)

    st.write(f"**Header row:** `{detection['header_row']}`")
    st.write(f"**Proposed columns:** {detection['proposed_columns']}")

    st.write("**Override column names (leave blank to keep):**")
    override = {}
    cols_ui = st.columns(min(len(detection["proposed_columns"]), 4))
    for i, col_name in enumerate(detection["proposed_columns"]):
        with cols_ui[i % len(cols_ui)]:
            val = st.text_input(f"Col {i+1}", value=col_name, key=f"col_rename_{i}")
            override[i] = val or col_name

    final_cols = [override[i] for i in range(len(detection["proposed_columns"]))]

    raw_bytes: bytes = s["df_raw_bytes"]
    filename: str = s["filename"]
    try:
        df = _cached_read_with_header(
            raw_bytes, filename,
            detection["header_row"], detection["skip_rows"],
        )
        # Apply user column name overrides (rename returns new df, cache unaffected)
        rename_map = {old: new for old, new in zip(df.columns, final_cols[: df.width]) if old != new}
        if rename_map:
            df = df.rename(rename_map)
    except Exception as e:
        st.error(f"Error building DataFrame: {e}")
        return

    st.write("**Preview after fix:**")
    st.dataframe(df.head(5).to_pandas(), use_container_width=True)

    if st.button("▶ Continue → EDA", key="gate1_proceed"):
        _set("df", df)
        _set("final_cols", final_cols)
        _advance()


def _step2_eda():
    _sh("◈", "EDA / PROFILING", color="#00d4ff", anim="float", subtitle="GATE ② // SCHEMA · STATS · OUTLIERS")
    s = _state()
    df: pl.DataFrame = s["df"]

    with st.spinner("Running EDA..."):
        eda_result = _cached_run_eda(df)  # cached — instant on rerender

    _set("eda_result", eda_result)

    if eda_result["warnings"]:
        with st.expander("⚠️ Auto-warnings", expanded=True):
            for w in eda_result["warnings"]:
                st.warning(w)

    st.write(f"**Rows:** {df.height:,}  |  **Cols:** {df.width}  |  **Duplicates:** {eda_result['duplicate_count']}")

    st.write("**Schema & Quality:**")
    st.dataframe(pl.DataFrame(eda_result["schema"]).to_pandas(), use_container_width=True)

    if eda_result["describe"].height > 0:
        st.write("**Descriptive Statistics:**")
        st.dataframe(eda_result["describe"].to_pandas(), use_container_width=True)

    if eda_result["skew_kurt"]:
        sk_rows = [{"col": k, **v} for k, v in eda_result["skew_kurt"].items()]
        st.write("**Skewness & Kurtosis:**")
        st.dataframe(pl.DataFrame(sk_rows).to_pandas(), use_container_width=True)

    numeric_cols = df.select(pl.selectors.numeric()).columns
    if numeric_cols:
        import plotly.express as px
        picked = st.selectbox("Column for histogram", numeric_cols, key="eda_hist_col")
        df_chart, was_sampled = _get_chart_df(df)
        fig = px.histogram(
            df_chart[picked].drop_nulls().to_list(), template="plotly_dark",
            title=f"Distribution — {picked}", labels={"value": picked},
        )
        st.plotly_chart(fig, use_container_width=True)
        if was_sampled:
            st.caption(
                f"ℹ️ Chart hiển thị {CHART_SAMPLE_SIZE:,} / {df.height:,} dòng (sampled, seed=42). "
                "Stats ở trên tính trên full data."
            )

    if eda_result["outlier_summary"]:
        out_rows = [{"col": k, **v} for k, v in eda_result["outlier_summary"].items()]
        st.write("**Outlier Summary (IQR):**")
        st.dataframe(pl.DataFrame(out_rows).to_pandas(), use_container_width=True)

    if st.button("▶ Continue → Clean", key="gate2_proceed"):
        _advance()


def _step3_clean():
    _sh("⬢", "CLEAN & TRANSFORM", color="#7c3aed", anim="pulse", subtitle="GATE ③ // DEDUPE · NULLS · ENCODE · OUTLIERS")
    s = _state()
    df: pl.DataFrame = s["df"]

    config = {
        "dedupe": st.checkbox("Remove duplicate rows", value=True, key="clean_dedupe"),
        "fill_null": st.checkbox("Fill nulls (median/mode)", value=True, key="clean_null"),
        "flag_outliers": st.checkbox("Flag outliers (IQR×1.5)", value=True, key="clean_outlier"),
        "encode_categoricals": st.checkbox("Label encode categoricals", value=True, key="clean_encode"),
        "split_dates": st.checkbox("Split dates → year/month/day_of_week/quarter", value=True, key="clean_date"),
    }

    if st.button("▶ Run Clean", key="gate3_run"):
        with st.spinner("Cleaning..."):
            df_clean, summary = run_clean(df, config)

        _set("df_clean", df_clean)
        _set("clean_summary", summary)
        _set("clean_config", config)

        st.success("✅ Done!")
        col1, col2 = st.columns(2)
        col1.metric("Rows before", summary["rows_before"])
        col2.metric("Rows after", summary["rows_after"])
        if summary["nulls_filled"]:
            st.write("Nulls filled:", summary["nulls_filled"])
        if summary["encoded_cols"]:
            st.write("Encoded:", summary["encoded_cols"])

    if "df_clean" in s:
        if st.button("▶ Continue → Feature Selection", key="gate3_proceed"):
            _advance()


def _build_explain_why_prompt(rec: dict, df: pl.DataFrame) -> str:
    target = rec.get("target", "")
    algo = rec.get("algorithm", "")
    features = rec.get("features", [])[:8]
    method = rec.get("method", "")
    prob = rec.get("problem_type", "")
    reasoning = rec.get("reasoning", "")
    return (
        "Bạn là chuyên gia ML và FMCG. Giải thích bằng tiếng Việt tại sao AI chọn các thông số sau, "
        "cho người dùng không có nền tảng kỹ thuật (marketing/sales manager).\n\n"
        f"AI đề xuất:\n"
        f"- Target (biến cần dự báo): {target}\n"
        f"- Algorithm (thuật toán): {algo}\n"
        f"- Features (yếu tố đầu vào): {', '.join(str(f) for f in features)}\n"
        f"- Phương pháp: {method} / {prob}\n"
        f"- Lý do kỹ thuật AI đưa ra: {reasoning}\n"
        f"- Dataset: {df.height:,} dòng × {df.width} cột\n\n"
        "Viết ĐÚNG format, mỗi phần 1-2 câu ngắn, KHÔNG dùng jargon:\n\n"
        f"**📌 Tại sao chọn `{target}` làm biến mục tiêu?**\n"
        "[Giải thích bằng business terms — ý nghĩa thực tế của chỉ số này]\n\n"
        f"**⚙️ Tại sao dùng {algo}?**\n"
        "[Giải thích bằng analogy đơn giản — algorithm này giỏi làm gì trong FMCG]\n\n"
        f"**🔢 Tại sao chọn các yếu tố đầu vào này?**\n"
        "[Giải thích tại sao từng nhóm feature này liên quan đến {target}]\n\n"
        "**⚡ Bước tiếp theo nên làm:**\n"
        "[1 gợi ý cụ thể để kiểm tra hoặc dùng kết quả]"
    )


def _step4_ai_recommend():
    _sh("⟁", "AI RECOMMEND", color="#bd00ff", anim="pulse", subtitle="GATE ④ // ANALYZE · SUGGEST · METHOD · TARGET")
    s = _state()
    df_clean = s.get("df_clean")
    if df_clean is None or not isinstance(df_clean, pl.DataFrame) or df_clean.height == 0:
        st.error("Không tìm thấy dữ liệu sau bước Clean. Vui lòng quay lại bước Clean.")
        return

    if "ai_rec" not in s:
        with st.spinner("Analyzing your data..."):
            rec = recommend(df_clean)
        _set("ai_rec", rec)

    rec = s["ai_rec"]
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Method:** {rec.get('method', '').title()}")
        st.info(f"**Problem Type:** {rec.get('problem_type', '').title()}")
        st.info(f"**Suggested Target:** `{rec.get('target', '')}`")
    with col2:
        st.info(f"**Algorithm:** {rec.get('algorithm', '')}")
        feats = rec.get("features", [])
        st.info(f"**Top Features:** {', '.join(str(f) for f in feats[:5])}")
    if rec.get("reasoning"):
        st.caption(f"Reasoning: {rec['reasoning']}")

    # ── AI explains WHY it chose each field
    with st.expander("🔍 AI giải thích tại sao chọn field này", expanded=False):
        if st.button("◈ Giải thích bằng business terms", key="ai_explain_why_btn"):
            with st.spinner("AI đang giải thích lý do chọn field..."):
                explain_prompt = _build_explain_why_prompt(rec, df_clean)
                try:
                    explanation = call_ai(explain_prompt, max_tokens=600)
                    _set("ai_field_explanation", explanation)
                except Exception as e:
                    st.error(f"AI lỗi: {e}")
        cached_explain = s.get("ai_field_explanation")
        if cached_explain:
            st.markdown(cached_explain)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("◉  Accept & Continue", key="ai_rec_accept"):
            _set("ai_rec_accepted", True)
            _advance()
    with col_b:
        if st.button("◈  Override manually", key="ai_rec_override"):
            _set("ai_rec_accepted", False)
            _advance()


_METHOD_MAP = {
    "Supervised": "supervised",
    "Unsupervised": "unsupervised",
    "Time Series": "timeseries",
}
_ALGOS_SUP = ["xgboost", "random_forest", "svm", "mlp"]
_ALGO_LABELS_SUP = {"xgboost": "XGBoost", "random_forest": "Random Forest",
                    "svm": "SVM", "mlp": "MLP (Neural Net)"}
_ALGOS_UNS = ["kmeans", "dbscan", "hierarchical"]
_ALGO_LABELS_UNS = {"kmeans": "K-Means", "dbscan": "DBSCAN",
                    "hierarchical": "Hierarchical Clustering"}
_ALGOS_TS = ["sarimax", "prophet", "exp_smoothing"]
_ALGO_LABELS_TS = {"sarimax": "SARIMAX", "prophet": "Prophet",
                   "exp_smoothing": "Exponential Smoothing"}


def _step5_features():
    _sh("△", "METHOD + FEATURES", color="#bd00ff", anim="pulse", subtitle="GATE ⑤ // METHOD · ALGO · TARGET · FEATURES")
    s = _state()
    df_clean: pl.DataFrame = s["df_clean"]
    rec = s.get("ai_rec", {})
    accepted = s.get("ai_rec_accepted", False)

    rec_method = rec.get("method", "supervised") if accepted else "supervised"
    default_method_idx = list(_METHOD_MAP.values()).index(rec_method) if rec_method in _METHOD_MAP.values() else 0
    method_label = st.selectbox("Method", list(_METHOD_MAP.keys()),
                                index=default_method_idx, key="method_label")
    method = _METHOD_MAP[method_label]
    _set("method", method)

    if method == "supervised":
        prob_types = ["regression", "classification"]
        rec_pt = rec.get("problem_type", "regression") if accepted else "regression"
        pt_idx = prob_types.index(rec_pt) if rec_pt in prob_types else 0
        problem_type = st.selectbox("Problem type", prob_types, index=pt_idx, key="prob_type")
        _set("problem_type", problem_type)

        rec_algo_raw = rec.get("algorithm", "").lower().replace(" ", "_") if accepted else ""
        default_algos = [rec_algo_raw] if rec_algo_raw in _ALGOS_SUP else ["xgboost"]
        selected_algos = st.multiselect(
            "Algorithms (select 1–2)", options=_ALGOS_SUP,
            format_func=lambda a: _ALGO_LABELS_SUP[a],
            default=default_algos, key="sel_algos",
        )
        _set("algorithms", selected_algos)

        if "mlp" in selected_algos:
            with st.expander("Neural Network Config"):
                hl_str = st.text_input("Hidden layer sizes (comma-separated)", value="100,50", key="mlp_hl")
                max_iter = st.number_input("Max iterations", value=300, min_value=50, key="mlp_iter")
                lr = st.number_input("Learning rate", value=0.001, format="%.4f", key="mlp_lr")
                try:
                    hl = [int(x.strip()) for x in hl_str.split(",")]
                except Exception:
                    hl = [100, 50]
                _set("nn_config", {"hidden_layer_sizes": hl, "max_iter": int(max_iter),
                                   "learning_rate_init": float(lr)})

        rec_target = rec.get("target", df_clean.columns[0]) if accepted else df_clean.columns[0]
        tgt_idx = df_clean.columns.index(rec_target) if rec_target in df_clean.columns else 0
        target = st.selectbox("Target column", df_clean.columns, index=tgt_idx, key="target_col")
        _set("target", target)

        if st.button("⟁  Compute Feature Importance", key="calc_importance"):
            with st.spinner("Computing..."):
                ranked = compute_feature_importance(df_clean, target, problem_type)
            _set("ranked_features", ranked)

        if "ranked_features" in s:
            ai_feats = rec.get("features", []) if accepted else []
            selected = []
            for item in s["ranked_features"]:
                default_on = item["feature"] in ai_feats if ai_feats else True
                if st.checkbox(f"{item['feature']}  (score: {item['score']:.4f})",
                               value=default_on, key=f"feat_{item['feature']}"):
                    selected.append(item["feature"])
            _set("features", selected)
            if selected and selected_algos and st.button("◉  Continue → Train", key="gate5_proceed"):
                _advance()

    elif method == "unsupervised":
        _set("problem_type", "clustering")
        selected_algos = st.multiselect(
            "Algorithms (select 1–2)", options=_ALGOS_UNS,
            format_func=lambda a: _ALGO_LABELS_UNS[a],
            default=["kmeans"], key="sel_algos_u",
        )
        _set("algorithms", selected_algos)

        if "dbscan" in selected_algos:
            with st.expander("DBSCAN Config"):
                eps = st.number_input("Epsilon (eps)", value=0.5, format="%.2f", key="dbscan_eps")
                min_samp = st.number_input("Min samples", value=5, min_value=1, key="dbscan_min")
                _set("dbscan_config", {"eps": float(eps), "min_samples": int(min_samp)})
        if "hierarchical" in selected_algos:
            with st.expander("Hierarchical Config"):
                hier_k = st.number_input("Number of clusters (k)", value=3, min_value=2, key="hier_k")
                _set("hierarchical_k", int(hier_k))

        numeric_cols = df_clean.select(cs.numeric()).columns
        selected_feats = st.multiselect(
            "Features", options=numeric_cols,
            default=numeric_cols[:min(5, len(numeric_cols))], key="u_features",
        )
        _set("features", selected_feats)
        if selected_feats and selected_algos and st.button("◉  Continue → Train", key="gate5u_proceed"):
            _advance()

    elif method == "timeseries":
        _set("problem_type", "timeseries")
        selected_algos = st.multiselect(
            "Algorithms (select 1–2)", options=_ALGOS_TS,
            format_func=lambda a: _ALGO_LABELS_TS[a],
            default=["sarimax"], key="sel_algos_t",
        )
        _set("algorithms", selected_algos)

        date_col = st.selectbox("Date column", df_clean.columns, key="date_col")
        target = st.selectbox("Target column", df_clean.columns, key="ts_target")
        horizon = st.number_input("Forecast horizon (days)", min_value=7, max_value=365,
                                  value=30, key="horizon")
        _set("date_col", date_col)
        _set("target", target)
        _set("horizon", int(horizon))

        other_cols = [c for c in df_clean.columns if c not in [date_col, target]]
        exog_cols = st.multiselect("Exogenous variables (optional)", options=other_cols,
                                   key="exog_cols")
        _set("exog_cols", exog_cols)
        if exog_cols and "exp_smoothing" in selected_algos:
            st.warning("⚠️ Exponential Smoothing ignores exogenous variables.")

        if selected_algos and st.button("◉  Continue → Train", key="gate5t_proceed"):
            _advance()


def _step6_train():
    _sh("◉", "TRAIN & COMPARE", color="#00d4ff", anim="spin", subtitle="STEP ⑥ // FIT · EVAL · COMPARE · NOTEBOOK")
    s = _state()
    df_clean: pl.DataFrame = s["df_clean"]
    method: str = s.get("method", "supervised")
    problem_type: str = s.get("problem_type", "regression")
    algorithms: list = s.get("algorithms", ["xgboost"])
    features: list = s.get("features", [])
    target: str = s.get("target", "")
    date_col: str = s.get("date_col", "")
    horizon: int = s.get("horizon", 30)
    exog_cols: list = s.get("exog_cols", [])
    nn_config: dict = s.get("nn_config", {})
    dbscan_cfg: dict = s.get("dbscan_config", {})
    hierarchical_k: int = s.get("hierarchical_k", 3)

    if problem_type == "timeseries" and date_col:
        n_dates = df_clean[date_col].n_unique() if date_col in df_clean.columns else 0
        n_rows = df_clean.height
        if n_rows > n_dates:
            st.info(
                f"◈ Data có {n_rows:,} dòng / {n_dates} mốc thời gian — "
                f"sẽ tự động **aggregate (sum)** theo `{date_col}` trước khi train. "
                f"Tổng dữ liệu timeseries = {n_dates} điểm."
            )

    # ── Large-dataset warning + subsample option ──────────────────────────────
    _SUBSAMPLE_THRESHOLD = 200_000
    _SUBSAMPLE_SIZE = 50_000
    n_train_rows = df_clean.height

    if n_train_rows > _SUBSAMPLE_THRESHOLD:
        st.warning(
            f"⚠️ Dataset lớn: **{n_train_rows:,} dòng** — training có thể mất vài phút."
        )
        use_sample = st.checkbox(
            f"⚡ Train nhanh trên {_SUBSAMPLE_SIZE:,} dòng "
            f"(kết quả tham khảo — nhanh hơn ~{max(n_train_rows // _SUBSAMPLE_SIZE, 2)}×)",
            key="train_use_sample",
            value=False,
        )
        df_to_train = df_clean.sample(_SUBSAMPLE_SIZE, seed=42) if use_sample else df_clean
        if use_sample:
            st.caption(f"⚡ Sẽ train trên {_SUBSAMPLE_SIZE:,} / {n_train_rows:,} dòng.")
    else:
        use_sample = False
        df_to_train = df_clean

    if st.button("▶ Start Training", key="start_train"):
        t0 = time.time()
        progress = st.progress(0)
        status = st.empty()
        all_results = {}
        for i, algo in enumerate(algorithms):
            elapsed = time.time() - t0
            status.text(f"Training {algo}... ({elapsed:.0f}s elapsed)")
            partial = train_model(
                method=method, problem_type=problem_type, algorithms=[algo],
                df=df_to_train, features=features, target=target,
                date_col=date_col, horizon=horizon, exog_cols=exog_cols,
                nn_config=nn_config,
                dbscan_eps=dbscan_cfg.get("eps", 0.5),
                dbscan_min_samples=dbscan_cfg.get("min_samples", 5),
                hierarchical_k=hierarchical_k,
            )
            all_results.update(partial["results"])
            progress.progress((i + 1) / len(algorithms))

        total_elapsed = time.time() - t0
        sample_badge = f" [SAMPLED {_SUBSAMPLE_SIZE:,}]" if use_sample else ""
        status.text(f"✅ Done!{sample_badge} Tổng: {total_elapsed:.1f}s")

        if method == "supervised" and problem_type == "regression":
            winner = min(all_results, key=lambda a: all_results[a]["metrics"]["rmse"])
        elif method == "supervised":
            winner = max(all_results, key=lambda a: all_results[a]["metrics"]["f1"])
        elif method == "unsupervised":
            winner = max(all_results, key=lambda a: all_results[a]["metrics"]["silhouette"])
        else:
            winner = min(all_results, key=lambda a: all_results[a]["metrics"]["rmse"])

        train_result = {"results": all_results, "winner": winner, "problem_type": problem_type}
        _set("train_result", train_result)

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = s.get("filename", "dataset.csv")
        session_name = f"{session_id}_{Path(dataset_name).stem}"
        session_dir = str(_SESSIONS_DIR / session_name)
        os.makedirs(session_dir, exist_ok=True)
        _set("session_dir", session_dir)
        _set("session_name", session_name)

        winner_result = all_results[winner]
        cs_summary = s.get("clean_summary", {})
        clean_steps = []
        dedup = cs_summary.get("rows_before", 0) - cs_summary.get("rows_after", 0)
        if dedup > 0:
            clean_steps.append(f"Removed {dedup} duplicates")
        if cs_summary.get("nulls_filled"):
            clean_steps.append(f"Filled nulls: {cs_summary['nulls_filled']}")
        if cs_summary.get("encoded_cols"):
            clean_steps.append(f"Encoded: {cs_summary['encoded_cols']}")
        detection = s.get("detection", {})
        nb_context = {
            "dataset_name": dataset_name, "target": target, "features": features,
            "skip_rows": detection.get("skip_rows", 0), "header_row": detection.get("header_row", 0),
            "timestamp": datetime.now().isoformat(), "problem_type": problem_type,
            "clean_steps": clean_steps or ["No cleaning applied"],
            "metrics": winner_result.get("metrics", {}),
            "horizon": horizon, "date_col": date_col,
        }
        nb_path = generate_notebook(session_dir, problem_type, nb_context)
        _set("notebook_path", nb_path)
        st.success("✅ Training complete!")
        _advance()


def _build_insight_prompt(s: dict, train_result: dict) -> str:
    import numpy as np

    problem_type = s.get("problem_type", train_result.get("problem_type", "regression"))
    target = s.get("target", "")
    features = s.get("features", [])
    filename = s.get("filename", "dataset")
    winner = train_result.get("winner", "")
    results = train_result.get("results", {})

    if results and winner:
        winner_result = results.get(winner, {})
        metrics = winner_result.get("metrics", {})
        _raw_pred = winner_result.get("y_pred")
        _raw_test = winner_result.get("y_test")
        forecast_raw = winner_result.get("forecast")
        cluster_labels = winner_result.get("cluster_labels", [])
        cluster_k = winner_result.get("k")
    else:
        metrics = {}
        _raw_pred = _raw_test = forecast_raw = None
        cluster_labels = []
        cluster_k = None

    y_pred = list(np.array(_raw_pred).flat) if _raw_pred is not None else []
    y_test = list(np.array(_raw_test).flat) if _raw_test is not None else []
    forecast = list(np.array(forecast_raw).flat) if forecast_raw is not None else []

    # Tóm tắt dữ liệu lịch sử
    hist_summary = ""
    if y_test:
        hist_summary = (
            f"Dữ liệu lịch sử: {len(y_test)} điểm | "
            f"min={min(y_test):.2f}, max={max(y_test):.2f}, "
            f"trung bình={np.mean(y_test):.2f}, "
            f"xu hướng={'tăng' if y_test[-1] > y_test[0] else 'giảm'} "
            f"({y_test[0]:.2f} → {y_test[-1]:.2f})"
        )

    # Tóm tắt forecast
    forecast_summary = ""
    if forecast:
        forecast_summary = (
            f"Dự báo {len(forecast)} kỳ tới: "
            f"min={min(forecast):.2f}, max={max(forecast):.2f}, "
            f"trung bình={np.mean(forecast):.2f}, "
            f"kỳ đầu={forecast[0]:.2f}, kỳ cuối={forecast[-1]:.2f}"
        )

    # 5 cặp actual/predicted để AI nhận xét pattern
    sample_pairs = ""
    if y_test and y_pred:
        pairs = list(zip(y_test[:5], y_pred[:5]))
        sample_pairs = " | ".join(f"thực={a:.1f}→dự={p:.1f}" for a, p in pairs)

    # Metrics đơn giản
    metrics_simple = ", ".join(
        f"{k}={v:.3f}" for k, v in metrics.items()
        if isinstance(v, (int, float)) and k not in ("elbow_ks", "elbow_inertias")
    )

    # Cluster context
    cluster_ctx = f"Số cụm tối ưu: {cluster_k}" if cluster_k else ""

    # ---- PROMPT ----
    problem_labels = {
        "regression": "dự báo số (regression)",
        "classification": "phân loại (classification)",
        "clustering": "phân cụm khách hàng/dữ liệu",
        "timeseries": "dự báo chuỗi thời gian",
    }
    problem_label = problem_labels.get(problem_type, problem_type)

    return f"""Bạn là chuyên gia phân tích dữ liệu, đang trình bày kết quả cho người dùng không có nền tảng kỹ thuật.
Viết hoàn toàn bằng tiếng Việt. KHÔNG dùng thuật ngữ kỹ thuật nếu không giải thích kèm.
Giọng văn: thân thiện, tự tin, có câu chuyện — như người đồng nghiệp thông minh giải thích cho sếp nghe.

=== DỮ LIỆU ĐẦU VÀO ===
File: {filename}
Bài toán: {problem_label}
Biến mục tiêu (muốn dự báo): {target}
Các yếu tố đầu vào: {', '.join(features) if features else 'không có (timeseries/clustering)'}
Model được chọn (tốt nhất): {winner}
Chỉ số đo lường: {metrics_simple}
{hist_summary}
{forecast_summary}
{sample_pairs and f'Ví dụ 5 điểm dự báo: {sample_pairs}' or ''}
{cluster_ctx}

=== YÊU CẦU OUTPUT ===
Viết ĐÚNG 4 phần dưới đây, KHÔNG thêm bớt:

**◈ CÂU CHUYỆN TỪ DỮ LIỆU**
[2–3 câu kể chuyện: dữ liệu này đang nói gì? xu hướng thế nào? forecast cho thấy điều gì?
Ví dụ kiểu: "Trong {len(y_test)} kỳ qua, {target} đã... Model dự báo {len(forecast)} kỳ tới sẽ..."
Dùng số thực từ dữ liệu. Không dùng từ "MAPE", "RMSE", "AIC".]

**⟁ MODEL ĐÃ LÀM GÌ** *(giải thích như nói chuyện)*
[2–3 câu: dùng analogy. Ví dụ: "Model này giống như một chuyên gia đã học thuộc {len(y_test)} kỳ số liệu quá khứ,
sau đó tự tìm ra quy luật để đoán tương lai — tương tự cách dự báo thời tiết dựa vào dữ liệu năm trước."
Giải thích tại sao chọn model {winner} thay vì các model khác (nếu có so sánh).]

**❓ CẦN LÀM RÕ THÊM**
[3 câu hỏi quan trọng nên đặt ra TRƯỚC khi dùng kết quả này để ra quyết định.
Format: "→ [câu hỏi]" — mỗi câu hỏi trên 1 dòng. Hỏi thực tế, không hỏi kỹ thuật.]

**⚠️ LƯU Ý KHI DÙNG KẾT QUẢ NÀY**
[1–2 điểm giới hạn của phân tích này viết theo kiểu "thực tế mà nói thì...",
ví dụ về data quá ngắn, thiếu yếu tố ngoài, v.v. Không dùng từ overfitting, bias, variance.]"""


def _suggested_followups(problem_type: str, target: str) -> list[str]:
    if problem_type == "timeseries":
        return [
            f"Xu hướng {target} 3 tháng tới theo model là gì?",
            "Yếu tố nào ảnh hưởng nhiều nhất đến dự báo?",
            "Nếu thực tế lệch >20% so với forecast thì làm gì?",
        ]
    if problem_type == "regression":
        return [
            f"Feature nào ảnh hưởng mạnh nhất đến {target}?",
            "Sai số của model có chấp nhận được với business không?",
            "Cần thêm dữ liệu gì để model chính xác hơn?",
        ]
    if problem_type == "classification":
        return [
            "Nhóm nào model hay dự đoán sai nhất?",
            "Threshold nào phù hợp nhất với bài toán này?",
            "Làm gì khi model dự báo nhầm class quan trọng?",
        ]
    if problem_type == "clustering":
        return [
            "Nhóm nào cần được ưu tiên chăm sóc nhất?",
            "Làm thế nào áp dụng kết quả phân cụm vào chiến lược?",
            "Bao lâu nên chạy lại phân cụm?",
        ]
    return [
        "Kết quả này có thể dùng ngay để ra quyết định chưa?",
        "Nên trình bày kết quả này cho sếp như thế nào?",
        "Cần xác minh thêm điều gì trước khi dùng?",
    ]


def _render_insight_followup(s: dict, train_result: dict):
    """Follow-up Q&A panel below AI insight."""
    cached = st.session_state.get("ml_insight_cache")
    if not cached:
        return

    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.1em;'
        'font-family:\'JetBrains Mono\',monospace;margin-bottom:8px">'
        'HỎI THÊM VỀ KẾT QUẢ PHÂN TÍCH NÀY</div>',
        unsafe_allow_html=True,
    )

    problem_type = train_result.get("problem_type", "")
    target = s.get("target", "")
    suggestions = _suggested_followups(problem_type, target)

    fkey = "ml_insight_followup_text"
    if fkey not in st.session_state:
        st.session_state[fkey] = ""

    sq_cols = st.columns(3)
    for i, q in enumerate(suggestions):
        with sq_cols[i]:
            if st.button(f"❓ {q}", key=f"insight_sugg_{i}", use_container_width=True):
                st.session_state[fkey] = q
                st.rerun()

    followup = st.text_input(
        "Hoặc tự hỏi:",
        key=fkey,
        placeholder="Hỏi thêm về kết quả phân tích...",
    )

    if followup and st.button("▶ Hỏi AI", key="insight_ask_ai_btn"):
        context = (
            f"File: {s.get('filename','')}, target={target}, "
            f"method={train_result.get('winner','')}, "
            f"problem={problem_type}"
        )
        prompt = (
            f"Bạn là chuyên gia ML và FMCG. Trả lời câu hỏi dựa trên kết quả phân tích sau.\n"
            f"Context: {context}\n"
            f"Kết quả AI: {cached[:800]}\n"
            f"Câu hỏi: {followup}\n"
            f"Trả lời bằng tiếng Việt, ≤5 câu, business-focused, có số liệu nếu cần."
        )
        with st.spinner("AI đang trả lời..."):
            try:
                ans = call_ai(prompt, max_tokens=400)
                st.info(f"◈ AI: {ans}")
            except Exception as e:
                st.error(f"AI lỗi: {e}")


def _render_ai_insight(s: dict, train_result: dict):
    st.divider()
    _sh("⟁", "AI INSIGHT AGENT", color="#bd00ff", anim="pulse", subtitle="CLAUDE // ĐỌC KẾT QUẢ · INSIGHT · DEFEND VỚI SẾP")
    if st.button("◈  Phân tích & giải thích kết quả", key="ai_insight_btn"):
        with st.spinner("AI đang đọc kết quả..."):
            try:
                prompt = _build_insight_prompt(s, train_result)
                insight = call_ai(prompt, max_tokens=1200)
                st.session_state["ml_insight_cache"] = insight
            except Exception as e:
                st.error(f"AI không phản hồi được: {e}")
                return

    cached = st.session_state.get("ml_insight_cache")
    if cached:
        st.markdown(cached)


def _step7_results():
    _sh("◈", "RESULTS", color="#00d4ff", anim="pulse", subtitle="STEP ⑦ // METRICS · CHARTS · INSIGHT · EXPORT")
    s = _state()
    train_result: dict = s.get("train_result", {})
    results: dict = train_result.get("results", {})
    winner: str = train_result.get("winner", "")

    if results:
        st.write("**Metrics Comparison:**")
        rows = []
        for algo, r in results.items():
            row = {"Algorithm": (f"◉ {algo}" if algo == winner else algo)}
            row.update({k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in r["metrics"].items()
                        if k not in ("elbow_ks", "elbow_inertias", "X_2d")})
            rows.append(row)
        st.dataframe(pl.DataFrame(rows).to_pandas())

    if results:
        # Legend card cho timeseries
        problem_type = train_result.get("problem_type", "")
        if problem_type == "timeseries":
            st.markdown(
                '<div style="background:#0d1f2d;border:1px solid #1e3a4f;border-radius:8px;'
                'padding:10px 16px;margin-bottom:12px;font-family:\'JetBrains Mono\',monospace;font-size:12px;">'
                '<span style="color:#888;letter-spacing:.1em">BIỂU ĐỒ DỰ BÁO — ĐỌC HƯỚNG DẪN</span><br><br>'
                '<span style="color:#5b9bd5">━━</span> <b style="color:#e6edf3">Đường xanh (Historical)</b>'
                ' — dữ liệu <b>thực tế</b> trong quá khứ bạn đã có<br>'
                '<span style="color:#ffa500">━━</span> <b style="color:#e6edf3">Đường cam (Forecast)</b>'
                ' — con số <b>model dự báo</b> cho các kỳ tới (chưa xảy ra)<br>'
                '<span style="color:#ffa500;opacity:.4">▓▓</span> <b style="color:#e6edf3">Vùng mờ (95% CI)</b>'
                ' — <b>khoảng dao động</b> có thể xảy ra — thực tế sẽ rơi vào vùng này với xác suất 95%'
                '</div>',
                unsafe_allow_html=True,
            )
        elif problem_type == "regression":
            st.markdown(
                '<div style="background:#0d1f2d;border:1px solid #1e3a4f;border-radius:8px;'
                'padding:10px 16px;margin-bottom:12px;font-family:\'JetBrains Mono\',monospace;font-size:12px;">'
                '<span style="color:#888;letter-spacing:.1em">ĐỌC BIỂU ĐỒ</span><br><br>'
                '<b style="color:#e6edf3">Actual vs Predicted</b>: mỗi chấm = 1 quan sát. '
                'Chấm càng gần <span style="color:#ff4444">đường đỏ</span> = dự báo càng chính xác.<br>'
                '<b style="color:#e6edf3">Feature Importance</b>: thanh dài = yếu tố ảnh hưởng nhiều hơn.<br>'
                '<b style="color:#e6edf3">Residuals</b>: phân phối sai số — lý tưởng là hình chuông cân xứng quanh 0.'
                '</div>',
                unsafe_allow_html=True,
            )
        elif problem_type == "classification":
            st.markdown(
                '<div style="background:#0d1f2d;border:1px solid #1e3a4f;border-radius:8px;'
                'padding:10px 16px;margin-bottom:12px;font-family:\'JetBrains Mono\',monospace;font-size:12px;">'
                '<span style="color:#888;letter-spacing:.1em">ĐỌC BIỂU ĐỒ</span><br><br>'
                '<b style="color:#e6edf3">Confusion Matrix</b>: ô chéo (trái-trên → phải-dưới) = dự đoán đúng. '
                'Ô ngoài chéo = dự đoán sai — số càng nhỏ càng tốt.<br>'
                '<b style="color:#e6edf3">Feature Importance</b>: thanh dài = yếu tố model coi trọng hơn.'
                '</div>',
                unsafe_allow_html=True,
            )
        elif problem_type == "clustering":
            st.markdown(
                '<div style="background:#0d1f2d;border:1px solid #1e3a4f;border-radius:8px;'
                'padding:10px 16px;margin-bottom:12px;font-family:\'JetBrains Mono\',monospace;font-size:12px;">'
                '<span style="color:#888;letter-spacing:.1em">ĐỌC BIỂU ĐỒ</span><br><br>'
                '<b style="color:#e6edf3">Elbow Curve</b>: điểm "khuỷu tay" = số cụm tối ưu (đường đỏ đứng).<br>'
                '<b style="color:#e6edf3">PCA 2D</b>: mỗi màu = 1 nhóm/cụm dữ liệu. '
                'Các chấm cùng màu có đặc điểm tương tự nhau.'
                '</div>',
                unsafe_allow_html=True,
            )

        tab_labels = [f"{'◉ ' if a == winner else '◈ '}{a}" for a in results]
        tabs = st.tabs(tab_labels)
        for tab, (algo, r) in zip(tabs, results.items()):
            with tab:
                for item in get_figures_for_algo(r):
                    st.plotly_chart(item["fig"])

    winner_result = results.get(winner, {})
    y_pred = winner_result.get("y_pred")
    y_test = winner_result.get("y_test")

    # ── Download row ─────────────────────────────────────────────────────────
    dl_cols = []
    if y_pred is not None and y_test is not None and len(y_pred) > 0:
        dl_cols.append("csv")
    nb_path = s.get("notebook_path", "")
    if nb_path and os.path.exists(nb_path):
        dl_cols.append("nb")

    if dl_cols:
        btn_cols = st.columns(len(dl_cols))
        col_idx = 0
        if "csv" in dl_cols:
            import numpy as np
            out_df = pl.DataFrame({"actual": list(np.array(y_pred).flat),
                                   "predicted": list(np.array(y_test).flat)})
            with btn_cols[col_idx]:
                st.download_button("⬇ Download Predictions (CSV)",
                                   out_df.write_csv().encode(), "predictions.csv", "text/csv",
                                   use_container_width=True)
            col_idx += 1
        if "nb" in dl_cols:
            with open(nb_path, "rb") as _f:
                nb_bytes = _f.read()
            nb_filename = f"{Path(s.get('session_dir', 'session')).name}_notebook.ipynb"
            with btn_cols[col_idx]:
                st.download_button("⬇ Download Notebook (.ipynb)",
                                   nb_bytes, nb_filename,
                                   "application/x-ipynb+json",
                                   use_container_width=True)

    if st.button("⬢  Save Session"):
        _save_session(s, train_result)
        st.success("◉  Session saved!")

    _render_ai_insight(s, train_result)
    _render_insight_followup(s, train_result)

    st.divider()
    if st.button("⬡  New Session"):
        _reset()


def _save_session(s: dict, train_result: dict):
    session_dir: str = s.get("session_dir", "")
    if not session_dir:
        st.error("Session dir not created.")
        return
    os.makedirs(session_dir, exist_ok=True)

    df_clean: pl.DataFrame = s.get("df_clean")
    if df_clean is not None:
        df_clean.write_parquet(os.path.join(session_dir, "cleaned.parquet"))

    raw_bytes: bytes = s.get("df_raw_bytes", b"")
    with open(os.path.join(session_dir, "raw.csv"), "wb") as f:
        f.write(raw_bytes)

    winner = train_result.get("winner", "")
    results = train_result.get("results", {})
    winner_result = results.get(winner, {})
    winner_model = winner_result.get("model")
    if winner_model is not None:
        try:
            with open(os.path.join(session_dir, "model.pkl"), "wb") as f:
                pickle.dump(winner_model, f)
        except Exception:
            pass

    y_pred = winner_result.get("y_pred")
    y_test = winner_result.get("y_test")
    if y_pred is not None and y_test is not None and len(y_pred) > 0:
        import numpy as np
        pl.DataFrame({"actual": list(np.array(y_test).flat),
                      "predicted": list(np.array(y_pred).flat)}).write_csv(
            os.path.join(session_dir, "predictions.csv"))

    report = {
        "session_id": Path(session_dir).name,
        "dataset": s.get("filename", ""),
        "rows": df_clean.height if df_clean is not None else 0,
        "cols": df_clean.width if df_clean is not None else 0,
        "method": s.get("method", ""),
        "problem": train_result.get("problem_type", ""),
        "target": s.get("target", ""),
        "features": s.get("features", []),
        "algorithms_run": list(results.keys()),
        "winner": winner,
        "model": type(winner_model).__name__ if winner_model else "",
        "metrics": {k: v for k, v in winner_result.get("metrics", {}).items()
                    if k not in ("elbow_ks", "elbow_inertias", "X_2d")},
        "created_at": datetime.now().isoformat(),
    }
    with open(os.path.join(session_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)


def _render_history():
    st.divider()
    _sh("⌥", "SESSION HISTORY", color="#3d5a6b", anim="float", subtitle="SAVED SESSIONS // CLICK TO RESTORE")
    sessions = sorted(_SESSIONS_DIR.glob("*/report.json"), reverse=True)
    if not sessions:
        st.info("No sessions saved yet.")
        return

    for report_path in list(sessions)[:10]:
        try:
            report = json.loads(report_path.read_text())
        except Exception:
            continue
        session_dir = str(report_path.parent)
        col_info, col_open = st.columns([4, 1])
        with col_info:
            st.write(
                f"**{report['session_id']}** — {report['problem']} — "
                f"target: `{report['target']}` — {report['rows']:,} rows — "
                f"{report.get('created_at', '')[:16]}"
            )
        with col_open:
            if st.button("Open", key=f"open_{report['session_id']}"):
                winner = report.get("winner", "")
                new_state = {
                    "step": 7,
                    "session_dir": session_dir,
                    "session_name": report["session_id"],
                    "filename": report["dataset"],
                    "method": report.get("method", "supervised"),
                    "problem_type": report["problem"],
                    "target": report["target"],
                    "features": report["features"],
                }
                parquet_path = os.path.join(session_dir, "cleaned.parquet")
                if os.path.exists(parquet_path):
                    new_state["df_clean"] = pl.read_parquet(parquet_path)
                model_path = os.path.join(session_dir, "model.pkl")
                if os.path.exists(model_path):
                    with open(model_path, "rb") as f:
                        model = pickle.load(f)
                    algo_result = {
                        "model": model,
                        "metrics": report.get("metrics", {}),
                        "y_pred": [], "y_test": [],
                        "feature_names": report["features"],
                        "feature_importances": None,
                        "problem_type": report["problem"],
                    }
                    new_state["train_result"] = {
                        "results": {winner: algo_result} if winner else {},
                        "winner": winner,
                        "problem_type": report["problem"],
                    }
                nb = os.path.join(session_dir, "notebook.ipynb")
                if os.path.exists(nb):
                    new_state["notebook_path"] = nb
                st.session_state["ml_pipeline"] = new_state
                st.rerun()


def render_ml_studio():
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _init_state()

    # ── Top-level split: Pipeline vs Stat Tests
    top_tab_pipeline, top_tab_stats = st.tabs(["⬢ ML PIPELINE", "◎ STATISTICS & ML"])

    with top_tab_stats:
        from modules.ml_pipeline.statistical_tests import render_stat_tests
        render_stat_tests()

    with top_tab_pipeline:
        _render_pipeline()


def _render_pipeline():
    s = _state()
    step = s.get("step", 0)

    step_labels = ["⬡ Upload", "◎ Header", "◈ EDA", "⬢ Clean", "⟁ AI Rec", "△ Features", "◉ Train", "◈ Results"]
    progress_cols = st.columns(len(step_labels))
    for i, label in enumerate(step_labels):
        with progress_cols[i]:
            if i < step:
                st.markdown(
                    f'<span style="color:#3d5a6b;font-family:\'JetBrains Mono\',monospace;font-size:11px;">'
                    f'<s>{label}</s></span>',
                    unsafe_allow_html=True,
                )
            elif i == step:
                st.markdown(
                    f'<span style="color:#00d4ff;font-family:\'JetBrains Mono\',monospace;font-size:11px;font-weight:700;">'
                    f'▶ {label}</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span style="color:#3d5a6b;font-family:\'JetBrains Mono\',monospace;font-size:11px;">'
                    f'{label}</span>',
                    unsafe_allow_html=True,
                )

    st.divider()

    # Back button — show for steps 1–5 (not upload, not results)
    if 1 <= step <= 5:
        if st.button("◁  Back", key="step_back"):
            _go_back()

    if step == 0:
        _step0_upload()
    elif step == 1:
        _step1_header()
    elif step == 2:
        _step2_eda()
    elif step == 3:
        _step3_clean()
    elif step == 4:
        _step4_ai_recommend()
    elif step == 5:
        _step5_features()
    elif step == 6:
        _step6_train()
    elif step >= 7:
        _step7_results()

    _render_history()
