import numpy as np
import pandas as pd
from src.transformers import (
    CustomersTransformer,
    InventoryTransformer,
    ProductsTransformer,
    SalesTransformer
)


def test_sales_transformer_cleaning_and_dedup():
    raw_df = pd.DataFrame([
        {
            "sale_id": "S1",
            "sale_date": "2026-01-01",
            "store_id": "STR_1",
            "product_id": "P1",
            "quantity": 2,
            "unit_price": 50.0,
            "discount": 0.1,
            "payment_method": "card",
            "updated_at": "2026-01-01T10:00:00"
        },
        {
            "sale_id": "S1",
            "sale_date": "2026-01-01",
            "store_id": "STR_1",
            "product_id": "P1",
            "quantity": 3,
            "unit_price": 50.0,
            "discount": 0.1,
            "payment_method": "cash",
            "updated_at": "2026-01-01T12:00:00"
        },
        {
            "sale_id": "S_BAD",
            "sale_date": "2026-01-01",
            "store_id": "STR_1",
            "product_id": "P1",
            "quantity": -1,
            "unit_price": 50.0,
            "discount": 0.0,
            "payment_method": "card",
            "updated_at": "2026-01-01T10:00:00"
        }
    ])

    transformer = SalesTransformer()
    res = transformer.transform(raw_df)

    assert res.input_count == 3
    assert res.duplicate_count == 1
    assert res.dropped_count == 1
    assert res.valid_count == 1

    clean_row = res.data.iloc[0]
    assert clean_row["sale_id"] == "S1"
    assert clean_row["quantity"] == 3
    assert clean_row["payment_method"] == "CASH"
    assert clean_row["total_amount"] == 135.0


def test_products_transformer_margin_and_cleaning():
    raw_df = pd.DataFrame([
        {
            "product_id": "P1",
            "product_name": "  laptop pro  ",
            "category": "electronics",
            "brand": "TechCo",
            "cost_price": 800.0,
            "retail_price": 1000.0,
            "updated_at": "2026-01-01T00:00:00"
        },
        {
            "product_id": "P2_INVALID",
            "product_name": "Free Item",
            "category": "promo",
            "cost_price": 10.0,
            "retail_price": -5.0,
            "updated_at": "2026-01-01T00:00:00"
        }
    ])

    transformer = ProductsTransformer()
    res = transformer.transform(raw_df)

    assert res.valid_count == 1
    assert res.dropped_count == 1
    clean_row = res.data.iloc[0]
    assert clean_row["product_name"] == "Laptop Pro"
    assert clean_row["category"] == "Electronics"
    assert clean_row["margin_amount"] == 200.0
    assert clean_row["margin_pct"] == 20.0


def test_customers_transformer_email_normalization():
    raw_df = pd.DataFrame([
        {
            "id": "C1",
            "first_name": "  john ",
            "last_name": " doe",
            "email": " JOHN.DOE@EXAMPLE.COM ",
            "city": "moscow",
            "updated_at": "2026-01-01T00:00:00"
        },
        {
            "id": "C2",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "invalid_email_format",
            "city": "kazan",
            "updated_at": "2026-01-01T00:00:00"
        }
    ])

    transformer = CustomersTransformer()
    res = transformer.transform(raw_df)

    assert res.valid_count == 2
    row1 = res.data[res.data["id"] == "C1"].iloc[0]
    assert row1["full_name"] == "John Doe"
    assert row1["email"] == "john.doe@example.com"
    assert row1["city"] == "Moscow"

    row2 = res.data[res.data["id"] == "C2"].iloc[0]
    assert pd.isna(row2["email"]) or row2["email"] is None


def test_inventory_transformer_bounds():
    raw_df = pd.DataFrame([
        {"store_id": "S1", "product_id": "P1", "quantity_on_hand": 20, "reorder_level": 5, "updated_at": "2026-01-01T00:00:00"},
        {"store_id": "S1", "product_id": "P2", "quantity_on_hand": -10, "reorder_level": 5, "updated_at": "2026-01-01T00:00:00"}
    ])

    transformer = InventoryTransformer()
    res = transformer.transform(raw_df)

    assert res.valid_count == 1
    assert res.dropped_count == 1
    assert res.data.iloc[0]["product_id"] == "P1"
