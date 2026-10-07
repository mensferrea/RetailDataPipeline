from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RawSale(BaseModel):
    sale_id: str
    sale_date: date
    store_id: str
    product_id: str
    customer_id: Optional[str] = None
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    discount: float = Field(default=0.0, ge=0.0, le=1.0)
    total_amount: float = Field(ge=0)
    payment_method: str
    updated_at: datetime

    @field_validator("payment_method")
    @classmethod
    def normalize_payment_method(cls, v: str) -> str:
        val = v.strip().upper()
        allowed = {"CARD", "CASH", "QR", "ONLINE"}
        return val if val in allowed else "OTHER"


class RawProduct(BaseModel):
    product_id: str
    product_name: str
    category: str
    brand: Optional[str] = "Generic"
    cost_price: float = Field(ge=0)
    retail_price: float = Field(gt=0)
    is_active: bool = True
    updated_at: datetime

    @field_validator("product_name", "category")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip().title()


class RawCustomer(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = "Unknown"
    loyalty_tier: str = "Standard"
    created_at: datetime
    updated_at: datetime

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if not v or "@" not in v:
            return None
        return v.strip().lower()


class RawInventory(BaseModel):
    store_id: str
    product_id: str
    quantity_on_hand: int = Field(ge=0)
    reorder_level: int = Field(ge=0)
    last_restock_date: Optional[date] = None
    updated_at: datetime
