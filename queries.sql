-- 1. Когортный анализ: Retention Rate по месяцам
WITH customer_first_order AS (
    SELECT
        "Customer ID" AS customer_id,
        MIN(strftime('%Y-%m-01', InvoiceDate)) AS cohort_month
    FROM retail_clean
    GROUP BY "Customer ID"
),

orders_with_cohort AS (
    SELECT
        r."Customer ID" AS customer_id,
        c.cohort_month,
        strftime('%Y-%m-01', r.InvoiceDate) AS order_month,
        -- Расчет номера месяца жизни когорты (0, 1, 2...)
        (
            (CAST(strftime('%Y', r.InvoiceDate) AS INTEGER) - CAST(strftime('%Y', c.cohort_month) AS INTEGER)) * 12 +
            (CAST(strftime('%m', r.InvoiceDate) AS INTEGER) - CAST(strftime('%m', c.cohort_month) AS INTEGER))
        ) AS cohort_index
    FROM retail_clean r
    JOIN customer_first_order c ON r."Customer ID" = c.customer_id
),

cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_id) AS total_customers
    FROM orders_with_cohort
    WHERE cohort_index = 0
    GROUP BY cohort_month
),

cohort_retention AS (
    SELECT
        o.cohort_month,
        s.total_customers,
        o.cohort_index,
        COUNT(DISTINCT o.customer_id) AS active_customers,
        ROUND(COUNT(DISTINCT o.customer_id) * 100.0 / s.total_customers, 2) AS retention_rate
    FROM orders_with_cohort o
    JOIN cohort_sizes s ON o.cohort_month = s.cohort_month
    GROUP BY o.cohort_month, s.total_customers, o.cohort_index
)

SELECT * 
FROM cohort_retention
WHERE cohort_index <= 12
ORDER BY cohort_month, cohort_index;

-- 2. RFM-анализ: Расчет метрик и сегментация
WITH max_date AS (
    SELECT datetime(MAX(InvoiceDate), '+1 day') AS snapshot_date FROM retail_clean
),

customer_summary AS (
    SELECT
        r."Customer ID" AS customer_id,
        CAST(julianday((SELECT snapshot_date FROM max_date)) - julianday(MAX(r.InvoiceDate)) AS INTEGER) AS recency,
        COUNT(DISTINCT r.Invoice) AS frequency,
        ROUND(SUM(r.TotalAmount), 2) AS monetary
    FROM retail_clean r
    GROUP BY r."Customer ID"
),

rfm_scoring AS (
    SELECT
        customer_id,
        recency,
        frequency,
        monetary,
        -- Чем меньше дней прошло с заказа, тем выше балл (1-4)
        NTILE(4) OVER (ORDER BY recency DESC) AS r_score,
        NTILE(4) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
    FROM customer_summary
)

SELECT
    customer_id,
    recency,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (CAST(r_score AS TEXT) || CAST(f_score AS TEXT) || CAST(m_score AS TEXT)) AS rfm_cell,
    CASE
        WHEN r_score = 4 AND f_score = 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 3 AND f_score <= 2 THEN 'Recent / Promising'
        WHEN r_score = 1 AND f_score >= 3 THEN 'At Risk (High-Value)'
        WHEN r_score = 1 AND f_score = 1 THEN 'Lost Customers'
        ELSE 'Needs Attention'
    END AS segment
FROM rfm_scoring
ORDER BY monetary DESC;