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

EDUCATIONAL_REPOS = [
    "ossu/computer-science",
    "EbookFoundation/free-programming-books",
    "jwasham/coding-interview-university",
    "kamranahmedse/developer-roadmap",
    "trekhleb/javascript-algorithms",
    "TheAlgorithms/Python",
    "freeCodeCamp/freeCodeCamp",
    "public-apis/public-apis",
    "sindresorhus/awesome",
    "CyberSecurityUP/Awesome-Certifications",
    "brianwgoldstein/Awesome-Cybersecurity-Certifications",
    "PumpkinSeed/awesome-k8s",
]

CERTIFICATION_LISTS = [
    "CyberSecurityUP/Awesome-Certifications",
    "brianwgoldstein/Awesome-Cybersecurity-Certifications",
    "infosecn1nja/AD-Attack-Defense",
    "enaqx/awesome-pentest",
    "hslatman/awesome-threat-intelligence",
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


async def aggregate_educational(
    db: Session,
    include_certs: bool = True,
) -> Tuple[int, int, int]:
    found = 0
    added = 0
    updated = 0

    all_repos = set(EDUCATIONAL_REPOS)
    if include_certs:
        all_repos.update(CERTIFICATION_LISTS)

    logger.info(f"Processing {len(all_repos)} educational/certification repos")

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

        is_cert = full_name in CERTIFICATION_LISTS
        source_type = "certificate-list" if is_cert else "educational"

        resource_data = {
            "id": repo_id,
            "name": full_name,
            "url": repo_info["html_url"],
            "source_type": source_type,
            "description": repo_info.get("description") or "",
            "readme": readme,
            "language": repo_info.get("language") or "",
            "license": (repo_info.get("license") or {}).get("spdx_id") or "",
            "topics": repo_info.get("topics") or [],
            "stars": repo_info.get("stargazers_count", 0),
            "forks": repo_info.get("forks_count", 0),
            "last_updated": datetime.fromisoformat(
                repo_info["pushed_at"].replace("Z", "+00:00")
            ),
            "is_archived": repo_info.get("archived", False),
            "extra_metadata": {
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
