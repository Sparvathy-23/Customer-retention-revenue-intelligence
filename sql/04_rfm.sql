-- 04_rfm.sql
-- RFM (recency, frequency, monetary) per customer, built from the `transactions` table.
--
-- Definitions
--   Snapshot date : 2011-12-10 (the day after the last transaction in the data)
--   Customers     : only rows with a customer_id (has_customer = true)
--   Purchase      : an invoice that is not a cancellation and has net value > 0
--   Recency       : days from the customer's last purchase to the snapshot date
--   Frequency     : number of purchase invoices
--   Monetary      : the customer's net revenue, cancellations subtracted
--
-- Exclusion rule
--   Customers with monetary <= 0 (20 customers: purchases fully cancelled) are
--   left out of scoring, because they never made a net purchase.
--
-- Note: these are full-history values, used for segmentation and the dashboard.
-- The repeat-purchase model must rebuild features as of each cutoff date,
-- otherwise it would leak future information.

CREATE OR REPLACE VIEW rfm_base AS
WITH purchases AS (
    SELECT customer_id, invoice,
           MIN(invoice_date) AS invoice_date
    FROM transactions
    WHERE has_customer AND NOT is_cancellation
    GROUP BY customer_id, invoice
    HAVING SUM(revenue) > 0
),
per_customer AS (
    SELECT customer_id,
           MIN(invoice_date)::date AS first_purchase,
           MAX(invoice_date)::date AS last_purchase,
           COUNT(*)                AS frequency
    FROM purchases
    GROUP BY customer_id
),
net AS (
    SELECT customer_id, SUM(revenue) AS net_revenue
    FROM transactions
    WHERE has_customer
    GROUP BY customer_id
)
SELECT p.customer_id,
       p.first_purchase,
       p.last_purchase,
       (DATE '2011-12-10' - p.last_purchase) AS recency_days,
       p.frequency,
       ROUND(n.net_revenue, 2)               AS monetary
FROM per_customer p
JOIN net n USING (customer_id);


-- Scores: 5 = best on every dimension.
-- Recency and frequency use fixed cut-offs (customers with the same value always
-- get the same score); monetary uses quintiles, since spend values rarely tie.
CREATE OR REPLACE VIEW rfm_scores AS
SELECT customer_id, first_purchase, last_purchase,
       recency_days, frequency, monetary,
       CASE WHEN recency_days <= 20  THEN 5     -- 20 days or fewer
            WHEN recency_days <= 59  THEN 4     -- 21 to 59 days
            WHEN recency_days <= 186 THEN 3     -- 60 to 186 days
            WHEN recency_days <= 409 THEN 2     -- 187 to 409 days
            ELSE 1 END                              AS r_score,   -- 410+ days
       CASE WHEN frequency = 1  THEN 1          -- 1 invoice
            WHEN frequency = 2  THEN 2          -- 2 invoices
            WHEN frequency <= 4 THEN 3          -- 3 to 4 invoices
            WHEN frequency <= 9 THEN 4          -- 5 to 9 invoices
            ELSE 5 END                              AS f_score,   -- 10+ invoices