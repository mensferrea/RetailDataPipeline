import pandas as pd
from src.transformers.base import BaseTransformer, TransformationResult


class InventoryTransformer(BaseTransformer):
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

        df_clean.dropna(subset=["store_id", "product_id"], inplace=True)

        if "updated_at" in df_clean.columns:
            df_clean["updated_at"] = pd.to_datetime(df_clean["updated_at"], errors="coerce")
            df_clean.dropna(subset=["updated_at"], inplace=True)
            df_clean.sort_values(by="updated_at", ascending=True, inplace=True)

        before_dedup = len(df_clean)
        df_clean.drop_duplicates(subset=["store_id", "product_id"], keep="last", inplace=True)
        duplicate_count = before_dedup - len(df_clean)

        df_clean["quantity_on_hand"] = pd.to_numeric(df_clean["quantity_on_hand"], errors="coerce")
        df_clean["reorder_level"] = pd.to_numeric(df_clean.get("reorder_level", 10), errors="coerce").fillna(10)

        df_clean = df_clean[(df_clean["quantity_on_hand"] >= 0) & (df_clean["reorder_level"] >= 0)].copy()
        df_clean["quantity_on_hand"] = df_clean["quantity_on_hand"].astype(int)
        df_clean["reorder_level"] = df_clean["reorder_level"].astype(int)

        if "last_restock_date" in df_clean.columns:
            df_clean["last_restock_date"] = pd.to_datetime(df_clean["last_restock_date"], errors="coerce").dt.date
        else:
            df_clean["last_restock_date"] = None

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
            metrics={"total_stock_units": int(df_clean["quantity_on_hand"].sum())}
        )
