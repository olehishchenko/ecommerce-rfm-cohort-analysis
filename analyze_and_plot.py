import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

conn = sqlite3.connect('retail.db')

# 1. Построение тепловой карты Retention Rate
cohort_query = """
WITH customer_first_order AS (
    SELECT "Customer ID" AS customer_id, MIN(strftime('%Y-%m-01', InvoiceDate)) AS cohort_month
    FROM retail_clean GROUP BY "Customer ID"
),
orders_with_cohort AS (
    SELECT r."Customer ID" AS customer_id, c.cohort_month,
        ((CAST(strftime('%Y', r.InvoiceDate) AS INTEGER) - CAST(strftime('%Y', c.cohort_month) AS INTEGER)) * 12 +
         (CAST(strftime('%m', r.InvoiceDate) AS INTEGER) - CAST(strftime('%m', c.cohort_month) AS INTEGER))) AS cohort_index
    FROM retail_clean r JOIN customer_first_order c ON r."Customer ID" = c.customer_id
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS total_customers
    FROM orders_with_cohort WHERE cohort_index = 0 GROUP BY cohort_month
)
SELECT o.cohort_month, o.cohort_index,
       ROUND(COUNT(DISTINCT o.customer_id) * 100.0 / s.total_customers, 1) AS retention_rate
FROM orders_with_cohort o JOIN cohort_sizes s ON o.cohort_month = s.cohort_month
WHERE o.cohort_index BETWEEN 1 AND 12
GROUP BY o.cohort_month, o.cohort_index;
"""

df_cohort = pd.read_sql_query(cohort_query, conn)
cohort_pivot = df_cohort.pivot(index='cohort_month', columns='cohort_index', values='retention_rate')

plt.figure(figsize=(14, 7))
sns.heatmap(cohort_pivot, annot=True, fmt='.1f', cmap='Blues', cbar_kws={'label': 'Retention Rate (%)'})
plt.title('Monthly Customer Retention Rate Heatmap', fontsize=14, weight='bold')
plt.xlabel('Cohort Lifetime (Months Since First Order)', fontsize=11)
plt.ylabel('Cohort Month', fontsize=11)
plt.tight_layout()
plt.savefig('cohort_retention_heatmap.png', dpi=300)
print("График 'cohort_retention_heatmap.png' сохранен.")

# 2. Построение распределения по сегментам RFM
rfm_query = """
WITH max_date AS (SELECT datetime(MAX(InvoiceDate), '+1 day') AS snapshot_date FROM retail_clean),
customer_summary AS (
    SELECT r."Customer ID" AS customer_id,
        CAST(julianday((SELECT snapshot_date FROM max_date)) - julianday(MAX(r.InvoiceDate)) AS INTEGER) AS recency,
        COUNT(DISTINCT r.Invoice) AS frequency,
        ROUND(SUM(r.TotalAmount), 2) AS monetary
    FROM retail_clean r GROUP BY r."Customer ID"
),
rfm_scoring AS (
    SELECT customer_id, monetary,
        NTILE(4) OVER (ORDER BY recency DESC) AS r_score,
        NTILE(4) OVER (ORDER BY frequency ASC) AS f_score
    FROM customer_summary
)
SELECT 
    CASE
        WHEN r_score = 4 AND f_score = 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 3 AND f_score <= 2 THEN 'Recent / Promising'
        WHEN r_score = 1 AND f_score >= 3 THEN 'At Risk (High-Value)'
        WHEN r_score = 1 AND f_score = 1 THEN 'Lost Customers'
        ELSE 'Needs Attention'
    END AS segment,
    COUNT(*) AS customer_count,
    ROUND(SUM(monetary), 2) AS total_revenue
FROM rfm_scoring
GROUP BY segment
ORDER BY total_revenue DESC;
"""

df_rfm = pd.read_sql_query(rfm_query, conn)
conn.close()

fig, ax1 = plt.subplots(figsize=(10, 5))
sns.barplot(data=df_rfm, x='segment', y='customer_count', ax=ax1, palette='Blues_r')
ax1.set_title('Customer Distribution by RFM Segment', fontsize=14, weight='bold')
ax1.set_xlabel('RFM Segment', fontsize=11)
ax1.set_ylabel('Number of Customers', fontsize=11)
plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig('rfm_segments_distribution.png', dpi=300)
print("График 'rfm_segments_distribution.png' сохранен.")