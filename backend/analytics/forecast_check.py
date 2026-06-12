"""Kiểm tra mức độ phù hợp của dữ liệu với thuật toán forecast.

Thuần Python, không phụ thuộc FastAPI/DB — unit-test bằng pytest. Trả về cấu trúc
giống analytics.cohort_check.check_suitability để router xử lý nhất quán: khi không
phù hợp, /forecast trả HTTP 200 kèm {suitable: False, ...} thay vì raise lỗi đỏ
khiến người dùng tưởng thuật toán hỏng.

Các ngưỡng chặn (đúng tinh thần Point 3b — chỉ cảnh báo khi kết quả thực sự vô nghĩa):
  • Mọi method: cần >= 2 điểm — khớp hard-fail của router (routers/ml.py:1558).
  • SARIMAX: cần >= 2 * seasonal_period điểm — khớp hard-fail của router
    (routers/ml.py:1609).
  • supervised: cần >= 4 điểm. Đây KHÔNG phải hard-fail của router (guard
    `n < lags + 2` với `lags = min(5, n // 4)` không bao giờ kích hoạt khi n >= 2)
    mà là ngưỡng "có nghĩa": khi n < 4 thì lags = 0 → ma trận đặc trưng X có 0 cột
    → `Ridge.fit` ném ValueError (router trả lỗi 500 đỏ, chưa bắt). Chặn sớm để
    biến lỗi 500 thành cảnh báo thân thiện + gợi ý method khác — đúng Point 3b.
"""
from __future__ import annotations

# Thứ tự ưu tiên gợi ý: ETS (tổng quát tốt) → moving_average → linear.
# Không bao giờ trùng method đang lỗi (sarimax/supervised).
_RECOMMEND_ORDER = [("ets", 2), ("moving_average", 2), ("linear", 2)]


def _recommend_method(n: int) -> str | None:
    for name, floor in _RECOMMEND_ORDER:
        if n >= floor:
            return name
    return None


def check_forecast_suitability(method: str, n: int, seasonal_period: int) -> dict:
    reasons: list[str] = []
    if n < 2:
        reasons.append(f"Cần tối thiểu 2 điểm dữ liệu để dự báo, nhưng chỉ có {n} điểm.")
    elif method == "sarimax":
        need = 2 * seasonal_period
        if n < need:
            reasons.append(
                f"SARIMAX cần tối thiểu {need} điểm (2 chu kỳ mùa vụ × "
                f"{seasonal_period}), nhưng dữ liệu chỉ có {n} điểm."
            )
    elif method == "supervised":
        if n < 4:
            reasons.append(
                f"Phương pháp 'supervised' cần tối thiểu 4 điểm để tạo đặc trưng "
                f"trễ (lag), nhưng dữ liệu chỉ có {n} điểm."
            )
    suitable = not reasons
    return {
        "suitable": suitable,
        "reasons": reasons,
        "recommended_method": None if suitable else _recommend_method(n),
    }
