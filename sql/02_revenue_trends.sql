SELECT DATE_TRUNC('month', invoice_date)::date AS month,
       ROUND(SUM(revenue)) AS net_revenue,
       COUNT(DISTINCT invoice) FILTER (WHERE NOT is_cancellation) AS invoices,
       COUNT(DISTINCT customer_id) AS customers
FROM transactions
GROUP BY 1
ORDER BY 1;