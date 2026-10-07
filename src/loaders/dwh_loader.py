from datetime import datetime, timezone
from typing import Any, Dict
import pandas as pd
from sqlalchemy import text
from src.database import engine

STAGING_COLUMNS = {
    "sales_csv": [
        "sale_id", "sale_date", "store_id", "product_id", "customer_id",
        "quantity", "unit_price", "discount", "total_amount", "payment_method",
        "updated_at", "loaded_at"
    ],
    "products_json": [
        "product_id", "product_name", "category", "brand", "cost_price",
        "retail_price", "is_active", "updated_at", "loaded_at"
    ],
    "customers_postgres": [
        "id", "first_name", "last_name", "email", "phone", "city",
        "loyalty_tier", "created_at", "updated_at", "loaded_at"
    ],
    "inventory_api": [
        "store_id", "product_id", "quantity_on_hand", "reorder_level",
        "last_restock_date", "updated_at", "loaded_at"
    ]
}


class DwhLoader:
    def load_staging(self, source_name: str, df: pd.DataFrame) -> int:
        if df.empty:
            return 0

        target_tables = {
            "sales_csv": "staging.stg_sales",
            "products_json": "staging.stg_products",
            "customers_postgres": "staging.stg_customers",
            "inventory_api": "staging.stg_inventory"
        }

        table_name = target_tables.get(source_name)
        if not table_name:
            raise ValueError(f"Unknown source name: {source_name}")

        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table_name};"))

        schema, table = table_name.split(".")
        df_to_load = df.copy()
        df_to_load["loaded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

        allowed_cols = [c for c in STAGING_COLUMNS[source_name] if c in df_to_load.columns]
        df_to_load = df_to_load[allowed_cols]

        df_to_load.to_sql(
            name=table,
            schema=schema,
            con=engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000
        )
        return len(df_to_load)

    def merge_customers_to_core(self) -> int:
        merge_sql = """
            INSERT INTO core.dim_customers (customer_id, full_name, email, phone, city, loyalty_tier, created_at, updated_at)
            SELECT 
                s.id,
                s.first_name || ' ' || s.last_name,
                s.email,
                s.phone,
                s.city,
                s.loyalty_tier,
                s.created_at,
                s.updated_at
            FROM staging.stg_customers s
            ON CONFLICT (customer_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                email = EXCLUDED.email,
                phone = EXCLUDED.phone,
                city = EXCLUDED.city,
                loyalty_tier = EXCLUDED.loyalty_tier,
                updated_at = EXCLUDED.updated_at;
        """
        with engine.begin() as conn:
            res = conn.execute(text(merge_sql))
            return res.rowcount

    def merge_products_to_core(self) -> int:
        merge_sql = """
            INSERT INTO core.dim_products (
                product_id, product_name, category, brand, cost_price, retail_price, margin_amount, margin_pct, is_active, updated_at
            )
            SELECT 
                s.product_id,
                s.product_name,
                s.category,
                s.brand,
                s.cost_price,
                s.retail_price,
                ROUND(s.retail_price - s.cost_price, 2) AS margin_amount,
                CASE 
                    WHEN s.retail_price > 0 THEN ROUND(((s.retail_price - s.cost_price) / s.retail_price) * 100.0, 2)
                    ELSE 0.0
                END AS margin_pct,
                s.is_active,
                s.updated_at
            FROM staging.stg_products s
            ON CONFLICT (product_id) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                brand = EXCLUDED.brand,
                cost_price = EXCLUDED.cost_price,
                retail_price = EXCLUDED.retail_price,
                margin_amount = EXCLUDED.margin_amount,
                margin_pct = EXCLUDED.margin_pct,
                is_active = EXCLUDED.is_active,
                updated_at = EXCLUDED.updated_at;
        """
        with engine.begin() as conn:
            res = conn.execute(text(merge_sql))
            return res.rowcount

    def merge_stores_to_core(self) -> int:
        merge_sql = """
            INSERT INTO core.dim_stores (store_id, store_name, city, region)
            SELECT DISTINCT
                store_id,
                'Store ' || store_id AS store_name,
                'Central City' AS city,
                'Central Region' AS region
            FROM (
                SELECT store_id FROM staging.stg_sales
                UNION
                SELECT store_id FROM staging.stg_inventory
            ) stores
            ON CONFLICT (store_id) DO NOTHING;
        """
        with engine.begin() as conn:
            res = conn.execute(text(merge_sql))
            return res.rowcount

    def merge_sales_to_core(self) -> int:
        merge_sql = """
            INSERT INTO core.fct_sales (
                sale_id, sale_date, store_id, product_id, customer_id, quantity, unit_price,
                discount, total_amount, cost_amount, profit_amount, payment_method, updated_at
            )
            SELECT 
                s.sale_id,
                s.sale_date,
                s.store_id,
                s.product_id,
                s.customer_id,
                s.quantity,
                s.unit_price,
                s.discount,
                s.total_amount,
                ROUND(s.quantity * COALESCE(p.cost_price, s.unit_price * 0.7), 2) AS cost_amount,
                ROUND(s.total_amount - (s.quantity * COALESCE(p.cost_price, s.unit_price * 0.7)), 2) AS profit_amount,
                s.payment_method,
                s.updated_at
            FROM staging.stg_sales s
            LEFT JOIN core.dim_products p ON s.product_id = p.product_id
            ON CONFLICT (sale_id) DO UPDATE SET
                sale_date = EXCLUDED.sale_date,
                store_id = EXCLUDED.store_id,
                product_id = EXCLUDED.product_id,
                customer_id = EXCLUDED.customer_id,
                quantity = EXCLUDED.quantity,
                unit_price = EXCLUDED.unit_price,
                discount = EXCLUDED.discount,
                total_amount = EXCLUDED.total_amount,
                cost_amount = EXCLUDED.cost_amount,
                profit_amount = EXCLUDED.profit_amount,
                payment_method = EXCLUDED.payment_method,
                updated_at = EXCLUDED.updated_at;
        """
        with engine.begin() as conn:
            res = conn.execute(text(merge_sql))
            return res.rowcount

    def load_inventory_snapshots(self) -> int:
        merge_sql = """
            INSERT INTO core.fct_inventory_snapshots (
                store_id, product_id, quantity_on_hand, reorder_level, last_restock_date, snapshot_date, updated_at
            )
            SELECT 
                store_id,
                product_id,
                quantity_on_hand,
                reorder_level,
                last_restock_date,
                CURRENT_DATE,
                updated_at
            FROM staging.stg_inventory;
        """
        with engine.begin() as conn:
            res = conn.execute(text(merge_sql))
            return res.rowcount
