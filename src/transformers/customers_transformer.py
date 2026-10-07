import numpy as np
import pandas as pd
from src.transformers.base import BaseTransformer, TransformationResult


class CustomersTransformer(BaseTransformer):
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

        df_clean.dropna(subset=["id", "first_name", "last_name"], inplace=True)

        if "updated_at" in df_clean.columns:
            df_clean["updated_at"] = pd.to_datetime(df_clean["updated_at"], errors="coerce")
            df_clean.dropna(subset=["updated_at"], inplace=True)
            df_clean.sort_values(by="updated_at", ascending=True, inplace=True)

        before_dedup = len(df_clean)
        df_clean.drop_duplicates(subset=["id"], keep="last", inplace=True)
        duplicate_count = before_dedup - len(df_clean)

        df_clean["id"] = df_clean["id"].astype(str).str.strip()
        df_clean["first_name"] = df_clean["first_name"].astype(str).str.strip().str.title()
        df_clean["last_name"] = df_clean["last_name"].astype(str).str.strip().str.title()
        df_clean["full_name"] = df_clean["first_name"] + " " + df_clean["last_name"]

        if "email" in df_clean.columns:
            emails = df_clean["email"].astype(str).str.strip().str.lower()
            valid_email_mask = emails.str.contains("@", regex=False) & emails.str.contains(r"\.", regex=True)
            df_clean["email"] = emails.where(valid_email_mask, None)
            df_clean["email"] = df_clean["email"].replace({np.nan: None})
        else:
            df_clean["email"] = None

        if "phone" in df_clean.columns:
            df_clean["phone"] = df_clean["phone"].astype(str).str.strip().replace({"nan": None, "None": None, "": None})
        else:
            df_clean["phone"] = None

        if "city" in df_clean.columns:
            df_clean["city"] = df_clean["city"].fillna("Unknown").astype(str).str.strip().str.title()
        else:
            df_clean["city"] = "Unknown"

        if "loyalty_tier" in df_clean.columns:
            df_clean["loyalty_tier"] = df_clean["loyalty_tier"].fillna("Standard").astype(str).str.strip().str.title()
        else:
            df_clean["loyalty_tier"] = "Standard"

        if "created_at" in df_clean.columns:
            df_clean["created_at"] = pd.to_datetime(df_clean["created_at"], errors="coerce")
            df_clean["created_at"] = df_clean["created_at"].fillna(df_clean["updated_at"])
        elif "updated_at" in df_clean.columns:
            df_clean["created_at"] = df_clean["updated_at"]
        else:
            df_clean["created_at"] = pd.Timestamp.now()

        valid_count = len(df_clean)
        dropped_count = input_count - valid_count - duplicate_count

        return TransformationResult(
            data=df_clean,
            input_count=input_count,
            valid_count=valid_count,
            dropped_count=dropped_count,
            duplicate_count=duplicate_count,
            metrics={"valid_emails_count": int(df_clean["email"].notna().sum())}
        )
