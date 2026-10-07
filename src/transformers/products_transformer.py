import numpy as np
import pandas as pd
from src.transformers.base import BaseTransformer, TransformationResult


class ProductsTransformer(BaseTransformer):
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

        df_clean.dropna(subset=["product_id", "product_name"], inplace=True)

        if "updated_at" in df_clean.columns:
            df_clean["updated_at"] = pd.to_datetime(df_clean["updated_at"], errors="coerce")
            df_clean.dropna(subset=["updated_at"], inplace=True)
            df_clean.sort_values(by="updated_at", ascending=True, inplace=True)

        before_dedup = len(df_clean)
        df_clean.drop_duplicates(subset=["product_id"], keep="last", inplace=True)
        duplicate_count = before_dedup - len(df_clean)

        df_clean["cost_price"] = pd.to_numeric(df_clean.get("cost_price", 0.0), errors="coerce").fillna(0.0)
        df_clean["retail_price"] = pd.to_numeric(df_clean.get("retail_price", 0.0), errors="coerce")
        df_clean = df_clean[(df_clean["retail_price"] > 0) & (df_clean["cost_price"] >= 0)].copy()

        df_clean["product_id"] = df_clean["product_id"].astype(str).str.strip()
        df_clean["product_name"] = df_clean["product_name"].astype(str).str.strip().str.title()

        if "category" in df_clean.columns:
            df_clean["category"] = df_clean["category"].fillna("Uncategorized").astype(str).str.strip().str.title()
        else:
            df_clean["category"] = "Uncategorized"

        if "brand" in df_clean.columns:
            df_clean["brand"] = df_clean["brand"].fillna("Generic").astype(str).str.strip()
        else:
            df_clean["brand"] = "Generic"

        if "is_active" in df_clean.columns:
            df_clean["is_active"] = df_clean["is_active"].fillna(True).astype(bool)
        else:
            df_clean["is_active"] = True

        df_clean["margin_amount"] = np.round(df_clean["retail_price"] - df_clean["cost_price"], 2)
        df_clean["margin_pct"] = np.round((df_clean["margin_amount"] / df_clean["retail_price"]) * 100.0, 2)

        valid_count = len(df_clean)
        dropped_count = input_count - valid_count - duplicate_count

        return TransformationResult(
            data=df_clean,
            input_count=input_count,
            valid_count=valid_count,
            dropped_count=dropped_count,
            duplicate_count=duplicate_count,
            metrics={"active_products_count": int(df_clean["is_active"].sum())}
        )
