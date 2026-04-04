from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.db import get_db, Snapshot
from app.snapshots.manager import create_snapshot, list_snapshots, load_snapshot

router = APIRouter()


@router.post("/create")
async def create_new_snapshot(
    snapshot_format: str = Query(
        "json", alias="format", pattern="^(json|csv|sqlite|all)$"
    ),
    db: Session = Depends(get_db),
):
    snapshot = await create_snapshot(db, format=snapshot_format)
    return {
        "id": snapshot.id,
        "version": snapshot.version,
        "created_at": snapshot.created_at,
        "resource_count": snapshot.resource_count,
        "file_paths": snapshot.metadata.get("filename", []),
        "formats": snapshot.metadata.get("formats", []),
    }


@router.get("/list")
async def list_available_snapshots(db: Session = Depends(get_db)):
    snapshots = list_snapshots(db)
    return snapshots


@router.get("/download/{snapshot_id}/{file_type}")
async def download_snapshot(
    snapshot_id: str,
    file_type: str = Query("json", pattern="^(json|csv|sqlite)$"),
    db: Session = Depends(get_db),
):
    snap = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    file_paths = snap.metadata.get("filename", [])
    target_path = None
    media_type = "application/json"
    ext = f".{file_type}"

    for fp in file_paths:
        if fp.endswith(ext):
            target_path = fp
            break

    if not target_path and file_type == "json":
        target_path = snap.file_path

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Snapshot file not found")

    if file_type == "csv":
        media_type = "text/csv"
    elif file_type == "sqlite":
        media_type = "application/octet-stream"

    return FileResponse(
        target_path,
        media_type=media_type,
        filename=os.path.basename(target_path),
    )


@router.get("/load/{snapshot_id}")
async def load_existing_snapshot(snapshot_id: str, db: Session = Depends(get_db)):
    result = await load_snapshot(db, snapshot_id)
    return result
