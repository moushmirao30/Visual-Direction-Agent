"""
utils/cache.py
Simple JSON cache for Agent 01 and Agent 02 outputs.

Why cache these two agents specifically?
  Agent 01 (Trend Researcher) makes live Tavily web searches — real API cost.
  Agent 02 (Design Theory Analyst) makes 4 RAG + 1 LLM call — CPU + token cost.
  Running the same aesthetic keyword twice during development hits full cost twice.

  Agents 03, 04, 05 are NOT cached because:
    - Agent 03 synthesis should always reflect the latest 01+02 outputs
    - Agent 04 report should always re-validate
    - Agent 05 images are already cached in moodboard_cache/ by filename hash

Cache location: visual-direction-agent/cache/
Cache key: agent_name + sha256(keyword)[:12]
Cache TTL: 24 hours (configurable via CACHE_TTL_HOURS env var)
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Default TTL: 24 hours. Set CACHE_TTL_HOURS=0 to disable TTL (keep forever).
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))


def _cache_key(agent_name: str, keyword: str) -> str:
    """Deterministic 12-char key from agent name + keyword."""
    raw = f"{agent_name}::{keyword.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _cache_path(agent_name: str, keyword: str) -> Path:
    key = _cache_key(agent_name, keyword)
    return CACHE_DIR / f"{agent_name}_{key}.json"


def load_from_cache(agent_name: str, keyword: str) -> str | None:
    """
    Returns cached output string if it exists and hasn't expired.
    Returns None on cache miss or expiry.
    """
    path = _cache_path(agent_name, keyword)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data["cached_at"])

        # TTL check
        if CACHE_TTL_HOURS > 0:
            expires_at = cached_at + timedelta(hours=CACHE_TTL_HOURS)
            if datetime.now() > expires_at:
                path.unlink()  # delete expired cache
                print(f"[CACHE] Expired cache for {agent_name} + '{keyword}' — re-running")
                return None

        age_mins = int((datetime.now() - cached_at).total_seconds() / 60)
        print(f"[CACHE] Hit: {agent_name} + '{keyword}' (cached {age_mins}m ago)")
        return data["output"]

    except Exception as e:
        print(f"[CACHE] Read error ({e}) — cache ignored")
        return None


def save_to_cache(agent_name: str, keyword: str, output: str) -> None:
    """Saves agent output to cache with current timestamp."""
    path = _cache_path(agent_name, keyword)
    payload = {
        "agent": agent_name,
        "keyword": keyword,
        "cached_at": datetime.now().isoformat(),
        "output": output,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CACHE] Saved: {agent_name} + '{keyword}' → {path.name}")


def clear_cache(agent_name: str | None = None, keyword: str | None = None) -> int:
    """
    Clears cache entries. Options:
      clear_cache()                          → clears all cache
      clear_cache(agent_name="agent_01")    → clears all entries for that agent
      clear_cache(agent_name="agent_01", keyword="quiet luxury wellness") → specific entry
    Returns count of files deleted.
    """
    deleted = 0
    if agent_name and keyword:
        path = _cache_path(agent_name, keyword)
        if path.exists():
            path.unlink()
            deleted = 1
    elif agent_name:
        for path in CACHE_DIR.glob(f"{agent_name}_*.json"):
            path.unlink()
            deleted += 1
    else:
        for path in CACHE_DIR.glob("*.json"):
            path.unlink()
            deleted += 1
    print(f"[CACHE] Cleared {deleted} cache file(s)")
    return deleted
