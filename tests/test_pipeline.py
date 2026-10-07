from src.services.pipeline_service import PipelineService
from src.services.state_service import StateService


def test_pipeline_full_run():
    pipeline = PipelineService()
    result = pipeline.run(run_type="FULL")

    assert result["status"] == "SUCCESS"
    assert result["run_type"] == "FULL"
    assert result["rows_extracted"] > 0
    assert result["rows_loaded"] > 0
    assert result["duration_seconds"] >= 0

    assert "products_json" in result["source_metrics"]
    assert "sales_csv" in result["source_metrics"]
    assert "customers_postgres" in result["source_metrics"]
    assert "inventory_api" in result["source_metrics"]

    for mart_name in [
        "dm_daily_sales",
        "dm_store_sales",
        "dm_product_sales",
        "dm_average_check",
        "dm_top_products",
        "dm_inventory_balance"
    ]:
        assert mart_name in result["marts_summary"]
        assert result["marts_summary"][mart_name] > 0


def test_pipeline_incremental_run():
    state_service = StateService()
    pipeline = PipelineService()

    run1 = pipeline.run(run_type="INCREMENTAL")
    assert run1["status"] == "SUCCESS"

    run2 = pipeline.run(run_type="INCREMENTAL")
    assert run2["status"] == "SUCCESS"
    assert run2["rows_extracted"] <= run1["rows_extracted"]


def test_pipeline_history():
    pipeline = PipelineService()
    history = pipeline.get_run_history(limit=5)

    assert isinstance(history, list)
    assert len(history) > 0
    assert "run_id" in history[0]
    assert "status" in history[0]
