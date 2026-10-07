import numpy as np
import pandas as pd
from src.transformers.base import BaseTransformer, TransformationResult


class SalesTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> TransformationResult:
        if df.empty:
            return TransformationResult(
                data=pd.DataFrame(),
                input_count=0,
                valid_count=0,
                dropped_count=0,
                duplicate_count=0
            )

        input_count = len(df)
        df_clean = df.copy()

        df_clean.dropna(subset=["sale_id", "sale_date", "store_id", "product_id"], inplace=True)

        if "updated_at" in df_clean.columns:
            df_clean["updated_at"] = pd.to_datetime(df_clean["updated_at"], errors="coerce")
            df_clean.dropna(subset=["updated_at"], inplace=True)
            df_clean.sort_values(by="updated_at", ascending=True, inplace=True)

        before_dedup = len(df_clean)
        df_clean.drop_duplicates(subset=["sale_id"], keep="last", inplace=True)
        duplicate_count = before_dedup - len(df_clean)

        df_clean["sale_date"] = pd.to_datetime(df_clean["sale_date"], errors="coerce").dt.date
        df_clean.dropna(subset=["sale_date"], inplace=True)

        df_clean["quantity"] = pd.to_numeric(df_clean["quantity"], errors="coerce")
        df_clean["unit_price"] = pd.to_numeric(df_clean["unit_price"], errors="coerce")
        df_clean["discount"] = pd.to_numeric(df_clean.get("discount", 0.0), errors="coerce").fillna(0.0)

        df_clean = df_clean[(df_clean["quantity"] > 0) & (df_clean["unit_price"] > 0)].copy()
        df_clean["quantity"] = df_clean["quantity"].astype(int)
        df_clean["discount"] = np.clip(df_clean["discount"].astype(float), 0.0, 1.0)

        calculated_total = np.round(df_clean["quantity"] * df_clean["unit_price"] * (1.0 - df_clean["discount"]), 2)
        if "total_amount" in df_clean.columns:
            provided_total = pd.to_numeric(df_clean["total_amount"], errors="coerce")
            df_clean["total_amount"] = np.where(provided_total.isna() | (provided_total <= 0), calculated_total, np.round(provided_total, 2))
        else:
            df_clean["total_amount"] = calculated_total

        df_clean["payment_method"] = df_clean.get("payment_method", "CARD").astype(str).str.strip().str.upper()
        allowed_methods = {"CARD", "CASH", "QR", "ONLINE"}
        df_clean["payment_method"] = df_clean["payment_method"].apply(lambda m: m if m in allowed_methods else "OTHER")

        if "customer_id" in df_clean.columns:
            df_clean["customer_id"] = df_clean["customer_id"].replace({np.nan: None, "": None})
        else:
            df_clean["customer_id"] = None

        df_clean["sale_id"] = df_clean["sale_id"].astype(str).str.strip()
        df_clean["store_id"] = df_clean["store_id"].astype(str).str.strip()
        df_clean["product_id"] = df_clean["product_id"].astype(str).str.strip()

        valid_count = len(df_clean)
        dropped_count = input_count - valid_count - duplicate_count

        return TransformationResult(
            data=df_clean,
            input_count=input_count,
            valid_count=valid_count,
            dropped_count=dropped_count,
            duplicate_count=duplicate_count,
            metrics={
                "total_sales_volume": float(df_clean["total_amount"].sum()) if not df_clean.empty else 0.0,
                "total_items_sold": int(df_clean["quantity"].sum()) if not df_clean.empty else 0
            }
        )
