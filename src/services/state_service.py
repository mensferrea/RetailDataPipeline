from datetime import datetime
from typing import Optional
from sqlalchemy import text
from src.database import engine


class StateService:
    def get_checkpoint(self, source_name: str) -> Optional[datetime]:
        query = text("SELECT last_extracted_at FROM core.pipeline_state WHERE source_name = :src")
        with engine.connect() as conn:
            res = conn.execute(query, {"src": source_name}).fetchone()
            if res and res[0]:
                return res[0]
            return None

    def update_checkpoint(self, source_name: str, checkpoint: datetime) -> None:
        upsert_query = text("""
            INSERT INTO core.pipeline_state (source_name, last_extracted_at, updated_at)
            VALUES (:src, :chk, NOW() AT TIME ZONE 'utc')
            ON CONFLICT (source_name) DO UPDATE SET
                last_extracted_at = EXCLUDED.last_extracted_at,
                updated_at = EXCLUDED.updated_at;
        """)
        with engine.begin() as conn:
            conn.execute(upsert_query, {"src": source_name, "chk": checkpoint})

    def reset_all_checkpoints(self) -> None:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE core.pipeline_state;"))
