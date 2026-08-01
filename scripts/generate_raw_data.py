"""
generate_raw_data.py
---------------------
Simulates a messy raw export from a retail POS / e-commerce system.
This is the "source data" that the ETL pipeline will extract from.
Intentionally includes real-world data quality issues:
 - inconsistent date formats
 - missing values (nulls)
 - duplicate transactions
 - inconsistent text casing / whitespace
 - mixed currency formatting
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

OUT_PATH = "/home/claude/retail_dw_project/data/raw_sales_data.csv"

# ---- Reference lists ----
CATEGORIES = {
    "Electronics": ["Wireless Mouse", "Bluetooth Speaker", "USB-C Cable", "Laptop Stand", "Webcam HD"],
    "Apparel": ["Cotton T-Shirt", "Denim Jacket", "Running Shoes", "Wool Sweater", "Sports Cap"],
    "Home & Kitchen": ["Non-Stick Pan", "Coffee Maker", "LED Desk Lamp", "Ceramic Mug Set", "Blender"],
    "Beauty": ["Face Moisturizer", "Shampoo 500ml", "Lip Balm", "Sunscreen SPF50", "Hair Dryer"],
    "Sports": ["Yoga Mat", "Dumbbell Set", "Cycling Helmet", "Football", "Resistance Bands"],
}

CITIES_STORES = [
    ("Lahore", "LHR-01"), ("Lahore", "LHR-02"), ("Karachi", "KHI-01"),
    ("Karachi", "KHI-02"), ("Islamabad", "ISB-01"), ("Faisalabad", "FSD-01"),
    ("Multan", "MUL-01"), ("Peshawar", "PSH-01"),
]

FIRST_NAMES = ["Ali", "Ahmed", "Sara", "Fatima", "Bilal", "Hina", "Usman", "Ayesha",
               "Hassan", "Zainab", "Omar", "Mariam", "Faisal", "Noor", "Kamran", "Sana"]
LAST_NAMES = ["Khan", "Malik", "Sheikh", "Butt", "Chaudhry", "Raza", "Iqbal", "Farooq"]

PAYMENT_METHODS = ["Credit Card", "Cash", "Debit Card", "Mobile Wallet", "cash", "CREDIT CARD"]

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]


def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def make_row(txn_id):
    category = random.choice(list(CATEGORIES.keys()))
    product = random.choice(CATEGORIES[category])
    city, store_id = random.choice(CITIES_STORES)
    customer_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

    # inconsistent casing sometimes
    if random.random() < 0.15:
        customer_name = customer_name.upper()
    if random.random() < 0.1:
        customer_name = "  " + customer_name + "  "  # stray whitespace

    order_date = random_date(datetime(2024, 1, 1), datetime(2026, 7, 31))
    date_fmt = random.choice(DATE_FORMATS)
    order_date_str = order_date.strftime(date_fmt)

    unit_price = round(random.uniform(5, 250), 2)
    quantity = random.randint(1, 6)

    # occasionally missing quantity or price (data quality issue)
    if random.random() < 0.03:
        quantity = ""
    if random.random() < 0.02:
        unit_price = ""

    discount_pct = random.choice([0, 0, 0, 5, 10, 15, 20])

    payment = random.choice(PAYMENT_METHODS)

    # occasionally missing customer email
    email_user = customer_name.strip().lower().replace(" ", ".")
    email = f"{email_user}@example.com" if random.random() > 0.05 else ""

    return {
        "transaction_id": f"TXN{txn_id:06d}",
        "order_date": order_date_str,
        "customer_name": customer_name,
        "customer_email": email,
        "product_name": product,
        "category": category,
        "store_id": store_id,
        "city": city,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_pct": discount_pct,
        "payment_method": payment,
    }


def main():
    rows = []
    n_transactions = 5000
    for i in range(1, n_transactions + 1):
        rows.append(make_row(i))

    # inject some exact duplicate rows (common ETL issue)
    duplicates = random.sample(rows, 60)
    rows.extend(duplicates)

    random.shuffle(rows)

    fieldnames = list(rows[0].keys())
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} raw rows -> {OUT_PATH}")


if __name__ == "__main__":
    main()
