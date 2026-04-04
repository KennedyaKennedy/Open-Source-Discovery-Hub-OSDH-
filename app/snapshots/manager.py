import json
import csv
import os
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Snapshot, Resource


def _ensure_snapshot_dir():
    if not os.path.exists(settings.OSDH_SNAPSHOT_DIR):
        os.makedirs(settings.OSDH_SNAPSHOT_DIR, exist_ok=True)


def _resource_dict(r: Resource) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "url": r.url,
        "source_type": r.source_type,
        "description": r.description,
        "readme_summary": r.readme_summary,
        "language": r.language,
        "license": r.license,
        "topics": json.dumps(r.topics) if r.topics else "",
        "ai_tags": json.dumps(r.ai_tags) if r.ai_tags else "",
        "maintenance_status": r.maintenance_status,
        "stars": r.stars,
        "forks": r.forks,
        "last_updated": r.last_updated.isoformat() if r.last_updated else "",
        "is_archived": r.is_archived,
        "is_duplicate": r.is_duplicate,
        "duplicate_of": r.duplicate_of,
    }


async def create_snapshot(db: Session, format: str = "json") -> Snapshot:
    _ensure_snapshot_dir()

    resources = db.query(Resource).all()
    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_id = str(uuid.uuid4())
    file_paths = {}

    if format in ("json", "all"):
        data = {
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resource_count": len(resources),
            "resources": [_resource_dict(r) for r in resources],
        }
        json_filename = f"osdh-snapshot-{version}.json"
        json_filepath = os.path.join(settings.OSDH_SNAPSHOT_DIR, json_filename)
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        file_paths["json"] = json_filepath

    if format in ("csv", "all"):
        csv_filename = f"osdh-snapshot-{version}.csv"
        csv_filepath = os.path.join(settings.OSDH_SNAPSHOT_DIR, csv_filename)
        if resources:
            fieldnames = list(_resource_dict(resources[0]).keys())
            with open(csv_filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in resources:
                    writer.writerow(_resource_dict(r))
        file_paths["csv"] = csv_filepath

    if format in ("sqlite", "all"):
        sqlite_filename = f"osdh-snapshot-{version}.db"
        sqlite_filepath = os.path.join(settings.OSDH_SNAPSHOT_DIR, sqlite_filename)
        conn = sqlite3.connect(sqlite_filepath)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                source_type TEXT NOT NULL,
                description TEXT,
                readme_summary TEXT,
                language TEXT,
                license TEXT,
                topics TEXT,
                ai_tags TEXT,
                maintenance_status TEXT,
                stars INTEGER,
                forks INTEGER,
                last_updated TEXT,
                is_archived INTEGER,
                is_duplicate INTEGER,
                duplicate_of TEXT
            )
        """)
        for r in resources:
            d = _resource_dict(r)
            cursor.execute(
                "INSERT OR REPLACE INTO resources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    d["id"],
                    d["name"],
                    d["url"],
                    d["source_type"],
                    d["description"],
                    d["readme_summary"],
                    d["language"],
                    d["license"],
                    d["topics"],
                    d["ai_tags"],
                    d["maintenance_status"],
                    d["stars"],
                    d["forks"],
                    d["last_updated"],
                    d["is_archived"],
                    d["is_duplicate"],
                    d["duplicate_of"],
                ),
            )
        conn.commit()
        conn.close()
        file_paths["sqlite"] = sqlite_filepath

    snapshot = Snapshot(
        id=snapshot_id,
        version=version,
        resource_count=len(resources),
        file_path=file_paths.get(
            "json", file_paths.get("csv", file_paths.get("sqlite", ""))
        ),
        metadata={
            "filename": list(file_paths.values()),
            "formats": list(file_paths.keys()),
        },
    )
    db.add(snapshot)
    db.commit()

    return snapshot


def list_snapshots(db: Session) -> List[Dict[str, Any]]:
    snapshots = db.query(Snapshot).order_by(Snapshot.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "version": s.version,
            "created_at": s.created_at,
            "resource_count": s.resource_count,
            "file_path": s.file_path,
            "metadata": s.metadata,
        }
        for s in snapshots
    ]


async def load_snapshot(db: Session, snapshot_id: str) -> Dict[str, Any]:
    snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snapshot:
        return {"error": "Snapshot not found"}

    if not os.path.exists(snapshot.file_path):
        return {"error": "Snapshot file not found"}

    with open(snapshot.file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data
