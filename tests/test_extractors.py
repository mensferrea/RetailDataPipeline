from datetime import datetime, timedelta
import pandas as pd
import pytest
from src.extractors import (
    BaseExtractor,
    CsvSalesExtractor,
    JsonProductsExtractor,
    PostgresCustomersExtractor,
    RestInventoryExtractor
)


def test_csv_extractor_reads_file(tmp_path):
    csv_file = tmp_path / "test_sales.csv"
    df = pd.DataFrame([
        {"sale_id": "S1", "sale_date": "2026-01-01", "store_id": "STR_1", "product_id": "P1", "quantity": 1, "unit_price": 10.0, "updated_at": "2026-01-01T10:00:00"},
        {"sale_id": "S2", "sale_date": "2026-01-02", "store_id": "STR_1", "product_id": "P2", "quantity": 2, "unit_price": 20.0, "updated_at": "2026-01-02T10:00:00"}
    ])
    df.to_csv(csv_file, index=False)

    extractor = CsvSalesExtractor(file_path=csv_file)
    result = extractor.extract()

    assert result.rows_extracted == 2
    assert len(result.data) == 2


def test_csv_extractor_incremental_filtering(tmp_path):
    csv_file = tmp_path / "test_sales.csv"
    df = pd.DataFrame([
        {"sale_id": "S1", "sale_date": "2026-01-01", "store_id": "STR_1", "product_id": "P1", "quantity": 1, "unit_price": 10.0, "updated_at": "2026-01-01T10:00:00"},
        {"sale_id": "S2", "sale_date": "2026-01-02", "store_id": "STR_1", "product_id": "P2", "quantity": 2, "unit_price": 20.0, "updated_at": "2026-01-05T10:00:00"}
    ])
    df.to_csv(csv_file, index=False)

    extractor = CsvSalesExtractor(file_path=csv_file)
    checkpoint = datetime(2026, 1, 3, 0, 0, 0)
    result = extractor.extract(checkpoint=checkpoint)

    assert result.rows_extracted == 1
    assert result.data.iloc[0]["sale_id"] == "S2"


def test_json_extractor_reads_file(tmp_path):
    json_file = tmp_path / "products.json"
    import json
    data = {
        "products": [
            {"product_id": "P1", "product_name": "Product 1", "category": "Cat 1", "retail_price": 50.0, "updated_at": "2026-01-01T00:00:00"}
        ]
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    extractor = JsonProductsExtractor(file_path=json_file)
    result = extractor.extract()

    assert result.rows_extracted == 1
    assert result.data.iloc[0]["product_id"] == "P1"


def test_postgres_extractor():
    extractor = PostgresCustomersExtractor()
    result = extractor.extract()

    assert result.rows_extracted >= 0
    assert "customers_postgres" in result.source_name


def test_rest_extractor_with_mock_provider():
    def mock_provider(chk):
        return [
            {"store_id": "STR_01", "product_id": "PRD_001", "quantity_on_hand": 50, "reorder_level": 10, "updated_at": "2026-01-01T00:00:00"}
        ]

    extractor = RestInventoryExtractor(mock_data_provider=mock_provider)
    result = extractor.extract()

    assert result.rows_extracted == 1
    assert result.data.iloc[0]["quantity_on_hand"] == 50


def test_extractor_retry_mechanism():
    class FailingExtractor(BaseExtractor):
        def __init__(self):
            super().__init__(name="failing_test", max_retries=2, retry_delay=0.01)
            self.attempts = 0

        def extract(self, checkpoint=None):
            def _op():
                self.attempts += 1
                if self.attempts < 2:
                    raise ConnectionError("Network issue")
                return pd.DataFrame([{"id": 1}])
            df = self._execute_with_retry(_op)
            return self.ExtractionResult(name="failing_test", data=df, rows_extracted=len(df))

    extractor = FailingExtractor()
    def _run():
        extractor.attempts += 1
        if extractor.attempts < 2:
            raise ConnectionError("Temporary failure")
        return pd.DataFrame([{"id": 1}])

    df = extractor._execute_with_retry(_run)
    assert len(df) == 1
    assert extractor.attempts == 2
