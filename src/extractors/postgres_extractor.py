from datetime import datetime
from typing import Optional
import pandas as pd
from sqlalchemy import text
from src.database import engine
from src.extractors.base import BaseExtractor, ExtractionResult


class PostgresCustomersExtractor(BaseExtractor):
    def __init__(self, name: str = "customers_postgres"):
        super().__init__(name=name)

    def extract(self, checkpoint: Optional[datetime] = None) -> ExtractionResult:
        def _read_postgres() -> pd.DataFrame:
            query = """
                SELECT id, first_name, last_name, email, phone, city, loyalty_tier, created_at, updated_at
                FROM source_crm.customers
            """
            params = {}
            if checkpoint is not None:
                query += " WHERE updated_at > :checkpoint ORDER BY updated_at ASC"
                params["checkpoint"] = checkpoint
            else:
                query += " ORDER BY updated_at ASC"

            with engine.connect() as conn:
                return pd.read_sql_query(text(query), conn, params=params)

        df = self._execute_with_retry(_read_postgres)

        return ExtractionResult(
            source_name=self.name,
            data=df,
            rows_extracted=len(df),
            checkpoint=checkpoint,
            metadata={"source_schema": "source_crm", "table": "customers"}
        )
