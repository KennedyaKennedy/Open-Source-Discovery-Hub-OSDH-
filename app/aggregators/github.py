import httpx
import logging
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Resource
from app.cache import get_cached_readme, cache_readme

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def _get_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OSDH-Aggregator/0.1.0",
    }
    if settings.GITHUB_API_TOKEN:
        headers["Authorization"] = f"token {settings.GITHUB_API_TOKEN}"
    return headers


async def _fetch_readme(owner: str, repo: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
    cached = get_cached_readme(url)
    if cached:
        return cached

    try:
        req_headers = _get_headers()
        req_headers["Accept"] = "application/vnd.github.v3.raw"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                url,
                headers=req_headers,
            )
            if resp.status_code == 200:
                content = resp.text
                cache_readme(url, content)
                return content
    except Exception as e:
        logger.error(f"Failed to fetch README for {owner}/{repo}: {e}")
    return ""


async def _search_github(
    query: Optional[str] = None,
    language: Optional[str] = None,
    topics: Optional[List[str]] = None,
    page: int = 1,
    per_page: int = 30,
) -> dict:
    search_parts = []

    if query:
        search_parts.append(query)
    else:
        search_parts.append("stars:>100")

    if language:
        search_parts.append(f"language:{language}")

    if topics:
        for topic in topics:
            search_parts.append(f"topic:{topic}")

    search_query = " ".join(search_parts)

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            f"{GITHUB_API}/search/repositories",
            headers=_get_headers(),
            params={
                "q": search_query,
                "sort": "updated",
                "order": "desc",
                "page": page,
                "per_page": per_page,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def aggregate_github(
    db: Session,
    query: Optional[str] = None,
    language: Optional[str] = None,
    topics: Optional[List[str]] = None,
    max_pages: int = 3,
) -> Tuple[int, int, int]:
    found = 0
    added = 0
    updated = 0

    for page in range(1, max_pages + 1):
        try:
            data = await _search_github(
                query=query,
                language=language,
                topics=topics,
                page=page,
            )
        except Exception as e:
            logger.error(f"GitHub search failed on page {page}: {e}")
            break

        items = data.get("items", [])
        if not items:
            break

        found += len(items)

        for item in items:
            repo_id = f"github-{item['id']}"
            owner = item["owner"]["login"]
            repo_name = item["name"]

            existing = db.query(Resource).filter(Resource.id == repo_id).first()

            readme = ""
            if not existing or not existing.readme:
                readme = await _fetch_readme(owner, repo_name)

            resource_data = {
                "id": repo_id,
                "name": f"{owner}/{repo_name}",
                "url": item["html_url"],
                "source_type": "github",
                "description": item.get("description") or "",
                "readme": readme,
                "language": item.get("language") or "",
                "license": (item.get("license") or {}).get("spdx_id") or "",
                "topics": item.get("topics") or [],
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "last_updated": datetime.fromisoformat(
                    item["pushed_at"].replace("Z", "+00:00")
                ),
                "is_archived": item.get("archived", False),
                "extra_metadata": {
                    "open_issues": item.get("open_issues_count", 0),
                    "default_branch": item.get("default_branch", ""),
                    "created_at": item.get("created_at", ""),
                },
            }

            if existing:
                for key, value in resource_data.items():
                    if key not in ("id",):
                        setattr(existing, key, value)
                updated += 1
            else:
                new_resource = Resource(**resource_data)
                db.add(new_resource)
                added += 1

        db.commit()

    return found, added, updated
