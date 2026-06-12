#!/usr/bin/env python3
"""
seed_snippets.py — Populate SnippetLibrary from 3 sources:
  1. Old task-tracker: data/sql_snippets.json  (16 T-SQL)
  2. Old task-tracker: data/snippets.json      (6 Python + 4 SQL + 2 Shell)
  3. Ad-hoc library:   05_Snipets/ad_hoc/      (37 files)

Run from project root:  python backend/seed_snippets.py
Re-runnable: skips titles already in DB.
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leonie.db")

# ──────────────────────────────────────────────────────────────
# SNIPPETS  — (title, category, tags, sql/code)
# category:  ad_hoc | metric | join | filter | template | other
# ──────────────────────────────────────────────────────────────
SNIPPETS = [

    # ═══════════════════════════════════════════════════════════
    # SOURCE 1 — sql_snippets.json (16 T-SQL, old task-tracker)
    # ═══════════════════════════════════════════════════════════

    (
        "List Customer CBB_Gold_New và Lactoferrin theo NPP Thế Giới Sữa",
        "ad_hoc",
        "sales,distributor,sub_brand,ColosBaby,filter",
        """SELECT
    dc.Customer                                 AS distributor_id,
    dc.Name                                     AS distributor_name,
    db.Sub_Brand                                AS brand_name,
    f.Store_ID__c                               AS store_id,
    f.Store_Name__c                             AS store_name,
    month(f.[Transaction_Date__date_only])      AS month_year,
    COUNT(f.Transaction_External_ID__c)         AS so_luot_tich,
    COUNT(DISTINCT f.Customer__c)               AS sl_user,
    ROUND(CAST(COUNT(f.Transaction_External_ID__c) AS FLOAT)
        / DAY(EOMONTH(MIN(f.[Transaction_Date__date_only]))), 2) AS avg_tich_per_day
FROM fact AS f
LEFT JOIN dim_channel AS dc
    ON  f.Distributor_Code__c = dc.Customer
LEFT JOIN dim_brand   AS db
    ON  f.Product_Code__c    = db.Product_Code
WHERE dc.Name              LIKE N'%Thế Giới Sữa%'
  AND db.Sub_Brand         IN ('ColosBaby_Gold_New', 'ColosBaby_Lactoferrin')
  AND f.Transaction_Type__c = 'Product Point'
  AND CAST(f.Transaction_Date__date_only AS DATE) >= '2026-03-25'
  AND CAST(f.Transaction_Date__date_only AS DATE) <= '2026-04-28'
GROUP BY db.Sub_Brand, month(f.[Transaction_Date__date_only]),
         dc.Name, dc.Customer, f.Store_ID__c, f.Store_Name__c
ORDER BY so_luot_tich DESC;""",
    ),

    (
        "Check Phone — full profile (phone + RFM + dim_account)",
        "filter",
        "customer,phone,lookup,rfm",
        """WITH input_phones AS (
    SELECT phone FROM (VALUES
        ('0973490089'),('0985555825'),('0378931092'),('0337426462'),
        ('0398992741'),('0868647993'),('0939193802'),('0979755902'),
        ('0969467923'),('0966293121'),('0339100923'),('0977238421'),
        ('0984770380'),('0975804454'),('0949766983')
    ) AS v(phone)
),
account_match AS (
    SELECT
         i.phone                    AS input_phone
        ,a.Id                       AS account_id
        ,a.Name                     AS customer_name
        ,a.Phone                    AS phone_in_dwh
        ,a.Customer_External_ID__c  AS ra_external_id
        ,a.Customer_Type__c         AS customer_type
        ,a.Tier__c                  AS tier
        ,a.Billing_Province_Name_New__c AS province_new
        ,a.Region                   AS region
        ,a.Last_Transaction_Date__c AS last_transaction
        ,a.Redeem_Points__c         AS current_points
    FROM input_phones i
    LEFT JOIN dim_account a ON i.phone = a.Phone
),
rfm_profile AS (
    SELECT
         dda.Customer__c    AS account_id
        ,dda.Account_SubType AS account_type_rfm
        ,dda.So_Tich        AS tong_so_luot_tich
        ,dda.Total_So_lon   AS tong_so_lon_tich
        ,dda.Months_Active  AS months_active
    FROM dim_detail_account dda
)
SELECT
     am.input_phone, am.account_id, am.customer_name
    ,am.customer_type, rp.account_type_rfm
    ,am.province_new, am.region, am.current_points
    ,am.tier, am.last_transaction
    ,rp.tong_so_luot_tich, rp.tong_so_lon_tich, rp.months_active
FROM account_match am
LEFT JOIN rfm_profile rp ON rp.account_id = am.account_id
ORDER BY am.input_phone;""",
    ),

    (
        "Check Phone ngắn gọn",
        "filter",
        "customer,phone,lookup",
        """WITH input_phones AS (
    SELECT phone FROM (VALUES
        ('0973490089'),('0985555825'),('0378931092'),('0337426462'),
        ('0398992741'),('0868647993'),('0939193802'),('0979755902'),
        ('0969467923'),('0966293121'),('0339100923'),('0977238421'),
        ('0984770380'),('0975804454'),('0949766983')
    ) AS v(phone)
)
SELECT
     a.Name                           AS customer_name
    ,a.Phone                          AS phone_in_dwh
    ,a.Customer_External_ID__c        AS ra_external_id
    ,a.Customer_Type__c               AS customer_type
    ,a.Billing_Province_Name_New__c   AS province_new
    ,a.Region                         AS region
    ,a.Redeem_Points__c               AS current_points
FROM input_phones i
LEFT JOIN dim_account a ON i.phone = a.Phone;""",
    ),

    (
        "Check Customer_External_ID (dim_detail_account)",
        "filter",
        "customer,external_id,lookup",
        """SELECT *
FROM dim_detail_account
WHERE Customer__c IN (
     '001TL00000r0S5qYAE'
    ,'001TL00000hjywtYAA'
    ,'001TL0000164QzGYAU'
    ,'001TL00000GhMPBYA3'
    ,'001A9000006HpVjlAK'
    ,'001TL00000xyz1wYAA'
    ,'001A9000007KFJGIA4'
    ,'0016F00003n2wYhQAI'
    ,'001TL00000Bp7SXYAZ'
    ,'001TL00000uPEfRYAW'
);""",
    ),

    (
        "Xuất DSO tích + Số lượt tích theo rule_name (ColosBaby)",
        "metric",
        "metric,rule_name,campaign,ColosBaby",
        """SELECT
     CAST(f.Transaction_Date__c AS DATETIME2(0))  AS transaction_date
    ,a.Customer_External_ID__c
    ,f.Rule_Name__c
    ,COUNT(DISTINCT f.Customer__c)                AS active_user
    ,SUM(f.Amount__c)                             AS dso_tich
    ,COUNT(f.Transaction_External_ID__c)          AS luot_tich
FROM fact f
JOIN dim_brand b   ON b.Product_Code = f.Product_Code__c
JOIN dim_account a ON a.Id = f.Customer__c
WHERE f.Transaction_Type__c = 'Product Point'
  AND b.Product_Type  = 'SỮA BỘT'
  AND b.Brand         = 'ColosBaby'
  AND f.Transaction_Date__c BETWEEN '2026-02-01' AND '2026-03-30'
GROUP BY
     f.Rule_Name__c
    ,a.Customer_External_ID__c
    ,f.Transaction_Date__c
ORDER BY f.Transaction_Date__c, a.Customer_External_ID__c;""",
    ),

    (
        "DSO tích + Deep-dive kênh End-users (CaloKid/ME_Y tế)",
        "metric",
        "metric,CaloKid,ME,End-users,channel",
        """WITH ranked_transactions AS (
    SELECT
         f.Customer__c          AS customer_id
        ,f.Amount__c            AS txn_amount
        ,ch.Channel             AS txn_channel
        ,b.Brand                AS brand_name
        ,ROW_NUMBER() OVER (
            PARTITION BY f.Customer__c
            ORDER BY
                CASE WHEN b.Brand = 'CaloKid' AND ch.Channel = 'ME_Y tế' THEN 0 ELSE 1 END ASC,
                f.Transaction_Date__c ASC
        )                       AS rn
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    WHERE f.Transaction_Type__c  = 'Product Point'
      AND b.Product_Type         = 'SỬA BỘT'
      AND dda.Account_SubType    = 'End-users'
      AND f.Transaction_Date__date_only BETWEEN '2026-01-01' AND '2026-04-30'
)
SELECT
     COUNT(DISTINCT CASE WHEN txn_channel = 'ME_Y tế' THEN customer_id END)            AS total_active_user_ME
    ,SUM(CASE WHEN txn_channel = 'ME_Y tế' THEN txn_amount ELSE 0 END)                 AS total_amount_ME
    ,COUNT(DISTINCT CASE WHEN rn = 1 AND txn_channel = 'ME_Y tế' THEN customer_id END) AS l1_me_active_user
    ,SUM(CASE WHEN rn = 1 AND txn_channel = 'ME_Y tế' THEN txn_amount ELSE 0 END)      AS l1_me_amount
    ,COUNT(DISTINCT CASE WHEN rn=1 AND txn_channel='ME_Y tế' AND brand_name='CaloKid' THEN customer_id END) AS l1_calokid_me_user
    ,SUM(CASE WHEN rn=1 AND txn_channel='ME_Y tế' AND brand_name='CaloKid' THEN txn_amount ELSE 0 END)      AS l1_calokid_me_amount
FROM ranked_transactions;""",
    ),

    (
        "Xuất BenchMark theo Layer (CaloKid/ME/End-users/Organic)",
        "metric",
        "metric,benchmark,layer,CaloKid",
        """WITH base_data AS (
    SELECT
         f.Customer__c, f.Transaction_External_ID__c, f.Amount__c
        ,b.Brand, ch.Channel, dda.Account_SubType, dda.Account_Source
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    WHERE f.Transaction_Type__c = 'Product Point'
      AND b.Product_Type        = 'SỬA BỘT'
      AND f.Transaction_Date__c >= '2026-01-01 00:00:00'
      AND f.Transaction_Date__c <= '2026-04-30 23:59:59'
)
SELECT 'Layer 1: CaloKid - All Channels' AS Layer_Name,
       COUNT(DISTINCT Customer__c) AS Active_User,
       COUNT(DISTINCT Transaction_External_ID__c) AS So_Luot_Tich,
       SUM(Amount__c) AS Doanh_So
FROM base_data WHERE Brand = 'CaloKid'
UNION ALL
SELECT 'Layer 2: CaloKid - ME_Y tế',
       COUNT(DISTINCT Customer__c), COUNT(DISTINCT Transaction_External_ID__c), SUM(Amount__c)
FROM base_data WHERE Brand = 'CaloKid' AND Channel = 'ME_Y tế'
UNION ALL
SELECT 'Layer 3: CaloKid - ME_Y tế - End-users',
       COUNT(DISTINCT Customer__c), COUNT(DISTINCT Transaction_External_ID__c), SUM(Amount__c)
FROM base_data WHERE Brand = 'CaloKid' AND Channel = 'ME_Y tế' AND Account_SubType = 'End-users'
UNION ALL
SELECT 'Layer 4: CaloKid - ME_Y tế - End-users - Organic',
       COUNT(DISTINCT Customer__c), COUNT(DISTINCT Transaction_External_ID__c), SUM(Amount__c)
FROM base_data WHERE Brand = 'CaloKid' AND Channel = 'ME_Y tế'
                 AND Account_SubType = 'End-users' AND Account_Source = 'Organic';""",
    ),

    (
        "Xuất full data đối chiếu (End-users, SỬA BỘT, YTD)",
        "ad_hoc",
        "ad_hoc,full-export,End-users",
        """SELECT
     f.Customer__c                        AS customer_id
    ,a.Phone                              AS phone_number
    ,a.Name                               AS customer_name
    ,f.Transaction_Date__c                AS transaction_date
    ,ch.Channel                           AS channel
    ,b.Product_Name                       AS product_name
    ,f.Distributor_Name__c                AS distributor_name
    ,f.Transaction_External_ID__c         AS transaction_external_id
    ,f.Amount__c                          AS amount
FROM fact f
JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
LEFT JOIN dim_account a    ON a.Id            = f.Customer__c
WHERE f.Transaction_Type__c  = 'Product Point'
  AND b.Product_Type         = 'SỬA BỘT'
  AND dda.Account_SubType    = 'End-users'
  AND f.Transaction_Date__date_only BETWEEN '2026-01-01' AND '2026-04-30'
ORDER BY f.Customer__c, f.Amount__c DESC;""",
    ),

    (
        "Check tệp customer không trong list + random sample (NEWID)",
        "filter",
        "filter,random,NEWID,exclusion",
        """WITH customer_list AS (
    SELECT id FROM (VALUES
        ('001TL00000r0S5qYAE'),('001TL00000hjywtYAA'),
        ('001TL0000164QzGYAU'),('001TL00000GhMPBYA3'),
        ('0016F00003n2wYhQAI'),('001A9000007KFJGIA4')
        -- thêm ID vào đây
    ) AS t(id)
),
base AS (
    SELECT
         f.Customer__c          AS customer_id
        ,a.Name                 AS customer_name
        ,f.Transaction_Date__c  AS txn_date
        ,ch.Channel, b.Brand, f.Amount__c
        ,ROW_NUMBER() OVER (PARTITION BY f.Customer__c ORDER BY f.Transaction_Date__c ASC) AS full_seq
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    LEFT JOIN dim_account a    ON a.Id            = f.Customer__c
    WHERE f.Transaction_Type__c = 'Product Point'
      AND b.Product_Type        = 'SỬA BỘT'
      AND dda.Account_SubType   = 'End-users'
      AND f.Transaction_Date__c >= '2026-01-01 00:00:00'
      AND f.Transaction_Date__c <= '2026-04-30 23:59:59'
)
SELECT TOP 50 b.*
FROM base b
LEFT JOIN customer_list cl ON b.customer_id = cl.id
WHERE cl.id IS NULL   -- loại các ID trong danh sách
ORDER BY NEWID();     -- lấy ngẫu nhiên""",
    ),

    (
        "Journey KH 5 lần mua — PIVOT theo kênh (CaloKid)",
        "join",
        "join,CaloKid,ME,journey,pivot",
        """WITH base_data AS (
    SELECT
         f.Customer__c AS customer_id, a.Name AS customer_name
        ,f.Transaction_Date__c AS txn_date, f.Transaction_External_ID__c AS txn_id
        ,f.Distributor_Name__c AS distributor_name, ch.Channel
        ,b.Product_Name AS product_name, b.Brand, f.Amount__c AS amount
        ,dda.Account_SubType, dda.RFM_Segment
        ,ROW_NUMBER() OVER (PARTITION BY f.Customer__c ORDER BY f.Transaction_Date__c ASC) AS full_seq
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    LEFT JOIN dim_account a    ON a.Id            = f.Customer__c
    WHERE f.Transaction_Type__c = 'Product Point'
      AND b.Product_Type = 'SỬA BỘT' AND b.Brand = 'CaloKid'
      AND dda.Account_SubType = 'End-users'
      AND f.Transaction_Date__c >= '2026-01-01 00:00:00'
      AND f.Transaction_Date__c <= '2026-04-30 23:59:59'
),
first_match_marker AS (
    SELECT customer_id, MIN(full_seq) AS first_me_seq
    FROM base_data WHERE brand = 'CaloKid' AND channel = 'ME_Y tế'
    GROUP BY customer_id
),
top_10_calokid AS (
    SELECT TOP 10 customer_id, SUM(amount) AS total_revenue, COUNT(*) AS total_visits
    FROM base_data WHERE brand = 'CaloKid' AND channel = 'ME_Y tế'
    GROUP BY customer_id ORDER BY total_revenue DESC
)
SELECT
     ROW_NUMBER() OVER (ORDER BY t10.total_revenue DESC) AS rank_n
    ,t10.customer_id, bd.customer_name, bd.RFM_Segment
    ,t10.total_visits, t10.total_revenue
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq     THEN bd.txn_date    END) AS GD_lan_01
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq     THEN bd.channel     END) AS Channel_01
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq     THEN bd.amount      END) AS Amount_01
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 1 THEN bd.txn_date    END) AS GD_lan_02
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 1 THEN bd.channel     END) AS Channel_02
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 1 THEN bd.amount      END) AS Amount_02
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 2 THEN bd.txn_date    END) AS GD_lan_03
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 2 THEN bd.channel     END) AS Channel_03
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 2 THEN bd.amount      END) AS Amount_03
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 3 THEN bd.txn_date    END) AS GD_lan_04
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 3 THEN bd.channel     END) AS Channel_04
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 3 THEN bd.amount      END) AS Amount_04
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 4 THEN bd.txn_date    END) AS GD_lan_05
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 4 THEN bd.channel     END) AS Channel_05
    ,MAX(CASE WHEN bd.full_seq = fm.first_me_seq + 4 THEN bd.amount      END) AS Amount_05
FROM top_10_calokid t10
JOIN first_match_marker fm ON t10.customer_id = fm.customer_id
JOIN base_data bd           ON t10.customer_id = bd.customer_id
GROUP BY t10.customer_id, bd.customer_name, bd.RFM_Segment,
         t10.total_revenue, t10.total_visits, fm.first_me_seq
ORDER BY rank_n;""",
    ),

    (
        "CaloKid first-touch cohort với skip logic (ME_Y tế)",
        "join",
        "join,CaloKid,ME,cohort,first-touch",
        """WITH customer_list AS (
    SELECT id FROM (VALUES ('001TL000002JUKdYAO'),('001TL000004awhXYAQ')) AS t(id)
    -- thay bằng danh sách ID thực tế
),
first_calokid_touch AS (
    SELECT f.Customer__c AS customer_id, MIN(f.Transaction_Date__c) AS first_touch_date
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    WHERE f.Transaction_Type__c = 'Product Point'
      AND b.Product_Type = 'SỬA BỘT' AND dda.Account_SubType = 'End-users'
      AND b.Brand = 'CaloKid' AND ch.Channel = 'ME_Y tế'
      AND f.Transaction_Date__c >= '2026-01-01 00:00:00'
      AND f.Transaction_Date__c <= '2026-04-30 23:59:59'
    GROUP BY f.Customer__c
),
base AS (
    SELECT
         f.Customer__c AS customer_id, a.Name AS customer_name
        ,f.Transaction_Date__c AS txn_date, f.Transaction_External_ID__c AS txn_id
        ,f.Distributor_Name__c AS distributor_name, ch.Channel
        ,b.Product_Name AS product_name, b.Brand, f.Amount__c AS amount
        ,dda.Account_Source, dda.Account_SubType, dda.RFM_Segment
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    LEFT JOIN dim_account a    ON a.Id            = f.Customer__c
    WHERE f.Transaction_Type__c = 'Product Point'
      AND b.Product_Type = 'SỬA BỘT' AND dda.Account_SubType = 'End-users'
      AND f.Transaction_Date__c >= '2026-01-01 00:00:00'
      AND f.Transaction_Date__c <= '2026-04-30 23:59:59'
)
SELECT TOP 100
     b.customer_id, b.customer_name, fct.first_touch_date
    ,b.txn_date, b.txn_id, b.distributor_name, b.channel
    ,b.product_name, b.brand, b.amount, b.account_source, b.account_type, b.rfm_segment
FROM base b
JOIN customer_list cl ON cl.id = b.customer_id
INNER JOIN first_calokid_touch fct ON fct.customer_id = b.customer_id
WHERE b.txn_date >= fct.first_touch_date
ORDER BY b.customer_id, b.txn_date ASC;""",
    ),

    (
        "Cohort tệp theo tháng CaloKid/ME (lần 2, lần 3)",
        "join",
        "join,cohort,monthly,CaloKid,retention",
        """WITH cohort_entry AS (
    SELECT
         f.Customer__c AS customer_id
        ,MIN(f.Transaction_Date__c)           AS first_calokid_me_date
        ,FORMAT(MIN(f.Transaction_Date__c), 'yyyy-MM') AS cohort_month
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    WHERE f.Transaction_Type__c = 'Product Point'
      AND b.Product_Type = 'SỬA BỘT' AND dda.Account_SubType = 'End-users'
      AND b.Brand = 'CaloKid' AND ch.Channel = 'ME_Y tế'
      AND f.Transaction_Date__c BETWEEN '2026-01-01' AND '2026-04-30 23:59:59'
    GROUP BY f.Customer__c
),
subsequent_activity AS (
    SELECT
         ce.customer_id, ce.cohort_month, f.Transaction_Date__c
        ,ROW_NUMBER() OVER (PARTITION BY f.Customer__c ORDER BY f.Transaction_Date__c ASC) AS event_seq
    FROM fact f
    JOIN cohort_entry ce ON f.Customer__c = ce.customer_id
    WHERE f.Transaction_Date__c >= ce.first_calokid_me_date
      AND f.Transaction_Date__c <= '2026-04-30 23:59:59'
)
SELECT
     cohort_month                                                      AS [Tháng_Cohort]
    ,COUNT(DISTINCT customer_id)                                       AS [Tổng_Khách_Vào_Nhóm]
    ,COUNT(DISTINCT CASE WHEN event_seq=2 THEN customer_id END)        AS [Số_Khách_Lần_2]
    ,CAST(COUNT(DISTINCT CASE WHEN event_seq=2 THEN customer_id END)*100.0
          / COUNT(DISTINCT customer_id) AS DECIMAL(10,2))             AS [Tỷ_lệ_Lần_2_%]
    ,COUNT(DISTINCT CASE WHEN event_seq=3 THEN customer_id END)        AS [Số_Khách_Lần_3]
    ,CAST(COUNT(DISTINCT CASE WHEN event_seq=3 THEN customer_id END)*100.0
          / COUNT(DISTINCT customer_id) AS DECIMAL(10,2))             AS [Tỷ_lệ_Lần_3_%]
FROM subsequent_activity
GROUP BY cohort_month ORDER BY cohort_month ASC;""",
    ),

    (
        "Retention rate theo Layer CaloKid/ME — conv 1→2, 2→3",
        "metric",
        "metric,retention,conversion,layer,CaloKid",
        """WITH base_data AS (
    SELECT
         f.Customer__c, f.Transaction_External_ID__c, f.Amount__c
        ,b.Brand, ch.Channel, dda.Account_SubType, dda.Account_Source
        ,ROW_NUMBER() OVER (PARTITION BY f.Customer__c ORDER BY f.Transaction_Date__c ASC) AS Txn_Rank
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    WHERE f.Transaction_Type__c = 'Product Point' AND b.Product_Type = 'SỬA BỘT'
      AND f.Transaction_Date__c >= '2026-01-01 00:00:00'
      AND f.Transaction_Date__c <= '2026-04-30 23:59:59'
),
agg_layers AS (
    SELECT 'Layer 1: CaloKid - All Channels'              AS Layer_Name, * FROM base_data WHERE Brand='CaloKid'
    UNION ALL
    SELECT 'Layer 2: CaloKid - ME_Y tế',                 * FROM base_data WHERE Brand='CaloKid' AND Channel='ME_Y tế'
    UNION ALL
    SELECT 'Layer 3: CaloKid - GT_Truyền thống',         * FROM base_data WHERE Brand='CaloKid' AND Channel='GT_Truyền thống'
    UNION ALL
    SELECT 'Layer 4: CaloKid - ME_Y tế - End-users',     * FROM base_data WHERE Brand='CaloKid' AND Channel='ME_Y tế' AND Account_SubType='End-users'
    UNION ALL
    SELECT 'Layer 5: CaloKid - ME_Y tế - End-users - Organic', * FROM base_data WHERE Brand='CaloKid' AND Channel='ME_Y tế' AND Account_SubType='End-users' AND Account_Source='Organic'
),
final_counts AS (
    SELECT Layer_Name,
           COUNT(DISTINCT Customer__c)                   AS Active_User,
           COUNT(DISTINCT Transaction_External_ID__c)    AS So_Luot_Tich,
           SUM(Amount__c)                                AS Doanh_So,
           COUNT(CASE WHEN Txn_Rank=1 THEN 1 END)        AS Tich_Lan_1,
           COUNT(CASE WHEN Txn_Rank=2 THEN 1 END)        AS Tich_Lan_2,
           COUNT(CASE WHEN Txn_Rank=3 THEN 1 END)        AS Tich_Lan_3
    FROM agg_layers GROUP BY Layer_Name
)
SELECT *,
       FORMAT(CAST(Tich_Lan_2 AS FLOAT)/NULLIF(Tich_Lan_1,0),'P2') AS Conv_Rate_1_to_2,
       FORMAT(CAST(Tich_Lan_3 AS FLOAT)/NULLIF(Tich_Lan_2,0),'P2') AS Conv_Rate_2_to_3
FROM final_counts;""",
    ),

    (
        "Cohort retention L1→L3 theo tháng (CaloKid/ME strict first-touch)",
        "join",
        "join,cohort,retention,CaloKid,ME,strict",
        """WITH base_data AS (
    SELECT
         f.Customer__c AS customer_id
        ,FORMAT(f.Transaction_Date__c,'yyyy-MM') AS cohort_month
        ,ch.Channel, b.Brand, dda.Account_SubType
        ,ROW_NUMBER() OVER (PARTITION BY f.Customer__c ORDER BY f.Transaction_Date__c ASC) AS full_seq
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    LEFT JOIN dim_account a    ON a.Id            = f.Customer__c
    WHERE f.Transaction_Type__c = 'Product Point' AND b.Product_Type = 'SỬA BỘT'
      AND dda.Account_SubType   = 'End-users'
      AND f.Transaction_Date__c BETWEEN '2026-01-01' AND '2026-04-30 23:59:59'
),
cohort_logic AS (
    SELECT customer_id, cohort_month,
           MAX(CASE WHEN full_seq=2 THEN 1 ELSE 0 END) AS has_step_2,
           MAX(CASE WHEN full_seq=3 THEN 1 ELSE 0 END) AS has_step_3
    FROM base_data
    GROUP BY customer_id, cohort_month
    HAVING MAX(CASE WHEN full_seq=1 THEN channel END) = 'ME_Y tế'
       AND MAX(CASE WHEN full_seq=1 THEN brand   END) = 'CaloKid'
)
SELECT
     cohort_month              AS [Tháng_Cohort]
    ,COUNT(customer_id)        AS [Tổng_Khách_Lần_1]
    ,SUM(has_step_2)           AS [Số_Khách_Lần_2]
    ,CAST(SUM(has_step_2)*100.0/COUNT(customer_id) AS DECIMAL(10,2)) AS [Tỷ_lệ_Lần_2_%]
    ,SUM(has_step_3)           AS [Số_Khách_Lần_3]
    ,CAST(SUM(has_step_3)*100.0/COUNT(customer_id) AS DECIMAL(10,2)) AS [Tỷ_lệ_Lần_3_%]
FROM cohort_logic
GROUP BY cohort_month ORDER BY cohort_month ASC;""",
    ),

    (
        "Sequential Cohort Drop-off Matrix YTD 2026 (L1→L5)",
        "join",
        "join,cohort,dropoff,L1-L5,CaloKid",
        """WITH base_data AS (
    SELECT
         f.Customer__c AS customer_id
        ,FORMAT(f.Transaction_Date__c,'yyyy-MM') AS cohort_month
        ,ch.Channel, b.Brand
        ,ROW_NUMBER() OVER (PARTITION BY f.Customer__c ORDER BY f.Transaction_Date__c ASC) AS full_seq
    FROM fact f
    JOIN dim_brand b          ON b.Product_Code  = f.Product_Code__c
    JOIN dim_detail_account dda ON dda.Customer__c = f.Customer__c
    JOIN dim_channel ch        ON ch.Customer     = f.Distributor_Code__c
    WHERE f.Transaction_Type__c = 'Product Point' AND b.Product_Type = 'SỬA BỘT'
      AND dda.Account_SubType   = 'End-users'
      AND f.Transaction_Date__c >= '2026-01-01'
      AND f.Transaction_Date__c <= GETDATE()
),
cohort_logic AS (
    SELECT customer_id, cohort_month,
           MAX(CASE WHEN full_seq=1 THEN 1 ELSE 0 END) AS has_L1,
           MAX(CASE WHEN full_seq=2 THEN 1 ELSE 0 END) AS has_L2,
           MAX(CASE WHEN full_seq=3 THEN 1 ELSE 0 END) AS has_L3,
           MAX(CASE WHEN full_seq=4 THEN 1 ELSE 0 END) AS has_L4,
           MAX(CASE WHEN full_seq=5 THEN 1 ELSE 0 END) AS has_L5
    FROM base_data
    GROUP BY customer_id, cohort_month
    HAVING MAX(CASE WHEN full_seq=1 THEN channel END) = 'ME_Y tế'
       AND MAX(CASE WHEN full_seq=1 THEN brand   END) = 'CaloKid'
),
summary_abs AS (
    SELECT cohort_month,
           SUM(has_L1) AS L1_Abs, SUM(has_L2) AS L2_Abs,
           SUM(has_L3) AS L3_Abs, SUM(has_L4) AS L4_Abs, SUM(has_L5) AS L5_Abs
    FROM cohort_logic GROUP BY cohort_month
)
SELECT cohort_month, L1_Abs, L2_Abs,
       CAST(L2_Abs*100.0/NULLIF(L1_Abs,0) AS DECIMAL(10,2)) AS [% L2/L1],
       L3_Abs,
       CAST(L3_Abs*100.0/NULLIF(L2_Abs,0) AS DECIMAL(10,2)) AS [% L3/L2],
       L4_Abs,
       CAST(L4_Abs*100.0/NULLIF(L3_Abs,0) AS DECIMAL(10,2)) AS [% L4/L3],
       L5_Abs,
       CAST(L5_Abs*100.0/NULLIF(L4_Abs,0) AS DECIMAL(10,2)) AS [% L5/L4]
FROM summary_abs ORDER BY cohort_month ASC;""",
    ),

    # ═══════════════════════════════════════════════════════════
    # SOURCE 2 — snippets.json (Python + SQL + Shell templates)
    # ═══════════════════════════════════════════════════════════

    (
        "Python: SARIMAX forecast (seasonal time-series)",
        "template",
        "python,forecast,time-series,statsmodels,seasonal",
        """from statsmodels.tsa.statespace.sarimax import SARIMAX

model = SARIMAX(
    endog=df['value'],
    order=(1, 1, 1),
    seasonal_order=(1, 1, 1, 12),
    enforce_stationarity=False,
)
results = model.fit(disp=False)
pred = results.forecast(steps=12)
print(pred)""",
    ),

    (
        "Python: Auto-ARIMA (pmdarima, auto select p/d/q)",
        "template",
        "python,forecast,arima,auto,pmdarima",
        """from pmdarima import auto_arima

model = auto_arima(
    df['value'],
    seasonal=True, m=12,
    stepwise=True, trace=True,
)
print(model.summary())
pred = model.predict(n_periods=6)""",
    ),

    (
        "Python: Pandas groupby pivot (1-chain)",
        "template",
        "python,pandas,groupby,pivot,unstack",
        """pivot = (
    df
    .groupby(['date', 'category'])['value']
    .sum()
    .unstack(fill_value=0)
    .reset_index()
)
pivot.columns.name = None
print(pivot.head())""",
    ),

    (
        "Python: Polars lazy scan parquet (filter + groupby)",
        "template",
        "python,polars,parquet,lazy,scan",
        """import polars as pl

df = (
    pl.scan_parquet('data/*.parquet')
    .filter(pl.col('date') >= '2025-01-01')
    .group_by('category')
    .agg(pl.col('value').sum().alias('total'))
    .sort('total', descending=True)
    .collect()
)
print(df)""",
    ),

    (
        "Python: Sklearn pipeline + cross-val (GBM + StandardScaler)",
        "template",
        "python,sklearn,ml,pipeline,cross-val,gbm",
        """from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score

pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('model',  GradientBoostingClassifier(n_estimators=200)),
])
scores = cross_val_score(pipe, X, y, cv=5, scoring='roc_auc')
print(f'AUC: {scores.mean():.4f} ± {scores.std():.4f}')""",
    ),

    (
        "Python: Plotly line chart (dark theme)",
        "template",
        "python,plotly,viz,chart,dark-theme",
        """import plotly.express as px

fig = px.line(
    df, x='date', y='value', color='category',
    title='Trend over time',
    template='plotly_dark',
)
fig.update_layout(legend_title_text='Category')
fig.show()""",
    ),

    (
        "SQL: Window — running total (cumulative sum per category)",
        "template",
        "sql,window,running-total,cumsum,partition",
        """SELECT
     date
    ,category
    ,value
    ,SUM(value) OVER (
        PARTITION BY category
        ORDER BY date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
     ) AS running_total
FROM fact_table
ORDER BY category, date;""",
    ),

    (
        "SQL: CTE recursive hierarchy (org tree / parent-child)",
        "template",
        "sql,cte,recursive,hierarchy,tree",
        """WITH RECURSIVE hier AS (
    SELECT id, name, parent_id, 0 AS level
    FROM org_table
    WHERE parent_id IS NULL

    UNION ALL

    SELECT c.id, c.name, c.parent_id, h.level + 1
    FROM org_table c
    JOIN hier h ON c.parent_id = h.id
)
SELECT * FROM hier ORDER BY level, name;""",
    ),

    (
        "SQL: Dynamic pivot (CASE WHEN — manual pivot pattern)",
        "template",
        "sql,pivot,case-when,dynamic,crosstab",
        """SELECT
     date
    ,SUM(CASE WHEN category = 'A' THEN value ELSE 0 END) AS cat_a
    ,SUM(CASE WHEN category = 'B' THEN value ELSE 0 END) AS cat_b
    ,SUM(CASE WHEN category = 'C' THEN value ELSE 0 END) AS cat_c
FROM fact_table
GROUP BY date
ORDER BY date;""",
    ),

    (
        "SQL: LAG/LEAD — month-over-month growth %",
        "template",
        "sql,window,lag,lead,mom,growth",
        """SELECT
     month
    ,revenue
    ,LAG(revenue, 1) OVER (ORDER BY month)              AS prev_month
    ,ROUND(
        100.0 * (revenue - LAG(revenue,1) OVER (ORDER BY month))
        / NULLIF(LAG(revenue,1) OVER (ORDER BY month), 0), 2
     )                                                   AS mom_pct
FROM monthly_revenue
ORDER BY month;""",
    ),

    (
        "Shell: Kill process on port (Windows + Linux)",
        "other",
        "shell,windows,linux,port,kill,process",
        """# Windows PowerShell
netstat -ano | findstr :<PORT>
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:<PORT> | xargs kill -9""",
    ),

    (
        "Shell: Git undo last commit (keep files staged)",
        "other",
        "shell,git,undo,reset,soft",
        """git reset --soft HEAD~1
# Undo commit nhưng giữ nguyên thay đổi đã staged""",
    ),

    # ═══════════════════════════════════════════════════════════
    # SOURCE 3 — 05_Snipets/ad_hoc/ (37 files)
    # ═══════════════════════════════════════════════════════════

    # ── 01_marketing ────────────────────────────────────────────

    (
        "mkt: Campaign DSO + Luot theo rule_name (YTD)",
        "metric",
        "marketing,rule_name,campaign,DSO,luot",
        """SELECT
     rule_name
    ,COUNT(DISTINCT customer_id)          AS active_user
    ,COUNT(DISTINCT txn_id)               AS so_luot_tich
    ,SUM(amount)                          AS dso_tich
    ,MIN(txn_date)                        AS first_date
    ,MAX(txn_date)                        AS last_date
FROM   dbo.vw_fact_txn_enriched
WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
  AND  rule_name IS NOT NULL
GROUP BY rule_name
ORDER BY dso_tich DESC;""",
    ),

    (
        "mkt: New vs Repeat customer split (brand/channel)",
        "metric",
        "marketing,new-vs-repeat,brand,channel,is_repeat",
        """SELECT
     brand
    ,channel
    ,is_repeat_buyer
    ,COUNT(DISTINCT customer_id)          AS customers
    ,COUNT(DISTINCT txn_id)               AS so_luot_tich
    ,SUM(amount)                          AS dso_tich
    ,CAST(SUM(amount)*1.0
          / NULLIF(COUNT(DISTINCT txn_id),0) AS DECIMAL(18,2))  AS aov
FROM   dbo.vw_fact_txn_enriched
WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
GROUP BY brand, channel, is_repeat_buyer
ORDER BY brand, channel, is_repeat_buyer;""",
    ),

    (
        "mkt: Sub-brand comparison — DSO + Active User + AOV",
        "metric",
        "marketing,sub_brand,comparison,DSO,AOV",
        """SELECT
     brand
    ,sub_brand
    ,COUNT(DISTINCT customer_id)          AS active_user
    ,COUNT(DISTINCT txn_id)               AS so_luot_tich
    ,SUM(amount)                          AS dso_tich
    ,CAST(SUM(amount)*1.0
          / NULLIF(COUNT(DISTINCT txn_id),0) AS DECIMAL(18,2))  AS aov
    ,CAST(SUM(amount)*100.0
          / NULLIF(SUM(SUM(amount)) OVER (PARTITION BY brand),0)
          AS DECIMAL(10,2))               AS pct_share_in_brand
FROM   dbo.vw_fact_txn_enriched
WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
  AND  sub_brand IS NOT NULL
GROUP BY brand, sub_brand
ORDER BY brand, dso_tich DESC;""",
    ),

    (
        "mkt: Funnel L1→L5 — cohort waterfall (has_L1 … has_L5)",
        "metric",
        "marketing,funnel,cohort,L1-L5,waterfall,vw_mart_cohort",
        """SELECT
     first_brand
    ,first_channel
    ,first_region
    ,COUNT(DISTINCT customer_id)                        AS cohort_size
    ,SUM(has_L1)                                        AS reached_L1
    ,SUM(has_L2)                                        AS reached_L2
    ,SUM(has_L3)                                        AS reached_L3
    ,SUM(has_L4)                                        AS reached_L4
    ,SUM(has_L5)                                        AS reached_L5
    ,CAST(SUM(has_L2)*100.0/NULLIF(SUM(has_L1),0) AS DECIMAL(10,2)) AS conv_L1_L2
    ,CAST(SUM(has_L3)*100.0/NULLIF(SUM(has_L2),0) AS DECIMAL(10,2)) AS conv_L2_L3
    ,CAST(SUM(has_L4)*100.0/NULLIF(SUM(has_L3),0) AS DECIMAL(10,2)) AS conv_L3_L4
    ,CAST(SUM(has_L5)*100.0/NULLIF(SUM(has_L4),0) AS DECIMAL(10,2)) AS conv_L4_L5
FROM   dbo.vw_mart_cohort
WHERE  (first_brand   = '<<BRAND_OPT>>'   OR '<<BRAND_OPT>>'   = '')
  AND  (first_channel = '<<CHANNEL_OPT>>' OR '<<CHANNEL_OPT>>' = '')
GROUP BY first_brand, first_channel, first_region
ORDER BY cohort_size DESC;""",
    ),

    (
        "mkt: Brand MoM trend with LAG (DSO + luot)",
        "metric",
        "marketing,mom,trend,lag,brand,monthly",
        """WITH monthly AS (
    SELECT
         brand
        ,FORMAT(txn_date,'yyyy-MM')            AS month_year
        ,COUNT(DISTINCT customer_id)            AS active_user
        ,COUNT(DISTINCT txn_id)                 AS so_luot_tich
        ,SUM(amount)                            AS dso_tich
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
    GROUP BY brand, FORMAT(txn_date,'yyyy-MM')
)
SELECT
     brand, month_year, active_user, so_luot_tich, dso_tich
    ,LAG(dso_tich) OVER (PARTITION BY brand ORDER BY month_year) AS prev_month_dso
    ,CAST((dso_tich - LAG(dso_tich) OVER (PARTITION BY brand ORDER BY month_year))
         * 100.0
         / NULLIF(LAG(dso_tich) OVER (PARTITION BY brand ORDER BY month_year), 0)
         AS DECIMAL(10,2))                       AS pct_mom_dso
FROM   monthly
ORDER BY brand, month_year;""",
    ),

    (
        "mkt: First-touch vs Last-touch attribution (brand/channel)",
        "join",
        "marketing,attribution,first-touch,last-touch,brand,channel",
        """WITH first_touch AS (
    SELECT customer_id, first_brand AS brand, first_channel AS channel, 'first' AS touch_type
    FROM   dbo.vw_dim_customer_360
),
last_touch AS (
    SELECT customer_id, top_brand AS brand, top_channel AS channel, 'last' AS touch_type
    FROM   dbo.vw_dim_customer_360
)
SELECT
     touch_type
    ,brand, channel
    ,COUNT(DISTINCT customer_id)               AS customers
    ,CAST(COUNT(DISTINCT customer_id)*100.0
          / SUM(COUNT(DISTINCT customer_id)) OVER (PARTITION BY touch_type)
          AS DECIMAL(10,2))                    AS pct_of_touch_type
FROM (SELECT * FROM first_touch UNION ALL SELECT * FROM last_touch) combined
GROUP BY touch_type, brand, channel
ORDER BY touch_type, customers DESC;""",
    ),

    (
        "mkt: Repeat rate per brand (% khách mua lại)",
        "metric",
        "marketing,repeat-rate,brand,retention",
        """SELECT
     brand
    ,COUNT(DISTINCT customer_id)                                    AS total_customers
    ,COUNT(DISTINCT CASE WHEN is_repeat_buyer=1 THEN customer_id END) AS repeat_customers
    ,CAST(COUNT(DISTINCT CASE WHEN is_repeat_buyer=1 THEN customer_id END)*100.0
          / NULLIF(COUNT(DISTINCT customer_id),0) AS DECIMAL(10,2))  AS repeat_rate_pct
    ,SUM(CASE WHEN is_repeat_buyer=0 THEN amount ELSE 0 END)        AS dso_new_buyers
    ,SUM(CASE WHEN is_repeat_buyer=1 THEN amount ELSE 0 END)        AS dso_repeat_buyers
FROM   dbo.vw_fact_txn_enriched
WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
GROUP BY brand
ORDER BY repeat_rate_pct DESC;""",
    ),

    (
        "mkt: Cross-brand basket overlap (customer đã mua brand A cũng mua brand B)",
        "join",
        "marketing,cross-brand,basket,overlap,self-join",
        """WITH brand_customers AS (
    SELECT DISTINCT customer_id, brand
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
)
SELECT
     a.brand                                          AS brand_a
    ,b.brand                                          AS brand_b
    ,COUNT(DISTINCT a.customer_id)                    AS overlap_customers
    ,CAST(COUNT(DISTINCT a.customer_id)*100.0
          / NULLIF((SELECT COUNT(DISTINCT customer_id) FROM brand_customers WHERE brand=a.brand),0)
          AS DECIMAL(10,2))                           AS pct_of_brand_a_base
FROM   brand_customers a
JOIN   brand_customers b
    ON a.customer_id = b.customer_id
   AND a.brand       < b.brand    -- avoid self-join & duplicates
GROUP BY a.brand, b.brand
ORDER BY overlap_customers DESC;""",
    ),

    (
        "mkt: Top SKU per brand (RANK by DSO within brand)",
        "metric",
        "marketing,sku,ranking,product,brand,RANK",
        """WITH sku_agg AS (
    SELECT
         brand
        ,product_code
        ,product_name
        ,sub_brand
        ,COUNT(DISTINCT customer_id)           AS active_user
        ,COUNT(DISTINCT txn_id)                AS so_luot_tich
        ,SUM(amount)                           AS dso_tich
        ,RANK() OVER (PARTITION BY brand ORDER BY SUM(amount) DESC) AS rank_in_brand
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
    GROUP BY brand, product_code, product_name, sub_brand
)
SELECT *
FROM   sku_agg
WHERE  rank_in_brand <= <<TOP_N>>            -- vd: 5
ORDER BY brand, rank_in_brand;""",
    ),

    (
        "mkt: Sub-brand × Channel matrix (% share)",
        "metric",
        "marketing,matrix,sub_brand,channel,share,window",
        """WITH agg AS (
    SELECT
         sub_brand, channel
        ,COUNT(DISTINCT customer_id)          AS active_user
        ,COUNT(DISTINCT txn_id)               AS so_luot_tich
        ,SUM(amount)                          AS dso_tich
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
      AND  brand = '<<BRAND>>'
      AND  sub_brand IS NOT NULL
    GROUP BY sub_brand, channel
)
SELECT
     sub_brand, channel, active_user, so_luot_tich, dso_tich
    ,CAST(dso_tich*100.0 / NULLIF(SUM(dso_tich) OVER (PARTITION BY sub_brand),0) AS DECIMAL(10,2)) AS pct_share_within_sub_brand
    ,CAST(dso_tich*100.0 / NULLIF(SUM(dso_tich) OVER (PARTITION BY channel),0)   AS DECIMAL(10,2)) AS pct_share_within_channel
FROM   agg
ORDER BY sub_brand, dso_tich DESC;""",
    ),

    (
        "mkt: Sub-brand × Region matrix (% share)",
        "metric",
        "marketing,matrix,sub_brand,region,share",
        """WITH agg AS (
    SELECT
         sub_brand, region
        ,COUNT(DISTINCT customer_id)          AS active_user
        ,COUNT(DISTINCT txn_id)               AS so_luot_tich
        ,SUM(amount)                          AS dso_tich
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
      AND  brand = '<<BRAND>>'
      AND  sub_brand IS NOT NULL AND region IS NOT NULL
    GROUP BY sub_brand, region
)
SELECT
     sub_brand, region, active_user, so_luot_tich, dso_tich
    ,CAST(dso_tich*100.0 / NULLIF(SUM(dso_tich) OVER (PARTITION BY sub_brand),0) AS DECIMAL(10,2)) AS pct_share_within_sub_brand
    ,CAST(dso_tich*100.0 / NULLIF(SUM(dso_tich) OVER (PARTITION BY region),0)    AS DECIMAL(10,2)) AS pct_share_within_region
FROM   agg
ORDER BY sub_brand, dso_tich DESC;""",
    ),

    (
        "mkt: Drop-off customer list (L→L+1 không convert, phục vụ retargeting)",
        "filter",
        "marketing,dropoff,retargeting,cohort,vw_mart_cohort,vw_dim_customer_360",
        """-- Input: <<STAGE_REACHED>>=1, <<STAGE_MISSED>>=2 → khách có L1 nhưng không L2
WITH stage_check AS (
    SELECT
         customer_id, cohort_month, first_brand, first_channel, first_region
        ,CASE <<STAGE_REACHED>>
            WHEN 1 THEN has_L1 WHEN 2 THEN has_L2 WHEN 3 THEN has_L3
            WHEN 4 THEN has_L4 WHEN 5 THEN has_L5
         END                                              AS reached
        ,CASE <<STAGE_MISSED>>
            WHEN 1 THEN has_L1 WHEN 2 THEN has_L2 WHEN 3 THEN has_L3
            WHEN 4 THEN has_L4 WHEN 5 THEN has_L5
         END                                              AS missed
    FROM   dbo.vw_mart_cohort
    WHERE  (first_brand   = '<<FIRST_BRAND>>'   OR '<<FIRST_BRAND>>'   = '')
      AND  (first_channel = '<<FIRST_CHANNEL>>' OR '<<FIRST_CHANNEL>>' = '')
)
SELECT
     sc.customer_id, c.customer_name, c.phone, c.tier, c.region
    ,sc.cohort_month, sc.first_brand, sc.first_channel
    ,c.first_txn_date, c.last_txn_date
    ,DATEDIFF(DAY, c.last_txn_date, GETDATE()) AS days_since_last
    ,c.so_luot_tich, c.dso_tich, c.top_brand, c.top_channel
FROM       stage_check sc
LEFT JOIN  dbo.vw_dim_customer_360 c ON c.customer_id = sc.customer_id
WHERE  sc.reached = 1 AND sc.missed = 0
ORDER BY c.dso_tich DESC;""",
    ),

    (
        "mkt: Awareness / Trial / Loyal funnel classification",
        "metric",
        "marketing,funnel,awareness,trial,loyal,max_txn_seq",
        """WITH classified AS (
    SELECT
         customer_id, top_brand, top_channel, dso_tich, max_txn_seq
        ,CASE
            WHEN max_txn_seq = 1             THEN '1_Awareness'
            WHEN max_txn_seq BETWEEN 2 AND 3 THEN '2_Trial'
            WHEN max_txn_seq >= 4            THEN '3_Loyal'
         END                                AS funnel_stage
    FROM   dbo.vw_dim_customer_360
    WHERE  (top_brand   = '<<BRAND_OPT>>'   OR '<<BRAND_OPT>>'   = '')
      AND  (top_channel = '<<CHANNEL_OPT>>' OR '<<CHANNEL_OPT>>' = '')
)
SELECT
     funnel_stage
    ,COUNT(*)                                                           AS customers
    ,CAST(COUNT(*)*100.0 / SUM(COUNT(*)) OVER () AS DECIMAL(10,2))     AS pct_distribution
    ,SUM(dso_tich)                                                      AS dso_total
    ,CAST(AVG(dso_tich) AS DECIMAL(18,2))                               AS dso_avg_per_cust
FROM   classified
GROUP BY funnel_stage
ORDER BY funnel_stage;""",
    ),

    # ── 02_sales ────────────────────────────────────────────────

    (
        "sales: Top N distributor — DSO + Luot + AOV + avg/day",
        "metric",
        "sales,distributor,ranking,DSO,AOV,avg-per-day",
        """SELECT TOP <<TOP_N>>
     distributor_code, distributor_name
    ,COUNT(DISTINCT customer_id)                            AS active_user
    ,COUNT(DISTINCT txn_id)                                 AS so_luot_tich
    ,SUM(amount)                                            AS dso_tich
    ,CAST(COUNT(DISTINCT txn_id)*1.0
          / NULLIF(DATEDIFF(DAY,'<<START_DATE>>','<<END_DATE>>')+1,0)
          AS DECIMAL(10,2))                                 AS avg_luot_per_day
    ,CAST(SUM(amount)*1.0 / NULLIF(COUNT(DISTINCT txn_id),0) AS DECIMAL(18,2)) AS aov
    ,COUNT(DISTINCT store_id)                               AS unique_stores
FROM   dbo.vw_fact_txn_enriched
WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
  AND  (brand = '<<BRAND_OPT>>' OR '<<BRAND_OPT>>' = '')
GROUP BY distributor_code, distributor_name
ORDER BY dso_tich DESC;""",
    ),

    (
        "sales: Region performance — DSO + Active User + % share (by brand)",
        "metric",
        "sales,region,brand,share,performance",
        """WITH agg AS (
    SELECT
         region, brand
        ,COUNT(DISTINCT customer_id)             AS active_user
        ,COUNT(DISTINCT txn_id)                  AS so_luot_tich
        ,SUM(amount)                             AS dso_tich
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
      AND  region IS NOT NULL
    GROUP BY region, brand
)
SELECT
     region, brand, active_user, so_luot_tich, dso_tich
    ,CAST(dso_tich*100.0 / NULLIF(SUM(dso_tich) OVER (PARTITION BY region),0) AS DECIMAL(10,2)) AS pct_share_within_region
FROM   agg
ORDER BY region, dso_tich DESC;""",
    ),

    (
        "sales: Province performance — Top N tỉnh + top brand per province",
        "metric",
        "sales,province,region,ranking,top-brand",
        """WITH agg AS (
    SELECT
         province
        ,MAX(region)                             AS region
        ,COUNT(DISTINCT customer_id)             AS active_user
        ,COUNT(DISTINCT txn_id)                  AS so_luot_tich
        ,SUM(amount)                             AS dso_tich
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
      AND  province IS NOT NULL
      AND  (brand = '<<BRAND_OPT>>' OR '<<BRAND_OPT>>' = '')
    GROUP BY province
),
top_brand_prov AS (
    SELECT province, brand AS top_brand
          ,ROW_NUMBER() OVER (PARTITION BY province ORDER BY SUM(amount) DESC) AS rn
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>' AND province IS NOT NULL
    GROUP BY province, brand
)
SELECT TOP <<TOP_N>> a.province, a.region, a.active_user, a.so_luot_tich, a.dso_tich, tb.top_brand
FROM agg a LEFT JOIN top_brand_prov tb ON tb.province=a.province AND tb.rn=1
ORDER BY a.dso_tich DESC;""",
    ),

    (
        "sales: Top N store per distributor (RANK within distributor)",
        "metric",
        "sales,store,distributor,ranking,ROW_NUMBER",
        """WITH store_agg AS (
    SELECT
         distributor_code, distributor_name, store_id, store_name
        ,COUNT(DISTINCT customer_id)             AS active_user
        ,COUNT(DISTINCT txn_id)                  AS so_luot_tich
        ,SUM(amount)                             AS dso_tich
        ,ROW_NUMBER() OVER (PARTITION BY distributor_code ORDER BY SUM(amount) DESC) AS rank_in_dist
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
      AND  distributor_name LIKE N'%<<DISTRIBUTOR_LIKE>>%'
      AND  store_id IS NOT NULL
    GROUP BY distributor_code, distributor_name, store_id, store_name
)
SELECT *
FROM   store_agg
WHERE  rank_in_dist <= <<TOP_N_STORE_PER_DIST>>
ORDER BY distributor_name, rank_in_dist;""",
    ),

    (
        "sales: Sales rep ranking (query trực tiếp fact — view chưa có column)",
        "ad_hoc",
        "sales,rep,ranking,raw-fact",
        """-- ⚠️ Query trực tiếp fact vì view chưa expose sales_rep column
-- Thay <<SALES_REP_COLUMN>> bằng tên thật: Sales_Rep__c, SalesRep__c ...
SELECT TOP <<TOP_N>>
     f.<<SALES_REP_COLUMN>>                               AS sales_rep
    ,COUNT(DISTINCT f.Customer__c)                        AS active_user
    ,COUNT(DISTINCT f.Transaction_External_ID__c)         AS so_luot_tich
    ,SUM(f.Amount__c)                                     AS dso_tich
    ,COUNT(DISTINCT f.Distributor_Code__c)                AS unique_distributors
    ,COUNT(DISTINCT f.Store_ID__c)                        AS unique_stores
FROM      fact f
JOIN      dim_brand b ON b.Product_Code = f.Product_Code__c
WHERE  f.Transaction_Type__c  = 'Product Point'
  AND  b.Product_Type         = 'SỬA BỘT'
  AND  f.Amount__c            > 0
  AND  f.Transaction_Date__c BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
  AND  f.<<SALES_REP_COLUMN>> IS NOT NULL
GROUP BY f.<<SALES_REP_COLUMN>>
ORDER BY dso_tich DESC;""",
    ),

    (
        "sales: Province filter — IN / NOT IN list (flexible mode)",
        "filter",
        "sales,province,filter,IN,NOT-IN",
        """-- Set <<MODE>> = IN hoặc NOT IN
WITH agg AS (
    SELECT
         province, MAX(region) AS region
        ,COUNT(DISTINCT customer_id)             AS active_user
        ,COUNT(DISTINCT txn_id)                  AS so_luot_tich
        ,SUM(amount)                             AS dso_tich
    FROM   dbo.vw_fact_txn_enriched
    WHERE  province <<MODE>> (<<PROVINCE_LIST>>)   -- vd: IN (N'HCM', N'Hà Nội')
      AND  province IS NOT NULL
    GROUP BY province
),
top_brand_prov AS (
    SELECT province, brand
          ,ROW_NUMBER() OVER (PARTITION BY province ORDER BY SUM(amount) DESC) AS rn
    FROM   dbo.vw_fact_txn_enriched
    WHERE  province <<MODE>> (<<PROVINCE_LIST>>) AND province IS NOT NULL
    GROUP BY province, brand
),
top_channel_prov AS (
    SELECT province, channel
          ,ROW_NUMBER() OVER (PARTITION BY province ORDER BY SUM(amount) DESC) AS rn
    FROM   dbo.vw_fact_txn_enriched
    WHERE  province <<MODE>> (<<PROVINCE_LIST>>) AND province IS NOT NULL
    GROUP BY province, channel
)
SELECT a.province, a.region, a.active_user, a.so_luot_tich, a.dso_tich,
       tb.brand AS top_brand, tc.channel AS top_channel
FROM agg a
LEFT JOIN top_brand_prov tb   ON tb.province=a.province AND tb.rn=1
LEFT JOIN top_channel_prov tc ON tc.province=a.province AND tc.rn=1
ORDER BY a.dso_tich DESC;""",
    ),

    (
        "sales: Distributor MoM growth — GROWING / DROPPING / NEW / CHURNED",
        "metric",
        "sales,distributor,mom,growth,classification",
        """WITH monthly AS (
    SELECT
         distributor_code, distributor_name
        ,FORMAT(txn_date,'yyyy-MM')              AS month_year
        ,SUM(amount)                             AS dso
        ,COUNT(DISTINCT txn_id)                  AS luot
    FROM   dbo.vw_fact_txn_enriched
    WHERE  FORMAT(txn_date,'yyyy-MM') IN ('<<CURRENT_MONTH>>','<<PREVIOUS_MONTH>>')
    GROUP BY distributor_code, distributor_name, FORMAT(txn_date,'yyyy-MM')
)
SELECT
     distributor_code, distributor_name
    ,SUM(CASE WHEN month_year='<<CURRENT_MONTH>>'  THEN dso ELSE 0 END) AS curr_dso
    ,SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso ELSE 0 END) AS prev_dso
    ,SUM(CASE WHEN month_year='<<CURRENT_MONTH>>'  THEN dso ELSE 0 END)
        - SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso ELSE 0 END)   AS delta_dso
    ,CAST((SUM(CASE WHEN month_year='<<CURRENT_MONTH>>'  THEN dso ELSE 0 END)
          -SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso ELSE 0 END))*100.0
        / NULLIF(SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso ELSE 0 END),0)
        AS DECIMAL(10,2))                                                       AS pct_mom
    ,CASE
        WHEN SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso ELSE 0 END)=0
         AND SUM(CASE WHEN month_year='<<CURRENT_MONTH>>'  THEN dso ELSE 0 END)>0 THEN 'NEW'
        WHEN SUM(CASE WHEN month_year='<<CURRENT_MONTH>>'  THEN dso ELSE 0 END)=0
         AND SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso ELSE 0 END)>0 THEN 'CHURNED'
        WHEN SUM(CASE WHEN month_year='<<CURRENT_MONTH>>' THEN dso ELSE 0 END)
             > SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso ELSE 0 END)*1.10 THEN 'GROWING (>10%)'
        WHEN SUM(CASE WHEN month_year='<<CURRENT_MONTH>>' THEN dso ELSE 0 END)
             < SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso ELSE 0 END)*0.90 THEN 'DROPPING (<-10%)'
        ELSE 'STABLE'
     END                                                                        AS growth_class
FROM   monthly
GROUP BY distributor_code, distributor_name
HAVING SUM(CASE WHEN month_year='<<CURRENT_MONTH>>'  THEN dso ELSE 0 END)>0
    OR SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso ELSE 0 END)>0
ORDER BY ABS(delta_dso) DESC;""",
    ),

    (
        "sales: Distributor × Brand matrix (% share trong distributor)",
        "metric",
        "sales,distributor,brand,matrix,share",
        """WITH top_dists AS (
    SELECT TOP <<TOP_N_DIST>> distributor_code, distributor_name
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
    GROUP BY distributor_code, distributor_name
    ORDER BY SUM(amount) DESC
),
matrix AS (
    SELECT
         f.distributor_code, f.distributor_name, f.brand
        ,COUNT(DISTINCT f.customer_id)         AS active_user
        ,COUNT(DISTINCT f.txn_id)              AS so_luot_tich
        ,SUM(f.amount)                         AS dso_tich
    FROM   dbo.vw_fact_txn_enriched f
    INNER JOIN top_dists td ON td.distributor_code = f.distributor_code
    WHERE  f.txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
    GROUP BY f.distributor_code, f.distributor_name, f.brand
)
SELECT
     distributor_code, distributor_name, brand
    ,active_user, so_luot_tich, dso_tich
    ,CAST(dso_tich*100.0 / NULLIF(SUM(dso_tich) OVER (PARTITION BY distributor_code),0) AS DECIMAL(10,2)) AS pct_share_in_distributor
FROM   matrix
ORDER BY distributor_name, dso_tich DESC;""",
    ),

    # ── 03_customer ─────────────────────────────────────────────

    (
        "cust: Lookup by RA External ID — full profile + 360 metrics",
        "filter",
        "customer,lookup,external_id,RA,360,vw_dim_customer_lookup",
        """WITH input_ids AS (
    SELECT ra_external_id FROM (VALUES (<<EXTERNAL_ID_LIST>>)) AS v(ra_external_id)
    -- vd: ('RA001'),('RA002'),('RA003')
)
SELECT
     i.ra_external_id, l.customer_id, l.customer_name, l.phone
    ,l.tier, l.region, l.province, l.customer_type
    ,l.account_subtype, l.rfm_segment, l.current_points, l.last_transaction
    ,c360.so_luot_tich, c360.dso_tich, c360.aov, c360.months_active
    ,c360.days_since_first_txn, c360.first_brand, c360.first_channel
    ,c360.top_brand, c360.top_channel, c360.max_txn_seq
    ,c360.reached_L1, c360.reached_L2, c360.reached_L3, c360.reached_L4, c360.reached_L5
FROM       input_ids i
LEFT JOIN  dbo.vw_dim_customer_lookup l   ON l.ra_external_id = i.ra_external_id
LEFT JOIN  dbo.vw_dim_customer_360    c360 ON c360.customer_id = l.customer_id
ORDER BY   i.ra_external_id;""",
    ),

    (
        "cust: Top N spenders YTD (rank by DSO)",
        "metric",
        "customer,top,DSO,ranking,spenders,vw_dim_customer_360",
        """SELECT TOP <<TOP_N>>
     ROW_NUMBER() OVER (ORDER BY dso_tich DESC) AS rank_n
    ,customer_id, customer_name, phone, tier, region, rfm_segment
    ,first_brand, first_channel, top_brand, top_channel
    ,so_luot_tich, dso_tich, aov, months_active, max_txn_seq
FROM   dbo.vw_dim_customer_360
WHERE  (top_brand   = '<<BRAND_OPT>>'   OR '<<BRAND_OPT>>'   = '')
  AND  (top_channel = '<<CHANNEL_OPT>>' OR '<<CHANNEL_OPT>>' = '')
  AND  (region      = '<<REGION_OPT>>'  OR '<<REGION_OPT>>'  = '')
ORDER BY dso_tich DESC;""",
    ),

    (
        "cust: Top N frequency (hyperactive buyers — rank by luot)",
        "metric",
        "customer,frequency,ranking,hyperactive,avg_tich_per_month",
        """SELECT TOP <<TOP_N>>
     ROW_NUMBER() OVER (ORDER BY so_luot_tich DESC) AS rank_n
    ,customer_id, customer_name, phone, tier, region
    ,first_brand, top_brand, top_channel
    ,so_luot_tich, dso_tich, aov, months_active
    ,avg_tich_per_month, days_since_first_txn
FROM   dbo.vw_dim_customer_360
WHERE  so_luot_tich >= <<MIN_LUOT>>
  AND  (top_brand = '<<BRAND_OPT>>' OR '<<BRAND_OPT>>' = '')
ORDER BY so_luot_tich DESC, dso_tich DESC;""",
    ),

    (
        "cust: Churned customers list (không mua N+ ngày — win-back)",
        "filter",
        "customer,churn,win-back,days_since_last,SMS",
        """SELECT
     customer_id, customer_name, phone, tier, region
    ,first_brand, top_brand, top_channel
    ,so_luot_tich AS lifetime_luot, dso_tich AS lifetime_dso, aov
    ,first_txn_date, last_txn_date
    ,DATEDIFF(DAY, last_txn_date, GETDATE())   AS days_since_last_txn
    ,CASE
        WHEN DATEDIFF(DAY, last_txn_date, GETDATE()) BETWEEN <<CHURN_DAYS>> AND <<CHURN_DAYS>>+30 THEN 'Just churned'
        WHEN DATEDIFF(DAY, last_txn_date, GETDATE()) > <<CHURN_DAYS>>+30 THEN 'Long churned'
        ELSE 'Active'
     END                                       AS churn_status
FROM   dbo.vw_dim_customer_360
WHERE  DATEDIFF(DAY, last_txn_date, GETDATE()) >= <<CHURN_DAYS>>
  AND  so_luot_tich >= <<MIN_LIFETIME_LUOT>>
  AND  (top_brand = '<<BRAND_OPT>>' OR '<<BRAND_OPT>>' = '')
ORDER BY lifetime_dso DESC;""",
    ),

    (
        "cust: New customers last N days — summary + list (acquisition)",
        "metric",
        "customer,new,acquisition,first_txn_date,DATEADD",
        """-- PART 1: Summary by brand/channel/region
SELECT
     first_brand, first_channel, region
    ,COUNT(DISTINCT customer_id)             AS new_customers
    ,SUM(dso_tich)                           AS dso_first_period
FROM   dbo.vw_dim_customer_360
WHERE  first_txn_date >= DATEADD(DAY, -<<LAST_N_DAYS>>, GETDATE())
GROUP BY first_brand, first_channel, region
ORDER BY new_customers DESC;

-- PART 2: List chi tiết top 200 khách mới
SELECT TOP 200
     customer_id, customer_name, phone, tier, region
    ,first_brand, first_sub_brand, first_channel, first_region
    ,first_txn_date
    ,DATEDIFF(DAY, first_txn_date, GETDATE()) AS days_since_signup
    ,so_luot_tich, dso_tich, max_txn_seq
FROM   dbo.vw_dim_customer_360
WHERE  first_txn_date >= DATEADD(DAY, -<<LAST_N_DAYS>>, GETDATE())
ORDER BY dso_tich DESC;""",
    ),

    (
        "cust: Tier + RFM distribution (3-part: Tier / RFM / cross-tab)",
        "metric",
        "customer,tier,rfm,distribution,cross-tab,segment",
        """-- PART 1: Distribution theo Tier
SELECT
     COALESCE(tier,'UNKNOWN')             AS tier
    ,COUNT(DISTINCT customer_id)          AS customer_count
    ,CAST(COUNT(DISTINCT customer_id)*100.0 / SUM(COUNT(DISTINCT customer_id)) OVER () AS DECIMAL(10,2)) AS pct_distribution
    ,SUM(dso_tich)                        AS dso_total
    ,CAST(AVG(dso_tich) AS DECIMAL(18,2)) AS dso_avg_per_cust
    ,CAST(AVG(so_luot_tich*1.0) AS DECIMAL(10,2)) AS luot_avg_per_cust
FROM   dbo.vw_dim_customer_360
GROUP BY tier ORDER BY customer_count DESC;

-- PART 2: Distribution theo RFM_Segment
SELECT
     COALESCE(rfm_segment,'UNKNOWN')      AS rfm_segment
    ,COUNT(DISTINCT customer_id)          AS customer_count
    ,CAST(COUNT(DISTINCT customer_id)*100.0 / SUM(COUNT(DISTINCT customer_id)) OVER () AS DECIMAL(10,2)) AS pct_distribution
    ,SUM(dso_tich)                        AS dso_total
    ,CAST(AVG(dso_tich) AS DECIMAL(18,2)) AS dso_avg_per_cust
FROM   dbo.vw_dim_customer_360
GROUP BY rfm_segment ORDER BY customer_count DESC;

-- PART 3: Cross-tab Tier × RFM
SELECT
     COALESCE(tier,'UNKNOWN')             AS tier
    ,COALESCE(rfm_segment,'UNKNOWN')      AS rfm_segment
    ,COUNT(DISTINCT customer_id)          AS customer_count
    ,SUM(dso_tich)                        AS dso_total
FROM   dbo.vw_dim_customer_360
GROUP BY tier, rfm_segment ORDER BY tier, customer_count DESC;""",
    ),

    (
        "cust: Phone timeline — full transaction drill-down per phone",
        "filter",
        "customer,phone,timeline,drill-down,vw_fact_txn_enriched",
        """WITH input_phones AS (
    SELECT phone FROM (VALUES
        (<<PHONE_LIST>>)          -- vd: ('0973490089'),('0985555825')
    ) AS v(phone)
)
SELECT
     f.phone, f.customer_id, f.customer_name, f.tier, f.region
    ,f.txn_seq AS lan_tich_thu
    ,f.txn_date, f.brand, f.sub_brand, f.product_name
    ,f.channel, f.distributor_name, f.store_name
    ,f.amount, f.rule_name, f.days_since_first_touch, f.cohort_month
FROM       dbo.vw_fact_txn_enriched f
INNER JOIN input_phones i ON i.phone = f.phone
ORDER BY f.phone, f.txn_date ASC;""",
    ),

    (
        "cust: Multi-channel customers (mua từ >= N kênh — STRING_AGG)",
        "filter",
        "customer,multi-channel,STRING_AGG,loyalty",
        """WITH cust_channel AS (
    SELECT
         customer_id
        ,MAX(customer_name)                     AS customer_name
        ,MAX(phone)                             AS phone
        ,MAX(tier)                              AS tier
        ,MAX(region)                            AS region
        ,COUNT(DISTINCT channel)                AS unique_channels
        ,STRING_AGG(DISTINCT channel, ', ')     AS channel_list
        ,SUM(amount)                            AS total_dso
        ,COUNT(DISTINCT txn_id)                 AS total_luot
    FROM   dbo.vw_fact_txn_enriched
    WHERE  (brand = '<<BRAND_OPT>>' OR '<<BRAND_OPT>>' = '')
    GROUP BY customer_id
)
SELECT customer_id, customer_name, phone, tier, region,
       unique_channels, channel_list, total_luot, total_dso
FROM   cust_channel
WHERE  unique_channels >= <<MIN_CHANNELS>>
ORDER BY unique_channels DESC, total_dso DESC;""",
    ),

    # ── 04_time_period ──────────────────────────────────────────

    (
        "time: MTD + QTD + YTD snapshot trong 1 query (UNION ALL)",
        "template",
        "time,MTD,QTD,YTD,UNION-ALL,DATEFROMPARTS",
        """WITH base AS (
    SELECT * FROM dbo.vw_fact_txn_enriched
    WHERE (brand   = '<<BRAND_OPT>>'   OR '<<BRAND_OPT>>'   = '')
      AND (channel = '<<CHANNEL_OPT>>' OR '<<CHANNEL_OPT>>' = '')
)
SELECT 'MTD' AS period
      ,COUNT(DISTINCT customer_id) AS active_user
      ,COUNT(DISTINCT txn_id)      AS so_luot_tich
      ,SUM(amount)                 AS dso_tich
      ,DAY(GETDATE())              AS days_in_period
      ,CAST(SUM(amount)/NULLIF(DAY(GETDATE()),0) AS DECIMAL(18,2)) AS avg_dso_per_day
FROM base
WHERE txn_date >= DATEFROMPARTS(YEAR(GETDATE()),MONTH(GETDATE()),1)
  AND txn_date <= GETDATE()
UNION ALL
SELECT 'QTD'
      ,COUNT(DISTINCT customer_id), COUNT(DISTINCT txn_id), SUM(amount)
      ,DATEDIFF(DAY, DATEFROMPARTS(YEAR(GETDATE()),((DATEPART(QUARTER,GETDATE())-1)*3)+1,1), GETDATE())+1
      ,CAST(SUM(amount)/NULLIF(DATEDIFF(DAY,DATEFROMPARTS(YEAR(GETDATE()),((DATEPART(QUARTER,GETDATE())-1)*3)+1,1),GETDATE())+1,0) AS DECIMAL(18,2))
FROM base
WHERE txn_date >= DATEFROMPARTS(YEAR(GETDATE()),((DATEPART(QUARTER,GETDATE())-1)*3)+1,1)
  AND txn_date <= GETDATE()
UNION ALL
SELECT 'YTD'
      ,COUNT(DISTINCT customer_id), COUNT(DISTINCT txn_id), SUM(amount)
      ,DATEDIFF(DAY,'2026-01-01',GETDATE())+1
      ,CAST(SUM(amount)/NULLIF(DATEDIFF(DAY,'2026-01-01',GETDATE())+1,0) AS DECIMAL(18,2))
FROM base WHERE txn_date >= '2026-01-01' AND txn_date <= GETDATE();""",
    ),

    (
        "time: Custom date range — trend theo DAY / WEEK / MONTH / QUARTER",
        "template",
        "time,custom-range,grain,DAY,WEEK,MONTH,QUARTER,trend",
        """SELECT
     CASE '<<GRAIN>>'
        WHEN 'DAY'     THEN CAST(txn_date AS VARCHAR(10))
        WHEN 'WEEK'    THEN CONCAT(YEAR(txn_date),'-W',FORMAT(DATEPART(WEEK,txn_date),'00'))
        WHEN 'MONTH'   THEN FORMAT(txn_date,'yyyy-MM')
        WHEN 'QUARTER' THEN CONCAT(YEAR(txn_date),'-Q',DATEPART(QUARTER,txn_date))
     END                                              AS period_label
    ,COUNT(DISTINCT customer_id)                      AS active_user
    ,COUNT(DISTINCT txn_id)                           AS so_luot_tich
    ,SUM(amount)                                      AS dso_tich
    ,CAST(SUM(amount)*1.0/NULLIF(COUNT(DISTINCT txn_id),0) AS DECIMAL(18,2)) AS aov
FROM   dbo.vw_fact_txn_enriched
WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
GROUP BY
     CASE '<<GRAIN>>'
        WHEN 'DAY'     THEN CAST(txn_date AS VARCHAR(10))
        WHEN 'WEEK'    THEN CONCAT(YEAR(txn_date),'-W',FORMAT(DATEPART(WEEK,txn_date),'00'))
        WHEN 'MONTH'   THEN FORMAT(txn_date,'yyyy-MM')
        WHEN 'QUARTER' THEN CONCAT(YEAR(txn_date),'-Q',DATEPART(QUARTER,txn_date))
     END
ORDER BY period_label;""",
    ),

    (
        "time: MoM compare — brand × channel side-by-side (curr vs prev)",
        "metric",
        "time,mom,compare,brand,channel,CASE-WHEN-pivot",
        """WITH base AS (
    SELECT brand, channel, FORMAT(txn_date,'yyyy-MM') AS month_year
          ,SUM(amount) AS dso, COUNT(DISTINCT txn_id) AS luot, COUNT(DISTINCT customer_id) AS active_user
    FROM   dbo.vw_fact_txn_enriched
    WHERE  FORMAT(txn_date,'yyyy-MM') IN ('<<CURRENT_MONTH>>','<<PREVIOUS_MONTH>>')
    GROUP BY brand, channel, FORMAT(txn_date,'yyyy-MM')
),
pivoted AS (
    SELECT brand, channel
          ,SUM(CASE WHEN month_year='<<CURRENT_MONTH>>'  THEN dso  ELSE 0 END) AS curr_dso
          ,SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN dso  ELSE 0 END) AS prev_dso
          ,SUM(CASE WHEN month_year='<<CURRENT_MONTH>>'  THEN luot ELSE 0 END) AS curr_luot
          ,SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN luot ELSE 0 END) AS prev_luot
          ,SUM(CASE WHEN month_year='<<CURRENT_MONTH>>'  THEN active_user ELSE 0 END) AS curr_user
          ,SUM(CASE WHEN month_year='<<PREVIOUS_MONTH>>' THEN active_user ELSE 0 END) AS prev_user
    FROM   base GROUP BY brand, channel
)
SELECT *, curr_dso-prev_dso AS delta_dso
         ,CAST((curr_dso-prev_dso)*100.0/NULLIF(prev_dso,0) AS DECIMAL(10,2)) AS pct_mom_dso
         ,CAST((curr_luot-prev_luot)*100.0/NULLIF(prev_luot,0) AS DECIMAL(10,2)) AS pct_mom_luot
         ,CAST((curr_user-prev_user)*100.0/NULLIF(prev_user,0) AS DECIMAL(10,2)) AS pct_mom_user
FROM   pivoted ORDER BY ABS(delta_dso) DESC;""",
    ),

    (
        "time: QoQ compare — brand × channel side-by-side",
        "metric",
        "time,qoq,compare,brand,channel,QUARTER",
        """WITH base AS (
    SELECT brand, channel
          ,CONCAT(YEAR(txn_date),'-Q',DATEPART(QUARTER,txn_date)) AS quarter_label
          ,SUM(amount) AS dso, COUNT(DISTINCT txn_id) AS luot, COUNT(DISTINCT customer_id) AS active_user
    FROM   dbo.vw_fact_txn_enriched
    WHERE  CONCAT(YEAR(txn_date),'-Q',DATEPART(QUARTER,txn_date)) IN ('<<CURRENT_QUARTER>>','<<PREVIOUS_QUARTER>>')
    GROUP BY brand, channel, CONCAT(YEAR(txn_date),'-Q',DATEPART(QUARTER,txn_date))
)
SELECT brand, channel
      ,SUM(CASE WHEN quarter_label='<<CURRENT_QUARTER>>'  THEN dso ELSE 0 END) AS curr_dso
      ,SUM(CASE WHEN quarter_label='<<PREVIOUS_QUARTER>>' THEN dso ELSE 0 END) AS prev_dso
      ,SUM(CASE WHEN quarter_label='<<CURRENT_QUARTER>>'  THEN dso ELSE 0 END)
        - SUM(CASE WHEN quarter_label='<<PREVIOUS_QUARTER>>' THEN dso ELSE 0 END) AS delta_dso
      ,CAST((SUM(CASE WHEN quarter_label='<<CURRENT_QUARTER>>'  THEN dso ELSE 0 END)
            -SUM(CASE WHEN quarter_label='<<PREVIOUS_QUARTER>>' THEN dso ELSE 0 END))*100.0
           /NULLIF(SUM(CASE WHEN quarter_label='<<PREVIOUS_QUARTER>>' THEN dso ELSE 0 END),0)
           AS DECIMAL(10,2)) AS pct_qoq_dso
      ,SUM(CASE WHEN quarter_label='<<CURRENT_QUARTER>>'  THEN luot ELSE 0 END) AS curr_luot
      ,SUM(CASE WHEN quarter_label='<<PREVIOUS_QUARTER>>' THEN luot ELSE 0 END) AS prev_luot
FROM   base
GROUP BY brand, channel
ORDER BY ABS(SUM(CASE WHEN quarter_label='<<CURRENT_QUARTER>>'  THEN dso ELSE 0 END)
            -SUM(CASE WHEN quarter_label='<<PREVIOUS_QUARTER>>' THEN dso ELSE 0 END)) DESC;""",
    ),

    (
        "time: YoY compare — bypass view, query fact trực tiếp (2 năm)",
        "ad_hoc",
        "time,yoy,compare,raw-fact,YEAR,bypass-view",
        """-- ⚠️ View filter >= 2026-01-01 → phải query fact trực tiếp cho YoY
WITH base AS (
    SELECT
         f.Customer__c AS customer_id, f.Transaction_External_ID__c AS txn_id
        ,f.Amount__c AS amount, YEAR(f.Transaction_Date__c) AS year_n
        ,MONTH(f.Transaction_Date__c) AS month_n
        ,b.Brand AS brand, ch.Channel AS channel
    FROM      fact f
    JOIN      dim_brand b  ON b.Product_Code  = f.Product_Code__c
    JOIN      dim_channel ch ON ch.Customer   = f.Distributor_Code__c
    WHERE  f.Transaction_Type__c = 'Product Point'
       AND b.Product_Type        = 'SỬA BỘT'
       AND f.Amount__c           > 0
       AND YEAR(f.Transaction_Date__c)  IN (<<CURRENT_YEAR>>, <<PREVIOUS_YEAR>>)
       AND MONTH(f.Transaction_Date__c) = <<MONTH_NUM>>
)
SELECT brand, channel
      ,SUM(CASE WHEN year_n=<<CURRENT_YEAR>>  THEN amount ELSE 0 END) AS curr_dso
      ,SUM(CASE WHEN year_n=<<PREVIOUS_YEAR>> THEN amount ELSE 0 END) AS prev_dso
      ,SUM(CASE WHEN year_n=<<CURRENT_YEAR>>  THEN amount ELSE 0 END)
        - SUM(CASE WHEN year_n=<<PREVIOUS_YEAR>> THEN amount ELSE 0 END)       AS delta_dso
      ,CAST((SUM(CASE WHEN year_n=<<CURRENT_YEAR>>  THEN amount ELSE 0 END)
            -SUM(CASE WHEN year_n=<<PREVIOUS_YEAR>> THEN amount ELSE 0 END))*100.0
           /NULLIF(SUM(CASE WHEN year_n=<<PREVIOUS_YEAR>> THEN amount ELSE 0 END),0)
           AS DECIMAL(10,2))                                                    AS pct_yoy_dso
      ,COUNT(DISTINCT CASE WHEN year_n=<<CURRENT_YEAR>>  THEN customer_id END) AS curr_user
      ,COUNT(DISTINCT CASE WHEN year_n=<<PREVIOUS_YEAR>> THEN customer_id END) AS prev_user
FROM   base GROUP BY brand, channel
ORDER BY ABS(delta_dso) DESC;""",
    ),

    (
        "time: Day-of-week analysis — Thứ 2 → CN (avg luot + DSO per day)",
        "metric",
        "time,day-of-week,WEEKDAY,DATENAME,avg-per-instance",
        """WITH base AS (
    SELECT
         DATEPART(WEEKDAY, txn_date) AS dow_num
        ,DATENAME(WEEKDAY, txn_date)  AS dow_name
        ,CAST(txn_date AS DATE)       AS txn_date_only
        ,customer_id, txn_id, amount
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date BETWEEN '<<START_DATE>>' AND '<<END_DATE>>'
      AND  (brand = '<<BRAND_OPT>>' OR '<<BRAND_OPT>>' = '')
),
day_count AS (
    SELECT dow_num, COUNT(DISTINCT txn_date_only) AS num_day_instances
    FROM   base GROUP BY dow_num
)
SELECT
     b.dow_num, b.dow_name
    ,COUNT(DISTINCT b.customer_id)  AS active_user
    ,COUNT(DISTINCT b.txn_id)       AS so_luot_tich
    ,SUM(b.amount)                  AS dso_tich
    ,dc.num_day_instances
    ,CAST(COUNT(DISTINCT b.txn_id)*1.0/NULLIF(dc.num_day_instances,0) AS DECIMAL(10,2)) AS avg_luot_per_day
    ,CAST(SUM(b.amount)*1.0/NULLIF(dc.num_day_instances,0) AS DECIMAL(18,2))           AS avg_dso_per_day
FROM base b LEFT JOIN day_count dc ON dc.dow_num=b.dow_num
GROUP BY b.dow_num, b.dow_name, dc.num_day_instances
ORDER BY b.dow_num;""",
    ),

    (
        "time: Rolling 7d vs prev 7d WoW snapshot (brand × channel)",
        "metric",
        "time,wow,rolling,7-day,DATEADD,window",
        """WITH base AS (
    SELECT brand, channel, region
          ,CASE
              WHEN txn_date >= DATEADD(DAY,-7,GETDATE())  THEN 'last_7d'
              WHEN txn_date >= DATEADD(DAY,-14,GETDATE())
               AND txn_date <  DATEADD(DAY,-7,GETDATE())  THEN 'prev_7d'
           END                               AS period
          ,amount, customer_id, txn_id
    FROM   dbo.vw_fact_txn_enriched
    WHERE  txn_date >= DATEADD(DAY,-14,GETDATE())
      AND  (brand = '<<BRAND_OPT>>' OR '<<BRAND_OPT>>' = '')
)
SELECT brand, channel
      ,SUM(CASE WHEN period='last_7d' THEN amount ELSE 0 END) AS last_7d_dso
      ,SUM(CASE WHEN period='prev_7d' THEN amount ELSE 0 END) AS prev_7d_dso
      ,SUM(CASE WHEN period='last_7d' THEN amount ELSE 0 END)
        - SUM(CASE WHEN period='prev_7d' THEN amount ELSE 0 END)              AS delta_dso
      ,CAST((SUM(CASE WHEN period='last_7d' THEN amount ELSE 0 END)
            -SUM(CASE WHEN period='prev_7d' THEN amount ELSE 0 END))*100.0
           /NULLIF(SUM(CASE WHEN period='prev_7d' THEN amount ELSE 0 END),0) AS DECIMAL(10,2)) AS pct_wow
      ,COUNT(DISTINCT CASE WHEN period='last_7d' THEN customer_id END) AS last_7d_user
      ,COUNT(DISTINCT CASE WHEN period='prev_7d' THEN customer_id END) AS prev_7d_user
      ,COUNT(DISTINCT CASE WHEN period='last_7d' THEN txn_id END)      AS last_7d_luot
      ,COUNT(DISTINCT CASE WHEN period='prev_7d' THEN txn_id END)      AS prev_7d_luot
FROM   base WHERE period IS NOT NULL
GROUP BY brand, channel
ORDER BY ABS(SUM(CASE WHEN period='last_7d' THEN amount ELSE 0 END)
            -SUM(CASE WHEN period='prev_7d' THEN amount ELSE 0 END)) DESC;""",
    ),

    # ── 05_utility ──────────────────────────────────────────────

    (
        "util: Distinct values reference — brand / sub_brand / channel / region / province / distributor / rule_name / tier+RFM",
        "filter",
        "utility,distinct,reference,lookup,filter-values,vw_fact_txn_enriched",
        """-- Run từng block riêng để xem distinct values trước khi filter

-- 1. Brand
SELECT brand, COUNT(DISTINCT customer_id) AS active_user, COUNT(DISTINCT txn_id) AS so_luot_tich, SUM(amount) AS dso_tich
FROM dbo.vw_fact_txn_enriched GROUP BY brand ORDER BY dso_tich DESC;

-- 2. Sub_Brand (brand + sub_brand)
SELECT brand, sub_brand, COUNT(DISTINCT customer_id) AS active_user, SUM(amount) AS dso_tich
FROM dbo.vw_fact_txn_enriched WHERE sub_brand IS NOT NULL GROUP BY brand, sub_brand ORDER BY brand, dso_tich DESC;

-- 3. Channel
SELECT channel, COUNT(DISTINCT customer_id) AS active_user, SUM(amount) AS dso_tich
FROM dbo.vw_fact_txn_enriched GROUP BY channel ORDER BY dso_tich DESC;

-- 4. Region
SELECT region, COUNT(DISTINCT customer_id) AS active_user, SUM(amount) AS dso_tich
FROM dbo.vw_fact_txn_enriched WHERE region IS NOT NULL GROUP BY region ORDER BY dso_tich DESC;

-- 5. Top 30 Province
SELECT TOP 30 province, region, COUNT(DISTINCT customer_id) AS active_user, SUM(amount) AS dso_tich
FROM dbo.vw_fact_txn_enriched WHERE province IS NOT NULL GROUP BY province, region ORDER BY dso_tich DESC;

-- 6. Top 30 Distributor
SELECT TOP 30 distributor_code, distributor_name, COUNT(DISTINCT customer_id) AS active_user, SUM(amount) AS dso_tich
FROM dbo.vw_fact_txn_enriched GROUP BY distributor_code, distributor_name ORDER BY dso_tich DESC;

-- 7. Rule_Name (campaign)
SELECT rule_name, COUNT(DISTINCT txn_id) AS so_luot_tich, SUM(amount) AS dso_tich, MIN(txn_date) AS first_seen, MAX(txn_date) AS last_seen
FROM dbo.vw_fact_txn_enriched WHERE rule_name IS NOT NULL GROUP BY rule_name ORDER BY dso_tich DESC;

-- 8. Tier × RFM cross-tab
SELECT COALESCE(tier,'UNKNOWN') AS tier, COALESCE(rfm_segment,'UNKNOWN') AS rfm_segment, COUNT(DISTINCT customer_id) AS unique_customers
FROM dbo.vw_fact_txn_enriched GROUP BY tier, rfm_segment ORDER BY unique_customers DESC;""",
    ),

]


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Ensure columns exist
    cols = {r[1] for r in conn.execute("PRAGMA table_info(snippets)").fetchall()}
    if "title" not in cols:
        conn.execute("ALTER TABLE snippets ADD COLUMN title TEXT NOT NULL DEFAULT ''")
        print("  → Added column: title")
    if "tags" not in cols:
        conn.execute("ALTER TABLE snippets ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
        print("  → Added column: tags")
    conn.commit()

    inserted = 0
    skipped  = 0

    for title, category, tags, sql in SNIPPETS:
        exists = conn.execute(
            "SELECT 1 FROM snippets WHERE title = ?", (title,)
        ).fetchone()
        if exists:
            skipped += 1
            continue
        conn.execute(
            "INSERT INTO snippets (filename, title, category, sql, source, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, title, category, sql.strip(), "user", tags),
        )
        inserted += 1

    conn.commit()

    # Normalise Source-3 (ad_hoc subfolder) snippets to 'data' category
    data_updated = 0
    for prefix in ('mkt:', 'sales:', 'cust:', 'time:', 'util:'):
        r = conn.execute(
            "UPDATE snippets SET category='data' WHERE title LIKE ? AND category != 'data'",
            (prefix + '%',)
        )
        data_updated += r.rowcount
    if data_updated:
        conn.commit()
        print(f"  → Updated {data_updated} source-3 snippets to category 'data'")

    conn.close()
    print(f"\nDone: {inserted} inserted, {skipped} skipped (title already exists)")
    print(f"   Total snippets in seed: {len(SNIPPETS)}")


if __name__ == "__main__":
    main()
