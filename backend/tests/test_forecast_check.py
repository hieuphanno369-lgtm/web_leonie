from analytics.forecast_check import check_forecast_suitability


def test_sarimax_insufficient_blocks_and_recommends_ets():
    r = check_forecast_suitability("sarimax", n=10, seasonal_period=12)
    assert r["suitable"] is False
    assert any("24" in reason for reason in r["reasons"])   # 2 * 12
    assert r["recommended_method"] == "ets"


def test_sarimax_enough_points_is_suitable():
    r = check_forecast_suitability("sarimax", n=24, seasonal_period=12)
    assert r["suitable"] is True
    assert r["reasons"] == []
    assert r["recommended_method"] is None


def test_supervised_below_four_is_blocked_but_four_is_suitable():
    # n < 4 → lags = min(5, n//4) = 0 → X có 0 cột → Ridge.fit ném ValueError (500) → chặn sớm.
    blocked = check_forecast_suitability("supervised", n=3, seasonal_period=12)
    assert blocked["suitable"] is False
    assert blocked["recommended_method"] == "ets"
    # n = 4 → lags = 1 (đã có đặc trưng trễ thật) → cho chạy.
    ok = check_forecast_suitability("supervised", n=4, seasonal_period=12)
    assert ok["suitable"] is True
    assert ok["recommended_method"] is None


def test_sarimax_one_below_threshold_blocks():
    # Ngưỡng = 2 * 12 = 24; n = 23 thiếu đúng 1 điểm → vẫn chặn (kiểm biên off-by-one).
    r = check_forecast_suitability("sarimax", n=23, seasonal_period=12)
    assert r["suitable"] is False
    assert any("24" in reason for reason in r["reasons"])
    assert r["recommended_method"] == "ets"


def test_linear_two_points_is_suitable():
    assert check_forecast_suitability("linear", n=2, seasonal_period=12)["suitable"] is True


def test_below_two_points_always_blocks_no_recommendation():
    r = check_forecast_suitability("linear", n=1, seasonal_period=12)
    assert r["suitable"] is False
    assert r["recommended_method"] is None


def test_recommended_never_equals_failing_method():
    r = check_forecast_suitability("sarimax", n=6, seasonal_period=12)
    assert r["recommended_method"] != "sarimax"
