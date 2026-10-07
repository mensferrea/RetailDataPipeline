from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from src.api.routes import marts_router, pipeline_router, source_router
from src.database import Base, engine, init_db_schemas


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db_schemas()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Retail ETL & Data Mart API",
    description="Production-grade retail ETL pipeline, data marts, and management API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(source_router, prefix="/api/v1")
app.include_router(pipeline_router, prefix="/api/v1")
app.include_router(marts_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Retail ETL & Data Mart"}
