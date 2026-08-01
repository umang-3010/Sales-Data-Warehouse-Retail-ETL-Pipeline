"""
etl_pipeline.py
================
End-to-end ETL pipeline for the Retail Sales Data Warehouse project.

Stages:
  1. EXTRACT  - Read raw transactional data from CSV (simulated POS export)
  2. TRANSFORM - Clean & standardize data:
       - Parse inconsistent date formats -> single ISO format
       - Trim / normalize text casing (names, payment methods)
       - Drop exact duplicate transactions
       - Handle missing values (impute / drop based on business rule)
       - Compute derived measures (gross, discount, net amount)
  3. LOAD     - Populate a star-schema SQLite data warehouse:
       dim_date, dim_product, dim_customer, dim_store, fact_sales

Run:
    python3 etl_pipeline.py

Output:
    ../output/retail_dw.db   (SQLite data warehouse)
    ../output/etl_log.txt    (run log / data-quality report)
"""

import csv
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_CSV = BASE_DIR / "data" / "raw_sales_data.csv"
SCHEMA_SQL = BASE_DIR / "sql" / "schema.sql"
DB_PATH = BASE_DIR / "output" / "retail_dw.db"
LOG_PATH = BASE_DIR / "output" / "etl_log.txt"

DATE_FORMATS_TO_TRY = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]

log_lines = []


def log(msg):
    print(msg)
    log_lines.append(msg)


# ----------------------------------------------------------------
# EXTRACT
# ----------------------------------------------------------------
def extract(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    log(f"[EXTRACT] Read {len(rows)} raw rows from {path.name}")
    return rows


# ----------------------------------------------------------------
# TRANSFORM
# ----------------------------------------------------------------
def parse_date(value):
    for fmt in DATE_FORMATS_TO_TRY:
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def clean_text(value):
    if value is None:
        return ""
    return " ".join(value.strip().split())


def transform(rows):
    seen_txn_ids = set()
    cleaned = []
    dropped_duplicates = 0
    dropped_bad_rows = 0
    imputed_quantity = 0
    imputed_price = 0

    # For price imputation: compute average unit price per product first
    price_by_product = {}
    for r in rows:
        p = clean_text(r.get("product_name", ""))
        try:
            price = float(r["unit_price"])
            price_by_product.setdefault(p, []).append(price)
        except (ValueError, TypeError):
            continue
    avg_price_by_product = {
        p: sum(v) / len(v) for p, v in price_by_product.items() if v
    }

    for r in rows:
        txn_id = clean_text(r.get("transaction_id", ""))

        # Drop exact duplicate transaction IDs
        if txn_id in seen_txn_ids:
            dropped_duplicates += 1
            continue
        seen_txn_ids.add(txn_id)

        # Parse & standardize date
        parsed_date = parse_date(r.get("order_date", ""))
        if parsed_date is None:
            dropped_bad_rows += 1
            continue

        customer_name = clean_text(r.get("customer_name", "")).title()
        customer_email = clean_text(r.get("customer_email", "")).lower()
        if not customer_email:
            # deterministic fallback so the row still maps to a customer
            customer_email = customer_name.lower().replace(" ", ".") + "@unknown.local"

        product_name = clean_text(r.get("product_name", ""))
        category = clean_text(r.get("category", ""))
        store_id = clean_text(r.get("store_id", ""))
        city = clean_text(r.get("city", ""))

        # Quantity: impute missing with 1 (minimum viable order)
        qty_raw = clean_text(str(r.get("quantity", "")))
        if qty_raw == "" or not qty_raw.isdigit():
            quantity = 1
            imputed_quantity += 1
        else:
            quantity = int(qty_raw)

        # Unit price: impute missing with avg price for that product
        price_raw = clean_text(str(r.get("unit_price", "")))
        try:
            unit_price = float(price_raw)
        except ValueError:
            unit_price = round(avg_price_by_product.get(product_name, 0.0), 2)
            imputed_price += 1

        # Discount
        try:
            discount_pct = float(r.get("discount_pct", 0) or 0)
        except ValueError:
            discount_pct = 0.0

        # Standardize payment method casing (Title Case, dedupe "cash"/"Cash")
        payment_method = clean_text(r.get("payment_method", "")).title()

        gross_amount = round(quantity * unit_price, 2)
        discount_amount = round(gross_amount * discount_pct / 100, 2)
        net_amount = round(gross_amount - discount_amount, 2)

        cleaned.append({
            "transaction_id": txn_id,
            "order_date": parsed_date.strftime("%Y-%m-%d"),
            "customer_name": customer_name,
            "customer_email": customer_email,
            "product_name": product_name,
            "category": category,
            "store_id": store_id,
            "city": city,
            "quantity": quantity,
            "unit_price": round(unit_price, 2),
            "discount_pct": discount_pct,
            "payment_method": payment_method,
            "gross_amount": gross_amount,
            "discount_amount": discount_amount,
            "net_amount": net_amount,
        })

    log(f"[TRANSFORM] Dropped {dropped_duplicates} duplicate transactions")
    log(f"[TRANSFORM] Dropped {dropped_bad_rows} rows with unparseable dates")
    log(f"[TRANSFORM] Imputed quantity for {imputed_quantity} rows (default = 1)")
    log(f"[TRANSFORM] Imputed unit_price for {imputed_price} rows (avg product price)")
    log(f"[TRANSFORM] {len(cleaned)} clean rows ready to load")
    return cleaned


# ----------------------------------------------------------------
# LOAD
# ----------------------------------------------------------------
def build_schema(conn):
    with open(SCHEMA_SQL, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    log("[LOAD] Star schema created (dim_date, dim_product, dim_customer, dim_store, fact_sales)")


def load_dim_date(conn, cleaned_rows):
    unique_dates = sorted({r["order_date"] for r in cleaned_rows})
    for d in unique_dates:
        dt = datetime.strptime(d, "%Y-%m-%d")
        date_key = int(dt.strftime("%Y%m%d"))
        conn.execute(
            """INSERT OR IGNORE INTO dim_date
               (date_key, full_date, day, month, month_name, quarter, year, day_of_week, is_weekend)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                date_key, d, dt.day, dt.month, dt.strftime("%B"),
                (dt.month - 1) // 3 + 1, dt.year, dt.strftime("%A"),
                1 if dt.weekday() >= 5 else 0,
            ),
        )
    log(f"[LOAD] dim_date populated with {len(unique_dates)} unique dates")


def load_dim_product(conn, cleaned_rows):
    pairs = {(r["product_name"], r["category"]) for r in cleaned_rows}
    for name, cat in pairs:
        conn.execute(
            "INSERT OR IGNORE INTO dim_product (product_name, category) VALUES (?,?)",
            (name, cat),
        )
    log(f"[LOAD] dim_product populated with {len(pairs)} products")


def load_dim_customer(conn, cleaned_rows):
    customers = {}
    for r in cleaned_rows:
        customers[r["customer_email"]] = r["customer_name"]
    for email, name in customers.items():
        conn.execute(
            "INSERT OR IGNORE INTO dim_customer (customer_name, customer_email) VALUES (?,?)",
            (name, email),
        )
    log(f"[LOAD] dim_customer populated with {len(customers)} customers")


def load_dim_store(conn, cleaned_rows):
    stores = {}
    for r in cleaned_rows:
        stores[r["store_id"]] = r["city"]
    for store_id, city in stores.items():
        conn.execute(
            "INSERT OR IGNORE INTO dim_store (store_id, city) VALUES (?,?)",
            (store_id, city),
        )
    log(f"[LOAD] dim_store populated with {len(stores)} stores")


def load_fact_sales(conn, cleaned_rows):
    cur = conn.cursor()
    inserted = 0
    for r in cleaned_rows:
        date_key = int(datetime.strptime(r["order_date"], "%Y-%m-%d").strftime("%Y%m%d"))

        product_key = cur.execute(
            "SELECT product_key FROM dim_product WHERE product_name=? AND category=?",
            (r["product_name"], r["category"]),
        ).fetchone()[0]

        customer_key = cur.execute(
            "SELECT customer_key FROM dim_customer WHERE customer_email=?",
            (r["customer_email"],),
        ).fetchone()[0]

        store_key = cur.execute(
            "SELECT store_key FROM dim_store WHERE store_id=?",
            (r["store_id"],),
        ).fetchone()[0]

        cur.execute(
            """INSERT OR IGNORE INTO fact_sales
               (transaction_id, date_key, product_key, customer_key, store_key,
                payment_method, quantity, unit_price, discount_pct,
                gross_amount, discount_amount, net_amount)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                r["transaction_id"], date_key, product_key, customer_key, store_key,
                r["payment_method"], r["quantity"], r["unit_price"], r["discount_pct"],
                r["gross_amount"], r["discount_amount"], r["net_amount"],
            ),
        )
        inserted += 1
    conn.commit()
    log(f"[LOAD] fact_sales populated with {inserted} transactions")


def run():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    log(f"ETL run started: {datetime.now().isoformat(timespec='seconds')}")

    raw_rows = extract(RAW_CSV)
    clean_rows = transform(raw_rows)

    conn = sqlite3.connect(DB_PATH)
    build_schema(conn)
    load_dim_date(conn, clean_rows)
    load_dim_product(conn, clean_rows)
    load_dim_customer(conn, clean_rows)
    load_dim_store(conn, clean_rows)
    load_fact_sales(conn, clean_rows)

    # Quick sanity summary
    total_revenue = conn.execute("SELECT ROUND(SUM(net_amount),2) FROM fact_sales").fetchone()[0]
    total_txns = conn.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
    log(f"[SUMMARY] Total transactions loaded: {total_txns}")
    log(f"[SUMMARY] Total net revenue: {total_revenue}")

    conn.close()
    log(f"ETL run finished: {datetime.now().isoformat(timespec='seconds')}")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print(f"\nWarehouse written to: {DB_PATH}")
    print(f"Log written to: {LOG_PATH}")


if __name__ == "__main__":
    run()
