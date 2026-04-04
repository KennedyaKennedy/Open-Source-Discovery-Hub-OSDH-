import os
import hashlib
import json
import time
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _ensure_cache_dir():
    if not os.path.exists(settings.OSDH_CACHE_DIR):
        os.makedirs(settings.OSDH_CACHE_DIR, exist_ok=True)


def _cache_key(*parts) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached(key: str, ttl: int = 86400) -> Optional[str]:
    _ensure_cache_dir()
    cache_file = os.path.join(settings.OSDH_CACHE_DIR, key)
    if not os.path.exists(cache_file):
        return None
    try:
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime > ttl:
            os.remove(cache_file)
            return None
        with open(cache_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def set_cached(key: str, content: str):
    _ensure_cache_dir()
    cache_file = os.path.join(settings.OSDH_CACHE_DIR, key)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Cache write failed for {key}: {e}")


def cache_readme(url: str, content: str):
    key = _cache_key("readme", url)
    set_cached(key, content)
    return key


def get_cached_readme(url: str) -> Optional[str]:
    key = _cache_key("readme", url)
    return get_cached(key, ttl=604800)


def cache_ai_result(resource_id: str, task: str, result):
    key = _cache_key("ai", resource_id, task)
    set_cached(key, json.dumps(result))


def get_cached_ai_result(resource_id: str, task: str) -> Optional[dict]:
    key = _cache_key("ai", resource_id, task)
    raw = get_cached(key, ttl=2592000)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            return None
    return None
