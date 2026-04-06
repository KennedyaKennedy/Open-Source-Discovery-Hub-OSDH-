from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db import get_db, AggregationLog
from app.api.schemas import AggregateRequest, AggregateResponse
from app.aggregators.github import aggregate_github
from app.aggregators.awesome import aggregate_awesome_lists
from app.aggregators.educational import aggregate_educational
from app.ai.ollama import process_ai_tasks
import uuid
from datetime import datetime, timezone

router = APIRouter()


@router.post("/run", response_model=AggregateResponse)
async def run_aggregation(
    request: AggregateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    log_id = str(uuid.uuid4())
    log = AggregationLog(
        id=log_id,
        source=request.source,
        status="running",
    )
    db.add(log)
    db.commit()

    found = added = updated = 0

    try:
        if request.source == "github":
            found, added, updated = await aggregate_github(
                db=db,
                query=request.query,
                language=request.language,
                topics=request.topics,
            )
        elif request.source == "awesome":
            found, added, updated = await aggregate_awesome_lists(db=db)
        elif request.source == "educational":
            found, added, updated = await aggregate_educational(db=db)
        elif request.source == "all":
            for aggregator in [
                aggregate_github,
                aggregate_awesome_lists,
                aggregate_educational,
            ]:
                kwargs = {}
                if aggregator == aggregate_github:
                    kwargs = {
                        "db": db,
                        "query": request.query,
                        "language": request.language,
                        "topics": request.topics,
                    }
                else:
                    kwargs = {"db": db}
                f, a, u = await aggregator(**kwargs)
                found += f
                added += a
                updated += u
        else:
            log.status = "failed"
            log.error = f"Unknown source: {request.source}"
            log.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise HTTPException(
                status_code=400, detail=f"Unknown source: {request.source}"
            )

        log.status = "completed"
    except HTTPException:
        log.resources_found = found
        log.resources_added = added
        log.resources_updated = updated
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise
    except Exception as e:
        log.status = "failed"
        log.error = str(e)
        log.resources_found = found
        log.resources_added = added
        log.resources_updated = updated
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    log.resources_found = found
    log.resources_added = added
    log.resources_updated = updated
    log.completed_at = datetime.now(timezone.utc)
    db.commit()

    if request.run_ai and added > 0:
        background_tasks.add_task(process_ai_tasks, None, log_id)

    return AggregateResponse(
        status="completed",
        resources_found=found,
        resources_added=added,
        resources_updated=updated,
        log_id=log_id,
    )


@router.get("/logs")
async def get_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    logs = (
        db.query(AggregationLog)
        .order_by(AggregationLog.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "source": l.source,
            "status": l.status,
            "resources_found": l.resources_found,
            "resources_added": l.resources_added,
            "resources_updated": l.resources_updated,
            "started_at": l.started_at,
            "completed_at": l.completed_at,
            "error": l.error,
        }
        for l in logs
    ]


@router.post("/ai-process")
async def run_ai_processing(
    background_tasks: BackgroundTasks,
    resource_ids: Optional[List[str]] = None,
    db: Session = Depends(get_db),
):
    # Pass None for db so process_ai_tasks creates its own session
    background_tasks.add_task(process_ai_tasks, None, None, resource_ids)
    return {"status": "ai_processing_started"}
