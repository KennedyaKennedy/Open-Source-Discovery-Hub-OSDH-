from pydantic import BaseModel, ConfigDict, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class ResourceResponse(BaseModel):
    id: str
    name: str
    url: str
    source_type: str
    description: str = ""
    readme_summary: str = ""
    language: str = ""
    license: str = ""
    topics: List[str] = []
    ai_tags: List[str] = []
    maintenance_status: str = "unknown"
    stars: int = 0
    forks: int = 0
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_archived: bool = False
    is_duplicate: bool = False
    duplicate_of: str = ""

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    resources: List[ResourceResponse]


class AggregateRequest(BaseModel):
    source: str = "github"
    query: Optional[str] = None
    language: Optional[str] = None
    topics: Optional[List[str]] = None
    run_ai: bool = True


class AggregateResponse(BaseModel):
    status: str
    resources_found: int
    resources_added: int
    resources_updated: int
    log_id: str


class SnapshotResponse(BaseModel):
    id: str
    version: str
    created_at: Optional[datetime]
    resource_count: int
    file_path: str
