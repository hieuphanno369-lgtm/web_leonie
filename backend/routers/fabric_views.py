from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/fabric-views", tags=["fabric_views"])

_VW_FACT_TXN = """\
CREATE OR ALTER VIEW dbo.vw_fact_txn_enriched AS
WITH base AS (
    SELECT
         f.Customer__c                       AS customer_id
        ,a.Phone                             AS phone
        ,a.Name                              AS customer_name
        ,a.Tier__c                           AS tier
        ,a.Region                            AS region
        ,a.Billing_Province_Name_New__c      AS province
        ,a.Customer_External_ID__c           AS ra_external_id
        ,f.Transaction_External_ID__c        AS txn_id
        ,f.Transaction_Date__c               AS txn_date
        ,CAST(f.Transaction_Date__c AS DATE) AS txn_date_only
        ,f.Amount__c                         AS amount
        ,f.Rule_Name__c                      AS rule_name
        ,f.Distributor_Code__c               AS distributor_code
        ,f.Distributor_Name__c               AS distributor_name
        ,f.Store_ID__c                       AS store_id
        ,f.Store_Name__c                     AS store_name
        ,ch.Channel                          AS channel
        ,b.Brand                             AS brand
        ,b.Sub_Brand                         AS sub_brand
        ,b.Product_Code                      AS product_code
        ,b.Product_Name                      AS product_name
        ,b.Product_Type                      AS product_type
        ,dda.Account_SubType                 AS account_subtype
        ,dda.Account_Source                  AS account_source
        ,dda.RFM_Segment                     AS rfm_segment
    FROM      fact f
    JOIN      dim_brand b    ON b.Product_Code  = f.Product_Code__c
    JOIN      dim_channel ch ON ch.Customer     = f.Distributor_Code__c
    JOIN      dim_detail_account dda ON dda.Customer__c = f.Customer__c
    LEFT JOIN dim_account a  ON a.Id            = f.Customer__c
    WHERE  f.Transaction_Type__c  = 'Product Point'
       AND b.Product_Type         = 'SỮA BỘT'
       AND f.Amount__c            > 0
       AND f.Transaction_Date__c >= '2026-01-01 00:00:00'
       AND f.Transaction_Date__c <= GETDATE()
),
seq AS (
    SELECT b.*
        ,ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY txn_date ASC, txn_id ASC) AS txn_seq
        ,MIN(txn_date) OVER (PARTITION BY customer_id) AS first_touch_date
    FROM base b
),
first_touch AS (
    SELECT customer_id, brand AS first_brand, sub_brand AS first_sub_brand
          ,channel AS first_channel, region AS first_region
    FROM seq WHERE txn_seq = 1
)
SELECT
     s.customer_id, s.phone, s.customer_name, s.tier, s.region, s.province, s.ra_external_id
    ,s.txn_id, s.txn_date, s.txn_date_only, s.amount, s.rule_name, s.txn_seq, s.first_touch_date
    ,DATEDIFF(DAY, s.first_touch_date, s.txn_date) AS days_since_first_touch
    ,FORMAT(s.first_touch_date, 'yyyy-MM')         AS cohort_month
    ,CASE WHEN s.txn_seq > 1 THEN 1 ELSE 0 END     AS is_repeat_buyer
    ,s.brand, s.sub_brand, s.product_code, s.product_name, s.product_type
    ,s.channel, s.distributor_code, s.distributor_name, s.store_id, s.store_name
    ,s.account_subtype, s.account_source, s.rfm_segment
    ,ft.first_brand, ft.first_sub_brand, ft.first_channel, ft.first_region
FROM seq s LEFT JOIN first_touch ft ON ft.customer_id = s.customer_id;"""

_VW_DIM_LOOKUP = """\
CREATE OR ALTER VIEW dbo.vw_dim_customer_lookup AS
SELECT
     a.Id                              AS customer_id
    ,a.Phone                           AS phone
    ,a.Name                            AS customer_name
    ,a.Customer_External_ID__c         AS ra_external_id
    ,a.Customer_Type__c                AS customer_type
    ,a.Tier__c                         AS tier
    ,a.Billing_Province_Name_New__c    AS province
    ,a.Region                          AS region
    ,a.Last_Transaction_Date__c        AS last_transaction
    ,a.Redeem_Points__c                AS current_points
    ,dda.Account_SubType               AS account_subtype
    ,dda.Account_Source                AS account_source
    ,dda.RFM_Segment                   AS rfm_segment
    ,dda.So_Tich                       AS tong_so_luot_tich_alltime
    ,dda.Total_So_lon                  AS tong_so_lon_tich_alltime
    ,dda.Months_Active                 AS months_active_alltime
FROM dim_account a
LEFT JOIN dim_detail_account dda ON dda.Customer__c = a.Id;"""

_VW_DIM_360 = """\
CREATE OR ALTER VIEW dbo.vw_dim_customer_360 AS
WITH agg AS (
    SELECT customer_id
        ,MAX(phone) AS phone, MAX(customer_name) AS customer_name
        ,MAX(tier) AS tier, MAX(region) AS region, MAX(rfm_segment) AS rfm_segment
        ,MAX(account_subtype) AS account_subtype, MAX(account_source) AS account_source
        ,MAX(first_brand) AS first_brand, MAX(first_sub_brand) AS first_sub_brand
        ,MAX(first_channel) AS first_channel, MAX(first_region) AS first_region
        ,COUNT(DISTINCT txn_id)                              AS so_luot_tich
        ,SUM(amount)                                         AS dso_tich
        ,MIN(txn_date)                                       AS first_txn_date
        ,MAX(txn_date)                                       AS last_txn_date
        ,CAST(SUM(amount)*1.0/NULLIF(COUNT(DISTINCT txn_id),0) AS DECIMAL(18,2)) AS aov
        ,DATEDIFF(DAY, MIN(txn_date), GETDATE())             AS days_since_first_txn
        ,COUNT(DISTINCT FORMAT(txn_date,'yyyy-MM'))          AS months_active
        ,MAX(txn_seq)                                        AS max_txn_seq
        ,MAX(CASE WHEN txn_seq>=1 THEN 1 ELSE 0 END)         AS reached_L1
        ,MAX(CASE WHEN txn_seq>=2 THEN 1 ELSE 0 END)         AS reached_L2
        ,MAX(CASE WHEN txn_seq>=3 THEN 1 ELSE 0 END)         AS reached_L3
        ,MAX(CASE WHEN txn_seq>=4 THEN 1 ELSE 0 END)         AS reached_L4
        ,MAX(CASE WHEN txn_seq>=5 THEN 1 ELSE 0 END)         AS reached_L5
    FROM dbo.vw_fact_txn_enriched GROUP BY customer_id
),
brand_mix AS (
    SELECT customer_id, brand AS top_brand
          ,ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY SUM(amount) DESC) AS rn
    FROM dbo.vw_fact_txn_enriched GROUP BY customer_id, brand
),
channel_mix AS (
    SELECT customer_id, channel AS top_channel
          ,ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY SUM(amount) DESC) AS rn
    FROM dbo.vw_fact_txn_enriched GROUP BY customer_id, channel
)
SELECT a.*
      ,CAST(a.so_luot_tich*1.0/NULLIF(a.months_active,0) AS DECIMAL(10,2)) AS avg_tich_per_month
      ,bm.top_brand, cm.top_channel
FROM agg a
LEFT JOIN brand_mix   bm ON bm.customer_id=a.customer_id AND bm.rn=1
LEFT JOIN channel_mix cm ON cm.customer_id=a.customer_id AND cm.rn=1;"""

_VW_MART_PIVOT = """\
CREATE OR ALTER VIEW dbo.vw_mart_cust_brand_channel_month AS
SELECT
     customer_id
    ,MAX(customer_name)  AS customer_name
    ,MAX(tier)           AS tier
    ,MAX(region)         AS region
    ,brand, sub_brand, channel
    ,FORMAT(txn_date,'yyyy-MM')                AS month_year
    ,COUNT(DISTINCT txn_id)                    AS so_luot_tich
    ,SUM(amount)                               AS dso_tich
    ,CAST(SUM(amount)*1.0/NULLIF(COUNT(DISTINCT txn_id),0) AS DECIMAL(18,2)) AS aov
    ,MIN(txn_date) AS first_txn_month
    ,MAX(txn_date) AS last_txn_month
FROM dbo.vw_fact_txn_enriched
GROUP BY customer_id, brand, sub_brand, channel, FORMAT(txn_date,'yyyy-MM');"""

_VW_MART_COHORT = """\
CREATE OR ALTER VIEW dbo.vw_mart_cohort AS
SELECT
     customer_id, cohort_month
    ,first_brand, first_sub_brand, first_channel, first_region
    ,MAX(account_subtype)                           AS account_subtype
    ,MAX(account_source)                            AS account_source
    ,MAX(CASE WHEN txn_seq=1 THEN 1 ELSE 0 END)     AS has_L1
    ,MAX(CASE WHEN txn_seq=2 THEN 1 ELSE 0 END)     AS has_L2
    ,MAX(CASE WHEN txn_seq=3 THEN 1 ELSE 0 END)     AS has_L3
    ,MAX(CASE WHEN txn_seq=4 THEN 1 ELSE 0 END)     AS has_L4
    ,MAX(CASE WHEN txn_seq=5 THEN 1 ELSE 0 END)     AS has_L5
    ,SUM(amount)            AS total_dso
    ,COUNT(DISTINCT txn_id) AS total_luot
FROM dbo.vw_fact_txn_enriched
GROUP BY customer_id, cohort_month
        ,first_brand, first_sub_brand, first_channel, first_region;"""

_SEED = [
    ("vw_fact_txn_enriched",            "dbo", "fact",   "Wide fact view — 1 row = 1 txn, enriched dim + derived cols. Base cho mọi analysis YTD 2026. Filter: Product Point + SỮA BỘT + Amount>0 + YTD 2026",                     _VW_FACT_TXN,    "Fact,YTD2026,Enriched"),
    ("vw_dim_customer_lookup",           "dbo", "dim",    "Light lookup — phone/customer_id → profile cơ bản: tier, region, points, RFM. Thay thế Query 1. Grain: 1 row = 1 customer",                                               _VW_DIM_LOOKUP,  "Dim,Customer,Lookup"),
    ("vw_dim_customer_360",              "dbo", "dim",    "Customer snapshot 360° YTD 2026 — KPI aggregate: so_luot_tich, dso_tich, AOV, months_active, reached_L1→L5, top_brand, top_channel. Thay thế Query 7",                    _VW_DIM_360,     "Dim,Customer,360,KPI"),
    ("vw_mart_cust_brand_channel_month", "dbo", "report", "Mart pivot cho Power BI — grain: customer × brand × channel × month. Dùng cho trend analysis, brand/channel comparison",                                                  _VW_MART_PIVOT,  "Mart,PowerBI,Pivot,Monthly"),
    ("vw_mart_cohort",                   "dbo", "report", "Cohort retention L1→L5 — flexible filter theo dimension (brand, channel, account_subtype). has_L1→L5 flags cho cohort waterfall. Thay thế Query 8",                        _VW_MART_COHORT, "Mart,Cohort,Retention"),
]


def _ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fabric_views (
            id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            name        TEXT NOT NULL UNIQUE,
            schema_name TEXT NOT NULL DEFAULT 'dbo',
            category    TEXT NOT NULL DEFAULT 'fact',
            description TEXT,
            sql_def     TEXT,
            tags        TEXT DEFAULT '',
            created     TEXT NOT NULL DEFAULT (datetime('now')),
            updated     TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    # Seed if empty
    count = conn.execute("SELECT COUNT(*) FROM fabric_views").fetchone()[0]
    if count == 0:
        for name, schema, cat, desc, sql, tags in _SEED:
            conn.execute(
                "INSERT OR IGNORE INTO fabric_views (name,schema_name,category,description,sql_def,tags) VALUES (?,?,?,?,?,?)",
                (name, schema, cat, desc, sql, tags)
            )
        conn.commit()


class ViewIn(BaseModel):
    name: str
    schema_name: str = "dbo"
    category: str = "fact"
    description: str = ""
    sql_def: str = ""
    tags: str = ""


@router.get("")
def list_views(q: str = "", category: str = ""):
    conn = get_connection(); _ensure_table(conn)
    sql = "SELECT * FROM fabric_views WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (name LIKE ? OR description LIKE ? OR tags LIKE ?)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND category=?"
        params.append(category)
    sql += " ORDER BY category, name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_view(body: ViewIn):
    conn = get_connection(); _ensure_table(conn)
    try:
        conn.execute(
            "INSERT INTO fabric_views (name,schema_name,category,description,sql_def,tags) VALUES (?,?,?,?,?,?)",
            (body.name, body.schema_name, body.category, body.description, body.sql_def, body.tags)
        )
        conn.commit()
    except Exception:
        raise HTTPException(400, "View name already exists")
    row = conn.execute("SELECT * FROM fabric_views WHERE rowid=last_insert_rowid()").fetchone()
    conn.close()
    return dict(row)


@router.put("/{view_id}")
def update_view(view_id: str, body: ViewIn):
    conn = get_connection(); _ensure_table(conn)
    conn.execute(
        "UPDATE fabric_views SET name=?,schema_name=?,category=?,description=?,sql_def=?,tags=?,updated=datetime('now') WHERE id=?",
        (body.name, body.schema_name, body.category, body.description, body.sql_def, body.tags, view_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM fabric_views WHERE id=?", (view_id,)).fetchone()
    conn.close()
    return dict(row)


@router.delete("/{view_id}", status_code=204)
def delete_view(view_id: str):
    conn = get_connection(); _ensure_table(conn)
    conn.execute("DELETE FROM fabric_views WHERE id=?", (view_id,))
    conn.commit()
    conn.close()
