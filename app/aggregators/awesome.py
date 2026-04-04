import re
import httpx
import logging
from typing import List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Resource
from app.cache import get_cached_readme, cache_readme

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
AWESOME_LIST_REPO = "sindresorhus/awesome"

CURATED_AWESOME = [
    "sindresorhus/awesome",
    "vinta/awesome-python",
    "avelino/awesome-go",
    "jnv/lists",
    "awesome-selfhosted/awesome-selfhosted",
    "ripienaar/free-for-dev",
    "public-apis/public-apis",
    "EbookFoundation/free-programming-books",
    "kahun/awesome-sysadmin",
    "terryum/awesome-deep-learning-papers",
]


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


async def _discover_awesome_lists() -> List[str]:
    try:
        req_headers = _get_headers()
        req_headers["Accept"] = "application/vnd.github.v3.raw"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{AWESOME_LIST_REPO}/readme",
                headers=req_headers,
            )
            if resp.status_code == 200:
                content = resp.text
                pattern = r"\[([^\]]+)\]\(https://github\.com/([^)]+)\)"
                matches = re.findall(pattern, content)
                repos = [m[1] for m in matches if m[1].count("/") == 1]
                return list(set(repos))
    except Exception as e:
        logger.error(f"Failed to discover Awesome lists: {e}")
    return []


async def _fetch_repo_info(full_name: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{full_name}",
                headers=_get_headers(),
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch repo info for {full_name}: {e}")
    return {}


async def aggregate_awesome_lists(
    db: Session,
    use_curated: bool = True,
    use_discovery: bool = True,
    max_repos: int = 100,
) -> Tuple[int, int, int]:
    found = 0
    added = 0
    updated = 0

    all_repos = set()

    if use_curated:
        all_repos.update(CURATED_AWESOME)

    if use_discovery:
        discovered = await _discover_awesome_lists()
        all_repos.update(discovered)

    all_repos = list(all_repos)[:max_repos]
    logger.info(f"Processing {len(all_repos)} Awesome list repos")

    for full_name in all_repos:
        if "/" not in full_name:
            continue

        repo_info = await _fetch_repo_info(full_name)
        if not repo_info:
            continue

        found += 1
        repo_id = f"github-{repo_info['id']}"
        owner = repo_info["owner"]["login"]
        repo_name = repo_info["name"]

        existing = db.query(Resource).filter(Resource.id == repo_id).first()

        readme = ""
        if not existing or not existing.readme:
            readme = await _fetch_readme(owner, repo_name)

        resource_data = {
            "id": repo_id,
            "name": full_name,
            "url": repo_info["html_url"],
            "source_type": "awesome-list",
            "description": repo_info.get("description") or "",
            "readme": readme,
            "language": repo_info.get("language") or "",
            "license": repo_info.get("license", {}).get("spdx_id") or "",
            "topics": repo_info.get("topics") or [],
            "stars": repo_info.get("stargazers_count", 0),
            "forks": repo_info.get("forks_count", 0),
            "last_updated": datetime.fromisoformat(
                repo_info["pushed_at"].replace("Z", "+00:00")
            ),
            "is_archived": repo_info.get("archived", False),
            "metadata": {
                "open_issues": repo_info.get("open_issues_count", 0),
                "default_branch": repo_info.get("default_branch", ""),
                "created_at": repo_info.get("created_at", ""),
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
