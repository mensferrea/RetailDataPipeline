from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict
import pandas as pd


@dataclass
class TransformationResult:
    data: pd.DataFrame
    input_count: int
    valid_count: int
    dropped_count: int
    duplicate_count: int
    metrics: Dict[str, Any] = field(default_factory=dict)


class BaseTransformer(ABC):
    @abstractmethod
    def transform(self, df: pd.DataFrame) -> TransformationResult:
        pass
