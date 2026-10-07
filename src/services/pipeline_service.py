import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import pandas as pd
from sqlalchemy import text
from src.config import settings
from src.database import Base, engine, init_db_schemas
import src.models.dwh_models
from src.extractors import (
    CsvSalesExtractor,
    JsonProductsExtractor,
    PostgresCustomersExtractor,
    RestInventoryExtractor
)
from src.loaders.dwh_loader import DwhLoader
from src.marts.mart_builder import MartBuilder
from src.services.seeder_service import SeederService
from src.services.state_service import StateService
from src.transformers import (
    CustomersTransformer,
    InventoryTransformer,
    ProductsTransformer,
    SalesTransformer
)

logger = logging.getLogger("retail_pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PipelineService:
    def __init__(self):
        self.state_service = StateService()
        self.loader = DwhLoader()
        self.mart_builder = MartBuilder()
        self.seeder = SeederService()

    def run(self, run_type: str = "INCREMENTAL") -> Dict[str, Any]:
        run_id = f"RUN_{uuid.uuid4().hex[:12].upper()}"
        started_at = utc_now()

        init_db_schemas()
        Base.metadata.create_all(bind=engine)

        self._create_pipeline_run_record(run_id, run_type, started_at)

        try:
            total_extracted = 0
            total_loaded = 0
            source_metrics: Dict[str, Any] = {}

            sources_config = [
                {
                    "name": "products_json",
                    "extractor": JsonProductsExtractor(settings.RAW_JSON_PRODUCTS_PATH),
                    "transformer": ProductsTransformer(),
                    "merge_fn": self.loader.merge_products_to_core
                },
                {
                    "name": "customers_postgres",
                    "extractor": PostgresCustomersExtractor(),
                    "transformer": CustomersTransformer(),
                    "merge_fn": self.loader.merge_customers_to_core
                },
                {
                    "name": "sales_csv",
                    "extractor": CsvSalesExtractor(settings.RAW_CSV_SALES_PATH),
                    "transformer": SalesTransformer(),
                    "merge_fn": self.loader.merge_sales_to_core
                },
                {
                    "name": "inventory_api",
                    "extractor": RestInventoryExtractor(
                        api_url=settings.INVENTORY_API_URL,
                        mock_data_provider=self.seeder.get_mock_inventory_items
                    ),
                    "transformer": InventoryTransformer(),
                    "merge_fn": self.loader.load_inventory_snapshots
                }
            ]

            self.loader.merge_stores_to_core()

            for src in sources_config:
                src_name = src["name"]
                checkpoint = None
                if run_type.upper() == "INCREMENTAL":
                    checkpoint = self.state_service.get_checkpoint(src_name)

                extraction = src["extractor"].extract(checkpoint=checkpoint)
                total_extracted += extraction.rows_extracted

                transformation = src["transformer"].transform(extraction.data)

                staged_rows = self.loader.load_staging(src_name, transformation.data)
                merged_rows = src["merge_fn"]()
                total_loaded += staged_rows

                if not transformation.data.empty and "updated_at" in transformation.data.columns:
                    max_upd = pd.to_datetime(transformation.data["updated_at"]).max()
                    if pd.notna(max_upd):
                        self.state_service.update_checkpoint(src_name, max_upd.to_pydatetime())

                source_metrics[src_name] = {
                    "extracted": extraction.rows_extracted,
                    "input": transformation.input_count,
                    "valid": transformation.valid_count,
                    "dropped": transformation.dropped_count,
                    "duplicates": transformation.duplicate_count,
                    "staged": staged_rows,
                    "merged": merged_rows,
                    **transformation.metrics
                }

            self.loader.merge_stores_to_core()

            marts_summary = self.mart_builder.build_all_marts()

            finished_at = utc_now()
            duration_sec = round((finished_at - started_at).total_seconds(), 2)

            self._update_pipeline_run_success(
                run_id=run_id,
                finished_at=finished_at,
                duration_sec=duration_sec,
                total_extracted=total_extracted,
                total_loaded=total_loaded,
                source_metrics={"sources": source_metrics, "marts": marts_summary}
            )

            return {
                "run_id": run_id,
                "status": "SUCCESS",
                "run_type": run_type,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_seconds": duration_sec,
                "rows_extracted": total_extracted,
                "rows_loaded": total_loaded,
                "source_metrics": source_metrics,
                "marts_summary": marts_summary
            }

        except Exception as exc:
            finished_at = utc_now()
            duration_sec = round((finished_at - started_at).total_seconds(), 2)
            self._update_pipeline_run_failure(run_id, finished_at, duration_sec, str(exc))
            logger.error(f"Pipeline run {run_id} failed: {exc}", exc_info=True)
            raise

    def _create_pipeline_run_record(self, run_id: str, run_type: str, started_at: datetime) -> None:
        query = text("""
            INSERT INTO core.pipeline_runs (run_id, run_type, status, started_at, rows_extracted, rows_loaded)
            VALUES (:run_id, :run_type, 'RUNNING', :started_at, 0, 0);
        """)
        with engine.begin() as conn:
            conn.execute(query, {"run_id": run_id, "run_type": run_type, "started_at": started_at})

    def _update_pipeline_run_success(
        self,
        run_id: str,
        finished_at: datetime,
        duration_sec: float,
        total_extracted: int,
        total_loaded: int,
        source_metrics: Dict[str, Any]
    ) -> None:
        import json
        query = text("""
            UPDATE core.pipeline_runs
            SET status = 'SUCCESS',
                finished_at = :finished_at,
                duration_seconds = :duration_sec,
                rows_extracted = :extracted,
                rows_loaded = :loaded,
                source_metrics = :metrics
            WHERE run_id = :run_id;
        """)
        with engine.begin() as conn:
            conn.execute(query, {
                "run_id": run_id,
                "finished_at": finished_at,
                "duration_sec": duration_sec,
                "extracted": total_extracted,
                "loaded": total_loaded,
                "metrics": json.dumps(source_metrics)
            })

    def _update_pipeline_run_failure(
        self,
        run_id: str,
        finished_at: datetime,
        duration_sec: float,
        error_message: str
    ) -> None:
        query = text("""
            UPDATE core.pipeline_runs
            SET status = 'FAILED',
                finished_at = :finished_at,
                duration_seconds = :duration_sec,
                error_message = :err
            WHERE run_id = :run_id;
        """)
        with engine.begin() as conn:
            conn.execute(query, {
                "run_id": run_id,
                "finished_at": finished_at,
                "duration_sec": duration_sec,
                "err": error_message
            })

    def get_run_history(self, limit: int = 20) -> list:
        query = text("""
            SELECT run_id, run_type, status, started_at, finished_at, duration_seconds, rows_extracted, rows_loaded, error_message, source_metrics
            FROM core.pipeline_runs
            ORDER BY started_at DESC
            LIMIT :lim;
        """)
        with engine.connect() as conn:
            rows = conn.execute(query, {"lim": limit}).mappings().all()
            return [dict(r) for r in rows]
