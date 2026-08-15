import os
import json
import logging
from typing import Any, Optional

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger("redis_cache")

class RedisCacheService:
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.client = None
        self.is_connected = False
        
        if redis is not None:
            try:
                self.client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    socket_connect_timeout=2,
                    decode_responses=True
                )
                self.client.ping()
                self.is_connected = True
                print(f"[REDIS] Connected successfully to Redis server at {self.host}:{self.port}")
            except Exception as e:
                print(f"[REDIS WARNING] Could not connect to Redis at {self.host}:{self.port}. Falling back to standard/memory mode. Details: {e}")
                self.client = None
        else:
            print("[REDIS WARNING] Redis python library not installed. Falling back to standard/memory mode.")

        # In-memory fallback
        self._memory_cache = {}

    def get(self, key: str) -> Optional[Any]:
        if self.is_connected and self.client:
            try:
                val = self.client.get(key)
                if val:
                    return json.loads(val)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        return self._memory_cache.get(key)

    def set(self, key: str, value: Any, expire_seconds: int = 30) -> bool:
        if self.is_connected and self.client:
            try:
                serialized = json.dumps(value)
                self.client.setex(key, expire_seconds, serialized)
                return True
            except Exception as e:
                logger.error(f"Redis setex error: {e}")
        
        self._memory_cache[key] = value
        return True

    def delete(self, key: str) -> bool:
        if self.is_connected and self.client:
            try:
                self.client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        if key in self._memory_cache:
            del self._memory_cache[key]
        return True

redis_cache = RedisCacheService()
