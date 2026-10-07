from typing import Dict
from sqlalchemy import text
from src.database import engine
from src.marts.sql_queries import (
    DAILY_SALES_SQL,
    STORE_SALES_SQL,
    PRODUCT_SALES_SQL,
    AVERAGE_CHECK_SQL,
    TOP_PRODUCTS_SQL,
    INVENTORY_BALANCE_SQL,
    CREATE_INDEXES_SQL
)


class MartBuilder:
    def __init__(self):
        self.marts = {
            "dm_daily_sales": DAILY_SALES_SQL,
            "dm_store_sales": STORE_SALES_SQL,
            "dm_product_sales": PRODUCT_SALES_SQL,
            "dm_average_check": AVERAGE_CHECK_SQL,
            "dm_top_products": TOP_PRODUCTS_SQL,
            "dm_inventory_balance": INVENTORY_BALANCE_SQL
        }

    def ensure_indexes(self) -> None:
        with engine.begin() as conn:
            for statement in CREATE_INDEXES_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))

    def build_mart(self, mart_name: str) -> int:
        query = self.marts.get(mart_name)
        if not query:
            raise ValueError(f"Unknown mart: {mart_name}")

        with engine.begin() as conn:
            for statement in query.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))

            count_res = conn.execute(text(f"SELECT COUNT(*) FROM marts.{mart_name}"))
            return count_res.scalar() or 0

    def build_all_marts(self) -> Dict[str, int]:
        results = {}
        for mart_name in self.marts:
            row_count = self.build_mart(mart_name)
            results[mart_name] = row_count
        self.ensure_indexes()
        return results
