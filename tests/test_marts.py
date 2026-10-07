from sqlalchemy import text
from src.database import engine
from src.marts.mart_builder import MartBuilder


def test_mart_builder_execution():
    builder = MartBuilder()
    summary = builder.build_all_marts()

    for mart in [
        "dm_daily_sales",
        "dm_store_sales",
        "dm_product_sales",
        "dm_average_check",
        "dm_top_products",
        "dm_inventory_balance"
    ]:
        assert mart in summary
        assert summary[mart] > 0


def test_marts_window_functions_consistency():
    with engine.connect() as conn:
        daily_rows = conn.execute(text("""
            SELECT sale_date, total_revenue, running_monthly_revenue
            FROM marts.dm_daily_sales
            ORDER BY sale_date ASC
            LIMIT 5;
        """)).fetchall()
        assert len(daily_rows) > 0

        store_ranks = conn.execute(text("""
            SELECT store_id, total_revenue, revenue_rank
            FROM marts.dm_store_sales
            ORDER BY revenue_rank ASC;
        """)).fetchall()
        assert len(store_ranks) > 0
        assert store_ranks[0][2] == 1

        top_products = conn.execute(text("""
            SELECT category, product_id, rank_in_category
            FROM marts.dm_top_products
            WHERE rank_in_category = 1;
        """)).fetchall()
        assert len(top_products) > 0

        checks = conn.execute(text("""
            SELECT store_id, sale_date, avg_check_amount, store_overall_avg_check, check_deviation_from_avg
            FROM marts.dm_average_check
            LIMIT 5;
        """)).fetchall()
        assert len(checks) > 0

        inventory = conn.execute(text("""
            SELECT store_id, product_id, quantity_on_hand, stock_status, category_stock_rank
            FROM marts.dm_inventory_balance
            LIMIT 5;
        """)).fetchall()
        assert len(inventory) > 0
        assert inventory[0][3] in {"OUT_OF_STOCK", "CRITICAL_LOW", "OVERSTOCK", "OPTIMAL"}


def test_indexes_exist():
    with engine.connect() as conn:
        indexes = conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname IN ('core', 'marts');
        """)).scalars().all()

        expected = [
            "idx_fct_sales_date",
            "idx_fct_sales_store_date",
            "idx_fct_sales_prod",
            "idx_dm_daily_date",
            "idx_dm_store_rank",
            "idx_dm_top_cat"
        ]
        for exp in expected:
            assert exp in indexes
