from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx
import pandas as pd
from src.config import settings
from src.extractors.base import BaseExtractor, ExtractionResult


class RestInventoryExtractor(BaseExtractor):
    def __init__(
        self,
        api_url: str = settings.INVENTORY_API_URL,
        name: str = "inventory_api",
        mock_data_provider: Optional[Any] = None
    ):
        super().__init__(name=name)
        self.api_url = api_url
        self.mock_data_provider = mock_data_provider

    def extract(self, checkpoint: Optional[datetime] = None) -> ExtractionResult:
        if self.mock_data_provider is not None:
            raw_items = self.mock_data_provider(checkpoint)
            df = pd.DataFrame(raw_items)
            return ExtractionResult(
                source_name=self.name,
                data=df,
                rows_extracted=len(df),
                checkpoint=checkpoint,
                metadata={"provider": "mock_data_provider"}
            )

        def _fetch_api() -> pd.DataFrame:
            params: Dict[str, Any] = {"limit": 1000}
            if checkpoint is not None:
                params["updated_after"] = checkpoint.isoformat()

            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.api_url, params=params)
                response.raise_for_status()
                payload = response.json()

            items: List[Dict[str, Any]] = payload.get("items", []) if isinstance(payload, dict) else payload
            return pd.DataFrame(items)

        df = self._execute_with_retry(_fetch_api)

        return ExtractionResult(
            source_name=self.name,
            data=df,
            rows_extracted=len(df),
            checkpoint=checkpoint,
            metadata={"api_url": self.api_url}
        )
