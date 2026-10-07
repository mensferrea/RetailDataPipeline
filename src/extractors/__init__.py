from src.extractors.base import BaseExtractor, ExtractionResult
from src.extractors.csv_extractor import CsvSalesExtractor
from src.extractors.json_extractor import JsonProductsExtractor
from src.extractors.postgres_extractor import PostgresCustomersExtractor
from src.extractors.rest_extractor import RestInventoryExtractor

__all__ = [
    "BaseExtractor",
    "ExtractionResult",
    "CsvSalesExtractor",
    "JsonProductsExtractor",
    "PostgresCustomersExtractor",
    "RestInventoryExtractor"
]
