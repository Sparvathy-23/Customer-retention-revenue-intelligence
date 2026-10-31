CREATE VIEW cohort_counts AS
WITH purchases AS (
    SELECT customer_id, invoice,
           MIN(invoice_date) AS invoice_date,
           SUM(revenue)      AS invoice_revenue
    FROM transactions
    WHERE has_customer AND NOT is_cancellation
    GROUP BY customer_id, invoice
    HAVING SUM(revenue) > 0
),
first_purchase AS (
    SELECT customer_id,
           DATE_TRUNC('month', MIN(invoice_date))::date AS cohort_month
    FROM purchases
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT
           p.customer_id,
           f.cohort_month,
           (EXTRACT(YEAR  FROM p.invoice_date) * 12 + EXTRACT(MONTH FROM p.invoice_date))
         - (EXTRACT(YEAR  FROM f.cohort_month) * 12 + EXTRACT(MONTH FROM f.cohort_month))
           AS month_index
    FROM purchases p
    JOIN first_purchase f USING (customer_id)
)
SELECT cohort_month,
       month_index::int AS month_index,
       COUNT(*)         AS active_customers
FROM activity
GROUP BY 1, 2;




SELECT cohort_month,
       MAX(active_customers) FILTER (WHERE month_index = 0) AS cohort_size,
       ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_index = 1)
             / MAX(active_customers) FILTER (WHERE month_index = 0), 1) AS m1_pct,
       ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_index = 3)
             / MAX(active_customers) FILTER (WHERE month_index = 0), 1) AS m3_pct,
       ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_index = 6)
             / MAX(active_customers) FILTER (WHERE month_index = 0), 1) AS m6_pct,
       ROUND(100.0 * MAX(active_customers) FILTER (WHERE month_index = 12)
             / MAX(active_customers) FILTER (WHERE month_index = 0), 1) AS m12_pct
FROM cohort_counts
GROUP BY cohort_month
ORDER BY cohort_month;