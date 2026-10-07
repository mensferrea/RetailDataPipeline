from datetime import date, datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Date,
    DateTime,
    Boolean,
    Index,
    JSON,
    Text
)
from src.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SourceCustomer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "source_crm"}

    id = Column(String(64), primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    city = Column(String(100))
    loyalty_tier = Column(String(50), default="Standard")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, index=True)


class StgSale(Base):
    __tablename__ = "stg_sales"
    __table_args__ = {"schema": "staging"}

    sale_id = Column(String(64), primary_key=True)
    sale_date = Column(Date, nullable=False)
    store_id = Column(String(64), nullable=False)
    product_id = Column(String(64), nullable=False)
    customer_id = Column(String(64), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(5, 2), default=0.0)
    total_amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    updated_at = Column(DateTime, nullable=False)
    loaded_at = Column(DateTime, default=utc_now)


class StgProduct(Base):
    __tablename__ = "stg_products"
    __table_args__ = {"schema": "staging"}

    product_id = Column(String(64), primary_key=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    brand = Column(String(100))
    cost_price = Column(Numeric(12, 2), nullable=False)
    retail_price = Column(Numeric(12, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, nullable=False)
    loaded_at = Column(DateTime, default=utc_now)


class StgCustomer(Base):
    __tablename__ = "stg_customers"
    __table_args__ = {"schema": "staging"}

    id = Column(String(64), primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    city = Column(String(100))
    loyalty_tier = Column(String(50))
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    loaded_at = Column(DateTime, default=utc_now)


class StgInventory(Base):
    __tablename__ = "stg_inventory"
    __table_args__ = {"schema": "staging"}

    store_id = Column(String(64), primary_key=True)
    product_id = Column(String(64), primary_key=True)
    quantity_on_hand = Column(Integer, nullable=False)
    reorder_level = Column(Integer, nullable=False)
    last_restock_date = Column(Date)
    updated_at = Column(DateTime, nullable=False)
    loaded_at = Column(DateTime, default=utc_now)


class DimCustomer(Base):
    __tablename__ = "dim_customers"
    __table_args__ = {"schema": "core"}

    customer_key = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(64), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    city = Column(String(100))
    loyalty_tier = Column(String(50))
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class DimProduct(Base):
    __tablename__ = "dim_products"
    __table_args__ = {"schema": "core"}

    product_key = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(64), unique=True, nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    brand = Column(String(100))
    cost_price = Column(Numeric(12, 2), nullable=False)
    retail_price = Column(Numeric(12, 2), nullable=False)
    margin_amount = Column(Numeric(12, 2), nullable=False)
    margin_pct = Column(Numeric(5, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, nullable=False)


class DimStore(Base):
    __tablename__ = "dim_stores"
    __table_args__ = {"schema": "core"}

    store_key = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(String(64), unique=True, nullable=False, index=True)
    store_name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    region = Column(String(100), nullable=False)


class FctSale(Base):
    __tablename__ = "fct_sales"
    __table_args__ = (
        Index("idx_fct_sales_date", "sale_date"),
        Index("idx_fct_sales_store_date", "store_id", "sale_date"),
        Index("idx_fct_sales_product", "product_id"),
        Index("idx_fct_sales_customer", "customer_id"),
        {"schema": "core"}
    )

    sale_key = Column(Integer, primary_key=True, autoincrement=True)
    sale_id = Column(String(64), unique=True, nullable=False)
    sale_date = Column(Date, nullable=False)
    store_id = Column(String(64), nullable=False)
    product_id = Column(String(64), nullable=False)
    customer_id = Column(String(64), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount = Column(Numeric(5, 2), default=0.0)
    total_amount = Column(Numeric(12, 2), nullable=False)
    cost_amount = Column(Numeric(12, 2), nullable=False)
    profit_amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    updated_at = Column(DateTime, nullable=False)


class FctInventorySnapshot(Base):
    __tablename__ = "fct_inventory_snapshots"
    __table_args__ = (
        Index("idx_fct_inv_store_prod", "store_id", "product_id"),
        {"schema": "core"}
    )

    snapshot_key = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(String(64), nullable=False)
    product_id = Column(String(64), nullable=False)
    quantity_on_hand = Column(Integer, nullable=False)
    reorder_level = Column(Integer, nullable=False)
    last_restock_date = Column(Date)
    snapshot_date = Column(Date, default=date.today)
    updated_at = Column(DateTime, nullable=False)


class PipelineState(Base):
    __tablename__ = "pipeline_state"
    __table_args__ = {"schema": "core"}

    source_name = Column(String(64), primary_key=True)
    last_extracted_at = Column(DateTime, nullable=True)
    last_extracted_id = Column(String(128), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = {"schema": "core"}

    run_id = Column(String(64), primary_key=True)
    run_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Numeric(8, 2), nullable=True)
    rows_extracted = Column(Integer, default=0)
    rows_loaded = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    source_metrics = Column(JSON, nullable=True)
