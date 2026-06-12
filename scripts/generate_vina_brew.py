#!/usr/bin/env python3
"""Generate VINA BREW Co. dataset — 6 CSV files for SQL Sandbox practice.

Usage: python scripts/generate_vina_brew.py
Output: data/vina_brew/{dim_date, dim_product, dim_channel, dim_store, fact_sales, fact_transactions}.csv
"""
import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "vina_brew"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── dim_date ──────────────────────────────────────────────────────────────────
def build_dim_date():
    rows = []
    d = date(2024, 1, 1)
    end = date(2025, 12, 31)
    MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    while d <= end:
        is_holiday = (
            (d.month == 1 and d.day == 1)                               # New Year
            or (d.month == 4 and d.day == 30)                           # Liberation Day
            or (d.month == 5 and d.day == 1)                            # Labour Day
            or (d.month == 9 and d.day == 2)                            # National Day
            or (d.year == 2024 and d.month == 2 and 8 <= d.day <= 14)   # Tết 2024
            or (d.year == 2025 and d.month == 1 and 25 <= d.day <= 31)  # Tết 2025
        )
        if d.month in (5, 6, 7, 8):
            season = "summer"
        elif (d.month == 1 and d.day >= 20) or (d.month == 2 and d.day <= 15) or (d.year == 2025 and d.month == 1 and d.day >= 25):
            season = "tet"
        elif d.month in (9, 10, 11):
            season = "rainy"
        else:
            season = "dry"

        rows.append({
            "date_key":    int(d.strftime("%Y%m%d")),
            "date":        d.strftime("%Y-%m-%d"),
            "year":        d.year,
            "month":       d.month,
            "quarter":     (d.month - 1) // 3 + 1,
            "month_name":  MONTH_NAMES[d.month - 1],
            "day_of_week": d.weekday(),   # 0=Mon … 6=Sun
            "is_weekend":  d.weekday() >= 5,
            "is_holiday":  is_holiday,
            "season":      season,
        })
        d += timedelta(days=1)
    return rows


# ── dim_product ───────────────────────────────────────────────────────────────
PRODUCTS = [
    # product_id, product_name, brand, category, sub_category, sku_code, volume_ml, gross_price, net_price, cost, is_active
    ("P001", "Highlands Coffee Lon 250ml",  "Highlands", "RTD_Coffee",    "Can",    "HLC-C-250", 250, 15000, 13500, 8000,  True),
    ("P002", "Highlands Coffee Chai 330ml", "Highlands", "RTD_Coffee",    "Bottle", "HLC-B-330", 330, 18000, 16200, 9500,  True),
    ("P003", "Wake Up Hộp 180ml",           "Wake Up",   "RTD_Coffee",    "Tetra",  "WKP-T-180", 180,  8000,  7200, 3800,  True),
    ("P004", "Wake Up Lon 250ml",           "Wake Up",   "RTD_Coffee",    "Can",    "WKP-C-250", 250, 12000, 10800, 6200,  True),
    ("P005", "G7 Coffee Lon 240ml",         "G7",        "RTD_Coffee",    "Can",    "G7C-C-240", 240, 13000, 11700, 7000,  True),
    ("P006", "G7 Coffee Chai 330ml",        "G7",        "RTD_Coffee",    "Bottle", "G7C-B-330", 330, 16000, 14400, 8800,  True),
    ("P007", "Nescafé Lon 240ml",           "Nescafe",   "RTD_Coffee",    "Can",    "NSC-C-240", 240, 14000, 12600, 7500,  True),
    ("P008", "Sting Dâu Lon 330ml",         "Sting",     "Energy_Drink",  "Can",    "STG-S-330", 330, 10000,  9000, 4500,  True),
    ("P009", "Sting Vàng Lon 330ml",        "Sting",     "Energy_Drink",  "Can",    "STG-G-330", 330, 10000,  9000, 4500,  True),
    ("P010", "Monster Energy 355ml",        "Monster",   "Energy_Drink",  "Can",    "MNS-E-355", 355, 25000, 22500,14000,  True),
    ("P011", "Monster Lo-Carb 355ml",       "Monster",   "Energy_Drink",  "Can",    "MNS-L-355", 355, 25000, 22500,14000,  True),
    ("P012", "Number 1 Lon 330ml",          "Number 1",  "Energy_Drink",  "Can",    "N1-C-330",  330,  9000,  8100, 4000,  True),
    ("P013", "Number 1 Active 330ml",       "Number 1",  "Energy_Drink",  "Can",    "N1-A-330",  330, 10000,  9000, 4200,  True),
    ("P014", "Red Bull 250ml",              "Red Bull",  "Energy_Drink",  "Can",    "RBL-E-250", 250, 22000, 19800,12000,  True),
    ("P015", "Red Bull Extra 330ml",        "Red Bull",  "Energy_Drink",  "Can",    "RBL-X-330", 330, 26000, 23400,14500,  True),
    ("P016", "Wake Up Ly 270ml",            "Wake Up",   "RTD_Coffee",    "Can",    "WKP-C-270", 270, 11000,  9900, 6000,  False),
    ("P017", "G7 Iced Tea 350ml",           "G7",        "RTD_Coffee",    "Bottle", "G7T-B-350", 350, 14000,  None, 7200,  False),
]
PRODUCT_FIELDS = [
    "product_id","product_name","brand","category","sub_category",
    "sku_code","volume_ml","gross_price","net_price","cost","is_active",
]


# ── dim_channel ───────────────────────────────────────────────────────────────
CHANNELS = [
    ("CH01", "Modern Trade - Siêu thị",           "MT",       0.08),
    ("CH02", "Modern Trade - Cửa hàng tiện lợi",  "MT",       0.06),
    ("CH03", "General Trade - Tạp hóa",            "GT",       0.04),
    ("CH04", "General Trade - Bách hóa",           "GT",       0.05),
    ("CH05", "On-Trade - Quán cà phê",             "OnTrade",  0.12),
    ("CH06", "On-Trade - Nhà hàng",                "OnTrade",  0.15),
    ("CH07", "Digital - Shopee",                   "Digital",  0.10),
    ("CH08", "Digital - TikTok Shop",              "Digital",  0.12),
]
CHANNEL_FIELDS = ["channel_id","channel_name","channel_type","commission_rate"]


# ── dim_store ─────────────────────────────────────────────────────────────────
REGIONS_PROVINCES = {
    "HCM":       ["TP. Hồ Chí Minh"],
    "HN":        ["Hà Nội"],
    "MienTrung": ["Đà Nẵng", "Huế", "Nha Trang", "Quy Nhơn"],
    "MienBac":   ["Hải Phòng", "Hạ Long", "Nam Định", "Thái Nguyên"],
    "MienNam":   ["Cần Thơ", "Đồng Nai", "Bình Dương", "Vũng Tàu"],
}
STORE_NAME_PREFIXES = {
    "CH01": ["BigC", "Lotte Mart", "AEON", "Vinmart"],
    "CH02": ["Circle K", "GS25", "7-Eleven", "Winmart+", "FamilyMart"],
    "CH03": ["Tạp hóa Lan", "Tạp hóa Hương", "Tạp hóa Minh", "Tạp hóa Hoa"],
    "CH04": ["Bách hóa Xanh", "Coopmart", "Coopfood"],
    "CH05": ["Highlands Coffee", "The Coffee House", "Cộng Cà Phê", "Phúc Long"],
    "CH06": ["Nhà hàng Ngon", "Buffet 789", "Quán Bình Dân"],
    "CH07": ["Shopee Official Store"],
    "CH08": ["TikTok VINA BREW"],
}
STORES_PER_CHANNEL = {
    "CH01": 3, "CH02": 5, "CH03": 8, "CH04": 4,
    "CH05": 4, "CH06": 2, "CH07": 1, "CH08": 1,
}
STORE_FIELDS = ["store_id","store_name","region","province","channel_id","tier","is_active"]

def build_dim_store():
    stores = []
    ctr = 1
    for region, provinces in REGIONS_PROVINCES.items():
        for ch_id, n in STORES_PER_CHANNEL.items():
            for _ in range(n):
                province = random.choice(provinces)
                prefix   = random.choice(STORE_NAME_PREFIXES[ch_id])
                tier     = random.choices(["A","B","C"], weights=[0.2, 0.5, 0.3])[0]
                stores.append({
                    "store_id":   f"S{ctr:04d}",
                    "store_name": f"{prefix} {province}",
                    "region":     region,
                    "province":   province,
                    "channel_id": ch_id,
                    "tier":       tier,
                    "is_active":  random.random() > 0.05,
                })
                ctr += 1
    return stores


# ── fact_sales ────────────────────────────────────────────────────────────────
SALES_FIELDS = [
    "sale_id","date_key","product_id","store_id","channel_id",
    "gross_amount","discount_amount","net_amount","quantity","trade_spend","target_amount",
]

def seasonal_mult(date_info: dict) -> float:
    s = date_info["season"]
    m = date_info["month"]
    if s == "tet":   return 2.2
    if m in (6,7,8): return 1.6   # summer energy drink peak
    if m in (9,10):  return 0.8
    return 1.0

def build_fact_sales(date_rows, stores, n=8000):
    active_stores   = [s for s in stores if s["is_active"]]
    active_products = [p for p in PRODUCTS if p[10]]   # is_active
    date_map        = {d["date_key"]: d for d in date_rows}
    date_keys       = list(date_map.keys())

    rows = []
    for i in range(1, n + 1):
        store   = random.choice(active_stores)
        product = random.choice(active_products)
        dk      = random.choice(date_keys)
        mult    = seasonal_mult(date_map[dk])

        base_qty = {"A": 80, "B": 50, "C": 25}[store["tier"]]
        qty      = max(1, int(random.gauss(base_qty * mult, base_qty * 0.3)))

        gross_price   = product[7]
        gross_amount  = qty * gross_price
        disc_pct      = random.uniform(0.05, 0.20)
        disc_amount   = round(gross_amount * disc_pct)
        net_amount    = gross_amount - disc_amount
        trade_spend   = round(gross_amount * random.uniform(0.02, 0.12)) if random.random() > 0.1 else None
        target_amount = round(gross_amount * random.uniform(0.8, 1.3))

        rows.append({
            "sale_id":       f"SAL{i:06d}",
            "date_key":      dk,
            "product_id":    product[0],
            "store_id":      store["store_id"],
            "channel_id":    store["channel_id"],
            "gross_amount":  round(gross_amount),
            "discount_amount": disc_amount,
            "net_amount":    round(net_amount),
            "quantity":      qty,
            "trade_spend":   trade_spend,
            "target_amount": target_amount,
        })
    return rows


# ── fact_transactions ─────────────────────────────────────────────────────────
TXN_FIELDS = [
    "txn_id","date_key","product_id","store_id","scan_count",
    "brew_points_earned","brew_points_redeemed","basket_size","is_new_buyer","app_channel",
]
APP_CHANNELS = ["Brew App", "Shopee", "TikTok", "QR Scan"]

def build_fact_transactions(date_rows, stores, n=5000):
    active_stores   = [s for s in stores if s["is_active"]]
    active_products = [p for p in PRODUCTS if p[10]]
    date_map        = {d["date_key"]: d for d in date_rows}
    date_keys       = list(date_map.keys())

    rows = []
    for i in range(1, n + 1):
        store   = random.choice(active_stores)
        product = random.choice(active_products)
        dk      = random.choice(date_keys)
        mult    = seasonal_mult(date_map[dk])

        scan_count   = max(1, int(random.gauss(15 * mult, 5)))
        pts_earned   = scan_count * 50
        pts_redeemed = int(pts_earned * random.uniform(0, 0.8)) if random.random() > 0.4 else 0
        basket_size  = round(max(0, random.gauss(85000 * mult, 20000)), -2)

        rows.append({
            "txn_id":               f"TXN{i:06d}",
            "date_key":             dk,
            "product_id":           product[0],
            "store_id":             store["store_id"],
            "scan_count":           scan_count,
            "brew_points_earned":   pts_earned,
            "brew_points_redeemed": pts_redeemed,
            "basket_size":          basket_size,
            "is_new_buyer":         random.random() < 0.15,
            "app_channel":          random.choice(APP_CHANNELS),
        })
    return rows


# ── Write helpers ─────────────────────────────────────────────────────────────
def write_csv(path: Path, fieldnames: list, rows: list):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  OK {path.name:35s} {len(rows):>6,} rows")


def main():
    print("Generating VINA BREW Co. dataset …")

    date_rows = build_dim_date()
    stores    = build_dim_store()
    sales     = build_fact_sales(date_rows, stores, n=8000)
    txns      = build_fact_transactions(date_rows, stores, n=5000)

    write_csv(OUTPUT_DIR / "dim_date.csv",          list(date_rows[0].keys()), date_rows)
    write_csv(OUTPUT_DIR / "dim_product.csv",       PRODUCT_FIELDS, [dict(zip(PRODUCT_FIELDS, p)) for p in PRODUCTS])
    write_csv(OUTPUT_DIR / "dim_channel.csv",       CHANNEL_FIELDS, [dict(zip(CHANNEL_FIELDS, c)) for c in CHANNELS])
    write_csv(OUTPUT_DIR / "dim_store.csv",         STORE_FIELDS,   stores)
    write_csv(OUTPUT_DIR / "fact_sales.csv",        SALES_FIELDS,   sales)
    write_csv(OUTPUT_DIR / "fact_transactions.csv", TXN_FIELDS,     txns)

    print(f"\nOutput -> {OUTPUT_DIR}")
    print("Done!")


if __name__ == "__main__":
    main()
