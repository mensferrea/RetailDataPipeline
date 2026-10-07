from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "retail_dwh"
    DB_USER: str = "retail_user"
    DB_PASSWORD: str = "retail_password"
    DATABASE_URL: str = "postgresql+psycopg2://retail_user:retail_password@localhost:5432/retail_dwh"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    INVENTORY_API_URL: str = "http://localhost:8000/api/v1/source/inventory"

    DATA_DIR: Path = Path("data")
    RAW_CSV_SALES_PATH: Path = Path("data/raw/sales.csv")
    RAW_JSON_PRODUCTS_PATH: Path = Path("data/raw/products.json")

    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
