from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from src.services.seeder_service import SeederService

router = APIRouter(prefix="/source", tags=["External Mock Sources"])
seeder = SeederService()


@router.get("/inventory")
def get_inventory(
    updated_after: Optional[datetime] = Query(None, description="Filter for incremental loading"),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    all_items = seeder.get_mock_inventory_items(checkpoint=updated_after)
    total_count = len(all_items)
    paginated = all_items[offset : offset + limit]

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "items": paginated
    }
