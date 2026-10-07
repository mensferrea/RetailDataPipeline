from datetime import datetime
from pathlib import Path
from typing import Optional, Union
import pandas as pd
from src.extractors.base import BaseExtractor, ExtractionResult


class CsvSalesExtractor(BaseExtractor):
    def __init__(self, file_path: Union[str, Path], name: str = "sales_csv"):
        super().__init__(name=name)
        self.file_path = Path(file_path)

    def extract(self, checkpoint: Optional[datetime] = None) -> ExtractionResult:
        def _read_csv() -> pd.DataFrame:
            if not self.file_path.exists():
                return pd.DataFrame()
            return pd.read_csv(self.file_path)

        df = self._execute_with_retry(_read_csv)

        if not df.empty and checkpoint is not None and "updated_at" in df.columns:
            df["_temp_updated"] = pd.to_datetime(df["updated_at"], errors="coerce")
            df = df[df["_temp_updated"] > pd.to_datetime(checkpoint)].copy()
            df.drop(columns=["_temp_updated"], inplace=True)

        return ExtractionResult(
            source_name=self.name,
            data=df,
            rows_extracted=len(df),
            checkpoint=checkpoint,
            metadata={"file_path": str(self.file_path)}
        )
