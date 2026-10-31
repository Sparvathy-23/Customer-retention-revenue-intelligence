CREATE OR REPLACE VIEW rfm_segments AS
SELECT *,
       CASE WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'New and promising'
            WHEN r_score = 3  AND f_score <= 2 THEN 'Needs attention'
            WHEN r_score <= 2 AND f_score >= 4 THEN 'Cannot lose'
            WHEN r_score <= 2 AND f_score = 3  THEN 'At risk'
            ELSE 'Lapsed'
       END AS segment
FROM rfm_scores;

SELECT segment,
       COUNT(*) AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_customers,
       ROUND(SUM(monetary)) AS revenue,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_revenue,
       ROUND(AVG(recency_days)) AS avg_recency_days,
       ROUND(AVG(frequency), 1) AS avg_frequency
FROM rfm_segments
GROUP BY segment
ORDER BY revenue DESC;

WITH ranked AS (
    SELECT customer_id, monetary,
           NTILE(10) OVER (ORDER BY monetary DESC) AS decile
    FROM rfm_scores
)
SELECT decile,
       COUNT(*) AS customers,
       ROUND(SUM(monetary)) AS revenue,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_revenue,
       ROUND(100.0 * SUM(SUM(monetary)) OVER (ORDER BY decile)
             / SUM(SUM(monetary)) OVER (), 1) AS cumulative_pct
FROM ranked
GROUP BY decile
ORDER BY decile;