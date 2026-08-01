-- ============================================================
-- Retail Sales Data Warehouse — Star Schema DDL
-- Fact table: fact_sales
-- Dimension tables: dim_date, dim_product, dim_customer, dim_store
-- ============================================================

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_store;

-- ---------------- DIM_DATE ----------------
CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,   -- YYYYMMDD
    full_date       TEXT NOT NULL,         -- YYYY-MM-DD
    day             INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    month_name      TEXT NOT NULL,
    quarter         INTEGER NOT NULL,
    year            INTEGER NOT NULL,
    day_of_week     TEXT NOT NULL,
    is_weekend      INTEGER NOT NULL       -- 0/1
);

-- ---------------- DIM_PRODUCT ----------------
CREATE TABLE dim_product (
    product_key     INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    UNIQUE(product_name, category)
);

-- ---------------- DIM_CUSTOMER ----------------
CREATE TABLE dim_customer (
    customer_key    INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name   TEXT NOT NULL,
    customer_email  TEXT,
    UNIQUE(customer_email)
);

-- ---------------- DIM_STORE ----------------
CREATE TABLE dim_store (
    store_key       INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id        TEXT NOT NULL UNIQUE,
    city            TEXT NOT NULL
);

-- ---------------- FACT_SALES ----------------
CREATE TABLE fact_sales (
    sales_key       INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  TEXT NOT NULL UNIQUE,
    date_key        INTEGER NOT NULL,
    product_key     INTEGER NOT NULL,
    customer_key    INTEGER NOT NULL,
    store_key       INTEGER NOT NULL,
    payment_method  TEXT,
    quantity        INTEGER NOT NULL,
    unit_price      REAL NOT NULL,
    discount_pct    REAL NOT NULL DEFAULT 0,
    gross_amount    REAL NOT NULL,   -- quantity * unit_price
    discount_amount REAL NOT NULL,   -- gross_amount * discount_pct/100
    net_amount      REAL NOT NULL,   -- gross_amount - discount_amount
    FOREIGN KEY (date_key)     REFERENCES dim_date(date_key),
    FOREIGN KEY (product_key)  REFERENCES dim_product(product_key),
    FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    FOREIGN KEY (store_key)    REFERENCES dim_store(store_key)
);

-- Helpful indexes for analytical queries
CREATE INDEX idx_fact_sales_date     ON fact_sales(date_key);
CREATE INDEX idx_fact_sales_product  ON fact_sales(product_key);
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_fact_sales_store    ON fact_sales(store_key);
