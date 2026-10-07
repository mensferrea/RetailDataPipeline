DAILY_SALES_SQL = """
CREATE TABLE IF NOT EXISTS marts.dm_daily_sales (
    sale_date DATE PRIMARY KEY,
    total_revenue NUMERIC(14, 2),
    total_orders INTEGER,
    total_items_sold INTEGER,
    unique_customers INTEGER,
    avg_order_value NUMERIC(10, 2),
    running_monthly_revenue NUMERIC(14, 2),
    prev_day_revenue NUMERIC(14, 2),
    dod_growth_pct NUMERIC(8, 2),
    refreshed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

TRUNCATE TABLE marts.dm_daily_sales;

WITH daily_base AS (
    SELECT 
        sale_date,
        ROUND(SUM(total_amount), 2) AS total_revenue,
        COUNT(DISTINCT sale_id) AS total_orders,
        SUM(quantity) AS total_items_sold,
        COUNT(DISTINCT customer_id) AS unique_customers,
        ROUND(SUM(total_amount) / NULLIF(COUNT(DISTINCT sale_id), 0), 2) AS avg_order_value
    FROM core.fct_sales
    GROUP BY sale_date
),
daily_with_windows AS (
    SELECT 
        sale_date,
        total_revenue,
        total_orders,
        total_items_sold,
        unique_customers,
        avg_order_value,
        SUM(total_revenue) OVER (
            PARTITION BY DATE_TRUNC('month', sale_date)
            ORDER BY sale_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_monthly_revenue,
        LAG(total_revenue, 1) OVER (
            ORDER BY sale_date
        ) AS prev_day_revenue
    FROM daily_base
)
INSERT INTO marts.dm_daily_sales (
    sale_date,
    total_revenue,
    total_orders,
    total_items_sold,
    unique_customers,
    avg_order_value,
    running_monthly_revenue,
    prev_day_revenue,
    dod_growth_pct
)
SELECT 
    sale_date,
    total_revenue,
    total_orders,
    total_items_sold,
    unique_customers,
    avg_order_value,
    running_monthly_revenue,
    prev_day_revenue,
    CASE 
        WHEN prev_day_revenue IS NOT NULL AND prev_day_revenue > 0 
        THEN ROUND(((total_revenue - prev_day_revenue) / prev_day_revenue) * 100.0, 2)
        ELSE 0.0
    END AS dod_growth_pct
FROM daily_with_windows
ORDER BY sale_date ASC;
"""

STORE_SALES_SQL = """
CREATE TABLE IF NOT EXISTS marts.dm_store_sales (
    store_id VARCHAR(64) PRIMARY KEY,
    store_name VARCHAR(100),
    city VARCHAR(100),
    total_revenue NUMERIC(14, 2),
    total_profit NUMERIC(14, 2),
    orders_count INTEGER,
    items_sold INTEGER,
    avg_order_value NUMERIC(10, 2),
    revenue_rank INTEGER,
    store_revenue_share_pct NUMERIC(6, 2),
    refreshed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

TRUNCATE TABLE marts.dm_store_sales;

WITH store_aggregated AS (
    SELECT 
        s.store_id,
        COALESCE(st.store_name, 'Store ' || s.store_id) AS store_name,
        COALESCE(st.city, 'Unknown') AS city,
        ROUND(SUM(s.total_amount), 2) AS total_revenue,
        ROUND(SUM(s.profit_amount), 2) AS total_profit,
        COUNT(DISTINCT s.sale_id) AS orders_count,
        SUM(s.quantity) AS items_sold,
        ROUND(SUM(s.total_amount) / NULLIF(COUNT(DISTINCT s.sale_id), 0), 2) AS avg_order_value
    FROM core.fct_sales s
    LEFT JOIN core.dim_stores st ON s.store_id = st.store_id
    GROUP BY s.store_id, st.store_name, st.city
)
INSERT INTO marts.dm_store_sales (
    store_id,
    store_name,
    city,
    total_revenue,
    total_profit,
    orders_count,
    items_sold,
    avg_order_value,
    revenue_rank,
    store_revenue_share_pct
)
SELECT 
    store_id,
    store_name,
    city,
    total_revenue,
    total_profit,
    orders_count,
    items_sold,
    avg_order_value,
    DENSE_RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank,
    ROUND(100.0 * total_revenue / NULLIF(SUM(total_revenue) OVER (), 0), 2) AS store_revenue_share_pct
FROM store_aggregated
ORDER BY total_revenue DESC;
"""

PRODUCT_SALES_SQL = """
CREATE TABLE IF NOT EXISTS marts.dm_product_sales (
    product_id VARCHAR(64) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(100),
    brand VARCHAR(100),
    units_sold INTEGER,
    total_revenue NUMERIC(14, 2),
    total_cost NUMERIC(14, 2),
    total_profit NUMERIC(14, 2),
    profit_margin_pct NUMERIC(6, 2),
    category_rank INTEGER,
    category_revenue_share_pct NUMERIC(6, 2),
    refreshed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

TRUNCATE TABLE marts.dm_product_sales;

WITH product_aggregated AS (
    SELECT 
        s.product_id,
        COALESCE(p.product_name, 'Unknown Product') AS product_name,
        COALESCE(p.category, 'General') AS category,
        COALESCE(p.brand, 'Generic') AS brand,
        SUM(s.quantity) AS units_sold,
        ROUND(SUM(s.total_amount), 2) AS total_revenue,
        ROUND(SUM(s.cost_amount), 2) AS total_cost,
        ROUND(SUM(s.profit_amount), 2) AS total_profit,
        CASE 
            WHEN SUM(s.total_amount) > 0 
            THEN ROUND((SUM(s.profit_amount) / SUM(s.total_amount)) * 100.0, 2)
            ELSE 0.0
        END AS profit_margin_pct
    FROM core.fct_sales s
    LEFT JOIN core.dim_products p ON s.product_id = p.product_id
    GROUP BY s.product_id, p.product_name, p.category, p.brand
)
INSERT INTO marts.dm_product_sales (
    product_id,
    product_name,
    category,
    brand,
    units_sold,
    total_revenue,
    total_cost,
    total_profit,
    profit_margin_pct,
    category_rank,
    category_revenue_share_pct
)
SELECT 
    product_id,
    product_name,
    category,
    brand,
    units_sold,
    total_revenue,
    total_cost,
    total_profit,
    profit_margin_pct,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS category_rank,
    ROUND(100.0 * total_revenue / NULLIF(SUM(total_revenue) OVER (PARTITION BY category), 0), 2) AS category_revenue_share_pct
FROM product_aggregated
ORDER BY category ASC, total_revenue DESC;
"""

AVERAGE_CHECK_SQL = """
CREATE TABLE IF NOT EXISTS marts.dm_average_check (
    id SERIAL PRIMARY KEY,
    store_id VARCHAR(64),
    sale_date DATE,
    orders_count INTEGER,
    avg_check_amount NUMERIC(10, 2),
    min_check_amount NUMERIC(10, 2),
    max_check_amount NUMERIC(10, 2),
    store_overall_avg_check NUMERIC(10, 2),
    check_deviation_from_avg NUMERIC(10, 2),
    refreshed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

TRUNCATE TABLE marts.dm_average_check;

WITH order_totals AS (
    SELECT 
        store_id,
        sale_date,
        sale_id,
        SUM(total_amount) AS basket_amount
    FROM core.fct_sales
    GROUP BY store_id, sale_date, sale_id
),
daily_store_checks AS (
    SELECT 
        store_id,
        sale_date,
        COUNT(sale_id) AS orders_count,
        ROUND(AVG(basket_amount), 2) AS avg_check_amount,
        ROUND(MIN(basket_amount), 2) AS min_check_amount,
        ROUND(MAX(basket_amount), 2) AS max_check_amount
    FROM order_totals
    GROUP BY store_id, sale_date
)
INSERT INTO marts.dm_average_check (
    store_id,
    sale_date,
    orders_count,
    avg_check_amount,
    min_check_amount,
    max_check_amount,
    store_overall_avg_check,
    check_deviation_from_avg
)
SELECT 
    store_id,
    sale_date,
    orders_count,
    avg_check_amount,
    min_check_amount,
    max_check_amount,
    ROUND(AVG(avg_check_amount) OVER (PARTITION BY store_id), 2) AS store_overall_avg_check,
    ROUND(avg_check_amount - AVG(avg_check_amount) OVER (PARTITION BY store_id), 2) AS check_deviation_from_avg
FROM daily_store_checks
ORDER BY store_id ASC, sale_date ASC;
"""

TOP_PRODUCTS_SQL = """
CREATE TABLE IF NOT EXISTS marts.dm_top_products (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100),
    product_id VARCHAR(64),
    product_name VARCHAR(255),
    units_sold INTEGER,
    total_revenue NUMERIC(14, 2),
    rank_in_category INTEGER,
    overall_rank INTEGER,
    refreshed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

TRUNCATE TABLE marts.dm_top_products;

WITH product_totals AS (
    SELECT 
        COALESCE(p.category, 'General') AS category,
        s.product_id,
        COALESCE(p.product_name, 'Product ' || s.product_id) AS product_name,
        SUM(s.quantity) AS units_sold,
        ROUND(SUM(s.total_amount), 2) AS total_revenue
    FROM core.fct_sales s
    LEFT JOIN core.dim_products p ON s.product_id = p.product_id
    GROUP BY p.category, s.product_id, p.product_name
),
ranked_products AS (
    SELECT 
        category,
        product_id,
        product_name,
        units_sold,
        total_revenue,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rank_in_category,
        DENSE_RANK() OVER (ORDER BY total_revenue DESC) AS overall_rank
    FROM product_totals
)
INSERT INTO marts.dm_top_products (
    category,
    product_id,
    product_name,
    units_sold,
    total_revenue,
    rank_in_category,
    overall_rank
)
SELECT 
    category,
    product_id,
    product_name,
    units_sold,
    total_revenue,
    rank_in_category,
    overall_rank
FROM ranked_products
WHERE rank_in_category <= 5
ORDER BY category ASC, rank_in_category ASC;
"""

INVENTORY_BALANCE_SQL = """
CREATE TABLE IF NOT EXISTS marts.dm_inventory_balance (
    store_id VARCHAR(64),
    store_name VARCHAR(100),
    product_id VARCHAR(64),
    product_name VARCHAR(255),
    category VARCHAR(100),
    quantity_on_hand INTEGER,
    reorder_level INTEGER,
    avg_daily_sales_30d NUMERIC(8, 2),
    days_of_stock_remaining NUMERIC(8, 1),
    stock_status VARCHAR(32),
    category_stock_rank INTEGER,
    refreshed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    PRIMARY KEY (store_id, product_id)
);

TRUNCATE TABLE marts.dm_inventory_balance;

WITH latest_inventory AS (
    SELECT DISTINCT ON (store_id, product_id)
        store_id,
        product_id,
        quantity_on_hand,
        reorder_level,
        last_restock_date,
        snapshot_date
    FROM core.fct_inventory_snapshots
    ORDER BY store_id, product_id, snapshot_date DESC, snapshot_key DESC
),
recent_sales_velocity AS (
    SELECT 
        store_id,
        product_id,
        ROUND(COALESCE(SUM(quantity), 0) / 30.0, 2) AS avg_daily_sales
    FROM core.fct_sales
    WHERE sale_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY store_id, product_id
),
inventory_enriched AS (
    SELECT 
        inv.store_id,
        COALESCE(st.store_name, 'Store ' || inv.store_id) AS store_name,
        inv.product_id,
        COALESCE(p.product_name, 'Product ' || inv.product_id) AS product_name,
        COALESCE(p.category, 'General') AS category,
        inv.quantity_on_hand,
        inv.reorder_level,
        COALESCE(vel.avg_daily_sales, 0.0) AS avg_daily_sales_30d,
        CASE 
            WHEN COALESCE(vel.avg_daily_sales, 0.0) > 0 
            THEN ROUND(inv.quantity_on_hand / vel.avg_daily_sales, 1)
            ELSE 999.0
        END AS days_of_stock_remaining,
        CASE 
            WHEN inv.quantity_on_hand <= 0 THEN 'OUT_OF_STOCK'
            WHEN inv.quantity_on_hand <= inv.reorder_level THEN 'CRITICAL_LOW'
            WHEN COALESCE(vel.avg_daily_sales, 0.0) > 0 AND (inv.quantity_on_hand / vel.avg_daily_sales) > 90.0 THEN 'OVERSTOCK'
            ELSE 'OPTIMAL'
        END AS stock_status,
        RANK() OVER (PARTITION BY COALESCE(p.category, 'General') ORDER BY inv.quantity_on_hand DESC) AS category_stock_rank
    FROM latest_inventory inv
    LEFT JOIN core.dim_stores st ON inv.store_id = st.store_id
    LEFT JOIN core.dim_products p ON inv.product_id = p.product_id
    LEFT JOIN recent_sales_velocity vel ON inv.store_id = vel.store_id AND inv.product_id = vel.product_id
)
INSERT INTO marts.dm_inventory_balance (
    store_id,
    store_name,
    product_id,
    product_name,
    category,
    quantity_on_hand,
    reorder_level,
    avg_daily_sales_30d,
    days_of_stock_remaining,
    stock_status,
    category_stock_rank
)
SELECT 
    store_id,
    store_name,
    product_id,
    product_name,
    category,
    quantity_on_hand,
    reorder_level,
    avg_daily_sales_30d,
    days_of_stock_remaining,
    stock_status,
    category_stock_rank
FROM inventory_enriched
ORDER BY category ASC, quantity_on_hand ASC;
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_fct_sales_date ON core.fct_sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_fct_sales_store_date ON core.fct_sales(store_id, sale_date);
CREATE INDEX IF NOT EXISTS idx_fct_sales_prod ON core.fct_sales(product_id);
CREATE INDEX IF NOT EXISTS idx_fct_sales_cust ON core.fct_sales(customer_id);

CREATE INDEX IF NOT EXISTS idx_dm_daily_date ON marts.dm_daily_sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_dm_store_rank ON marts.dm_store_sales(revenue_rank);
CREATE INDEX IF NOT EXISTS idx_dm_prod_cat_rank ON marts.dm_product_sales(category, category_rank);
CREATE INDEX IF NOT EXISTS idx_dm_top_cat ON marts.dm_top_products(category, rank_in_category);
CREATE INDEX IF NOT EXISTS idx_dm_inv_status ON marts.dm_inventory_balance(stock_status);
"""
