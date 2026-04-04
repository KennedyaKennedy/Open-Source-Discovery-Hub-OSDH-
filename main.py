"""
Open-Source Discovery Hub (OSDH)
Main application entry point.
"""

from app.config import settings
from app.db import init_db
from app.api import app


def create_app():
    init_db()
    return app


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run(
        "app.api:app",
        host=settings.OSDH_HOST,
        port=settings.OSDH_PORT,
        reload=settings.OSDH_ENV == "development",
    )
