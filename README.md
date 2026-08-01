# Sales Data Warehouse & Retail ETL Pipeline

An end-to-end data engineering project: a Python ETL pipeline that extracts messy raw
retail sales data, cleans and transforms it, and loads it into a **Star Schema** SQLite
data warehouse — with an analytics dashboard on top for sales trend reporting.

## Architecture

```
raw_sales_data.csv (messy source export)
        │
        ▼
┌───────────────────┐
│   EXTRACT          │  scripts/generate_raw_data.py  → simulated POS/e-commerce export
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   TRANSFORM         │  scripts/etl_pipeline.py
│  - standardize dates (3 inconsistent formats → ISO)              │
│  - trim / normalize text casing                                  │
│  - drop duplicate transactions                                   │
│  - impute missing quantity / unit_price                          │
│  - compute gross / discount / net amount                         │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   LOAD              │  sql/schema.sql  →  output/retail_dw.db (SQLite)
│  Star Schema:                                                    │
│   dim_date · dim_product · dim_customer · dim_store · fact_sales │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   REPORT             │  output/dashboard.html  (interactive analytics dashboard)
│                       │  output/sales_flat_export_for_powerbi.csv (Power BI-ready)
└───────────────────┘
```

## Star Schema

- **fact_sales** — one row per transaction: quantity, unit_price, discount_pct,
  gross_amount, discount_amount, net_amount, plus foreign keys to every dimension.
- **dim_date** — calendar attributes (year, month, quarter, day of week, weekend flag).
- **dim_product** — product name + category.
- **dim_customer** — customer name + email.
- **dim_store** — store ID + city.

This design supports fast slice-and-dice analytical queries (revenue by month,
by category, by city, by customer, etc.) — see `sql/sample_analytical_queries.sql`.

## Project structure

```
retail_dw_project/
├── data/
│   └── raw_sales_data.csv          # simulated messy source data (5,060 rows)
├── scripts/
│   ├── generate_raw_data.py        # generates the raw source CSV
│   └── etl_pipeline.py             # extract → transform → load
├── sql/
│   ├── schema.sql                  # star schema DDL
│   └── sample_analytical_queries.sql
├── output/
│   ├── retail_dw.db                # SQLite data warehouse (final deliverable)
│   ├── etl_log.txt                 # data-quality / run log from the last ETL run
│   ├── sales_flat_export_for_powerbi.csv   # flattened fact+dims, ready for Power BI / Excel
│   ├── dashboard_data.json         # pre-aggregated metrics used by the dashboard
│   └── dashboard.html              # interactive analytics dashboard
└── README.md
```

## How to run

```bash
# 1. Generate the raw (messy) source data
python3 scripts/generate_raw_data.py

# 2. Run the ETL pipeline: extract → clean/transform → load into star schema
python3 scripts/etl_pipeline.py
```

This produces `output/retail_dw.db`, a SQLite warehouse ready to query.

## Data quality handled by the pipeline

| Issue | Handling |
|---|---|
| 3 inconsistent date formats (`2026-07-13`, `20/01/2025`, `08-Jan-2025`) | Parsed and normalized to ISO `YYYY-MM-DD` |
| 60 exact duplicate transactions | Detected by `transaction_id` and dropped |
| Missing `quantity` (~3%) | Imputed with 1 (minimum viable order) |
| Missing `unit_price` (~2%) | Imputed with the average price for that product |
| Inconsistent name casing / stray whitespace | Trimmed and title-cased |
| Inconsistent payment method casing (`cash` vs `CREDIT CARD`) | Normalized to Title Case |

Every run writes a summary to `output/etl_log.txt` (rows read, dropped, imputed, and
final row counts per table) — a lightweight data-quality audit trail.

## Connecting to Power BI

Since this environment can't run Power BI Desktop directly, two paths are provided:

1. **Recommended:** open Power BI Desktop → *Get Data* → *SQLite database* → point it at
   `output/retail_dw.db`. Load `fact_sales` and all four `dim_*` tables, then build
   relationships exactly as defined in `sql/schema.sql` (Power BI will usually
   auto-detect them from the foreign keys).
2. **Quick path:** import `output/sales_flat_export_for_powerbi.csv` directly — it's the
   fact table pre-joined with every dimension, ready for pivot tables / charts with no
   modeling required.

## Included dashboard (in-browser substitute)

`output/dashboard.html` is a self-contained interactive dashboard (no Power BI needed to
view it) covering:
- KPI summary (total revenue, orders, AOV, unique customers)
- Monthly revenue trend
- Revenue by category, city, and top products
- Payment method mix

Open it directly in any browser.

## Tech stack

- **Python 3** (standard library only — `csv`, `sqlite3`, `datetime`) for the ETL
- **SQLite** as the warehouse engine (star schema, indexed foreign keys)
- **SQL** for analytical/reporting queries
- **HTML/JS (Chart.js)** for the dashboard, built on data exported from the warehouse
- Designed to plug directly into **Power BI** via SQLite connector or CSV import
