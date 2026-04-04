from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api.routes import router as api_router
from app.api.aggregate import router as aggregate_router
from app.api.snapshots import router as snapshots_router

app = FastAPI(title="Open-Source Discovery Hub", version="0.1.0")

app.include_router(api_router, prefix="/api")
app.include_router(aggregate_router, prefix="/api/aggregate")
app.include_router(snapshots_router, prefix="/api/snapshots")

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def index():
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)
