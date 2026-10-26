import hashlib
import json
import os
import time
from typing import Optional, Dict, Any

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_client = None
_redis_available = False

try:
    import redis
    try:
        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1.5)
        _redis_client.ping()
        _redis_available = True
    except Exception:
        _redis_available = False
        _redis_client = None
except ImportError:
    _redis_available = False
    _redis_client = None

# In-Memory Fallback Cache (LRU + TTL)
_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
_MAX_MEMORY_CACHE_SIZE = 250

_CACHE_STATS = {
    "hits": 0,
    "misses": 0,
    "saved_latency_seconds": 0.0,
}


def make_cache_key(question: str, model: str = "codellama:latest", top_k: int = 2, threshold: float = 0.60) -> str:
    normalized = f"{question.strip().lower()}|{model}|{top_k}|{threshold:.2f}"
    return f"rag:query:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def get_cache(key: str) -> Optional[Dict[str, Any]]:
    global _redis_available, _CACHE_STATS

    # 1. Try Redis if available
    if _redis_available and _redis_client:
        try:
            cached_val = _redis_client.get(key)
            if cached_val:
                _CACHE_STATS["hits"] += 1
                return json.loads(cached_val)
        except Exception:
            _redis_available = False

    # 2. Try Memory Cache
    now = time.time()
    if key in _MEMORY_CACHE:
        entry = _MEMORY_CACHE[key]
        if entry["expires_at"] > now:
            _CACHE_STATS["hits"] += 1
            return entry["data"]
        else:
            del _MEMORY_CACHE[key]

    _CACHE_STATS["misses"] += 1
    return None


def set_cache(key: str, data: Dict[str, Any], ttl_seconds: int = 3600) -> None:
    global _redis_available

    # 1. Store in Redis if available
    if _redis_available and _redis_client:
        try:
            _redis_client.setex(key, ttl_seconds, json.dumps(data))
            return
        except Exception:
            _redis_available = False

    # 2. Store in In-Memory Cache with eviction
    now = time.time()
    if len(_MEMORY_CACHE) >= _MAX_MEMORY_CACHE_SIZE:
        # Evict expired or oldest
        expired_keys = [k for k, v in _MEMORY_CACHE.items() if v["expires_at"] <= now]
        if expired_keys:
            for k in expired_keys:
                del _MEMORY_CACHE[k]
        else:
            oldest_key = next(iter(_MEMORY_CACHE))
            del _MEMORY_CACHE[oldest_key]

    _MEMORY_CACHE[key] = {
        "data": data,
        "expires_at": now + ttl_seconds,
    }


def record_saved_latency(latency: float) -> None:
    _CACHE_STATS["saved_latency_seconds"] += max(0.0, latency)


def clear_cache() -> int:
    """
    Purges all cached query responses from both In-Memory and Redis tiers.
    Ensures that updated documents immediately reflect in new chat queries.
    Returns the count of purged items.
    """
    global _redis_available, _MEMORY_CACHE
    cleared = len(_MEMORY_CACHE)
    _MEMORY_CACHE.clear()

    if _redis_available and _redis_client:
        try:
            keys = _redis_client.keys("rag:query:*")
            if keys:
                _redis_client.delete(*keys)
                cleared += len(keys)
        except Exception:
            _redis_available = False

    return cleared


def get_cache_stats() -> Dict[str, Any]:
    total = _CACHE_STATS["hits"] + _CACHE_STATS["misses"]
    hit_ratio = (_CACHE_STATS["hits"] / total * 100.0) if total > 0 else 0.0
    return {
        "backend": "redis" if _redis_available else "in-memory-lru",
        "redis_connected": _redis_available,
        "hits": _CACHE_STATS["hits"],
        "misses": _CACHE_STATS["misses"],
        "hit_ratio_percent": round(hit_ratio, 2),
        "saved_latency_seconds": round(_CACHE_STATS["saved_latency_seconds"], 2),
        "cached_entries_count": len(_MEMORY_CACHE) if not _redis_available else "redis-managed",
    }
