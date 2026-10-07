from typing import Any, Dict, List
from fastapi import APIRouter, Query
from sqlalchemy import text
from src.database import engine

router = APIRouter(prefix="/marts", tags=["Data Marts"])


def _fetch_mart(table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    query = text(f"SELECT * FROM marts.{table_name} LIMIT :lim;")
    with engine.connect() as conn:
        rows = conn.execute(query, {"lim": limit}).mappings().all()
        return [dict(r) for r in rows]


@router.get("/daily-sales")
def get_daily_sales(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return _fetch_mart("dm_daily_sales", limit)


@router.get("/store-sales")
def get_store_sales(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return _fetch_mart("dm_store_sales", limit)


@router.get("/product-sales")
def get_product_sales(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return _fetch_mart("dm_product_sales", limit)


@router.get("/average-check")
def get_average_check(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return _fetch_mart("dm_average_check", limit)


@router.get("/top-products")
def get_top_products(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return _fetch_mart("dm_top_products", limit)


@router.get("/inventory-balance")
def get_inventory_balance(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return _fetch_mart("dm_inventory_balance", limit)
