export interface MetricDef {
  name:       string
  group:      string
  definition: string
  formula:    string
  notes?:     string
}

export interface MetricGroup {
  id:      string
  label:   string
  metrics: MetricDef[]
}

export interface ContextRow {
  concept:   string
  fmcgcorp:  string
  vinabrew:  string
}

// ── Metric groups ─────────────────────────────────────────────────────────────

export const METRIC_GROUPS: MetricGroup[] = [
  {
    id: 'VOLUME_REVENUE', label: 'Volume & Revenue',
    metrics: [
      {
        name: 'GSV',
        group: 'VOLUME_REVENUE',
        definition: 'Gross Sales Value — Doanh thu gộp trước chiết khấu',
        formula: 'SUM(gross_amount)',
      },
      {
        name: 'NSR',
        group: 'VOLUME_REVENUE',
        definition: 'Net Sales Revenue — Doanh thu thuần sau chiết khấu',
        formula: 'SUM(net_amount)  -- hoặc SUM(gross_amount - discount_amount)',
      },
      {
        name: 'Trade_Spend%',
        group: 'VOLUME_REVENUE',
        definition: '% chi phí trade marketing trên GSV',
        formula: 'SUM(trade_spend) * 100.0 / SUM(gross_amount)',
        notes: 'COALESCE(trade_spend, 0) khi có NULL',
      },
      {
        name: 'NSR_Per_Case',
        group: 'VOLUME_REVENUE',
        definition: 'NSR trung bình per thùng bán ra',
        formula: 'SUM(net_amount) / SUM(quantity)',
      },
      {
        name: 'Offtake',
        group: 'VOLUME_REVENUE',
        definition: 'Doanh số sell-out (tiêu thụ thực tế từ kệ)',
        formula: 'SUM(quantity)  -- từ fact_sales, channel GT/MT',
        notes: 'Tương đương "Secondary" trong FMCG truyền thống',
      },
      {
        name: 'Sell_In',
        group: 'VOLUME_REVENUE',
        definition: 'Lượng hàng nhập kho nhà phân phối (sell-in)',
        formula: 'SUM(quantity) -- thường từ bảng riêng hoặc fact_sales kênh GT',
      },
      {
        name: 'Offtake_vs_SellIn%',
        group: 'VOLUME_REVENUE',
        definition: 'Tỉ lệ tiêu thụ thực tế trên lượng nhập kho',
        formula: 'SUM(offtake_qty) * 100.0 / SUM(sellin_qty)',
      },
    ],
  },
  {
    id: 'DISTRIBUTION', label: 'Distribution & Market Share',
    metrics: [
      {
        name: 'Numeric_Dist%',
        group: 'DISTRIBUTION',
        definition: '% số điểm bán có bán sản phẩm trên tổng điểm bán target',
        formula: 'COUNT(DISTINCT store_id having sales) * 100.0 / COUNT(DISTINCT total_stores)',
      },
      {
        name: 'Velocity',
        group: 'DISTRIBUTION',
        definition: 'Doanh số trung bình per điểm bán per tháng',
        formula: 'SUM(net_amount) / COUNT(DISTINCT store_id) / COUNT(DISTINCT month)',
      },
      {
        name: 'Brand_Share%',
        group: 'DISTRIBUTION',
        definition: '% thị phần doanh thu của brand trên tổng category',
        formula: 'SUM(brand_gsv) * 100.0 / SUM(category_gsv)',
      },
      {
        name: 'Category_Mix%',
        group: 'DISTRIBUTION',
        definition: '% đóng góp từng category (RTD Coffee vs Energy Drink) trên tổng',
        formula: 'SUM(cat_gsv) * 100.0 / SUM(total_gsv)',
      },
      {
        name: 'Achievement%',
        group: 'DISTRIBUTION',
        definition: 'Tỉ lệ hoàn thành chỉ tiêu doanh thu',
        formula: 'SUM(gross_amount) * 100.0 / NULLIF(SUM(target_amount), 0)',
        notes: 'Dùng NULLIF để tránh chia 0',
      },
    ],
  },
  {
    id: 'DIGITAL_LOYALTY', label: 'Digital & Loyalty',
    metrics: [
      {
        name: 'App_Revenue',
        group: 'DIGITAL_LOYALTY',
        definition: 'Doanh thu qua kênh app (Brew App / TikTok / Shopee)',
        formula: "SUM(basket_size) WHERE app_channel IN ('Brew App','Shopee','TikTok')",
      },
      {
        name: 'Scan_Count',
        group: 'DIGITAL_LOYALTY',
        definition: 'Tổng số lon/chai được quét để tích điểm',
        formula: 'SUM(scan_count)',
      },
      {
        name: 'Basket_Size',
        group: 'DIGITAL_LOYALTY',
        definition: 'Giá trị giỏ hàng trung bình per giao dịch',
        formula: 'AVG(basket_size)',
      },
      {
        name: 'Brew_Points_Earned',
        group: 'DIGITAL_LOYALTY',
        definition: 'Tổng điểm tích lũy (50 điểm/lon)',
        formula: 'SUM(brew_points_earned)',
      },
      {
        name: 'Brew_Points_Redeemed',
        group: 'DIGITAL_LOYALTY',
        definition: 'Tổng điểm đã đổi quà',
        formula: 'SUM(brew_points_redeemed)',
      },
      {
        name: 'Point_Burn_Rate%',
        group: 'DIGITAL_LOYALTY',
        definition: '% điểm đã đổi trên tổng điểm tích',
        formula: 'SUM(brew_points_redeemed) * 100.0 / NULLIF(SUM(brew_points_earned), 0)',
        notes: 'Tương đương "Conversion Redeem" trong FMCG Corp',
      },
      {
        name: 'Point_Liability_VND',
        group: 'DIGITAL_LOYALTY',
        definition: 'Giá trị quy VND của điểm chưa đổi (1 điểm = 2,750đ)',
        formula: '(SUM(pts_earned) - SUM(pts_redeemed)) * 2750',
      },
      {
        name: 'Redemption_ROI',
        group: 'DIGITAL_LOYALTY',
        definition: 'Doanh thu phát sinh từ khách hàng đổi điểm / Chi phí quà tặng',
        formula: 'SUM(basket_size WHERE redeemed > 0) / (SUM(pts_redeemed) * 2750)',
      },
    ],
  },
  {
    id: 'CUSTOMER', label: 'Customer Metrics',
    metrics: [
      {
        name: 'Active_Buyer',
        group: 'CUSTOMER',
        definition: 'Số store/người mua có ít nhất 1 giao dịch trong kỳ',
        formula: 'COUNT(DISTINCT store_id)',
        notes: 'Tương đương "Active Account" trong FMCG Corp',
      },
      {
        name: 'New_Buyer',
        group: 'CUSTOMER',
        definition: 'Số store/người mua lần đầu (is_new_buyer = true)',
        formula: 'COUNT(DISTINCT store_id) WHERE is_new_buyer = true',
      },
      {
        name: 'Returning_Buyer',
        group: 'CUSTOMER',
        definition: 'Active Buyer − New Buyer',
        formula: 'COUNT(DISTINCT store_id WHERE is_new_buyer = false)',
      },
      {
        name: 'MAU',
        group: 'CUSTOMER',
        definition: 'Monthly Active Users — số store active theo tháng',
        formula: 'COUNT(DISTINCT store_id) GROUP BY year_month',
      },
      {
        name: 'Purchase_Freq',
        group: 'CUSTOMER',
        definition: 'Số lần mua trung bình per store per tháng',
        formula: 'COUNT(txn_id) / COUNT(DISTINCT store_id) / COUNT(DISTINCT month)',
      },
      {
        name: 'Conversion%',
        group: 'CUSTOMER',
        definition: '% store đã mua trên tổng store target',
        formula: 'COUNT(DISTINCT buyers) * 100.0 / COUNT(DISTINCT total_target_stores)',
      },
    ],
  },
  {
    id: 'ADVANCED_WINDOW', label: 'Window Functions',
    metrics: [
      {
        name: 'MoM_Growth%',
        group: 'ADVANCED_WINDOW',
        definition: 'Tăng trưởng doanh thu tháng này so với tháng trước',
        formula: '(current_month - LAG(current_month)) * 100.0 / LAG(current_month)\n-- DuckDB: LAG(gsv) OVER (ORDER BY year_month)\n-- T-SQL:  LAG(gsv) OVER (ORDER BY year_month)',
      },
      {
        name: 'YTD_NSR',
        group: 'ADVANCED_WINDOW',
        definition: 'Doanh thu NSR lũy kế từ đầu năm đến tháng hiện tại',
        formula: 'SUM(monthly_nsr) OVER (PARTITION BY year ORDER BY month)',
      },
      {
        name: 'Rolling_3M_NSR',
        group: 'ADVANCED_WINDOW',
        definition: 'Trung bình động 3 tháng gần nhất',
        formula: 'AVG(monthly_nsr) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)',
      },
      {
        name: 'Store_Rank',
        group: 'ADVANCED_WINDOW',
        definition: 'Xếp hạng store theo NSR trong từng region',
        formula: 'RANK() OVER (PARTITION BY region ORDER BY SUM(net_amount) DESC)',
      },
      {
        name: 'Velocity_Rank',
        group: 'ADVANCED_WINDOW',
        definition: 'Xếp hạng sản phẩm theo Velocity (NSR/store/tháng)',
        formula: 'DENSE_RANK() OVER (ORDER BY velocity DESC)',
      },
    ],
  },
  {
    id: 'ML_PYTHON', label: 'ML / RFM',
    metrics: [
      {
        name: 'RFM_Recency',
        group: 'ML_PYTHON',
        definition: 'Số ngày từ lần mua cuối đến ngày phân tích',
        formula: "MAX(date_key) subtracted from reference_date\n-- DuckDB: datediff('day', MAX(date), reference_date)",
      },
      {
        name: 'RFM_Frequency',
        group: 'ML_PYTHON',
        definition: 'Tổng số lần giao dịch trong kỳ phân tích',
        formula: 'COUNT(DISTINCT date_key) per store_id',
      },
      {
        name: 'RFM_Monetary',
        group: 'ML_PYTHON',
        definition: 'Tổng doanh thu NSR trong kỳ phân tích',
        formula: 'SUM(net_amount) per store_id',
      },
      {
        name: 'Seasonality_Idx',
        group: 'ML_PYTHON',
        definition: 'Chỉ số mùa vụ: NSR tháng / NSR trung bình tháng',
        formula: 'monthly_nsr / AVG(monthly_nsr) OVER ()',
        notes: 'Tết ~2.2x, Hè ~1.6x, Mưa ~0.8x baseline',
      },
    ],
  },
]

// ── Context comparison: FMCG Corp vs VINA BREW ────────────────────────────────

export const CONTEXT_TABLE: ContextRow[] = [
  { concept: 'Revenue term',      fmcgcorp: 'DSO',                        vinabrew: 'GSV / NSR' },
  { concept: 'Sell-out',          fmcgcorp: 'Secondary',                  vinabrew: 'Offtake' },
  { concept: 'Hiệu quả kênh',     fmcgcorp: '—',                          vinabrew: 'Numeric Dist% + Velocity' },
  { concept: 'Market position',   fmcgcorp: '—',                          vinabrew: 'Brand Share%, Category Mix%' },
  { concept: 'Điểm tích',         fmcgcorp: 'Xu (137,500đ)',              vinabrew: 'Brew Points (50pt/lon = 2,750đ)' },
  { concept: 'Điểm tồn',          fmcgcorp: '—',                          vinabrew: 'Point Liability VND' },
  { concept: '% điểm dùng',       fmcgcorp: 'Conversion Redeem',          vinabrew: 'Point Burn Rate%' },
  { concept: 'ROI loyalty',       fmcgcorp: 'DSO_RA / Gift_Cost',         vinabrew: 'Redemption ROI' },
  { concept: 'Customer term',     fmcgcorp: 'Active Account',             vinabrew: 'Active Buyer' },
  { concept: 'Tần suất mua',      fmcgcorp: 'Lượt tích / lon tích',       vinabrew: 'Purchase Freq + Basket Size' },
  { concept: 'Achievement',       fmcgcorp: 'Actual / Target',            vinabrew: 'Achievement% = Actual / Target' },
  { concept: 'DA metric focus',   fmcgcorp: 'Volume, DSO, Streak',        vinabrew: 'NSR, Dist%, Velocity, Loyalty' },
]
