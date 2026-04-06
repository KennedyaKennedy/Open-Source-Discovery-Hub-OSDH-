import httpx
import json
import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import String

from app.config import settings
from app.db import Resource
from app.cache import get_cached_ai_result, cache_ai_result

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    async def _generate(self, prompt: str, system: str = "") -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 500,
                    },
                },
            )
            response.raise_for_status()
            return response.json().get("response", "")

    async def summarize_readme(self, resource_id: str, readme: str) -> str:
        cached = get_cached_ai_result(resource_id, "summary")
        if cached:
            return cached.get("result", "")

        if not readme or len(readme) < 100:
            return ""

        truncated = readme[:8000]

        system = (
            "You are a factual summarizer. Provide concise, neutral summaries of "
            "software project READMEs. Only state facts. Do not give opinions, "
            "recommendations, or rankings. Use 2-4 sentences maximum."
        )

        prompt = (
            f"Summarize this README in 2-4 factual, neutral sentences:\n\n{truncated}"
        )

        try:
            result = await self._generate(prompt, system)
            result = result.strip()
            cache_ai_result(resource_id, "summary", {"result": result})
            return result
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return ""

    async def extract_tags(
        self,
        resource_id: str,
        name: str,
        description: str,
        topics: List[str],
        readme: str = "",
    ) -> List[str]:
        cached = get_cached_ai_result(resource_id, "tags")
        if cached:
            return cached.get("result", [])

        content = (
            f"Name: {name}\nDescription: {description}\nTopics: {', '.join(topics)}"
        )
        if readme:
            content += f"\nREADME excerpt: {readme[:2000]}"

        system = (
            "You are a tag extractor. Extract 5-10 relevant keyword tags from the "
            "project information. Tags should cover: domain/industry, programming language, "
            "platform, use case, and technology. Return ONLY a JSON array of lowercase "
            'string tags. Example: ["web-scraping", "python", "cli-tool", "automation"]'
        )

        prompt = f"Extract tags from this project:\n\n{content}"

        try:
            result = await self._generate(prompt, system)
            start = result.find("[")
            end = result.rfind("]") + 1
            if start != -1 and end > start:
                tags = json.loads(result[start:end])
                tags = [t.lower().strip() for t in tags if isinstance(t, str)]
                cache_ai_result(resource_id, "tags", {"result": tags})
                return tags
        except Exception as e:
            logger.error(f"Tag extraction failed: {e}")

        return []

    def classify_maintenance_hybrid(self, resource: Resource) -> str:
        if resource.is_archived:
            return "archived"

        if resource.last_updated:
            now = datetime.now(timezone.utc)
            last_update = resource.last_updated
            if last_update.tzinfo is None:
                last_update = last_update.replace(tzinfo=timezone.utc)
            days_since = (now - last_update).days

            if days_since <= 30:
                return "active"
            if days_since <= 180:
                return "maintained"
            return "stale"

        return "needs_ai_check"

    async def detect_duplicate(
        self, resource: Resource, existing_resources: List[Resource]
    ) -> Optional[str]:
        if not existing_resources:
            return None

        candidates = existing_resources[:20]
        candidate_info = "\n".join(
            [f"- {r.name} ({r.url}): {r.description}" for r in candidates]
        )

        system = (
            "You detect duplicate or near-duplicate software projects. "
            "Compare the target project against the candidate list. "
            "If you find a project that serves the exact same purpose or is a fork, "
            'return its name. If no duplicate, return "none". '
            "Return ONLY the name or 'none', nothing else."
        )

        prompt = (
            f"Is this project a duplicate of any in the list?\n\n"
            f"Target: {resource.name} ({resource.url}): {resource.description}\n\n"
            f"Candidates:\n{candidate_info}"
        )

        try:
            result = await self._generate(prompt, system)
            result = result.strip().lower().strip('"').strip()
            if result and result != "none":
                for r in candidates:
                    if r.name.lower() == result:
                        return r.id
        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")

        return None


ollama_client = OllamaClient()


async def process_ai_tasks(
    db: Optional[Session] = None,
    log_id: Optional[str] = None,
    resource_ids: Optional[List[str]] = None,
):
    """Process AI tasks for resources needing summarization, tagging, or classification.

    If db is None (background task), creates its own session.
    """
    own_session = db is None
    if own_session:
        from app.db import SessionLocal

        db = SessionLocal()

    try:
        logger.info("Starting AI processing tasks")

        # Find resources needing ANY AI task (OR logic)
        from sqlalchemy import or_

        query = db.query(Resource).filter(
            or_(
                Resource.readme_summary == "",
                Resource.ai_tags.cast(String) == "[]",
                Resource.maintenance_status == "unknown",
            )
        )

        if resource_ids:
            query = query.filter(Resource.id.in_(resource_ids))

        resources = query.all()
        logger.info(f"Processing {len(resources)} resources with AI")

        for resource in resources:
            try:
                if not resource.readme_summary and resource.readme:
                    resource.readme_summary = await ollama_client.summarize_readme(
                        resource.id, resource.readme
                    )
                    db.commit()

                if not resource.ai_tags or resource.ai_tags == []:
                    resource.ai_tags = await ollama_client.extract_tags(
                        resource.id,
                        resource.name,
                        resource.description,
                        resource.topics or [],
                        resource.readme[:2000] if resource.readme else "",
                    )
                    db.commit()

                if resource.maintenance_status == "unknown":
                    hybrid_result = ollama_client.classify_maintenance_hybrid(resource)
                    if hybrid_result == "needs_ai_check":
                        resource.maintenance_status = (
                            await ollama_client.classify_maintenance_ai(resource)
                        )
                    else:
                        resource.maintenance_status = hybrid_result
                    db.commit()

                logger.info(f"Processed AI tasks for: {resource.name}")

            except Exception as e:
                logger.error(f"AI processing failed for {resource.name}: {e}")
                db.rollback()

        logger.info("AI processing complete")
    finally:
        if own_session:
            db.close()
