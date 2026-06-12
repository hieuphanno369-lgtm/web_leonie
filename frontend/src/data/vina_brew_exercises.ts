export interface Exercise {
  id: string
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  category: string
  description: string
  businessContext: string
  starterQuery: string
  solutionQuery: string
  hints: [string, string, string]
  expectedColumns: string[]
  explanation: string
}

export const VINA_BREW_EXERCISES: Exercise[] = [
  // ─── EASY 1–10 ────────────────────────────────────────────────────────────
  {
    id: 'ex-01',
    title: 'Danh sách sản phẩm VINA BREW',
    difficulty: 'easy',
    category: 'SELECT',
    description: 'Lấy danh sách tất cả sản phẩm trong hệ thống, hiển thị tên sản phẩm, thương hiệu và danh mục. Sắp xếp theo thương hiệu rồi theo tên sản phẩm.',
    businessContext: 'DA cần nắm toàn bộ danh mục sản phẩm trước khi phân tích doanh số để xác minh dữ liệu đầy đủ và nhất quán.',
    starterQuery: `SELECT product_name, brand, category
FROM dim_product
-- ORDER BY brand, product_name`,
    solutionQuery: `SELECT product_name, brand, category
FROM dim_product
ORDER BY brand, product_name`,
    hints: [
      'Chọn 3 cột từ bảng dim_product, sau đó sắp xếp kết quả theo hai cột lồng nhau.',
      'Dùng ORDER BY với nhiều cột: ORDER BY col1, col2. DuckDB và T-SQL đều dùng cú pháp giống nhau.',
      'SELECT product_name, brand, category FROM dim_product ORDER BY brand, product_name'
    ],
    expectedColumns: ['product_name', 'brand', 'category'],
    explanation: 'ORDER BY nhiều cột: hàng đầu tiên sắp xếp theo brand (A→Z), trong cùng brand thì sắp xếp tiếp theo product_name.'
  },
  {
    id: 'ex-02',
    title: 'Lọc Energy Drink còn bán',
    difficulty: 'easy',
    category: 'WHERE',
    description: 'Lọc các sản phẩm thuộc danh mục Energy Drink đang còn hoạt động (is_active = true). Hiển thị tên, thương hiệu và giá niêm yết, sắp xếp giá từ cao xuống thấp.',
    businessContext: 'Trước khi đàm phán giá hay lập kế hoạch khuyến mãi, DA cần nhanh chóng xem danh mục Energy Drink đang active để so sánh định giá giữa các nhãn.',
    starterQuery: `SELECT product_name, brand, gross_price
FROM dim_product
WHERE category = 'Energy_Drink'
  -- AND is_active = ...
ORDER BY gross_price DESC`,
    solutionQuery: `SELECT product_name, brand, gross_price
FROM dim_product
WHERE category = 'Energy_Drink'
  AND is_active = true
ORDER BY gross_price DESC`,
    hints: [
      'Kết hợp hai điều kiện trong WHERE bằng AND: lọc category và trạng thái active.',
      'Boolean: DuckDB dùng true/false (không cần dấu nháy). T-SQL dùng 1/0 hoặc BIT.',
      "SELECT product_name, brand, gross_price FROM dim_product WHERE category='Energy_Drink' AND is_active=true ORDER BY gross_price DESC"
    ],
    expectedColumns: ['product_name', 'brand', 'gross_price'],
    explanation: 'AND kết hợp hai điều kiện — chỉ trả về hàng thỏa cả hai. is_active=true loại bỏ sản phẩm đã ngừng bán.'
  },
  {
    id: 'ex-03',
    title: 'Đếm store theo region',
    difficulty: 'easy',
    category: 'GROUP BY + COUNT',
    description: 'Đếm số lượng cửa hàng đang hoạt động theo từng vùng. Sắp xếp vùng có nhiều cửa hàng nhất lên đầu.',
    businessContext: 'Hiểu phân bổ điểm bán theo vùng giúp ban lãnh đạo ưu tiên nguồn lực bán hàng và phân bổ ngân sách trade marketing hợp lý.',
    starterQuery: `SELECT region, COUNT(store_id) AS store_count
FROM dim_store
-- WHERE is_active = ...
GROUP BY region
ORDER BY store_count DESC`,
    solutionQuery: `SELECT region, COUNT(store_id) AS store_count
FROM dim_store
WHERE is_active = true
GROUP BY region
ORDER BY store_count DESC`,
    hints: [
      'Lọc is_active=true trước khi GROUP BY để chỉ đếm store đang mở.',
      'COUNT(col) đếm số hàng khác NULL. DuckDB và T-SQL dùng cú pháp COUNT() giống nhau.',
      'SELECT region, COUNT(store_id) AS store_count FROM dim_store WHERE is_active=true GROUP BY region ORDER BY store_count DESC'
    ],
    expectedColumns: ['region', 'store_count'],
    explanation: 'WHERE lọc trước GROUP BY. COUNT(store_id) đếm số store active trong mỗi region.'
  },
  {
    id: 'ex-04',
    title: 'Sản phẩm thiếu giá vốn',
    difficulty: 'easy',
    category: 'IS NULL',
    description: 'Tìm các sản phẩm chưa được nhập giá vốn (cost = NULL). Hiển thị tên sản phẩm, thương hiệu và giá trị cost (NULL), sắp xếp theo thương hiệu.',
    businessContext: 'Phân tích lợi nhuận gộp không thể thực hiện khi thiếu cost — DA cần danh sách này để yêu cầu bộ phận tài chính bổ sung dữ liệu.',
    starterQuery: `SELECT product_name, brand, cost
FROM dim_product
WHERE cost -- IS NULL
ORDER BY brand`,
    solutionQuery: `SELECT product_name, brand, cost
FROM dim_product
WHERE cost IS NULL
ORDER BY brand`,
    hints: [
      'NULL không so sánh được bằng = hay !=; phải dùng IS NULL hoặc IS NOT NULL.',
      'IS NULL: cú pháp giống nhau trong DuckDB và T-SQL. Không dùng cost = NULL.',
      'SELECT product_name, brand, cost FROM dim_product WHERE cost IS NULL ORDER BY brand'
    ],
    expectedColumns: ['product_name', 'brand', 'cost'],
    explanation: 'IS NULL là cú pháp chuẩn SQL để kiểm tra giá trị vắng mặt. cost = NULL luôn trả về FALSE/UNKNOWN.'
  },
  {
    id: 'ex-05',
    title: 'Doanh số tháng 6/2024 (BETWEEN)',
    difficulty: 'easy',
    category: 'BETWEEN',
    description: 'Lấy 20 giao dịch bán hàng đầu tiên trong tháng 6/2024. date_key được lưu dạng số nguyên YYYYMMDD (ví dụ: 20240601).',
    businessContext: 'Kiểm tra nhanh dữ liệu tháng gần nhất để xác nhận pipeline ETL đã chạy đúng và dữ liệu được nạp đầy đủ.',
    starterQuery: `SELECT sale_id, date_key, gross_amount
FROM fact_sales
WHERE date_key -- BETWEEN ... AND ...
ORDER BY date_key
LIMIT 20`,
    solutionQuery: `SELECT sale_id, date_key, gross_amount
FROM fact_sales
WHERE date_key BETWEEN 20240601 AND 20240630
ORDER BY date_key
LIMIT 20`,
    hints: [
      'date_key là số nguyên YYYYMMDD. Dùng BETWEEN với hai giá trị nguyên để lọc cả tháng.',
      'BETWEEN a AND b tương đương >= a AND <= b. DuckDB: LIMIT N | T-SQL: TOP N (đặt trước SELECT list).',
      'SELECT sale_id, date_key, gross_amount FROM fact_sales WHERE date_key BETWEEN 20240601 AND 20240630 ORDER BY date_key LIMIT 20'
    ],
    expectedColumns: ['sale_id', 'date_key', 'gross_amount'],
    explanation: 'BETWEEN bao gồm cả hai đầu mút. LIMIT 20 (DuckDB) tương đương TOP 20 trong T-SQL.'
  },
  {
    id: 'ex-06',
    title: 'Phân loại tier giá sản phẩm',
    difficulty: 'easy',
    category: 'CASE WHEN',
    description: 'Phân loại sản phẩm đang bán thành ba nhóm giá: Premium (≥ 20.000đ), Standard (12.000–19.999đ), và Budget (< 12.000đ). Sắp xếp giá từ cao xuống thấp.',
    businessContext: 'Phân khúc giá giúp team marketing thiết kế chương trình khuyến mãi phù hợp với từng tệp khách hàng mục tiêu.',
    starterQuery: `SELECT product_name, gross_price,
  CASE
    -- WHEN gross_price >= 20000 THEN 'Premium'
    -- WHEN gross_price >= 12000 THEN 'Standard'
    -- ELSE 'Budget'
  END AS price_tier
FROM dim_product
WHERE is_active = true
ORDER BY gross_price DESC`,
    solutionQuery: `SELECT product_name, gross_price,
  CASE
    WHEN gross_price >= 20000 THEN 'Premium'
    WHEN gross_price >= 12000 THEN 'Standard'
    ELSE 'Budget'
  END AS price_tier
FROM dim_product
WHERE is_active = true
ORDER BY gross_price DESC`,
    hints: [
      'CASE WHEN kiểm tra điều kiện tuần tự từ trên xuống — điều kiện đầu tiên khớp sẽ được dùng.',
      'CASE WHEN ... THEN ... ELSE ... END: cú pháp giống nhau trong DuckDB và T-SQL.',
      "SELECT product_name, gross_price, CASE WHEN gross_price>=20000 THEN 'Premium' WHEN gross_price>=12000 THEN 'Standard' ELSE 'Budget' END AS price_tier FROM dim_product WHERE is_active=true ORDER BY gross_price DESC"
    ],
    expectedColumns: ['product_name', 'gross_price', 'price_tier'],
    explanation: 'CASE WHEN xử lý tuần tự: sản phẩm 25.000đ khớp điều kiện đầu tiên (>=20000) và được nhãn Premium ngay, không kiểm tra tiếp.'
  },
  {
    id: 'ex-07',
    title: 'Top 10 ngày doanh số cao nhất',
    difficulty: 'easy',
    category: 'ORDER BY + LIMIT',
    description: 'Tìm 10 ngày có tổng doanh số (gross_amount) cao nhất trong toàn bộ lịch sử dữ liệu.',
    businessContext: 'Xác định các ngày đỉnh doanh số giúp DA phân tích tác động của sự kiện, khuyến mãi, hay mùa cao điểm để tái lập chiến lược trong các kỳ tới.',
    starterQuery: `SELECT date_key, SUM(gross_amount) AS daily_gsv
FROM fact_sales
GROUP BY date_key
-- ORDER BY daily_gsv DESC
-- LIMIT 10`,
    solutionQuery: `SELECT date_key, SUM(gross_amount) AS daily_gsv
FROM fact_sales
GROUP BY date_key
ORDER BY daily_gsv DESC
LIMIT 10`,
    hints: [
      'Aggregate trước bằng GROUP BY + SUM, sau đó sắp xếp kết quả đã aggregate và lấy top.',
      'DuckDB: LIMIT 10 ở cuối | T-SQL: SELECT TOP 10 ... ở đầu câu query.',
      'SELECT date_key, SUM(gross_amount) AS daily_gsv FROM fact_sales GROUP BY date_key ORDER BY daily_gsv DESC LIMIT 10'
    ],
    expectedColumns: ['date_key', 'daily_gsv'],
    explanation: 'ORDER BY chạy sau GROUP BY — alias daily_gsv dùng được trong ORDER BY ở DuckDB (và SQL Server 2008+).'
  },
  {
    id: 'ex-08',
    title: 'Doanh số Q1 2024 theo sản phẩm',
    difficulty: 'easy',
    category: 'DATE filter',
    description: 'Tính tổng doanh số Q1 2024 (tháng 1–3/2024) cho từng sản phẩm. Sắp xếp sản phẩm có doanh số cao nhất lên đầu.',
    businessContext: 'Báo cáo kết quả quý là nhịp đánh giá định kỳ quan trọng — DA cần số liệu Q1 để so sánh với target và xây dựng dự báo Q2.',
    starterQuery: `SELECT product_id, SUM(gross_amount) AS q1_gsv
FROM fact_sales
WHERE date_key -- BETWEEN 20240101 AND 20240331
GROUP BY product_id
ORDER BY q1_gsv DESC`,
    solutionQuery: `SELECT product_id, SUM(gross_amount) AS q1_gsv
FROM fact_sales
WHERE date_key BETWEEN 20240101 AND 20240331
GROUP BY product_id
ORDER BY q1_gsv DESC`,
    hints: [
      'Q1 2024 = 1/1/2024 đến 31/3/2024. date_key là YYYYMMDD integer nên dùng BETWEEN với số nguyên.',
      'BETWEEN 20240101 AND 20240331 hoạt động giống nhau trong DuckDB và T-SQL.',
      'SELECT product_id, SUM(gross_amount) AS q1_gsv FROM fact_sales WHERE date_key BETWEEN 20240101 AND 20240331 GROUP BY product_id ORDER BY q1_gsv DESC'
    ],
    expectedColumns: ['product_id', 'q1_gsv'],
    explanation: 'date_key dạng integer YYYYMMDD cho phép so sánh và BETWEEN trực tiếp mà không cần hàm chuyển đổi date.'
  },
  {
    id: 'ex-09',
    title: 'Số SKU đang bán theo brand',
    difficulty: 'easy',
    category: 'GROUP BY + COUNT DISTINCT',
    description: 'Đếm số sản phẩm (SKU) đang active của mỗi thương hiệu. Sắp xếp thương hiệu có nhiều SKU nhất lên đầu.',
    businessContext: 'Độ rộng danh mục (breadth) là chỉ số quan trọng trong đánh giá portfolio — thương hiệu có ít SKU có thể cần bổ sung sản phẩm để cạnh tranh.',
    starterQuery: `SELECT brand, COUNT(product_id) AS sku_count
FROM dim_product
WHERE is_active = true
GROUP BY brand
-- ORDER BY sku_count DESC`,
    solutionQuery: `SELECT brand, COUNT(product_id) AS sku_count
FROM dim_product
WHERE is_active = true
GROUP BY brand
ORDER BY sku_count DESC`,
    hints: [
      'COUNT(product_id) đếm số hàng có product_id khác NULL trong mỗi brand group.',
      'COUNT(col) vs COUNT(*): COUNT(col) bỏ qua NULL, COUNT(*) đếm tất cả hàng. Cú pháp giống nhau DuckDB/T-SQL.',
      'SELECT brand, COUNT(product_id) AS sku_count FROM dim_product WHERE is_active=true GROUP BY brand ORDER BY sku_count DESC'
    ],
    expectedColumns: ['brand', 'sku_count'],
    explanation: 'COUNT(product_id) đếm số sản phẩm per brand. Bởi vì đã lọc is_active=true trước, kết quả chỉ phản ánh SKU đang kinh doanh.'
  },
  {
    id: 'ex-10',
    title: 'Tổng GSV per sản phẩm (JOIN đơn)',
    difficulty: 'easy',
    category: 'JOIN',
    description: 'Kết hợp fact_sales với dim_product để tính tổng doanh số theo tên và thương hiệu sản phẩm. Sắp xếp sản phẩm có doanh số cao nhất lên đầu.',
    businessContext: 'fact_sales chỉ lưu product_id — cần JOIN với dim_product để có tên sản phẩm dễ đọc cho báo cáo ban lãnh đạo.',
    starterQuery: `SELECT p.product_name, p.brand, SUM(s.gross_amount) AS total_gsv
FROM fact_sales s
-- JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.brand
ORDER BY total_gsv DESC`,
    solutionQuery: `SELECT p.product_name, p.brand, SUM(s.gross_amount) AS total_gsv
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.brand
ORDER BY total_gsv DESC`,
    hints: [
      'INNER JOIN trả về chỉ những hàng khớp ở cả hai bảng. Đặt alias s cho fact_sales và p cho dim_product.',
      'JOIN ... ON: cú pháp giống nhau DuckDB và T-SQL. GROUP BY phải bao gồm tất cả cột không aggregate.',
      'SELECT p.product_name, p.brand, SUM(s.gross_amount) AS total_gsv FROM fact_sales s JOIN dim_product p ON s.product_id=p.product_id GROUP BY p.product_id, p.product_name, p.brand ORDER BY total_gsv DESC'
    ],
    expectedColumns: ['product_name', 'brand', 'total_gsv'],
    explanation: 'JOIN nối fact table với dimension table qua khóa chung product_id. GROUP BY bao gồm product_id để tránh trùng lặp khi product_name không unique.'
  },

  // ─── MEDIUM 11–25 ─────────────────────────────────────────────────────────
  {
    id: 'ex-11',
    title: 'Doanh thu theo brand và kênh (Multi-JOIN)',
    difficulty: 'medium',
    category: 'Multi-JOIN',
    description: 'Tính tổng doanh thu thuần (net_amount) phân tách theo thương hiệu và loại kênh phân phối. Sắp xếp theo NSR giảm dần.',
    businessContext: 'Hiểu kênh nào đóng góp doanh thu cao nhất cho từng brand giúp team sales tối ưu chiến lược go-to-market và phân bổ nguồn lực đội ngũ.',
    starterQuery: `SELECT p.brand, c.channel_type, SUM(s.net_amount) AS nsr
FROM fact_sales s
-- JOIN dim_product p ON ...
-- JOIN dim_channel c ON ...
GROUP BY p.brand, c.channel_type
ORDER BY nsr DESC`,
    solutionQuery: `SELECT p.brand, c.channel_type, SUM(s.net_amount) AS nsr
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
JOIN dim_channel c ON s.channel_id = c.channel_id
GROUP BY p.brand, c.channel_type
ORDER BY nsr DESC`,
    hints: [
      'Cần 2 JOIN: fact_sales → dim_product (product_id) và fact_sales → dim_channel (channel_id).',
      'Chuỗi JOIN: FROM table1 JOIN table2 ON ... JOIN table3 ON ... Cú pháp giống nhau DuckDB/T-SQL.',
      'SELECT p.brand, c.channel_type, SUM(s.net_amount) AS nsr FROM fact_sales s JOIN dim_product p ON s.product_id=p.product_id JOIN dim_channel c ON s.channel_id=c.channel_id GROUP BY p.brand, c.channel_type ORDER BY nsr DESC'
    ],
    expectedColumns: ['brand', 'channel_type', 'nsr'],
    explanation: 'Multi-JOIN cho phép kết hợp nhiều dimension vào một query. fact_sales đóng vai trò trung tâm kết nối với các bảng dim qua foreign key.'
  },
  {
    id: 'ex-12',
    title: 'Store có NSR trên trung bình (Subquery)',
    difficulty: 'medium',
    category: 'Subquery',
    description: 'Tìm các store có tổng NSR vượt trên mức trung bình của tất cả store. Sắp xếp store hiệu quả nhất lên đầu.',
    businessContext: 'Nhận diện store vượt trội giúp team Key Account học hỏi best practice và áp dụng cho các store dưới mức trung bình để nâng tổng doanh thu.',
    starterQuery: `SELECT store_id, SUM(net_amount) AS total_nsr
FROM fact_sales
GROUP BY store_id
HAVING SUM(net_amount) > (
  -- subquery tính AVG NSR per store
)
ORDER BY total_nsr DESC`,
    solutionQuery: `SELECT store_id, SUM(net_amount) AS total_nsr
FROM fact_sales
GROUP BY store_id
HAVING SUM(net_amount) > (
  SELECT AVG(store_nsr)
  FROM (
    SELECT store_id, SUM(net_amount) AS store_nsr
    FROM fact_sales
    GROUP BY store_id
  )
)
ORDER BY total_nsr DESC`,
    hints: [
      'Subquery trong HAVING: tính tổng NSR per store trước, rồi lấy AVG của các tổng đó làm ngưỡng so sánh.',
      'Subquery lồng nhau: SELECT AVG(...) FROM (SELECT ... GROUP BY ...). Cú pháp giống DuckDB/T-SQL.',
      'HAVING SUM(net_amount) > (SELECT AVG(store_nsr) FROM (SELECT store_id, SUM(net_amount) AS store_nsr FROM fact_sales GROUP BY store_id))'
    ],
    expectedColumns: ['store_id', 'total_nsr'],
    explanation: 'Subquery trong HAVING cho phép so sánh kết quả aggregate với một giá trị tính toán động. Inner subquery cần alias để outer query tham chiếu.'
  },
  {
    id: 'ex-13',
    title: 'Brand GSV > 1 tỷ (HAVING)',
    difficulty: 'medium',
    category: 'HAVING',
    description: 'Lọc những thương hiệu có tổng doanh số vượt 1 tỷ đồng. Hiển thị tên brand và tổng GSV, sắp xếp từ cao xuống thấp.',
    businessContext: 'Xác định các brand "trụ cột" doanh thu giúp CFO ưu tiên đầu tư và team marketing tập trung ngân sách vào nhãn hàng có quy mô đủ lớn.',
    starterQuery: `SELECT p.brand, SUM(s.gross_amount) AS total_gsv
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.brand
-- HAVING SUM(s.gross_amount) > ...
ORDER BY total_gsv DESC`,
    solutionQuery: `SELECT p.brand, SUM(s.gross_amount) AS total_gsv
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.brand
HAVING SUM(s.gross_amount) > 1000000000
ORDER BY total_gsv DESC`,
    hints: [
      'HAVING lọc sau GROUP BY — dùng cho điều kiện trên aggregate. WHERE không dùng được với SUM().',
      'HAVING SUM(...) > value: cú pháp giống nhau DuckDB/T-SQL. 1 tỷ VND = 1,000,000,000.',
      'HAVING SUM(s.gross_amount) > 1000000000'
    ],
    expectedColumns: ['brand', 'total_gsv'],
    explanation: 'WHERE lọc hàng trước GROUP BY; HAVING lọc group sau khi aggregate. Không thể dùng WHERE với SUM() vì SUM chưa được tính lúc WHERE chạy.'
  },
  {
    id: 'ex-14',
    title: 'Doanh thu theo tháng (STRFTIME)',
    difficulty: 'medium',
    category: 'Date Functions',
    description: 'Tính tổng GSV theo từng tháng bằng cách join với dim_date và dùng STRFTIME để trích xuất năm-tháng. Sắp xếp theo thứ tự thời gian.',
    businessContext: 'Trend doanh số hàng tháng là đầu vào cốt lõi cho báo cáo P&L, forecast, và phát hiện sớm xu hướng tăng/giảm bất thường.',
    starterQuery: `SELECT STRFTIME(d.date, '%Y-%m') AS year_month,
       SUM(s.gross_amount) AS monthly_gsv
FROM fact_sales s
JOIN dim_date d ON s.date_key = d.date_key
-- GROUP BY year_month
ORDER BY year_month`,
    solutionQuery: `SELECT STRFTIME(d.date, '%Y-%m') AS year_month,
       SUM(s.gross_amount) AS monthly_gsv
FROM fact_sales s
JOIN dim_date d ON s.date_key = d.date_key
GROUP BY year_month
ORDER BY year_month`,
    hints: [
      'Join với dim_date để lấy cột date (VARCHAR), rồi dùng STRFTIME để format thành chuỗi YYYY-MM.',
      "DuckDB: STRFTIME(date,'%Y-%m') | T-SQL: FORMAT(date,'yyyy-MM'). GROUP BY có thể dùng alias trong DuckDB.",
      "SELECT STRFTIME(d.date,'%Y-%m') AS year_month, SUM(s.gross_amount) AS monthly_gsv FROM fact_sales s JOIN dim_date d ON s.date_key=d.date_key GROUP BY year_month ORDER BY year_month"
    ],
    expectedColumns: ['year_month', 'monthly_gsv'],
    explanation: "STRFTIME(date,'%Y-%m') trích xuất chuỗi 'YYYY-MM' từ date. DuckDB cho phép GROUP BY alias (year_month) — T-SQL yêu cầu lặp lại toàn bộ biểu thức."
  },
  {
    id: 'ex-15',
    title: 'Top 5 sản phẩm NSR (CTE)',
    difficulty: 'medium',
    category: 'CTE',
    description: 'Dùng CTE để tính NSR per sản phẩm trước, sau đó join kết quả với dim_product để lấy tên. Lấy top 5 sản phẩm có NSR cao nhất.',
    businessContext: 'CTE cải thiện khả năng đọc query phức tạp — quan trọng khi DA cần chia sẻ logic với team hoặc lưu vào tài liệu kỹ thuật.',
    starterQuery: `-- WITH product_nsr AS (
--   SELECT product_id, SUM(net_amount) AS total_nsr
--   FROM fact_sales
--   GROUP BY product_id
-- )
SELECT p.product_name, p.brand, pn.total_nsr
FROM product_nsr pn
JOIN dim_product p ON pn.product_id = p.product_id
ORDER BY total_nsr DESC
LIMIT 5`,
    solutionQuery: `WITH product_nsr AS (
  SELECT product_id, SUM(net_amount) AS total_nsr
  FROM fact_sales
  GROUP BY product_id
)
SELECT p.product_name, p.brand, pn.total_nsr
FROM product_nsr pn
JOIN dim_product p ON pn.product_id = p.product_id
ORDER BY total_nsr DESC
LIMIT 5`,
    hints: [
      'CTE (Common Table Expression) định nghĩa tập kết quả tạm thời trước câu SELECT chính bằng WITH.',
      'WITH cte_name AS (SELECT ...) SELECT ... FROM cte_name: cú pháp giống nhau DuckDB và T-SQL.',
      'WITH product_nsr AS (SELECT product_id, SUM(net_amount) AS total_nsr FROM fact_sales GROUP BY product_id) SELECT p.product_name, p.brand, pn.total_nsr FROM product_nsr pn JOIN dim_product p ON pn.product_id=p.product_id ORDER BY total_nsr DESC LIMIT 5'
    ],
    expectedColumns: ['product_name', 'brand', 'total_nsr'],
    explanation: 'CTE giúp tách logic thành bước rõ ràng: bước 1 tính NSR per product_id, bước 2 enrich với tên sản phẩm. Dễ đọc và debug hơn subquery lồng nhau.'
  },
  {
    id: 'ex-16',
    title: 'Brands kể cả không có doanh số (LEFT JOIN)',
    difficulty: 'medium',
    category: 'LEFT JOIN',
    description: 'Liệt kê tất cả brand từ dim_product kèm tổng số lần bán và tổng GSV — kể cả brand chưa có giao dịch nào. Dùng COALESCE để thay NULL bằng 0.',
    businessContext: 'LEFT JOIN đảm bảo không brand nào bị bỏ sót trong báo cáo dù chưa có doanh số — quan trọng khi launch sản phẩm mới trong kỳ báo cáo.',
    starterQuery: `SELECT p.brand,
       COUNT(s.sale_id) AS sale_count,
       COALESCE(SUM(s.gross_amount), 0) AS total_gsv
FROM dim_product p
-- LEFT JOIN fact_sales s ON ...
GROUP BY p.brand
ORDER BY total_gsv DESC`,
    solutionQuery: `SELECT p.brand,
       COUNT(s.sale_id) AS sale_count,
       COALESCE(SUM(s.gross_amount), 0) AS total_gsv
FROM dim_product p
LEFT JOIN fact_sales s ON p.product_id = s.product_id
GROUP BY p.brand
ORDER BY total_gsv DESC`,
    hints: [
      'LEFT JOIN giữ tất cả hàng từ bảng trái (dim_product) kể cả không khớp. Cột từ bảng phải sẽ NULL nếu không khớp.',
      "COALESCE(val, 0): DuckDB và T-SQL đều dùng COALESCE. T-SQL còn có ISNULL(val, 0) ngắn hơn.",
      'SELECT p.brand, COUNT(s.sale_id) AS sale_count, COALESCE(SUM(s.gross_amount),0) AS total_gsv FROM dim_product p LEFT JOIN fact_sales s ON p.product_id=s.product_id GROUP BY p.brand ORDER BY total_gsv DESC'
    ],
    expectedColumns: ['brand', 'sale_count', 'total_gsv'],
    explanation: 'LEFT JOIN khác INNER JOIN: giữ lại brand không có doanh số với COUNT=0, SUM=NULL. COALESCE chuyển NULL→0 cho tổng tiền hiển thị đẹp hơn.'
  },
  {
    id: 'ex-17',
    title: 'So sánh GSV 2 vùng HCM và HN (UNION ALL)',
    difficulty: 'medium',
    category: 'UNION',
    description: 'Dùng UNION ALL để xếp song song tổng GSV của vùng HCM và HN thành hai dòng trong cùng một bảng kết quả.',
    businessContext: 'Đặt hai vùng kinh doanh lớn nhất cạnh nhau giúp leadership so sánh nhanh và thảo luận tập trung trong cuộc họp review hàng tháng.',
    starterQuery: `SELECT 'HCM' AS region, SUM(s.gross_amount) AS total_gsv
FROM fact_sales s
JOIN dim_store st ON s.store_id = st.store_id
WHERE st.region = 'HCM'
-- UNION ALL
-- SELECT 'HN', SUM(...) FROM ... WHERE region = 'HN'`,
    solutionQuery: `SELECT 'HCM' AS region, SUM(s.gross_amount) AS total_gsv
FROM fact_sales s
JOIN dim_store st ON s.store_id = st.store_id
WHERE st.region = 'HCM'
UNION ALL
SELECT 'HN', SUM(s.gross_amount)
FROM fact_sales s
JOIN dim_store st ON s.store_id = st.store_id
WHERE st.region = 'HN'`,
    hints: [
      'UNION ALL ghép kết quả của hai SELECT mà không loại bỏ trùng lặp. Số cột và kiểu dữ liệu phải khớp.',
      'UNION ALL (giữ trùng lặp) vs UNION (loại trùng lặp). Cú pháp giống nhau DuckDB/T-SQL.',
      "SELECT 'HCM' AS region, SUM(s.gross_amount) AS total_gsv FROM fact_sales s JOIN dim_store st ON s.store_id=st.store_id WHERE st.region='HCM' UNION ALL SELECT 'HN', SUM(s.gross_amount) FROM fact_sales s JOIN dim_store st ON s.store_id=st.store_id WHERE st.region='HN'"
    ],
    expectedColumns: ['region', 'total_gsv'],
    explanation: "UNION ALL nhanh hơn UNION vì không sort để loại trùng. Hằng chuỗi 'HCM' và 'HN' được dùng làm label cho từng phần."
  },
  {
    id: 'ex-18',
    title: 'Xử lý trade_spend NULL (COALESCE)',
    difficulty: 'medium',
    category: 'COALESCE',
    description: 'Lấy 20 giao dịch đầu tiên từ fact_sales, thay thế trade_spend NULL bằng 0, và tính net_after_trade = gross_amount − trade_spend.',
    businessContext: 'trade_spend là nullable — không xử lý NULL sẽ khiến phép tính net revenue trả về NULL thay vì con số thực, gây sai lệch báo cáo P&L.',
    starterQuery: `SELECT sale_id,
       gross_amount,
       COALESCE(trade_spend, 0) AS trade_spend_clean,
       -- gross_amount - COALESCE(...) AS net_after_trade
FROM fact_sales
ORDER BY date_key
LIMIT 20`,
    solutionQuery: `SELECT sale_id,
       gross_amount,
       COALESCE(trade_spend, 0) AS trade_spend_clean,
       gross_amount - COALESCE(trade_spend, 0) AS net_after_trade
FROM fact_sales
ORDER BY date_key
LIMIT 20`,
    hints: [
      'COALESCE(a, b) trả về giá trị đầu tiên khác NULL. Dùng nó ở cả cột hiển thị lẫn trong phép tính.',
      'DuckDB: COALESCE(col, 0) | T-SQL: COALESCE(col, 0) hoặc ISNULL(col, 0). Kết quả giống nhau.',
      'gross_amount - COALESCE(trade_spend, 0) AS net_after_trade'
    ],
    expectedColumns: ['sale_id', 'gross_amount', 'trade_spend_clean', 'net_after_trade'],
    explanation: 'Khi một toán hạng là NULL, toàn bộ phép tính trả về NULL. COALESCE đảm bảo phép trừ luôn có giá trị số, không bị mất dữ liệu.'
  },
  {
    id: 'ex-19',
    title: 'Chỉ kênh MT và GT (IN)',
    difficulty: 'medium',
    category: 'IN',
    description: 'Tính tổng NSR chỉ cho kênh Modern Trade (MT) và General Trade (GT). Sắp xếp theo NSR giảm dần.',
    businessContext: 'MT và GT là hai kênh truyền thống chiếm phần lớn doanh thu FMCG — tách riêng hai kênh này để theo dõi hiệu quả của lực lượng bán hàng field.',
    starterQuery: `SELECT c.channel_name, SUM(s.net_amount) AS nsr
FROM fact_sales s
JOIN dim_channel c ON s.channel_id = c.channel_id
WHERE c.channel_type -- IN ('MT', 'GT')
GROUP BY c.channel_name
ORDER BY nsr DESC`,
    solutionQuery: `SELECT c.channel_name, SUM(s.net_amount) AS nsr
FROM fact_sales s
JOIN dim_channel c ON s.channel_id = c.channel_id
WHERE c.channel_type IN ('MT', 'GT')
GROUP BY c.channel_name
ORDER BY nsr DESC`,
    hints: [
      "IN (...) thay thế cho nhiều điều kiện OR. WHERE col IN ('val1','val2') ngắn gọn và dễ đọc hơn.",
      "IN ('MT','GT'): cú pháp giống nhau DuckDB và T-SQL. Lưu ý phân biệt hoa thường với chuỗi.",
      "WHERE c.channel_type IN ('MT','GT')"
    ],
    expectedColumns: ['channel_name', 'nsr'],
    explanation: "IN ('MT','GT') tương đương WHERE channel_type='MT' OR channel_type='GT'. IN tốt hơn khi có nhiều giá trị cần lọc."
  },
  {
    id: 'ex-20',
    title: 'Loại trừ kênh Digital (NOT IN)',
    difficulty: 'medium',
    category: 'NOT IN',
    description: 'Tính tổng GSV theo channel_type, loại trừ kênh Digital. Hiển thị các kênh còn lại sắp xếp theo GSV giảm dần.',
    businessContext: 'Phân tích offline vs online thường yêu cầu loại kênh Digital ra khỏi báo cáo offline để tránh đếm hai lần doanh số.',
    starterQuery: `SELECT c.channel_type, SUM(s.gross_amount) AS gsv
FROM fact_sales s
JOIN dim_channel c ON s.channel_id = c.channel_id
WHERE c.channel_type -- NOT IN ('Digital')
GROUP BY c.channel_type
ORDER BY gsv DESC`,
    solutionQuery: `SELECT c.channel_type, SUM(s.gross_amount) AS gsv
FROM fact_sales s
JOIN dim_channel c ON s.channel_id = c.channel_id
WHERE c.channel_type NOT IN ('Digital')
GROUP BY c.channel_type
ORDER BY gsv DESC`,
    hints: [
      'NOT IN loại trừ các giá trị liệt kê. Cẩn thận: NOT IN không hoạt động đúng khi danh sách có NULL.',
      "NOT IN ('val1','val2'): cú pháp giống nhau DuckDB và T-SQL.",
      "WHERE c.channel_type NOT IN ('Digital')"
    ],
    expectedColumns: ['channel_type', 'gsv'],
    explanation: "NOT IN ('Digital') giữ lại tất cả kênh trừ Digital. Lưu ý: nếu danh sách trong NOT IN chứa NULL, toàn bộ WHERE trả về FALSE — luôn đảm bảo danh sách không có NULL."
  },
  {
    id: 'ex-21',
    title: 'Số store active mỗi tháng (MAU)',
    difficulty: 'medium',
    category: 'MAU',
    description: 'Đếm số store khác nhau có giao dịch bán hàng trong mỗi tháng, tính dạng integer YYYYMM. Sắp xếp theo thứ tự thời gian.',
    businessContext: 'Monthly Active Stores (MAS) là KPI đo độ phủ thị trường — xu hướng giảm store active có thể báo hiệu vấn đề về phân phối hoặc đứt hàng.',
    starterQuery: `SELECT d.year * 100 + d.month AS year_month,
       COUNT(DISTINCT s.store_id) AS active_stores
FROM fact_sales s
JOIN dim_date d ON s.date_key = d.date_key
-- GROUP BY year_month
ORDER BY year_month`,
    solutionQuery: `SELECT d.year * 100 + d.month AS year_month,
       COUNT(DISTINCT s.store_id) AS active_stores
FROM fact_sales s
JOIN dim_date d ON s.date_key = d.date_key
GROUP BY year_month
ORDER BY year_month`,
    hints: [
      'Dùng d.year * 100 + d.month để tạo integer YYYYMM (ví dụ: 2024 * 100 + 6 = 202406). COUNT DISTINCT đếm store unique.',
      'COUNT(DISTINCT col): cú pháp giống nhau DuckDB và T-SQL.',
      'SELECT d.year*100+d.month AS year_month, COUNT(DISTINCT s.store_id) AS active_stores FROM fact_sales s JOIN dim_date d ON s.date_key=d.date_key GROUP BY year_month ORDER BY year_month'
    ],
    expectedColumns: ['year_month', 'active_stores'],
    explanation: 'year * 100 + month tạo integer sắp xếp được theo thứ tự thời gian. COUNT(DISTINCT store_id) đếm mỗi store một lần dù có nhiều giao dịch trong tháng.'
  },
  {
    id: 'ex-22',
    title: 'Trade Spend% theo brand',
    difficulty: 'medium',
    category: 'Trade Spend%',
    description: 'Tính tỉ lệ Trade Spend trên GSV (%) theo từng brand. trade_spend có thể NULL — cần xử lý trước khi tính tỉ lệ.',
    businessContext: 'Trade Spend% là chỉ số đo hiệu quả chi tiêu thương mại — brand nào có Trade Spend% cao nhưng GSV thấp cần được xem xét lại ngân sách.',
    starterQuery: `SELECT p.brand,
       SUM(s.gross_amount) AS gsv,
       SUM(COALESCE(s.trade_spend, 0)) AS trade_spend_total,
       -- ROUND(... * 100.0 / SUM(s.gross_amount), 2) AS trade_spend_pct
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.brand
ORDER BY trade_spend_pct DESC`,
    solutionQuery: `SELECT p.brand,
       SUM(s.gross_amount) AS gsv,
       SUM(COALESCE(s.trade_spend, 0)) AS trade_spend_total,
       ROUND(SUM(COALESCE(s.trade_spend, 0)) * 100.0 / SUM(s.gross_amount), 2) AS trade_spend_pct
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.brand
ORDER BY trade_spend_pct DESC`,
    hints: [
      'Tỉ lệ % = trade_spend / gsv * 100. Nhân 100.0 (không phải 100) để tránh integer division.',
      'ROUND(val, decimals): cú pháp giống nhau DuckDB và T-SQL. COALESCE xử lý NULL trước khi SUM.',
      'ROUND(SUM(COALESCE(s.trade_spend,0))*100.0/SUM(s.gross_amount),2) AS trade_spend_pct'
    ],
    expectedColumns: ['brand', 'gsv', 'trade_spend_total', 'trade_spend_pct'],
    explanation: 'Nhân 100.0 thay vì 100 ép kiểu float division. COALESCE trước SUM hiệu quả hơn COALESCE sau SUM vì xử lý từng hàng trước khi cộng dồn.'
  },
  {
    id: 'ex-23',
    title: 'Basket Size trung bình (fact_transactions)',
    difficulty: 'medium',
    category: 'Basket Size',
    description: 'Tính basket size trung bình và số lượng transaction theo từng brand từ bảng fact_transactions. Sắp xếp basket size từ cao xuống thấp.',
    businessContext: 'Basket size đo lường giá trị trung bình mỗi lần mua hàng — brand có basket size cao thường được mua cùng với sản phẩm khác, phản ánh hành vi bundle purchase.',
    starterQuery: `SELECT p.brand,
       ROUND(AVG(t.basket_size), 0) AS avg_basket_size,
       COUNT(t.txn_id) AS txn_count
FROM fact_transactions t
-- JOIN dim_product p ON ...
GROUP BY p.brand
ORDER BY avg_basket_size DESC`,
    solutionQuery: `SELECT p.brand,
       ROUND(AVG(t.basket_size), 0) AS avg_basket_size,
       COUNT(t.txn_id) AS txn_count
FROM fact_transactions t
JOIN dim_product p ON t.product_id = p.product_id
GROUP BY p.brand
ORDER BY avg_basket_size DESC`,
    hints: [
      'JOIN fact_transactions với dim_product qua product_id. AVG tính trung bình basket_size per brand.',
      'ROUND(AVG(col), 0): làm tròn đến số nguyên. Cú pháp giống nhau DuckDB và T-SQL.',
      'SELECT p.brand, ROUND(AVG(t.basket_size),0) AS avg_basket_size, COUNT(t.txn_id) AS txn_count FROM fact_transactions t JOIN dim_product p ON t.product_id=p.product_id GROUP BY p.brand ORDER BY avg_basket_size DESC'
    ],
    expectedColumns: ['brand', 'avg_basket_size', 'txn_count'],
    explanation: 'fact_transactions là bảng loyalty/scan data riêng biệt với fact_sales. AVG(basket_size) tính trung bình tất cả transaction của brand đó.'
  },
  {
    id: 'ex-24',
    title: 'MoM Growth% doanh số (LAG)',
    difficulty: 'medium',
    category: 'LAG / MoM',
    description: 'Tính tăng trưởng doanh số tháng so tháng (Month-over-Month %) dùng window function LAG. CTE tính GSV theo tháng trước, SELECT chính tính delta và %.',
    businessContext: 'MoM growth là chỉ số bắt buộc trong mọi báo cáo business review — cho thấy tốc độ tăng trưởng ngắn hạn và phát hiện sớm tháng bất thường.',
    starterQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS year_month,
         SUM(s.gross_amount) AS gsv
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  GROUP BY year_month
)
SELECT year_month, gsv,
  -- LAG(gsv) OVER (ORDER BY year_month) AS prev_month_gsv,
  -- ROUND((gsv - LAG(...)) * 100.0 / LAG(...), 1) AS mom_growth_pct
FROM monthly
ORDER BY year_month`,
    solutionQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS year_month,
         SUM(s.gross_amount) AS gsv
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  GROUP BY year_month
)
SELECT year_month,
       gsv,
       LAG(gsv) OVER (ORDER BY year_month) AS prev_month_gsv,
       ROUND((gsv - LAG(gsv) OVER (ORDER BY year_month)) * 100.0
             / LAG(gsv) OVER (ORDER BY year_month), 1) AS mom_growth_pct
FROM monthly
ORDER BY year_month`,
    hints: [
      'LAG(col) OVER (ORDER BY ...) lấy giá trị của hàng trước. Tháng đầu tiên sẽ có prev = NULL.',
      'LAG(col) OVER (ORDER BY col): cú pháp giống nhau DuckDB và T-SQL (SQL Server 2012+).',
      'LAG(gsv) OVER (ORDER BY year_month) AS prev_month_gsv, ROUND((gsv - LAG(gsv) OVER (ORDER BY year_month))*100.0/LAG(gsv) OVER (ORDER BY year_month),1) AS mom_growth_pct'
    ],
    expectedColumns: ['year_month', 'gsv', 'prev_month_gsv', 'mom_growth_pct'],
    explanation: 'LAG là window function — tính trên kết quả đã GROUP BY trong CTE. Tháng đầu trả về NULL cho prev và pct vì không có tháng trước.'
  },
  {
    id: 'ex-25',
    title: 'Achievement% Actual vs Target',
    difficulty: 'medium',
    category: 'Achievement%',
    description: 'So sánh doanh số thực tế (gross_amount) với target (target_amount) per sản phẩm, tính tỉ lệ hoàn thành %. Dùng NULLIF để tránh chia cho 0.',
    businessContext: 'Achievement% so với target là KPI số 1 trong mọi cuộc họp sales review — cho thấy sản phẩm nào vượt/không đạt kế hoạch để ra quyết định điều chỉnh.',
    starterQuery: `SELECT p.product_name, p.brand,
       SUM(s.gross_amount) AS actual_gsv,
       SUM(s.target_amount) AS target_gsv,
       -- ROUND(SUM(gross_amount) * 100.0 / NULLIF(SUM(target_amount), 0), 1) AS achievement_pct
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.brand
ORDER BY achievement_pct DESC`,
    solutionQuery: `SELECT p.product_name, p.brand,
       SUM(s.gross_amount) AS actual_gsv,
       SUM(s.target_amount) AS target_gsv,
       ROUND(SUM(s.gross_amount) * 100.0 / NULLIF(SUM(s.target_amount), 0), 1) AS achievement_pct
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.brand
ORDER BY achievement_pct DESC`,
    hints: [
      'NULLIF(a, b) trả về NULL nếu a=b, ngược lại trả về a. Dùng NULLIF(target, 0) để tránh lỗi chia cho 0.',
      'NULLIF(col, 0): cú pháp giống nhau DuckDB và T-SQL. Kết quả NULL sẽ hiển thị NULL thay vì lỗi.',
      'ROUND(SUM(s.gross_amount)*100.0/NULLIF(SUM(s.target_amount),0),1) AS achievement_pct'
    ],
    expectedColumns: ['product_name', 'brand', 'actual_gsv', 'target_gsv', 'achievement_pct'],
    explanation: 'NULLIF phòng trường hợp target = 0 (sản phẩm mới chưa có target). Chia cho NULL trả về NULL thay vì lỗi division by zero.'
  },

  // ─── HARD 26–40 ───────────────────────────────────────────────────────────
  {
    id: 'ex-26',
    title: 'Xếp hạng store theo NSR trong vùng (RANK)',
    difficulty: 'hard',
    category: 'RANK',
    description: 'Xếp hạng từng store theo NSR trong phạm vi vùng địa lý của nó bằng RANK() OVER (PARTITION BY region). Sắp xếp theo vùng và hạng.',
    businessContext: 'Xếp hạng store trong vùng giúp Area Manager xác định top store để nhân rộng mô hình thành công và bottom store cần hỗ trợ.',
    starterQuery: `SELECT st.store_name, st.region,
       SUM(s.net_amount) AS nsr,
       -- RANK() OVER (PARTITION BY st.region ORDER BY SUM(...) DESC) AS region_rank
FROM fact_sales s
JOIN dim_store st ON s.store_id = st.store_id
GROUP BY st.store_id, st.store_name, st.region
ORDER BY st.region, region_rank`,
    solutionQuery: `SELECT st.store_name, st.region,
       SUM(s.net_amount) AS nsr,
       RANK() OVER (PARTITION BY st.region ORDER BY SUM(s.net_amount) DESC) AS region_rank
FROM fact_sales s
JOIN dim_store st ON s.store_id = st.store_id
GROUP BY st.store_id, st.store_name, st.region
ORDER BY st.region, region_rank`,
    hints: [
      'RANK() OVER (PARTITION BY region ORDER BY nsr DESC): tạo hạng riêng cho mỗi region, bỏ qua số hạng khi có tie.',
      'RANK() OVER (PARTITION BY col ORDER BY col): cú pháp giống nhau DuckDB và T-SQL (SQL Server 2005+). DENSE_RANK() không bỏ số.',
      'RANK() OVER (PARTITION BY st.region ORDER BY SUM(s.net_amount) DESC) AS region_rank'
    ],
    expectedColumns: ['store_name', 'region', 'nsr', 'region_rank'],
    explanation: 'PARTITION BY tạo "cửa sổ" riêng mỗi region. RANK bỏ số khi có tie (ví dụ: hạng 1, 1, 3). Window function chạy sau GROUP BY nên có thể dùng SUM() trong ORDER BY của OVER.'
  },
  {
    id: 'ex-27',
    title: 'DENSE_RANK sản phẩm theo GSV',
    difficulty: 'hard',
    category: 'DENSE_RANK',
    description: 'Xếp hạng liên tiếp (không bỏ số) tất cả sản phẩm theo tổng GSV toàn cục. Hai sản phẩm cùng GSV cùng hạng, sản phẩm tiếp theo là hạng liền sau.',
    businessContext: 'DENSE_RANK phù hợp hơn RANK trong báo cáo portfolio vì không tạo khoảng trống số hạng — danh sách "Top 10 sản phẩm" dễ đọc hơn.',
    starterQuery: `SELECT p.product_name, p.brand,
       SUM(s.gross_amount) AS gsv,
       -- DENSE_RANK() OVER (ORDER BY SUM(...) DESC) AS gsv_rank
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.brand
ORDER BY gsv_rank`,
    solutionQuery: `SELECT p.product_name, p.brand,
       SUM(s.gross_amount) AS gsv,
       DENSE_RANK() OVER (ORDER BY SUM(s.gross_amount) DESC) AS gsv_rank
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.brand
ORDER BY gsv_rank`,
    hints: [
      'DENSE_RANK() không bỏ số hạng khi có tie. Không cần PARTITION BY nếu xếp hạng toàn cục.',
      'DENSE_RANK() OVER (ORDER BY col DESC): cú pháp giống nhau DuckDB và T-SQL.',
      'DENSE_RANK() OVER (ORDER BY SUM(s.gross_amount) DESC) AS gsv_rank'
    ],
    expectedColumns: ['product_name', 'brand', 'gsv', 'gsv_rank'],
    explanation: 'DENSE_RANK vs RANK: nếu hạng 2 có tie, RANK cho hạng 4 tiếp theo, DENSE_RANK cho hạng 3. DENSE_RANK phù hợp hơn cho báo cáo "Top N".'
  },
  {
    id: 'ex-28',
    title: 'LAG: NSR category theo tháng',
    difficulty: 'hard',
    category: 'LAG / Window',
    description: 'Dùng LAG với PARTITION BY category để lấy NSR tháng trước trong cùng category. Kết quả cho thấy xu hướng tháng-sau-tháng của từng danh mục sản phẩm.',
    businessContext: 'Phân tích trend theo category giúp Brand Manager hiểu RTD Coffee và Energy Drink đang tăng/giảm độc lập hay cùng chiều, phục vụ quyết định phân bổ ngân sách.',
    starterQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS ym,
         p.category,
         SUM(s.net_amount) AS nsr
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  JOIN dim_product p ON s.product_id = p.product_id
  GROUP BY ym, p.category
)
SELECT ym, category, nsr,
  -- LAG(nsr) OVER (PARTITION BY category ORDER BY ym) AS prev_nsr
FROM monthly
ORDER BY category, ym`,
    solutionQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS ym,
         p.category,
         SUM(s.net_amount) AS nsr
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  JOIN dim_product p ON s.product_id = p.product_id
  GROUP BY ym, p.category
)
SELECT ym, category, nsr,
       LAG(nsr) OVER (PARTITION BY category ORDER BY ym) AS prev_nsr
FROM monthly
ORDER BY category, ym`,
    hints: [
      'LAG với PARTITION BY category đảm bảo prev_nsr lấy từ cùng category, không nhảy sang category khác.',
      'LAG(col) OVER (PARTITION BY cat ORDER BY ym): cú pháp giống nhau DuckDB/T-SQL.',
      'LAG(nsr) OVER (PARTITION BY category ORDER BY ym) AS prev_nsr'
    ],
    expectedColumns: ['ym', 'category', 'nsr', 'prev_nsr'],
    explanation: 'PARTITION BY trong LAG tạo ra window riêng mỗi category — hàng đầu tiên của mỗi category trả về NULL cho prev_nsr thay vì lấy từ category khác.'
  },
  {
    id: 'ex-29',
    title: 'LEAD: Dự báo tháng tiếp theo',
    difficulty: 'hard',
    category: 'LEAD',
    description: 'Dùng LEAD để nhìn sang tháng tiếp theo trong cùng chuỗi thời gian. Kết quả hiển thị GSV tháng hiện tại và GSV thực tế của tháng sau (nếu có).',
    businessContext: 'LEAD hữu ích để xây dựng bảng so sánh "tháng này vs tháng tới" trong dashboard — giúp planner nhìn thấy trajectory và điều chỉnh kế hoạch kịp thời.',
    starterQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS ym,
         SUM(s.gross_amount) AS gsv
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  GROUP BY ym
)
SELECT ym, gsv,
  -- LEAD(gsv) OVER (ORDER BY ym) AS next_month_gsv
FROM monthly
ORDER BY ym`,
    solutionQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS ym,
         SUM(s.gross_amount) AS gsv
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  GROUP BY ym
)
SELECT ym, gsv,
       LEAD(gsv) OVER (ORDER BY ym) AS next_month_gsv
FROM monthly
ORDER BY ym`,
    hints: [
      'LEAD(col) lấy giá trị của hàng tiếp theo (ngược với LAG). Tháng cuối cùng sẽ có next_month_gsv = NULL.',
      'LEAD(col, offset, default) OVER (ORDER BY ...): offset mặc định 1, default mặc định NULL. Giống nhau DuckDB/T-SQL.',
      'LEAD(gsv) OVER (ORDER BY ym) AS next_month_gsv'
    ],
    expectedColumns: ['ym', 'gsv', 'next_month_gsv'],
    explanation: 'LEAD nhìn về phía trước trong cửa sổ sắp xếp theo thời gian. Hàng cuối của dataset trả về NULL vì không có tháng sau.'
  },
  {
    id: 'ex-30',
    title: 'Running Total NSR lũy kế (SUM OVER)',
    difficulty: 'hard',
    category: 'Running Total',
    description: 'Tính NSR lũy kế từ đầu năm đến từng tháng (YTD) dùng SUM() OVER với cửa sổ không giới hạn từ đầu đến hàng hiện tại.',
    businessContext: 'YTD NSR là con số lãnh đạo xem mỗi ngày để theo dõi tiến độ so với kế hoạch năm — running total biến báo cáo tháng thành biểu đồ tích lũy.',
    starterQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS ym,
         SUM(s.net_amount) AS monthly_nsr
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  GROUP BY ym
)
SELECT ym, monthly_nsr,
  -- SUM(monthly_nsr) OVER (ORDER BY ym) AS ytd_nsr
FROM monthly
ORDER BY ym`,
    solutionQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS ym,
         SUM(s.net_amount) AS monthly_nsr
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  GROUP BY ym
)
SELECT ym, monthly_nsr,
       SUM(monthly_nsr) OVER (ORDER BY ym) AS ytd_nsr
FROM monthly
ORDER BY ym`,
    hints: [
      'SUM() OVER (ORDER BY col) tạo running total — mặc định cửa sổ từ hàng đầu đến hàng hiện tại (ROWS UNBOUNDED PRECEDING TO CURRENT ROW).',
      'SUM(col) OVER (ORDER BY col): cú pháp giống nhau DuckDB/T-SQL. Không cần ROWS BETWEEN nếu muốn cumulative sum mặc định.',
      'SUM(monthly_nsr) OVER (ORDER BY ym) AS ytd_nsr'
    ],
    expectedColumns: ['ym', 'monthly_nsr', 'ytd_nsr'],
    explanation: 'SUM() OVER (ORDER BY) với frame mặc định RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW tạo cumulative sum. Mỗi hàng cộng dồn tất cả hàng từ đầu đến hàng đó.'
  },
  {
    id: 'ex-31',
    title: 'Top 1 sản phẩm per kênh (ROW_NUMBER)',
    difficulty: 'hard',
    category: 'ROW_NUMBER',
    description: 'Dùng ROW_NUMBER() để tìm sản phẩm bán chạy nhất (theo GSV) trong mỗi kênh phân phối. Lọc chỉ lấy rn=1 trong CTE.',
    businessContext: 'Biết hero product của từng kênh giúp Key Account Manager tập trung đẩy mạnh sản phẩm phù hợp nhất với từng loại điểm bán.',
    starterQuery: `WITH ranked AS (
  SELECT c.channel_name, p.product_name,
         SUM(s.gross_amount) AS gsv,
         ROW_NUMBER() OVER (
           PARTITION BY c.channel_id
           ORDER BY SUM(s.gross_amount) DESC
         ) AS rn
  FROM fact_sales s
  JOIN dim_channel c ON s.channel_id = c.channel_id
  JOIN dim_product p ON s.product_id = p.product_id
  GROUP BY c.channel_id, c.channel_name, p.product_id, p.product_name
)
-- SELECT channel_name, product_name, gsv FROM ranked WHERE rn = 1`,
    solutionQuery: `WITH ranked AS (
  SELECT c.channel_name, p.product_name,
         SUM(s.gross_amount) AS gsv,
         ROW_NUMBER() OVER (
           PARTITION BY c.channel_id
           ORDER BY SUM(s.gross_amount) DESC
         ) AS rn
  FROM fact_sales s
  JOIN dim_channel c ON s.channel_id = c.channel_id
  JOIN dim_product p ON s.product_id = p.product_id
  GROUP BY c.channel_id, c.channel_name, p.product_id, p.product_name
)
SELECT channel_name, product_name, gsv
FROM ranked
WHERE rn = 1
ORDER BY gsv DESC`,
    hints: [
      'ROW_NUMBER() đánh số thứ tự duy nhất, không có tie. PARTITION BY channel đảm bảo đánh số lại từ 1 cho mỗi kênh.',
      'Không thể dùng window function trong WHERE trực tiếp — cần bọc trong CTE hoặc subquery rồi lọc WHERE rn=1.',
      'WITH ranked AS (...ROW_NUMBER() OVER (PARTITION BY c.channel_id ORDER BY SUM(s.gross_amount) DESC) AS rn...) SELECT ... FROM ranked WHERE rn=1'
    ],
    expectedColumns: ['channel_name', 'product_name', 'gsv'],
    explanation: 'ROW_NUMBER khác RANK: luôn đánh số duy nhất ngay cả khi tie — đảm bảo WHERE rn=1 trả về đúng 1 hàng mỗi kênh. Cần CTE vì không filter được window function trong WHERE.'
  },
  {
    id: 'ex-32',
    title: 'Phân nhóm store theo NSR (NTILE quartile)',
    difficulty: 'hard',
    category: 'NTILE',
    description: 'Dùng NTILE(4) để chia store thành 4 nhóm bằng nhau theo NSR (Q1=cao nhất, Q4=thấp nhất). Hiển thị tên store, vùng, NSR và quartile.',
    businessContext: 'Phân quartile store giúp xác định rõ top 25% (Q1) để áp dụng chương trình loyalty premium và bottom 25% (Q4) để có kế hoạch phục hồi.',
    starterQuery: `SELECT st.store_name, st.region,
       SUM(s.net_amount) AS nsr,
       -- NTILE(4) OVER (ORDER BY SUM(s.net_amount) DESC) AS nsr_quartile
FROM fact_sales s
JOIN dim_store st ON s.store_id = st.store_id
GROUP BY st.store_id, st.store_name, st.region
ORDER BY nsr DESC`,
    solutionQuery: `SELECT st.store_name, st.region,
       SUM(s.net_amount) AS nsr,
       NTILE(4) OVER (ORDER BY SUM(s.net_amount) DESC) AS nsr_quartile
FROM fact_sales s
JOIN dim_store st ON s.store_id = st.store_id
GROUP BY st.store_id, st.store_name, st.region
ORDER BY nsr DESC`,
    hints: [
      'NTILE(n) chia kết quả thành n bucket bằng nhau theo thứ tự. NTILE(4) → quartile (Q1 to Q4).',
      'NTILE(n) OVER (ORDER BY col): cú pháp giống nhau DuckDB và T-SQL. Bucket 1 là group đầu theo ORDER BY.',
      'NTILE(4) OVER (ORDER BY SUM(s.net_amount) DESC) AS nsr_quartile'
    ],
    expectedColumns: ['store_name', 'region', 'nsr', 'nsr_quartile'],
    explanation: 'NTILE(4) tạo 4 nhóm từ dữ liệu đã sắp xếp: nhóm 1 là top stores, nhóm 4 là bottom stores. Nếu số hàng không chia hết cho 4, các nhóm đầu được thêm 1 hàng.'
  },
  {
    id: 'ex-33',
    title: 'Rolling 3 tháng NSR (Moving Average)',
    difficulty: 'hard',
    category: 'Rolling Avg',
    description: 'Tính trung bình động NSR 3 tháng (current + 2 tháng trước) dùng AVG() OVER với ROWS BETWEEN 2 PRECEDING AND CURRENT ROW.',
    businessContext: 'Moving average làm mịn biến động tháng và loại nhiễu từ sự kiện đơn lẻ — giúp leadership nhìn thấy trend dài hạn thay vì phản ứng với từng tháng bất thường.',
    starterQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS ym,
         SUM(s.net_amount) AS monthly_nsr
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  GROUP BY ym
)
SELECT ym, monthly_nsr,
  -- ROUND(AVG(monthly_nsr) OVER (
  --   ORDER BY ym
  --   ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
  -- ), 0) AS rolling_3m_avg
FROM monthly
ORDER BY ym`,
    solutionQuery: `WITH monthly AS (
  SELECT STRFTIME(d.date, '%Y-%m') AS ym,
         SUM(s.net_amount) AS monthly_nsr
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  GROUP BY ym
)
SELECT ym, monthly_nsr,
       ROUND(AVG(monthly_nsr) OVER (
         ORDER BY ym
         ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ), 0) AS rolling_3m_avg
FROM monthly
ORDER BY ym`,
    hints: [
      'ROWS BETWEEN 2 PRECEDING AND CURRENT ROW định nghĩa cửa sổ trượt 3 hàng (hàng hiện tại + 2 hàng trước).',
      'AVG() OVER (ORDER BY col ROWS BETWEEN n PRECEDING AND CURRENT ROW): cú pháp giống nhau DuckDB/T-SQL.',
      'AVG(monthly_nsr) OVER (ORDER BY ym ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)'
    ],
    expectedColumns: ['ym', 'monthly_nsr', 'rolling_3m_avg'],
    explanation: '2 tháng đầu có rolling avg tính trên ít hơn 3 điểm (1 và 2 tháng tương ứng) vì không đủ preceding rows. ROWS khác RANGE: ROWS tính theo vị trí vật lý, RANGE theo giá trị.'
  },
  {
    id: 'ex-34',
    title: 'RFM: Recency Frequency Monetary (CTE)',
    difficulty: 'hard',
    category: 'RFM / CTE',
    description: 'Tính ba chỉ số RFM cho từng store: Recency (số ngày từ giao dịch cuối đến ngày max), Frequency (số ngày có giao dịch), Monetary (tổng NSR). Dùng hai CTE lồng nhau.',
    businessContext: 'RFM là framework phân tích khách hàng kinh điển trong retail — giúp Key Account Manager phân loại store thành groups để có chiến lược tiếp cận khác nhau.',
    starterQuery: `WITH ref AS (
  SELECT MAX(date_key) AS max_dk FROM fact_sales
),
rfm AS (
  SELECT store_id,
    (SELECT max_dk FROM ref) - MAX(date_key) AS recency_days,
    COUNT(DISTINCT date_key) AS frequency,
    SUM(net_amount) AS monetary
  FROM fact_sales
  GROUP BY store_id
)
-- SELECT store_id, recency_days, frequency, monetary FROM rfm`,
    solutionQuery: `WITH ref AS (
  SELECT MAX(date_key) AS max_dk FROM fact_sales
),
rfm AS (
  SELECT store_id,
    (SELECT max_dk FROM ref) - MAX(date_key) AS recency_days,
    COUNT(DISTINCT date_key) AS frequency,
    SUM(net_amount) AS monetary
  FROM fact_sales
  GROUP BY store_id
)
SELECT store_id, recency_days, frequency, monetary
FROM rfm
ORDER BY recency_days, monetary DESC`,
    hints: [
      'CTE ref tính max_dk một lần. CTE rfm dùng scalar subquery (SELECT max_dk FROM ref) trong SELECT list để tính recency.',
      'Multiple CTE: WITH cte1 AS (...), cte2 AS (...) SELECT ... FROM cte2. Cú pháp giống nhau DuckDB/T-SQL.',
      'WITH ref AS (SELECT MAX(date_key) AS max_dk FROM fact_sales), rfm AS (SELECT store_id, (SELECT max_dk FROM ref)-MAX(date_key) AS recency_days, COUNT(DISTINCT date_key) AS frequency, SUM(net_amount) AS monetary FROM fact_sales GROUP BY store_id) SELECT store_id, recency_days, frequency, monetary FROM rfm ORDER BY recency_days, monetary DESC'
    ],
    expectedColumns: ['store_id', 'recency_days', 'frequency', 'monetary'],
    explanation: 'date_key là integer YYYYMMDD — phép trừ hai integer không cho số ngày thực nhưng nhất quán để so sánh tương đối. Trong thực tế dùng DATE_DIFF để tính ngày chính xác.'
  },
  {
    id: 'ex-35',
    title: 'YoY 2024 vs 2025 theo brand (CTE)',
    difficulty: 'hard',
    category: 'YoY / CTE',
    description: 'So sánh GSV năm 2024 và 2025 theo brand dùng hai CTE riêng biệt, sau đó JOIN và tính % tăng trưởng YoY. Sắp xếp brand tăng trưởng tốt nhất lên đầu.',
    businessContext: 'Year-over-Year growth là metric chiến lược được báo cáo với C-level và board — cho thấy brand nào đang tăng trưởng bền vững hay mất thị phần.',
    starterQuery: `WITH y24 AS (
  SELECT p.brand, SUM(s.gross_amount) AS gsv_2024
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  JOIN dim_product p ON s.product_id = p.product_id
  WHERE d.year = 2024
  GROUP BY p.brand
),
y25 AS (
  -- tương tự cho year = 2025
  SELECT p.brand, SUM(s.gross_amount) AS gsv_2025
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  JOIN dim_product p ON s.product_id = p.product_id
  WHERE d.year = 2025
  GROUP BY p.brand
)
-- SELECT brand, gsv_2024, gsv_2025, YoY% FROM y24 JOIN y25 ...`,
    solutionQuery: `WITH y24 AS (
  SELECT p.brand, SUM(s.gross_amount) AS gsv_2024
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  JOIN dim_product p ON s.product_id = p.product_id
  WHERE d.year = 2024
  GROUP BY p.brand
),
y25 AS (
  SELECT p.brand, SUM(s.gross_amount) AS gsv_2025
  FROM fact_sales s
  JOIN dim_date d ON s.date_key = d.date_key
  JOIN dim_product p ON s.product_id = p.product_id
  WHERE d.year = 2025
  GROUP BY p.brand
)
SELECT a.brand,
       a.gsv_2024,
       b.gsv_2025,
       ROUND((b.gsv_2025 - a.gsv_2024) * 100.0 / a.gsv_2024, 1) AS yoy_pct
FROM y24 a
JOIN y25 b ON a.brand = b.brand
ORDER BY yoy_pct DESC`,
    hints: [
      'Hai CTE y24 và y25 lọc theo year. JOIN hai CTE trên brand để đặt song song, rồi tính delta %.',
      'YoY% = (year2 - year1) / year1 * 100. Cần nhân 100.0 để tránh integer division. Cú pháp giống DuckDB/T-SQL.',
      'ROUND((b.gsv_2025 - a.gsv_2024)*100.0/a.gsv_2024, 1) AS yoy_pct'
    ],
    expectedColumns: ['brand', 'gsv_2024', 'gsv_2025', 'yoy_pct'],
    explanation: 'Pattern hai CTE + JOIN là cách chuẩn để so sánh hai kỳ. INNER JOIN chỉ trả về brand có dữ liệu cả hai năm — dùng FULL OUTER JOIN nếu muốn giữ brand chỉ có 1 năm.'
  },
  {
    id: 'ex-36',
    title: 'NSR per kênh per tháng + Running Total (Partition)',
    difficulty: 'hard',
    category: 'Partition + Running',
    description: 'Tính NSR theo kênh và tháng, đồng thời tính running total NSR trong từng kênh theo thời gian bằng SUM() OVER (PARTITION BY channel ORDER BY month).',
    businessContext: 'Running total per kênh cho thấy kênh nào đang tích lũy doanh thu nhanh hơn — hữu ích trong mid-year review để dự báo liệu kênh có đạt target năm không.',
    starterQuery: `SELECT STRFTIME(d.date, '%Y-%m') AS ym,
       c.channel_type,
       SUM(s.net_amount) AS channel_nsr,
       -- SUM(SUM(s.net_amount)) OVER (
       --   PARTITION BY c.channel_type ORDER BY STRFTIME(d.date, '%Y-%m')
       -- ) AS running_channel_nsr
FROM fact_sales s
JOIN dim_date d ON s.date_key = d.date_key
JOIN dim_channel c ON s.channel_id = c.channel_id
GROUP BY ym, c.channel_type
ORDER BY ym, c.channel_type`,
    solutionQuery: `SELECT STRFTIME(d.date, '%Y-%m') AS ym,
       c.channel_type,
       SUM(s.net_amount) AS channel_nsr,
       SUM(SUM(s.net_amount)) OVER (
         PARTITION BY c.channel_type
         ORDER BY STRFTIME(d.date, '%Y-%m')
       ) AS running_channel_nsr
FROM fact_sales s
JOIN dim_date d ON s.date_key = d.date_key
JOIN dim_channel c ON s.channel_id = c.channel_id
GROUP BY ym, c.channel_type
ORDER BY ym, c.channel_type`,
    hints: [
      'SUM(SUM(col)) OVER (...): SUM bên trong là aggregate (GROUP BY), SUM bên ngoài là window function chạy trên kết quả đã group.',
      'Nested aggregate trong window function: SUM(SUM(col)) OVER (PARTITION BY ... ORDER BY ...): cú pháp giống DuckDB/T-SQL.',
      'SUM(SUM(s.net_amount)) OVER (PARTITION BY c.channel_type ORDER BY STRFTIME(d.date,\'%Y-%m\')) AS running_channel_nsr'
    ],
    expectedColumns: ['ym', 'channel_type', 'channel_nsr', 'running_channel_nsr'],
    explanation: 'SUM(SUM()) lồng nhau: SUM bên trong group dữ liệu raw thành monthly NSR per channel, SUM bên ngoài là window function tính cumulative trên kết quả đó theo từng channel.'
  },
  {
    id: 'ex-37',
    title: 'Brand Share% trong category',
    difficulty: 'hard',
    category: 'Brand Share%',
    description: 'Tính tỉ trọng % GSV của từng brand trong tổng GSV toàn danh mục. Dùng CTE để tính tổng một lần, tránh subquery tính lại nhiều lần.',
    businessContext: 'Market share (brand share%) là KPI được theo dõi hàng tuần bởi Marketing Director — brand mất share liên tiếp 2-3 tháng cần can thiệp ngay về pricing hoặc activation.',
    starterQuery: `WITH total AS (
  SELECT SUM(gross_amount) AS total_gsv FROM fact_sales
)
SELECT p.brand, p.category,
       SUM(s.gross_amount) AS brand_gsv,
       -- ROUND(SUM(s.gross_amount) * 100.0 / (SELECT total_gsv FROM total), 2) AS brand_share_pct
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.brand, p.category
ORDER BY brand_share_pct DESC`,
    solutionQuery: `WITH total AS (
  SELECT SUM(gross_amount) AS total_gsv FROM fact_sales
)
SELECT p.brand, p.category,
       SUM(s.gross_amount) AS brand_gsv,
       ROUND(SUM(s.gross_amount) * 100.0 / (SELECT total_gsv FROM total), 2) AS brand_share_pct
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.brand, p.category
ORDER BY brand_share_pct DESC`,
    hints: [
      'CTE total tính tổng một lần. Scalar subquery (SELECT total_gsv FROM total) trong SELECT list tái sử dụng giá trị đó cho mỗi hàng.',
      'Scalar subquery trong SELECT: (SELECT single_value FROM cte). Cú pháp giống nhau DuckDB/T-SQL.',
      'ROUND(SUM(s.gross_amount)*100.0/(SELECT total_gsv FROM total),2) AS brand_share_pct'
    ],
    expectedColumns: ['brand', 'category', 'brand_gsv', 'brand_share_pct'],
    explanation: 'CTE total tính mẫu số một lần duy nhất thay vì subquery lặp lại cho mỗi hàng. Tổng brand_share_pct của tất cả brand sẽ bằng 100%.'
  },
  {
    id: 'ex-38',
    title: 'Category Mix% theo vùng',
    difficulty: 'hard',
    category: 'Category Mix%',
    description: 'Tính tỉ trọng % GSV của mỗi category trong từng vùng. Dùng hai CTE: region_total cho mẫu số và region_cat cho tử số, sau đó JOIN để tính %.',
    businessContext: 'Category mix theo vùng phát hiện sự khác biệt tiêu dùng địa phương — ví dụ MienTrung có thể ưa Energy Drink hơn RTD Coffee, ảnh hưởng đến phân bổ SKU per store.',
    starterQuery: `WITH region_total AS (
  SELECT st.region, SUM(s.gross_amount) AS region_gsv
  FROM fact_sales s
  JOIN dim_store st ON s.store_id = st.store_id
  GROUP BY st.region
),
region_cat AS (
  SELECT st.region, p.category, SUM(s.gross_amount) AS cat_gsv
  FROM fact_sales s
  JOIN dim_store st ON s.store_id = st.store_id
  JOIN dim_product p ON s.product_id = p.product_id
  GROUP BY st.region, p.category
)
-- SELECT region, category, cat_gsv, category_mix_pct
-- FROM region_cat JOIN region_total ON ...`,
    solutionQuery: `WITH region_total AS (
  SELECT st.region, SUM(s.gross_amount) AS region_gsv
  FROM fact_sales s
  JOIN dim_store st ON s.store_id = st.store_id
  GROUP BY st.region
),
region_cat AS (
  SELECT st.region, p.category, SUM(s.gross_amount) AS cat_gsv
  FROM fact_sales s
  JOIN dim_store st ON s.store_id = st.store_id
  JOIN dim_product p ON s.product_id = p.product_id
  GROUP BY st.region, p.category
)
SELECT rc.region, rc.category, rc.cat_gsv,
       ROUND(rc.cat_gsv * 100.0 / rt.region_gsv, 2) AS category_mix_pct
FROM region_cat rc
JOIN region_total rt ON rc.region = rt.region
ORDER BY rc.region, category_mix_pct DESC`,
    hints: [
      'Hai CTE: region_total có denominator (GSV toàn vùng), region_cat có numerator (GSV per category per region). JOIN trên region để tính %.',
      'Pattern denominator CTE + numerator CTE + JOIN để tính tỉ lệ: cú pháp giống nhau DuckDB/T-SQL.',
      'ROUND(rc.cat_gsv*100.0/rt.region_gsv,2) AS category_mix_pct FROM region_cat rc JOIN region_total rt ON rc.region=rt.region'
    ],
    expectedColumns: ['region', 'category', 'cat_gsv', 'category_mix_pct'],
    explanation: 'Pattern hai CTE tách biệt tử số và mẫu số làm code rõ ràng và tái sử dụng được. Tổng category_mix_pct trong mỗi region sẽ bằng 100%.'
  },
  {
    id: 'ex-39',
    title: 'Brew Points: Earned vs Redeemed (Burn Rate)',
    difficulty: 'hard',
    category: 'Loyalty / Burn Rate',
    description: 'Tính tỉ lệ đốt điểm (burn rate) = điểm đã đổi / điểm đã tích lũy × 100% theo từng brand từ fact_transactions. Dùng NULLIF để tránh chia cho 0.',
    businessContext: 'Burn rate thấp báo hiệu loyalty program không thu hút — người dùng tích điểm nhưng không đổi thưởng, có thể do phần thưởng kém hấp dẫn hoặc UX app khó dùng.',
    starterQuery: `SELECT p.brand,
       SUM(t.brew_points_earned) AS pts_earned,
       SUM(t.brew_points_redeemed) AS pts_redeemed,
       -- ROUND(SUM(pts_redeemed) * 100.0 / NULLIF(SUM(pts_earned), 0), 1) AS burn_rate_pct
FROM fact_transactions t
JOIN dim_product p ON t.product_id = p.product_id
GROUP BY p.brand
ORDER BY burn_rate_pct DESC`,
    solutionQuery: `SELECT p.brand,
       SUM(t.brew_points_earned) AS pts_earned,
       SUM(t.brew_points_redeemed) AS pts_redeemed,
       ROUND(SUM(t.brew_points_redeemed) * 100.0 / NULLIF(SUM(t.brew_points_earned), 0), 1) AS burn_rate_pct
FROM fact_transactions t
JOIN dim_product p ON t.product_id = p.product_id
GROUP BY p.brand
ORDER BY burn_rate_pct DESC`,
    hints: [
      'Burn rate = redeemed / earned * 100. Dùng NULLIF(earned, 0) để tránh lỗi chia cho 0 khi brand chưa có điểm tích.',
      'NULLIF(col, 0): cú pháp giống nhau DuckDB/T-SQL. Trả về NULL khi col=0 → phép chia trả về NULL thay vì lỗi.',
      'ROUND(SUM(t.brew_points_redeemed)*100.0/NULLIF(SUM(t.brew_points_earned),0),1) AS burn_rate_pct'
    ],
    expectedColumns: ['brand', 'pts_earned', 'pts_redeemed', 'burn_rate_pct'],
    explanation: 'fact_transactions là bảng riêng cho loyalty/scan data. NULLIF phòng edge case brand mới chưa có điểm tích. Burn rate > 100% là dấu hiệu dữ liệu bất thường cần investigate.'
  },
  {
    id: 'ex-40',
    title: 'Full Scorecard: Brand Performance Dashboard',
    difficulty: 'hard',
    category: 'Full Scorecard',
    description: 'Xây dựng bảng scorecard tổng hợp đầy đủ cho từng brand: GSV, Discount, NSR, Trade Spend%, Achievement%, và số store active. Tất cả trong một query duy nhất.',
    businessContext: 'One-page brand scorecard là tài liệu bắt buộc trong mọi cuộc họp monthly business review — DA giỏi biết cách tổng hợp 6–7 KPI vào một query gọn thay vì chạy nhiều báo cáo rời.',
    starterQuery: `SELECT p.brand,
       SUM(s.gross_amount) AS gsv,
       SUM(s.discount_amount) AS discount,
       SUM(s.net_amount) AS nsr,
       -- ROUND(trade_spend% ...) AS trade_spend_pct,
       -- ROUND(achievement% ...) AS achievement_pct,
       COUNT(DISTINCT s.store_id) AS active_stores
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.brand
ORDER BY gsv DESC`,
    solutionQuery: `SELECT p.brand,
       SUM(s.gross_amount) AS gsv,
       SUM(s.discount_amount) AS discount,
       SUM(s.net_amount) AS nsr,
       ROUND(SUM(COALESCE(s.trade_spend, 0)) * 100.0 / SUM(s.gross_amount), 2) AS trade_spend_pct,
       ROUND(SUM(s.gross_amount) * 100.0 / NULLIF(SUM(s.target_amount), 0), 1) AS achievement_pct,
       COUNT(DISTINCT s.store_id) AS active_stores
FROM fact_sales s
JOIN dim_product p ON s.product_id = p.product_id
GROUP BY p.brand
ORDER BY gsv DESC`,
    hints: [
      'Kết hợp: COALESCE cho trade_spend nullable, NULLIF cho target nullable, COUNT DISTINCT cho store. Tất cả tính trên cùng GROUP BY brand.',
      'Scorecard query: một GROUP BY duy nhất, nhiều metric aggregate. Cú pháp giống nhau DuckDB/T-SQL. Không cần CTE nếu chỉ cần một mức group.',
      'ROUND(SUM(COALESCE(s.trade_spend,0))*100.0/SUM(s.gross_amount),2) AS trade_spend_pct, ROUND(SUM(s.gross_amount)*100.0/NULLIF(SUM(s.target_amount),0),1) AS achievement_pct, COUNT(DISTINCT s.store_id) AS active_stores'
    ],
    expectedColumns: ['brand', 'gsv', 'discount', 'nsr', 'trade_spend_pct', 'achievement_pct', 'active_stores'],
    explanation: 'Scorecard query tổng hợp nhiều KPI trong một pass duy nhất qua dữ liệu — hiệu quả hơn nhiều query riêng lẻ. Kết hợp COALESCE, NULLIF, COUNT DISTINCT và tỉ lệ % trong cùng SELECT list là kỹ năng DA thực chiến.'
  }
]
