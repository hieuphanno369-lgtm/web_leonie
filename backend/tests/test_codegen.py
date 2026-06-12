# backend/tests/test_codegen.py
from analytics.codegen import forecast_code


def _compiles(code: str):
    compile(code, "<generated>", "exec")   # raise SyntaxError nếu code hỏng


def test_forecast_sarimax_code_faithful_and_compiles():
    code = forecast_code(
        method="sarimax", date_col="Order Date", value_col="Sales",
        filename="orders.csv", grain="month", agg="sum",
        seasonal_period=12, periods=6, n=48,
    )
    _compiles(code)
    assert "SARIMAX" in code
    assert "get_forecast" in code
    assert "dt.truncate" in code            # khối gộp thời gian
    assert "f\"" not in code and "f'" not in code   # KHÔNG f-string trong code sinh ra


def test_forecast_linear_uses_linregress():
    code = forecast_code("linear", "d", "v", "x.csv", "week", "sum", 52, 4, 30)
    _compiles(code)
    assert "linregress" in code


def test_forecast_moving_average_uses_mean():
    code = forecast_code("moving_average", "d", "v", "x.csv", "day", "sum", 7, 4, 30)
    _compiles(code)
    assert "mean" in code


def test_forecast_ets_uses_exponential_smoothing():
    code = forecast_code("ets", "d", "v", "x.csv", "month", "sum", 12, 4, 30)
    _compiles(code)
    assert "ExponentialSmoothing" in code


def test_forecast_supervised_uses_ridge():
    code = forecast_code("supervised", "d", "v", "x.csv", "month", "sum", 12, 4, 30)
    _compiles(code)
    assert "Ridge" in code


def test_forecast_raw_grain_reads_rows_not_aggregate():
    code = forecast_code("linear", "d", "v", "x.csv", "raw", "sum", 12, 4, 30)
    _compiles(code)
    assert "dt.truncate" not in code        # raw không gộp
    assert "to_numpy()" in code


def test_forecast_xlsx_uses_read_excel():
    code = forecast_code("linear", "d", "v", "báo cáo.xlsx", "month", "sum", 12, 4, 30)
    _compiles(code)
    assert "read_excel" in code


from analytics.codegen import correlation_code


def test_correlation_code_faithful():
    code = correlation_code(["Doanh thu", "Chi phí", "Lợi nhuận"], "kpi.xlsx")
    _compiles(code)
    assert "pearsonr" in code
    assert "read_excel" in code
    assert "pair.height < 3" in code        # guard trung thực với router
    assert "f\"" not in code and "f'" not in code


from analytics.codegen import timeseries_code


def test_timeseries_code_aggregates_and_compiles():
    code = timeseries_code("Ngày", "Doanh thu", "ban_hang.csv", "month", "sum",
                           comparisons=[], rolling_window=7, cumulative_reset="year")
    _compiles(code)
    assert "dt.truncate" in code
    assert "group_by" in code
    assert "f\"" not in code and "f'" not in code


def test_timeseries_code_emits_only_requested_comparisons():
    code = timeseries_code("Ngày", "Doanh thu", "ban_hang.csv", "month", "sum",
                           comparisons=["pop", "yoy", "rolling"],
                           rolling_window=3, cumulative_reset="year")
    _compiles(code)
    assert "_pop(values)" in code
    assert "_yoy(period_starts, values, 'month')" in code
    assert "_rolling(values, 3)" in code
    # Chỉ kiểm tra phép GỌI không được phát — không dùng "_cumulative(" / "_share("
    # vì khối helper LUÔN định nghĩa `def _cumulative(...)`/`def _share(...)`.
    # Nhãn 'Cumulative ='/'Share% =' chỉ xuất hiện ở chỗ gọi (print), nên dùng nó.
    assert "Cumulative =" not in code        # không yêu cầu cumulative
    assert "Share% =" not in code


import pytest
from analytics.codegen import stats_code

_STATS_KEYWORD = {
    "describe": "mean", "bootstrap": "np.random", "distribution": "histogram",
    "correlation": "pearsonr", "ttest": "ttest_ind", "mannwhitney": "mannwhitneyu",
    "anova": "f_oneway", "chi2": "chi2_contingency", "zscore": "std",
    "boxplot": "percentile",
}


@pytest.mark.parametrize("test,kw", list(_STATS_KEYWORD.items()))
def test_stats_code_each_test_faithful(test, kw):
    code = stats_code(test, "Giá trị", "Nhóm", "data.csv")
    _compiles(code)
    assert kw in code
    assert "f\"" not in code and "f'" not in code


from analytics.codegen import cohort_code, describe_code


def test_describe_code_compiles_and_uses_polars():
    code = describe_code("báo cáo.xlsx")
    _compiles(code)
    assert "read_excel" in code
    assert "median" in code
    assert "range" in code
    assert "f\"" not in code and "f'" not in code   # no f-string in generated code


def test_cohort_transactional_uses_n_unique_and_pivot():
    code = cohort_code("month", "Ngày mua", "Khách hàng", "don_hang.csv")
    _compiles(code)
    assert "n_unique" in code
    assert "pivot" in code
    assert "f\"" not in code and "f'" not in code


def test_cohort_period_index_changes_with_period():
    assert "dt.week" in cohort_code("week", "d", "u", "x.csv")
    assert "dt.epoch" in cohort_code("day", "d", "u", "x.csv")
    assert "// 3" in cohort_code("quarter", "d", "u", "x.csv")


def test_cohort_preaggregated_branch_compiles():
    code = cohort_code("month", "Cohort", "User", "x.csv",
                       offset_col="period_idx", metric_col="Revenue")
    _compiles(code)
    assert "_cohort_label" in code
    assert "pivot" in code


from analytics.codegen import drilldown_code


def test_drilldown_code_year_compiles():
    code = drilldown_code("Order Date", "Sales", "orders.csv", "year", "sum")
    _compiles(code)
    assert "strftime('%Y')" in code
    assert "group_by('_period')" in code
    assert "f\"" not in code and "f'" not in code


def test_drilldown_code_month_filters_year():
    code = drilldown_code("Ngày", "Doanh thu", "x.xlsx", "month", "mean", year=2024)
    _compiles(code)
    assert "read_excel" in code
    assert "dt.year() == 2024" in code
    assert "strftime('%Y-%m')" in code
    assert "mean()" in code
