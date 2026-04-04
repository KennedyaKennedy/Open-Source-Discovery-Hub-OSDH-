from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    JSON,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

from app.config import settings

engine = create_engine(f"sqlite:///{settings.OSDH_DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    source_type = Column(String, nullable=False)
    description = Column(Text, default="")
    readme = Column(Text, default="")
    readme_summary = Column(Text, default="")
    language = Column(String, default="")
    license = Column(String, default="")
    topics = Column(JSON, default=list)
    ai_tags = Column(JSON, default=list)
    maintenance_status = Column(String, default="unknown")
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_archived = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(String, default="")
    metadata = Column(JSON, default=dict)


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(String, primary_key=True)
    version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resource_count = Column(Integer, default=0)
    file_path = Column(String, default="")
    metadata = Column(JSON, default=dict)


class AggregationLog(Base):
    __tablename__ = "aggregation_logs"

    id = Column(String, primary_key=True)
    source = Column(String, nullable=False)
    status = Column(String, nullable=False)
    resources_found = Column(Integer, default=0)
    resources_added = Column(Integer, default=0)
    resources_updated = Column(Integer, default=0)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)
    error = Column(Text, default="")


def init_db():
    import os

    db_dir = os.path.dirname(settings.OSDH_DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
