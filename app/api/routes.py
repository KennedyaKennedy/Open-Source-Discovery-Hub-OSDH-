from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from datetime import datetime

from app.db import get_db, Resource
from app.api.schemas import ResourceResponse, SearchResponse

router = APIRouter()


@router.get("/resources", response_model=SearchResponse)
async def search_resources(
    q: Optional[str] = Query(None, description="Search query"),
    language: Optional[str] = Query(None),
    license: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    maintenance_status: Optional[str] = Query(None),
    is_archived: Optional[bool] = Query(None),
    is_duplicate: Optional[bool] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    sort: str = Query("last_updated", pattern="^(name|stars|last_updated|created_at)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Resource)

    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Resource.name.ilike(search_term),
                Resource.description.ilike(search_term),
                Resource.readme_summary.ilike(search_term),
            )
        )

    if language:
        query = query.filter(Resource.language == language)

    if license:
        query = query.filter(Resource.license == license)

    if source_type:
        query = query.filter(Resource.source_type == source_type)

    if maintenance_status:
        query = query.filter(Resource.maintenance_status == maintenance_status)

    if is_archived is not None:
        query = query.filter(Resource.is_archived == is_archived)

    if is_duplicate is not None:
        query = query.filter(Resource.is_duplicate == is_duplicate)

    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",")]
        for tag in tag_list:
            query = query.filter(Resource.ai_tags.contains([tag]))

    sort_col = getattr(Resource, sort)
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    total = query.count()
    resources = query.offset(offset).limit(limit).all()

    return SearchResponse(
        total=total,
        limit=limit,
        offset=offset,
        resources=[ResourceResponse.model_validate(r) for r in resources],
    )


@router.get("/resources/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: str, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return ResourceResponse.model_validate(resource)


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    total = db.query(Resource).count()
    active = db.query(Resource).filter(Resource.maintenance_status == "active").count()
    maintained = (
        db.query(Resource).filter(Resource.maintenance_status == "maintained").count()
    )
    stale = db.query(Resource).filter(Resource.maintenance_status == "stale").count()
    archived = db.query(Resource).filter(Resource.is_archived == True).count()

    languages = (
        db.query(Resource.language).filter(Resource.language != "").distinct().all()
    )
    licenses = (
        db.query(Resource.license).filter(Resource.license != "").distinct().all()
    )

    all_tags = db.query(Resource.ai_tags).all()
    tag_counts = {}
    for (tags,) in all_tags:
        if tags:
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return {
        "total": total,
        "by_status": {
            "active": active,
            "maintained": maintained,
            "stale": stale,
            "archived": archived,
        },
        "languages": sorted([l[0] for l in languages if l[0]]),
        "licenses": sorted([l[0] for l in licenses if l[0]]),
        "top_tags": dict(
            sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:50]
        ),
    }


@router.get("/filters")
async def get_filter_options(db: Session = Depends(get_db)):
    languages = (
        db.query(Resource.language)
        .filter(Resource.language != "")
        .distinct()
        .order_by(Resource.language)
        .all()
    )
    licenses = (
        db.query(Resource.license)
        .filter(Resource.license != "")
        .distinct()
        .order_by(Resource.license)
        .all()
    )
    source_types = (
        db.query(Resource.source_type).distinct().order_by(Resource.source_type).all()
    )

    return {
        "languages": [l[0] for l in languages if l[0]],
        "licenses": [l[0] for l in licenses if l[0]],
        "source_types": [s[0] for s in source_types if s[0]],
        "maintenance_statuses": [
            "active",
            "maintained",
            "stale",
            "archived",
            "unknown",
        ],
    }
