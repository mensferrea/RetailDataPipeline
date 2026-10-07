from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from src.services.pipeline_service import PipelineService
from src.services.seeder_service import SeederService
from src.services.state_service import StateService

router = APIRouter(prefix="/pipeline", tags=["Pipeline Management"])
pipeline_service = PipelineService()
seeder_service = SeederService()
state_service = StateService()


class RunRequest(BaseModel):
    run_type: str = "INCREMENTAL"


@router.post("/run")
def trigger_pipeline(request: RunRequest) -> Dict[str, Any]:
    try:
        result = pipeline_service.run(run_type=request.run_type.upper())
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history")
def get_run_history(limit: int = Query(20, ge=1, le=100)) -> List[Dict[str, Any]]:
    return pipeline_service.get_run_history(limit=limit)


@router.post("/seed")
def seed_source_data() -> Dict[str, Any]:
    counts = seeder_service.seed_all()
    return {"message": "Sample source data seeded successfully", "records_created": counts}


@router.post("/reset-state")
def reset_state() -> Dict[str, str]:
    state_service.reset_all_checkpoints()
    return {"message": "All pipeline source checkpoints reset successfully"}
