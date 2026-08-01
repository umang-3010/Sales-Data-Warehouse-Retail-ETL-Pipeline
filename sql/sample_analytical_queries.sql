-- ============================================================
-- Sample analytical queries against the retail star schema
-- Run against output/retail_dw.db
-- ============================================================

-- 1. Monthly revenue & order trend
SELECT d.year, d.month, d.month_name,
       ROUND(SUM(f.net_amount), 2) AS revenue,
       COUNT(*) AS orders
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 2. Top 10 products by revenue
SELECT p.product_name, p.category,
       ROUND(SUM(f.net_amount), 2) AS revenue,
       SUM(f.quantity) AS units_sold
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;

-- 3. Revenue & order count by store / city
SELECT s.city, s.store_id,
       ROUND(SUM(f.net_amount), 2) AS revenue,
       COUNT(*) AS orders,
       ROUND(AVG(f.net_amount), 2) AS avg_order_value
FROM fact_sales f
JOIN dim_store s ON f.store_key = s.store_key
GROUP BY s.city, s.store_id
ORDER BY revenue DESC;

-- 4. Top customers by lifetime spend
SELECT c.customer_name, c.customer_email,
       COUNT(*) AS total_orders,
       ROUND(SUM(f.net_amount), 2) AS lifetime_value
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.customer_name, c.customer_email
ORDER BY lifetime_value DESC
LIMIT 10;

-- 5. Weekend vs weekday sales performance
SELECT CASE WHEN d.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       ROUND(SUM(f.net_amount), 2) AS revenue,
       COUNT(*) AS orders,
       ROUND(AVG(f.net_amount), 2) AS avg_order_value
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY day_type;

-- 6. Category performance by quarter
SELECT d.year, d.quarter, p.category,
       ROUND(SUM(f.net_amount), 2) AS revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY d.year, d.quarter, p.category
ORDER BY d.year, d.quarter, revenue DESC;

-- 7. Discount impact analysis
SELECT
    CASE WHEN discount_pct = 0 THEN 'No Discount' ELSE 'Discounted' END AS discount_flag,
    COUNT(*) AS orders,
    ROUND(AVG(net_amount), 2) AS avg_order_value,
    ROUND(SUM(discount_amount), 2) AS total_discount_given
FROM fact_sales
GROUP BY discount_flag;

-- 8. Payment method preference by city
SELECT s.city, f.payment_method,
       COUNT(*) AS orders,
       ROUND(SUM(f.net_amount), 2) AS revenue
FROM fact_sales f
JOIN dim_store s ON f.store_key = s.store_key
GROUP BY s.city, f.payment_method
ORDER BY s.city, revenue DESC;
