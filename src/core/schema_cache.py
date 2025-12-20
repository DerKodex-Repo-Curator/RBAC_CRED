"""
Schema Cache - Caches discovered schemas to avoid repeated API calls.
"""

import json
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from src.mock_apis import RolesPermissionsAPI, ResourceSchemaAPI, ContextSchemaAPI


class SchemaCache:
    """
    Caches schema discovery results to improve performance.
    Persists cache to disk for recovery across restarts.
    """
    
    DEFAULT_TTL_SECONDS = 3600  # 1 hour
    CACHE_FILE = "data/schema_cache.json"
    
    def __init__(self, cache_dir: str = "data", ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "schema_cache.json")
        self.ttl_seconds = ttl_seconds
        
        # In-memory cache
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # Ensure cache directory exists
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        # Load cache from disk if available
        self._load_cache()
    
    def _load_cache(self) -> bool:
        """Load cache from disk."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self._cache = data.get("cache", {})
                    self._cache_timestamps = {
                        k: v for k, v in data.get("timestamps", {}).items()
                    }
                    return True
        except Exception as e:
            print(f"Warning: Could not load cache: {e}")
        return False
    
    def _save_cache(self) -> bool:
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    "cache": self._cache,
                    "timestamps": self._cache_timestamps,
                    "saved_at": datetime.utcnow().isoformat()
                }, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
            return False
    
    def is_valid(self, key: str) -> bool:
        """Check if a cached item is still valid."""
        if key not in self._cache or key not in self._cache_timestamps:
            return False
        
        cached_time = self._cache_timestamps[key]
        return (time.time() - cached_time) < self.ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get an item from cache if valid."""
        if self.is_valid(key):
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set an item in cache."""
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
        self._save_cache()
    
    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry."""
        self._cache.pop(key, None)
        self._cache_timestamps.pop(key, None)
        self._save_cache()
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._cache_timestamps.clear()
        self._save_cache()
    
    def discover_and_cache_schemas(
        self,
        roles_api: RolesPermissionsAPI,
        resource_api: ResourceSchemaAPI,
        context_api: ContextSchemaAPI,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Discover all schemas and cache them.
        Returns cached data if valid, otherwise fetches fresh data.
        """
        cache_key = "all_schemas"
        
        if not force_refresh:
            cached = self.get(cache_key)
            if cached:
                return cached
        
        # Fetch fresh data from APIs
        schemas = {
            "roles": roles_api.discover(),
            "resources": resource_api.discover(),
            "context": context_api.discover(),
            "discovered_at": datetime.utcnow().isoformat(),
        }
        
        # Cache the result
        self.set(cache_key, schemas)
        
        return schemas
    
    def get_roles_schema(self) -> Optional[Dict]:
        """Get cached roles schema."""
        all_schemas = self.get("all_schemas")
        if all_schemas:
            return all_schemas.get("roles")
        return None
    
    def get_resources_schema(self) -> Optional[Dict]:
        """Get cached resources schema."""
        all_schemas = self.get("all_schemas")
        if all_schemas:
            return all_schemas.get("resources")
        return None
    
    def get_context_schema(self) -> Optional[Dict]:
        """Get cached context schema."""
        all_schemas = self.get("all_schemas")
        if all_schemas:
            return all_schemas.get("context")
        return None
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the cache state."""
        info = {
            "cache_file": self.cache_file,
            "ttl_seconds": self.ttl_seconds,
            "entries": len(self._cache),
            "keys": list(self._cache.keys()),
        }
        
        for key, timestamp in self._cache_timestamps.items():
            age_seconds = time.time() - timestamp
            info[f"{key}_age_seconds"] = age_seconds
            info[f"{key}_valid"] = age_seconds < self.ttl_seconds
        
        return info
