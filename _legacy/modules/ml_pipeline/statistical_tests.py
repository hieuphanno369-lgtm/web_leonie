# modules/ml_pipeline/statistical_tests.py
"""
FMCG Statistical Tests — Bootstrap, A/B Campaign, Seasonal, Correlation, Market Share
Pattern: compute → store in session_state → always render from state (results persist).
"""
import numpy as np
import polars as pl
import polars.selectors as cs
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats

from modules.ai_client import call_ai


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _sh(icon: str, title: str, color: str = "#00d4ff", subtitle: str = ""):
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:9px;padding:2px 0 8px;">'
        f'<span style="color:{color};font-size:20px;line-height:1">{icon}</span>'
        f'<div>'
        f'<div style="font-size:13px;font-weight:700;color:#e6edf3;letter-spacing:.07em;'
        f'font-family:\'JetBrains Mono\',monospace">{title}</div>'
        + (f'<div style="font-size:9px;color:#3d5a6b;letter-spacing:.18em;'
           f'font-family:\'JetBrains Mono\',monospace">{subtitle}</div>' if subtitle else "")
        + f'</div></div>',
        unsafe_allow_html=True,
    )


def _running_badge():
    """Visual badge shown while computing."""
    st.markdown(
        '<div style="display:inline-flex;align-items:center;gap:6px;'
        'background:#0d1f2d;border:1px solid #00d4ff33;border-radius:4px;'
        'padding:4px 10px;font-family:\'JetBrains Mono\',monospace;font-size:11px;">'
        '<span style="color:#00d4ff;animation:pulse 1s infinite">⟳</span>'
        '<span style="color:#8b949e">Đang tính toán...</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def _result_banner(text: str, ok: bool = True):
    color = "#30d158" if ok else "#ff9f0a"
    icon = "✅" if ok else "⬡"
    st.markdown(
        f'<div style="background:{color}18;border:1px solid {color}44;border-radius:6px;'
        f'padding:8px 14px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:{color}">'
        f'{icon} {text}</div>',
        unsafe_allow_html=True,
    )


def _ai_explain(result_text: str, test_name: str, context: str = "") -> str:
    ctx_line = f"Ngữ cảnh: {context}\n" if context else ""
    prompt = (
        f"Bạn là chuyên gia phân tích FMCG. Giải thích kết quả kiểm định bằng tiếng Việt "
        f"cho marketing/sales manager (không có nền tảng thống kê).\n\n"
        f"Kiểm định: {test_name}\nKết quả: {result_text}\n{ctx_line}\n"
        f"Viết ĐÚNG format (dùng đúng ký tự này, không thay đổi):\n"
        f"**▣ Kết quả:** [1 câu — số + ý nghĩa, không dùng p-value/statistic]\n"
        f"**◉ Nghĩa là gì:** [1-2 câu business terms]\n"
        f"**▸ Gợi ý:** [1 câu action cụ thể]\n"
        f"**◇ Hỏi thêm:**\n- [câu 1]\n- [câu 2]\n- [câu 3]"
    )
    try:
        return call_ai(prompt, max_tokens=500)
    except Exception as e:
        return f"*(AI không phản hồi: {e})*"


def _get_df(key_prefix: str) -> "pl.DataFrame | None":
    ml_df = st.session_state.get("ml_pipeline", {}).get("df_clean")
    use_existing = False
    if ml_df is not None and isinstance(ml_df, pl.DataFrame) and ml_df.height > 0:
        use_existing = st.checkbox(
            f"Dùng dataset từ ML Pipeline ({ml_df.height:,} rows × {ml_df.width} cols)",
            value=True, key=f"{key_prefix}_use_existing",
        )
    if use_existing and ml_df is not None:
        return ml_df
    import io
    uploaded = st.file_uploader("Upload CSV / Excel", type=["csv", "xlsx"],
                                key=f"{key_prefix}_upload")
    if uploaded is None:
        return None
    raw = uploaded.read()
    if uploaded.name.endswith(".xlsx"):
        import pandas as pd
        return pl.from_pandas(pd.read_excel(io.BytesIO(raw)))
    return pl.read_csv(io.BytesIO(raw), infer_schema_length=500, encoding="utf8-lossy")


def _followup_widget(prefix: str, context: str, test_name: str, metric: str):
    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.1em;'
        'font-family:\'JetBrains Mono\',monospace;margin-bottom:8px">HỎI THÊM VỀ KẾT QUẢ NÀY</div>',
        unsafe_allow_html=True,
    )
    suggestions = [
        f"Kết quả {test_name} này ảnh hưởng gì đến quyết định business?",
        "Cần thêm dữ liệu gì để kết luận chắc chắn hơn?",
        "Sample size có đủ lớn để tin tưởng kết quả không?",
    ]
    fkey = f"{prefix}_followup_text"
    if fkey not in st.session_state:
        st.session_state[fkey] = ""
    q_cols = st.columns(3)
    for i, q in enumerate(suggestions):
        with q_cols[i]:
            if st.button(f"❓ {q}", key=f"{prefix}_sugg_{i}", use_container_width=True):
                st.session_state[fkey] = q
                st.rerun()
    followup = st.text_input("Hoặc tự hỏi:", key=fkey,
                             placeholder="Nhập câu hỏi của bạn...")
    if followup and st.button("▶ Hỏi AI", key=f"{prefix}_ask_ai"):
        with st.spinner("🤖 AI đang trả lời..."):
            prompt = (
                f"Chuyên gia FMCG. Kiểm định: {test_name}, metric: {metric}\n"
                f"Kết quả: {context[:600]}\nCâu hỏi: {followup}\n"
                f"Trả lời bằng tiếng Việt, ≤5 câu, business-focused."
            )
            try:
                ans = call_ai(prompt, max_tokens=400)
                st.info(f"◈ AI: {ans}")
            except Exception as e:
                st.error(f"AI lỗi: {e}")


# ── 1. Bootstrap ───────────────────────────────────────────────────────────────

def render_bootstrap():
    _sh("◎", "BOOTSTRAP", color="#00d4ff",
        subtitle="CONFIDENCE INTERVAL + 2-SAMPLE COMPARISON // KHÔNG CẦN PHÂN PHỐI CHUẨN")

    df = _get_df("boot")
    if df is None:
        st.info("Upload dữ liệu hoặc chạy ML Pipeline trước."); return

    num_cols = df.select(cs.numeric()).columns
    if not num_cols:
        st.error("Không có cột số."); return

    mode = st.radio("Chế độ", ["📊 Confidence Interval (1 metric)", "⚖️ So sánh 2 nhóm"],
                    horizontal=True, key="boot_mode")
    col = st.selectbox("Metric (cột số)", num_cols, key="boot_col")
    n_iter = st.slider("Số lần Bootstrap", 500, 5000, 1000, step=500, key="boot_iter")
    ci = st.slider("Mức tin cậy (%)", 90, 99, 95, key="boot_ci")
    alpha = (100 - ci) / 100

    g1_data = g2_data = None
    g1_label = g2_label = ""

    if mode == "⚖️ So sánh 2 nhóm":
        cat_cols = [c for c in df.columns if c not in num_cols]
        if not cat_cols:
            st.warning("Cần có cột phân loại để chia nhóm."); return
        grp_col = st.selectbox("Cột nhóm", cat_cols, key="boot_gcol")
        unique_v = df[grp_col].drop_nulls().unique().to_list()
        if len(unique_v) < 2:
            st.warning("Cần ít nhất 2 giá trị."); return
        chosen = st.multiselect("Chọn 2 nhóm", unique_v, default=unique_v[:2],
                                max_selections=2, key="boot_groups")
        if len(chosen) == 2:
            g1_data = df.filter(pl.col(grp_col) == chosen[0])[col].drop_nulls().to_numpy().astype(float)
            g2_data = df.filter(pl.col(grp_col) == chosen[1])[col].drop_nulls().to_numpy().astype(float)
            g1_label, g2_label = str(chosen[0]), str(chosen[1])

    # ── Run button
    if st.button("▶ Chạy Bootstrap", key="boot_run", type="primary"):
        data = df[col].drop_nulls().to_numpy().astype(float)
        with st.status(f"⟳ COMPUTING BOOTSTRAP — {n_iter:,} iterations...", expanded=True) as _status:
            st.write(f"▸ Resampling {len(data):,} observations × {n_iter:,} rounds")
            rng = np.random.default_rng(42)
            if mode == "📊 Confidence Interval (1 metric)":
                boot_means = np.array([
                    np.mean(rng.choice(data, size=len(data), replace=True))
                    for _ in range(n_iter)
                ])
                lo = float(np.percentile(boot_means, 100 * alpha / 2))
                hi = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
                st.session_state["boot_result"] = {
                    "mode": "ci", "col": col, "ci": ci, "n": len(data),
                    "mean": float(np.mean(data)), "lo": lo, "hi": hi,
                    "boot_means": boot_means.tolist(),
                    "result_text": f"Mean={np.mean(data):.3f}, CI {ci}%=[{lo:.3f},{hi:.3f}], n={len(data)}",
                }
            else:
                if g1_data is None or g2_data is None:
                    st.warning("Chọn đủ 2 nhóm."); _status.update(label="⚠ Chưa đủ nhóm", state="error"); return
                obs_diff = float(np.mean(g1_data) - np.mean(g2_data))
                st.write(f"▸ {g1_label}: n={len(g1_data):,}   {g2_label}: n={len(g2_data):,}")
                boot_diffs = np.array([
                    np.mean(rng.choice(g1_data, len(g1_data), replace=True))
                    - np.mean(rng.choice(g2_data, len(g2_data), replace=True))
                    for _ in range(n_iter)
                ])
                lo = float(np.percentile(boot_diffs, 100 * alpha / 2))
                hi = float(np.percentile(boot_diffs, 100 * (1 - alpha / 2)))
                significant = lo > 0 or hi < 0
                st.session_state["boot_result"] = {
                    "mode": "2sample", "col": col, "ci": ci,
                    "g1_label": g1_label, "g2_label": g2_label,
                    "g1_mean": float(np.mean(g1_data)), "g2_mean": float(np.mean(g2_data)),
                    "g1_n": len(g1_data), "g2_n": len(g2_data),
                    "obs_diff": obs_diff, "lo": lo, "hi": hi,
                    "significant": significant,
                    "boot_diffs": boot_diffs.tolist(),
                    "result_text": (
                        f"Nhóm {g1_label}: mean={np.mean(g1_data):.3f} (n={len(g1_data)}), "
                        f"Nhóm {g2_label}: mean={np.mean(g2_data):.3f} (n={len(g2_data)}), "
                        f"Diff CI {ci}%=[{lo:.3f},{hi:.3f}], "
                        f"{'Có ý nghĩa' if significant else 'Chưa có ý nghĩa'}"
                    ),
                }
            _status.update(label="◈ BOOTSTRAP COMPLETE", state="complete", expanded=False)
        st.session_state.pop("boot_ai", None)  # reset AI cache when re-running

    # ── Always render result from state
    r = st.session_state.get("boot_result")
    if r is None:
        return

    st.markdown("---")
    if r["mode"] == "ci":
        boot_means = np.array(r["boot_means"])
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=boot_means, nbinsx=50, marker_color="#00d4ff",
                                   opacity=0.7, name="Bootstrap means"))
        fig.add_vline(x=r["lo"], line_color="#ff2d55", line_dash="dash",
                      annotation_text=f"Lower {r['lo']:.3f}")
        fig.add_vline(x=r["hi"], line_color="#30d158", line_dash="dash",
                      annotation_text=f"Upper {r['hi']:.3f}")
        fig.add_vline(x=r["mean"], line_color="#ff9f0a",
                      annotation_text=f"Mean {r['mean']:.3f}")
        fig.update_layout(template="plotly_dark", title=f"Bootstrap Distribution — {r['col']}")
        st.plotly_chart(fig, use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Mean", f"{r['mean']:.3f}")
        c2.metric(f"Lower {r['ci']}% CI", f"{r['lo']:.3f}")
        c3.metric(f"Upper {r['ci']}% CI", f"{r['hi']:.3f}")
        _result_banner(f"Với {r['ci']}% tin cậy: {r['col']} nằm trong [{r['lo']:.3f}, {r['hi']:.3f}]")
    else:
        boot_diffs = np.array(r["boot_diffs"])
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=boot_diffs, nbinsx=50, marker_color="#bd00ff",
                                   opacity=0.7, name="Bootstrap diffs"))
        fig.add_vline(x=r["lo"], line_color="#ff2d55", line_dash="dash",
                      annotation_text=f"Lower {r['lo']:.3f}")
        fig.add_vline(x=r["hi"], line_color="#30d158", line_dash="dash",
                      annotation_text=f"Upper {r['hi']:.3f}")
        fig.add_vline(x=0, line_color="#8b949e", line_dash="dot", annotation_text="No diff")
        fig.add_vline(x=r["obs_diff"], line_color="#ff9f0a",
                      annotation_text=f"Observed {r['obs_diff']:.3f}")
        fig.update_layout(template="plotly_dark",
                          title=f"Bootstrap: {r['g1_label']} vs {r['g2_label']} — {r['col']}")
        st.plotly_chart(fig, use_container_width=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Mean {r['g1_label']}", f"{r['g1_mean']:.3f}")
        c2.metric(f"Mean {r['g2_label']}", f"{r['g2_mean']:.3f}")
        c3.metric(f"Lower {r['ci']}% CI", f"{r['lo']:.3f}")
        c4.metric(f"Upper {r['ci']}% CI", f"{r['hi']:.3f}")
        _result_banner(
            f"Sự khác biệt {'CÓ' if r['significant'] else 'CHƯA'} ý nghĩa thống kê "
            f"({r['ci']}% CI {'không chứa 0' if r['significant'] else 'chứa 0'})",
            ok=r["significant"],
        )

    # ── AI explanation (cached per run)
    if "boot_ai" not in st.session_state:
        with st.spinner("🤖 AI đang giải thích kết quả..."):
            ai = _ai_explain(r["result_text"], "Bootstrap", f"Metric: {r['col']}")
        st.session_state["boot_ai"] = ai
    if st.session_state.get("boot_ai"):
        st.markdown(st.session_state["boot_ai"])
        _followup_widget("boot", r["result_text"], "Bootstrap", r["col"])


# ── 2. A/B Campaign Test ───────────────────────────────────────────────────────

def render_ab_test():
    _sh("⟁", "A/B CAMPAIGN TEST", color="#ff9f0a",
        subtitle="T-TEST + MANN-WHITNEY // TỰ CHỌN TEST DỰA TRÊN PHÂN PHỐI DỮ LIỆU")

    df = _get_df("ab")
    if df is None:
        st.info("Upload dữ liệu hoặc chạy ML Pipeline trước."); return

    num_cols = df.select(cs.numeric()).columns
    cat_cols = [c for c in df.columns if c not in num_cols]
    if not num_cols:
        st.error("Không có cột số."); return

    col = st.selectbox("Metric (GMV, đơn hàng...)", num_cols, key="ab_col")
    gmode = st.radio("Chế độ nhóm",
                     ["Cột phân loại (campaign, region...)", "So sánh 2 cột số trực tiếp"],
                     horizontal=True, key="ab_gmode")

    g1_data = g2_data = None
    g1_label = g2_label = ""

    if gmode == "Cột phân loại (campaign, region...)":
        if not cat_cols:
            st.warning("Không có cột phân loại."); return
        grp_col = st.selectbox("Cột nhóm", cat_cols, key="ab_gcol")
        unique_v = df[grp_col].drop_nulls().unique().to_list()
        chosen = st.multiselect("Chọn 2 nhóm", unique_v, default=unique_v[:2],
                                max_selections=2, key="ab_groups")
        if len(chosen) == 2:
            g1_data = df.filter(pl.col(grp_col) == chosen[0])[col].drop_nulls().to_numpy().astype(float)
            g2_data = df.filter(pl.col(grp_col) == chosen[1])[col].drop_nulls().to_numpy().astype(float)
            g1_label, g2_label = str(chosen[0]), str(chosen[1])
    else:
        ca, cb = st.columns(2)
        with ca:
            col_a = st.selectbox("Cột A (trước/control)", num_cols, key="ab_cola")
        with cb:
            remaining = [c for c in num_cols if c != col_a] or list(num_cols)
            col_b = st.selectbox("Cột B (sau/treatment)", remaining, key="ab_colb")
        g1_data = df[col_a].drop_nulls().to_numpy().astype(float)
        g2_data = df[col_b].drop_nulls().to_numpy().astype(float)
        g1_label, g2_label = col_a, col_b

    alpha = st.slider("Mức ý nghĩa (α)", 0.01, 0.10, 0.05, step=0.01, key="ab_alpha",
                      help="Thường dùng 0.05 — xác suất kết luận sai tối đa cho phép")

    if st.button("▶ Chạy A/B Test", key="ab_run", type="primary"):
        if g1_data is None or g2_data is None:
            st.warning("Chọn đủ 2 nhóm trước."); return
        with st.status("⟳ COMPUTING A/B TEST...", expanded=True) as _status:
            n1, n2 = len(g1_data), len(g2_data)
            st.write(f"▸ Shapiro-Wilk normality check  ({g1_label}: n={n1:,}, {g2_label}: n={n2:,})")
            _, p_norm1 = stats.shapiro(g1_data[:min(n1, 5000)])
            _, p_norm2 = stats.shapiro(g2_data[:min(n2, 5000)])
            is_normal = p_norm1 > 0.05 and p_norm2 > 0.05
            if is_normal:
                st.write("▸ Phân phối chuẩn → chạy T-test")
                stat, p_val = stats.ttest_ind(g1_data, g2_data)
                test_used = "T-test (phân phối chuẩn)"
            else:
                st.write("▸ Không chuẩn → chạy Mann-Whitney U")
                stat, p_val = stats.mannwhitneyu(g1_data, g2_data, alternative="two-sided")
                test_used = "Mann-Whitney U (không chuẩn)"
            st.write("▸ Tính Cohen's d effect size...")
            pooled_std = np.sqrt((np.std(g1_data) ** 2 + np.std(g2_data) ** 2) / 2)
            cohens_d = float((np.mean(g1_data) - np.mean(g2_data)) / pooled_std) if pooled_std > 0 else 0.0
            significant = float(p_val) < alpha
            effect = "lớn" if abs(cohens_d) >= 0.8 else "trung bình" if abs(cohens_d) >= 0.3 else "nhỏ"
            st.session_state["ab_result"] = {
                "col": col, "g1_label": g1_label, "g2_label": g2_label,
                "g1_mean": float(np.mean(g1_data)), "g2_mean": float(np.mean(g2_data)),
                "g1_std": float(np.std(g1_data)), "g2_std": float(np.std(g2_data)),
                "n1": n1, "n2": n2,
                "g1_data": g1_data.tolist(), "g2_data": g2_data.tolist(),
                "test_used": test_used, "p_val": float(p_val), "stat": float(stat),
                "cohens_d": cohens_d, "effect": effect,
                "significant": significant, "alpha": alpha,
                "result_text": (
                    f"Nhóm A ({g1_label}): mean={np.mean(g1_data):.3f} n={n1}, "
                    f"Nhóm B ({g2_label}): mean={np.mean(g2_data):.3f} n={n2}, "
                    f"Test: {test_used}, p={p_val:.4f}, "
                    f"{'Có ý nghĩa' if significant else 'Không ý nghĩa'}, "
                    f"Cohen's d={cohens_d:.3f} ({effect})"
                ),
            }
            _status.update(label="◈ A/B TEST COMPLETE", state="complete", expanded=False)
        st.session_state.pop("ab_ai", None)

    r = st.session_state.get("ab_result")
    if r is None:
        return

    st.markdown("---")
    import pandas as pd
    fig = go.Figure()
    fig.add_trace(go.Box(y=r["g1_data"], name=r["g1_label"], marker_color="#00d4ff", boxmean=True))
    fig.add_trace(go.Box(y=r["g2_data"], name=r["g2_label"], marker_color="#bd00ff", boxmean=True))
    fig.update_layout(template="plotly_dark", title=f"A/B Distribution — {r['col']}")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Mean {r['g1_label']}", f"{r['g1_mean']:.3f}", f"±{r['g1_std']:.3f}")
    c2.metric(f"Mean {r['g2_label']}", f"{r['g2_mean']:.3f}", f"±{r['g2_std']:.3f}")
    c3.metric("p-value", f"{r['p_val']:.4f}")
    c4.metric("Cohen's d", f"{r['cohens_d']:.3f}", r["effect"])

    _result_banner(
        f"Sự khác biệt {'CÓ' if r['significant'] else 'CHƯA'} ý nghĩa (p={r['p_val']:.4f} "
        f"{'<' if r['significant'] else '≥'} α={r['alpha']}) — {r['test_used']}",
        ok=r["significant"],
    )
    st.caption(f"📏 Effect size {r['effect']}: Cohen's d = {r['cohens_d']:.3f}")

    if "ab_ai" not in st.session_state:
        with st.spinner("🤖 AI đang giải thích kết quả..."):
            ai = _ai_explain(r["result_text"], "A/B Campaign Test", f"Metric: {r['col']}")
        st.session_state["ab_ai"] = ai
    if st.session_state.get("ab_ai"):
        st.markdown(st.session_state["ab_ai"])
        _followup_widget("ab", r["result_text"], "A/B Test", r["col"])


# ── 3. Seasonal Test ───────────────────────────────────────────────────────────

def render_seasonal_test():
    _sh("△", "SEASONAL TEST (KRUSKAL-WALLIS)", color="#30d158",
        subtitle="DOANH SỐ THEO MÙA / QUÝ / THÁNG + POST-HOC PAIRWISE")

    df = _get_df("season")
    if df is None:
        st.info("Upload dữ liệu hoặc chạy ML Pipeline trước."); return

    num_cols = df.select(cs.numeric()).columns
    if not num_cols:
        st.error("Không có cột số."); return

    col = st.selectbox("Metric (GMV, đơn hàng, doanh thu...)", num_cols, key="season_col")
    gmode = st.radio("Phân nhóm theo",
                     ["Cột có sẵn (region, quarter, category...)",
                      "Tự phân theo tháng/quý từ date column"],
                     horizontal=True, key="season_gmode")

    groups_data: dict = {}
    group_label = ""

    if gmode == "Cột có sẵn (region, quarter, category...)":
        others = [c for c in df.columns if c != col]
        if not others:
            st.warning("Không có cột khác."); return
        gcol = st.selectbox("Cột nhóm", others, key="season_gcol")
        group_label = gcol
        for g in df[gcol].drop_nulls().unique().to_list():
            d = df.filter(pl.col(gcol) == g)[col].drop_nulls().to_numpy().astype(float)
            if len(d) >= 3:
                groups_data[str(g)] = d
    else:
        date_hints = [c for c in df.columns if any(
            k in c.lower() for k in ["date", "month", "year", "ngay", "thang", "time"]
        )]
        date_cols = date_hints or [c for c in df.columns if c not in num_cols]
        if not date_cols:
            st.warning("Không tìm thấy cột date."); return
        date_col = st.selectbox("Cột ngày tháng", date_cols, key="season_date")
        period = st.radio("Phân theo", ["Tháng", "Quý"], horizontal=True, key="season_period")
        try:
            temp = df.with_columns(pl.col(date_col).cast(pl.Date, strict=False))
            if period == "Tháng":
                temp = temp.with_columns(pl.col(date_col).dt.month().alias("_p"))
                lmap = {i: f"T{i:02d}" for i in range(1, 13)}
            else:
                temp = temp.with_columns(pl.col(date_col).dt.quarter().alias("_p"))
                lmap = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
            for p in sorted(temp["_p"].drop_nulls().unique().to_list()):
                d = temp.filter(pl.col("_p") == p)[col].drop_nulls().to_numpy().astype(float)
                if len(d) >= 3:
                    groups_data[lmap.get(int(p), str(p))] = d
            group_label = period
        except Exception as e:
            st.error(f"Lỗi parse date: {e}"); return

    if len(groups_data) < 2:
        st.warning("Cần ít nhất 2 nhóm (mỗi nhóm ≥ 3 quan sát)."); return

    alpha = st.slider("Mức ý nghĩa (α)", 0.01, 0.10, 0.05, step=0.01, key="season_alpha")

    if st.button("▶ Chạy Seasonal Test", key="season_run", type="primary"):
        with st.status(f"⟳ COMPUTING KRUSKAL-WALLIS — {len(groups_data)} nhóm...", expanded=True) as _status:
            st.write(f"▸ Nhóm: {', '.join(groups_data.keys())}")
            stat, p_val = stats.kruskal(*list(groups_data.values()))
            significant = float(p_val) < alpha
            pairs = []
            if significant:
                st.write("▸ Có ý nghĩa → chạy post-hoc pairwise Mann-Whitney...")
                gnames = list(groups_data.keys())
                for i in range(len(gnames)):
                    for j in range(i + 1, len(gnames)):
                        _, pp = stats.mannwhitneyu(
                            groups_data[gnames[i]], groups_data[gnames[j]],
                            alternative="two-sided",
                        )
                        pairs.append({
                            "Nhóm A": gnames[i], "Nhóm B": gnames[j],
                            "p-value": round(float(pp), 4),
                            "Khác biệt?": "✅" if pp < alpha else "—",
                        })
            means = {g: float(np.mean(d)) for g, d in groups_data.items()}
            st.session_state["season_result"] = {
                "col": col, "group_label": group_label, "alpha": alpha,
                "stat": float(stat), "p_val": float(p_val), "significant": significant,
                "means": means, "pairs": pairs,
                "plot_data": {g: d.tolist() for g, d in groups_data.items()},
                "result_text": (
                    f"Kruskal-Wallis: H={stat:.4f}, p={p_val:.4f}, "
                    f"{'Có ý nghĩa' if significant else 'Không ý nghĩa'}, "
                    f"Mean từng nhóm: {means}"
                ),
            }
            _status.update(label="◈ SEASONAL TEST COMPLETE", state="complete", expanded=False)
        st.session_state.pop("season_ai", None)

    r = st.session_state.get("season_result")
    if r is None:
        return

    st.markdown("---")
    import pandas as pd
    vals, grps = [], []
    for g, d in r["plot_data"].items():
        vals.extend(d); grps.extend([g] * len(d))
    fig = px.violin(
        pd.DataFrame({"value": vals, "group": grps}),
        x="group", y="value", box=True,
        color_discrete_sequence=["#30d158"],
        template="plotly_dark",
        title=f"Phân phối {r['col']} theo {r['group_label']}",
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Kruskal-Wallis H", f"{r['stat']:.4f}")
    c2.metric("p-value", f"{r['p_val']:.4f}")
    c3.metric("Số nhóm", len(r["plot_data"]))

    _result_banner(
        f"Doanh số theo mùa {'CÓ' if r['significant'] else 'CHƯA'} khác biệt "
        f"(p={r['p_val']:.4f} {'<' if r['significant'] else '≥'} α={r['alpha']})",
        ok=r["significant"],
    )

    if r["pairs"]:
        st.write("**So sánh từng cặp (Post-hoc Mann-Whitney):**")
        st.dataframe(pl.DataFrame(r["pairs"]).to_pandas(), use_container_width=True)

    if "season_ai" not in st.session_state:
        with st.spinner("🤖 AI đang giải thích kết quả..."):
            ai = _ai_explain(r["result_text"], "Seasonal Test",
                             f"Metric: {r['col']}, Nhóm: {r['group_label']}")
        st.session_state["season_ai"] = ai
    if st.session_state.get("season_ai"):
        st.markdown(st.session_state["season_ai"])
        _followup_widget("season", r["result_text"], "Seasonal Test", r["col"])


# ── 4. Correlation Test ────────────────────────────────────────────────────────

def render_correlation_test():
    _sh("◈", "CORRELATION TEST", color="#bd00ff",
        subtitle="PEARSON + SPEARMAN // SPEND vs GMV // LINEAR & MONOTONIC")

    df = _get_df("corr")
    if df is None:
        st.info("Upload dữ liệu hoặc chạy ML Pipeline trước."); return

    num_cols = df.select(cs.numeric()).columns
    if len(num_cols) < 2:
        st.error("Cần ít nhất 2 cột số."); return

    ca, cb = st.columns(2)
    with ca:
        col_x = st.selectbox("Biến X (ngân sách, spend...)", num_cols, key="corr_x")
    with cb:
        remaining = [c for c in num_cols if c != col_x] or list(num_cols)
        col_y = st.selectbox("Biến Y (GMV, đơn hàng...)", remaining, key="corr_y")

    alpha = st.slider("Mức ý nghĩa (α)", 0.01, 0.10, 0.05, step=0.01, key="corr_alpha")

    if st.button("▶ Chạy Correlation", key="corr_run", type="primary"):
        with st.status("⟳ COMPUTING CORRELATION...", expanded=True) as _status:
            x = df[col_x].drop_nulls().to_numpy().astype(float)
            y = df[col_y].drop_nulls().to_numpy().astype(float)
            n = min(len(x), len(y))
            x, y = x[:n], y[:n]
            st.write(f"▸ n={n:,} observations  |  X: {col_x}  →  Y: {col_y}")
            st.write("▸ Pearson r (linear)...")
            r_p, p_p = stats.pearsonr(x, y)
            st.write("▸ Spearman ρ (monotonic)...")
            r_s, p_s = stats.spearmanr(x, y)
            strength = (
                "rất mạnh" if abs(r_p) > 0.8 else "mạnh" if abs(r_p) > 0.6
                else "trung bình" if abs(r_p) > 0.4 else "yếu" if abs(r_p) > 0.2
                else "rất yếu"
            )
            direction = "thuận" if r_p > 0 else "nghịch"
            significant = float(p_p) < alpha
            r2 = float(r_p ** 2)
            st.session_state["corr_result"] = {
                "col_x": col_x, "col_y": col_y, "n": n, "alpha": alpha,
                "r_p": float(r_p), "p_p": float(p_p),
                "r_s": float(r_s), "p_s": float(p_s),
                "r2": r2, "strength": strength, "direction": direction,
                "significant": significant,
                "x": x.tolist(), "y": y.tolist(),
                "result_text": (
                    f"Pearson r={r_p:.4f} (p={p_p:.4f}), "
                    f"Spearman ρ={r_s:.4f} (p={p_s:.4f}), "
                    f"n={n}, R²={r2:.3f}, "
                    f"Tương quan {direction} {strength}, "
                    f"{'Có ý nghĩa' if significant else 'Không ý nghĩa'}"
                ),
            }
            _status.update(label="◈ CORRELATION COMPLETE", state="complete", expanded=False)
        st.session_state.pop("corr_ai", None)

    r = st.session_state.get("corr_result")
    if r is None:
        return

    st.markdown("---")
    import pandas as pd
    fig = px.scatter(
        pd.DataFrame({r["col_x"]: r["x"], r["col_y"]: r["y"]}),
        x=r["col_x"], y=r["col_y"],
        trendline="ols", trendline_color_override="#ff9f0a",
        template="plotly_dark",
        title=f"Correlation: {r['col_x']} vs {r['col_y']}",
    )
    fig.update_traces(marker=dict(color="#00d4ff", size=6, opacity=0.7),
                      selector=dict(mode="markers"))
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pearson r", f"{r['r_p']:.4f}")
    c2.metric("p (Pearson)", f"{r['p_p']:.4f}")
    c3.metric("Spearman ρ", f"{r['r_s']:.4f}")
    c4.metric("R²", f"{r['r2']:.3f}")

    _result_banner(
        f"Tương quan {r['direction']} {r['strength']} — "
        f"{'CÓ' if r['significant'] else 'CHƯA'} ý nghĩa "
        f"(r={r['r_p']:.3f}, p={r['p_p']:.4f})",
        ok=r["significant"],
    )
    st.caption(
        f"📐 R² = {r['r2']:.3f} → {r['col_x']} giải thích được "
        f"{r['r2']*100:.1f}% biến động của {r['col_y']}"
    )

    if "corr_ai" not in st.session_state:
        with st.spinner("🤖 AI đang giải thích kết quả..."):
            ai = _ai_explain(r["result_text"], "Correlation Test",
                             f"X: {r['col_x']}, Y: {r['col_y']}")
        st.session_state["corr_ai"] = ai
    if st.session_state.get("corr_ai"):
        st.markdown(st.session_state["corr_ai"])
        _followup_widget("corr", r["result_text"], "Correlation",
                         f"{r['col_x']} vs {r['col_y']}")


# ── 5. Market Share Chi-square ─────────────────────────────────────────────────

def render_chi_square():
    _sh("⬢", "MARKET SHARE SHIFT (CHI-SQUARE)", color="#ff2d55",
        subtitle="THỊ PHẦN BRAND THAY ĐỔI CÓ Ý NGHĨA THỐNG KÊ?")

    df = _get_df("chi")
    if df is None:
        st.info("Upload dữ liệu hoặc chạy ML Pipeline trước."); return

    num_cols = df.select(cs.numeric()).columns
    cat_cols = [c for c in df.columns if c not in num_cols]

    mode = st.radio("Chế độ nhập liệu",
                    ["Nhập % thị phần thủ công", "Từ dữ liệu (cột brand + doanh số + kỳ)"],
                    horizontal=True, key="chi_mode")

    brands: list = []
    prev_s: list = []
    curr_s: list = []
    label_prev = "Kỳ trước"
    label_curr = "Kỳ này"
    ready = False

    if mode == "Nhập % thị phần thủ công":
        n_brands = int(st.number_input("Số thương hiệu", min_value=2, max_value=8,
                                       value=3, key="chi_n"))
        st.write("**Nhập thị phần (%) từng brand:**")
        for i in range(n_brands):
            ca, cb, cc = st.columns(3)
            with ca:
                brands.append(st.text_input(f"Brand {i+1}", value=f"Brand {i+1}", key=f"chi_b_{i}"))
            with cb:
                prev_s.append(st.number_input(f"Kỳ trước (%)", 0.0, 100.0,
                                              round(100 / n_brands, 1), key=f"chi_p_{i}"))
            with cc:
                curr_s.append(st.number_input(f"Kỳ này (%)", 0.0, 100.0,
                                              round(100 / n_brands, 1), key=f"chi_c_{i}"))
        ready = True
    else:
        if not cat_cols or not num_cols:
            st.warning("Cần có cột phân loại (brand) và cột số (doanh số)."); return
        brand_col = st.selectbox("Cột thương hiệu/sản phẩm", cat_cols, key="chi_bcol")
        val_col = st.selectbox("Cột doanh số/số lượng", num_cols, key="chi_vcol")
        period_col = st.selectbox("Cột kỳ/thời gian",
                                  ["— (so với phân phối đồng đều)"] + list(df.columns),
                                  key="chi_pcol")
        ready = True

    if ready and st.button("▶ Kiểm định Market Share", key="chi_run", type="primary"):
        with st.status("⟳ COMPUTING CHI-SQUARE MARKET SHARE...", expanded=True) as _status:
            if mode == "Nhập % thị phần thủ công":
                st.write(f"▸ {len(brands)} brands, mode: thủ công")
                obs = np.array(curr_s, dtype=float)
                exp_pct = np.array(prev_s, dtype=float)
                if obs.sum() == 0 or exp_pct.sum() == 0:
                    st.error("Tổng thị phần = 0."); _status.update(label="⚠ Lỗi dữ liệu", state="error"); return
                exp = exp_pct / exp_pct.sum() * obs.sum()
                chi2, p_val = stats.chisquare(obs, f_exp=exp)
            else:
                no_period = period_col == "— (so với phân phối đồng đều)"
                if no_period:
                    st.write("▸ So sánh với phân phối đồng đều...")
                    agg = df.group_by(brand_col).agg(pl.col(val_col).sum())
                    brands = [str(b) for b in agg[brand_col].to_list()]
                    curr_arr = np.array(agg[val_col].to_list(), dtype=float)
                    prev_arr = np.full_like(curr_arr, curr_arr.mean())
                    label_prev, label_curr = "Đồng đều", "Thực tế"
                else:
                    periods = sorted(df[period_col].drop_nulls().unique().to_list())
                    if len(periods) < 2:
                        st.warning("Cần ít nhất 2 kỳ."); _status.update(label="⚠ Cần 2 kỳ", state="error"); return
                    p1, p2 = periods[-2], periods[-1]
                    st.write(f"▸ So sánh kỳ {p1} → {p2}")
                    df1 = df.filter(pl.col(period_col) == p1).group_by(brand_col).agg(pl.col(val_col).sum())
                    df2 = df.filter(pl.col(period_col) == p2).group_by(brand_col).agg(pl.col(val_col).sum())
                    brands = sorted(set(df1[brand_col].to_list()) | set(df2[brand_col].to_list()))
                    brands = [str(b) for b in brands]
                    m1 = dict(zip(df1[brand_col].to_list(), df1[val_col].to_list()))
                    m2 = dict(zip(df2[brand_col].to_list(), df2[val_col].to_list()))
                    prev_arr = np.array([m1.get(b, 0) for b in brands], dtype=float)
                    curr_arr = np.array([m2.get(b, 0) for b in brands], dtype=float)
                    label_prev, label_curr = str(p1), str(p2)
                if prev_arr.sum() == 0 or curr_arr.sum() == 0:
                    st.error("Không có dữ liệu."); _status.update(label="⚠ Lỗi dữ liệu", state="error"); return
                exp = prev_arr / prev_arr.sum() * curr_arr.sum()
                chi2, p_val = stats.chisquare(curr_arr, f_exp=exp)
                prev_s = (prev_arr / prev_arr.sum() * 100).tolist()
                curr_s = (curr_arr / curr_arr.sum() * 100).tolist()

            significant = float(p_val) < 0.05
            result_text = (
                f"Chi-square={chi2:.4f}, p={p_val:.4f}, "
                f"{'Thị phần thay đổi có ý nghĩa' if significant else 'Chưa đổi đáng kể'}"
            )
            st.session_state["chi_result"] = {
                "chi2": float(chi2), "p_val": float(p_val), "significant": significant,
                "brands": brands, "prev_s": list(prev_s), "curr_s": list(curr_s),
                "label_prev": label_prev, "label_curr": label_curr,
                "result_text": result_text,
            }
            _status.update(label="◈ MARKET SHARE TEST COMPLETE", state="complete", expanded=False)
        st.session_state.pop("chi_ai", None)

    r = st.session_state.get("chi_result")
    if r is None:
        return

    st.markdown("---")
    import pandas as pd
    plot_df = pd.DataFrame({
        "Brand": r["brands"] * 2,
        "Thị phần (%)": r["prev_s"] + r["curr_s"],
        "Kỳ": [r["label_prev"]] * len(r["brands"]) + [r["label_curr"]] * len(r["brands"]),
    })
    fig = px.bar(
        plot_df, x="Brand", y="Thị phần (%)", color="Kỳ", barmode="group",
        color_discrete_map={r["label_prev"]: "#3d5a6b", r["label_curr"]: "#00d4ff"},
        template="plotly_dark",
        title=f"Market Share: {r['label_prev']} vs {r['label_curr']}",
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    c1.metric("Chi-square statistic", f"{r['chi2']:.4f}")
    c2.metric("p-value", f"{r['p_val']:.4f}")

    _result_banner(
        f"Thị phần {'ĐÃ thay đổi' if r['significant'] else 'CHƯA thay đổi'} có ý nghĩa thống kê "
        f"(p={r['p_val']:.4f} {'< 0.05' if r['significant'] else '≥ 0.05'})",
        ok=r["significant"],
    )

    if "chi_ai" not in st.session_state:
        with st.spinner("🤖 AI đang giải thích kết quả..."):
            ai = _ai_explain(r["result_text"], "Market Share Chi-square",
                             f"Brands: {', '.join(r['brands'])}")
        st.session_state["chi_ai"] = ai
    if st.session_state.get("chi_ai"):
        st.markdown(st.session_state["chi_ai"])
        _followup_widget("chi", r["result_text"], "Chi-square", "Market Share")


# ── Main render ─────────────────────────────────────────────────────────────────

def render_stat_tests():
    t1, t2, t3, t4, t5 = st.tabs([
        "◎ Bootstrap",
        "⟁ A/B Campaign",
        "△ Seasonal Test",
        "◈ Correlation",
        "⬢ Market Share",
    ])
    with t1:
        render_bootstrap()
    with t2:
        render_ab_test()
    with t3:
        render_seasonal_test()
    with t4:
        render_correlation_test()
    with t5:
        render_chi_square()
