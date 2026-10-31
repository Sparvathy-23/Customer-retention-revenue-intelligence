-- Clean transactions table (loaded from data/processed/online_retail_clean.csv)
CREATE TABLE transactions (
    invoice          TEXT,
    stock_code       TEXT,
    description      TEXT,
    quantity         INTEGER,
    invoice_date     TIMESTAMP,
    price            NUMERIC(12,2),
    customer_id      INTEGER,
    country          TEXT,
    source_sheet     TEXT,
    revenue          NUMERIC(14,2),
    is_cancellation  BOOLEAN,
    has_customer     BOOLEAN
);

CREATE INDEX idx_tx_customer ON transactions (customer_id);
CREATE INDEX idx_tx_date     ON transactions (invoice_date);
CREATE INDEX idx_tx_invoice  ON transactions (invoice);