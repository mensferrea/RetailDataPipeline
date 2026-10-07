import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
import pandas as pd
from src.config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class ExtractionResult:
    source_name: str
    data: pd.DataFrame
    rows_extracted: int
    extracted_at: datetime = field(default_factory=utc_now)
    checkpoint: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseExtractor(ABC):
    def __init__(self, name: str, max_retries: int = settings.MAX_RETRIES, retry_delay: float = settings.RETRY_DELAY_SECONDS):
        self.name = name
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @abstractmethod
    def extract(self, checkpoint: Optional[datetime] = None) -> ExtractionResult:
        pass

    def _execute_with_retry(self, operation: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        attempts = 0
        last_exception = None

        while attempts < self.max_retries:
            try:
                return operation(*args, **kwargs)
            except Exception as exc:
                attempts += 1
                last_exception = exc
                if attempts < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** (attempts - 1)))

        raise RuntimeError(f"Extractor '{self.name}' failed after {self.max_retries} attempts: {last_exception}") from last_exception
