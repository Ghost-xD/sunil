"""
Cache Module - SQLite-based caching for HTML and LLM responses
Saves tokens during development by caching webpage HTML and LLM analysis results.
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any


class Cache:
    """SQLite-based cache for HTML content and LLM responses."""
    
    def __init__(self, db_path: str = "src/.cache/test_cache.db", ttl_hours: int = 24):
        """
        Initialize cache.
        
        Args:
            db_path: Path to SQLite database file
            ttl_hours: Time-to-live for cache entries in hours (default: 24)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # HTML cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS html_cache (
                url TEXT PRIMARY KEY,
                html TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        # LLM response cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                request_hash TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        # Popup HTML cache table (keyed by normalized structure)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS popup_cache (
                structure_key TEXT PRIMARY KEY,
                html TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_html_expires ON html_cache(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_expires ON llm_cache(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_popup_expires ON popup_cache(expires_at)")
        
        conn.commit()
        conn.close()
    
    def get_html(self, url: str) -> Optional[str]:
        """
        Get cached HTML for a URL.
        
        Args:
            url: The URL to get HTML for
            
        Returns:
            Cached HTML string or None if not found/expired
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT html FROM html_cache 
            WHERE url = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (url,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print(f"[CACHE] ✓ HTML cache HIT for {url}")
            return result[0]
        else:
            print(f"[CACHE] ✗ HTML cache MISS for {url}")
            return None
    
    def set_html(self, url: str, html: str):
        """
        Cache HTML for a URL.
        
        Args:
            url: The URL
            html: HTML content to cache
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(hours=self.ttl_hours)
        
        cursor.execute("""
            INSERT OR REPLACE INTO html_cache (url, html, cached_at, expires_at)
            VALUES (?, ?, datetime('now'), ?)
        """, (url, html, expires_at))
        
        conn.commit()
        conn.close()
        print(f"[CACHE] ✓ Cached HTML for {url} (expires in {self.ttl_hours}h)")
    
    def get_llm_response(self, prompt: str, model: str) -> Optional[str]:
        """
        Get cached LLM response.
        
        Args:
            prompt: The prompt sent to LLM
            model: Model name
            
        Returns:
            Cached response or None if not found/expired
        """
        # Create hash of prompt + model
        request_hash = hashlib.md5(f"{model}:{prompt}".encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT response FROM llm_cache 
            WHERE request_hash = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (request_hash,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print(f"[CACHE] ✓ LLM cache HIT (saved tokens!)")
            return result[0]
        else:
            print(f"[CACHE] ✗ LLM cache MISS")
            return None
    
    def set_llm_response(self, prompt: str, response: str, model: str):
        """
        Cache LLM response.
        
        Args:
            prompt: The prompt sent to LLM
            response: LLM response to cache
            model: Model name
        """
        request_hash = hashlib.md5(f"{model}:{prompt}".encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(hours=self.ttl_hours)
        
        cursor.execute("""
            INSERT OR REPLACE INTO llm_cache (request_hash, prompt, response, model, cached_at, expires_at)
            VALUES (?, ?, ?, ?, datetime('now'), ?)
        """, (request_hash, prompt, response, model, expires_at))
        
        conn.commit()
        conn.close()
        print(f"[CACHE] ✓ Cached LLM response")
    
    def clear_expired(self):
        """Remove expired cache entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM html_cache WHERE expires_at <= datetime('now')")
        html_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM llm_cache WHERE expires_at <= datetime('now')")
        llm_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"[CACHE] Cleared {html_deleted} HTML + {llm_deleted} LLM expired entries")
    
    def get_popup_html(self, structure_key: str) -> Optional[str]:
        """
        Get cached popup HTML by normalized structure key.
        
        Args:
            structure_key: Normalized popup structure (button texts, etc.)
            
        Returns:
            Cached popup HTML or None if not found/expired
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT html FROM popup_cache 
            WHERE structure_key = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (structure_key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print(f"[CACHE] ✓ Popup HTML cache HIT (structure key: {structure_key[:50]}...)")
            return result[0]
        else:
            print(f"[CACHE] ✗ Popup HTML cache MISS")
            return None
    
    def set_popup_html(self, structure_key: str, html: str):
        """
        Cache popup HTML by normalized structure key.
        
        Args:
            structure_key: Normalized popup structure (button texts, etc.)
            html: Popup HTML content to cache
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(hours=self.ttl_hours)
        
        cursor.execute("""
            INSERT OR REPLACE INTO popup_cache (structure_key, html, cached_at, expires_at)
            VALUES (?, ?, datetime('now'), ?)
        """, (structure_key, html, expires_at))
        
        conn.commit()
        conn.close()
        print(f"[CACHE] ✓ Cached popup HTML (structure key: {structure_key[:50]}..., expires in {self.ttl_hours}h)")
    
    def clear_all(self):
        """Clear all cache entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM html_cache")
        cursor.execute("DELETE FROM llm_cache")
        cursor.execute("DELETE FROM popup_cache")
        
        conn.commit()
        conn.close()
        
        print(f"[CACHE] ✓ Cleared all cache")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM html_cache")
        html_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM llm_cache")
        llm_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM popup_cache")
        popup_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM html_cache WHERE expires_at <= datetime('now')")
        html_expired = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM llm_cache WHERE expires_at <= datetime('now')")
        llm_expired = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM popup_cache WHERE expires_at <= datetime('now')")
        popup_expired = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "html_entries": html_count,
            "html_expired": html_expired,
            "llm_entries": llm_count,
            "llm_expired": llm_expired,
            "popup_entries": popup_count,
            "popup_expired": popup_expired,
            "ttl_hours": self.ttl_hours
        }


# Global cache instance
_cache_instance = None
_cache_enabled = True  # Can be disabled via environment variable


def get_cache(enabled: bool = None) -> Optional[Cache]:
    """
    Get or create global cache instance.
    
    Args:
        enabled: Override cache enabled status
        
    Returns:
        Cache instance or None if disabled
    """
    global _cache_instance, _cache_enabled
    
    import os
    
    # Check environment variable
    if enabled is None:
        enabled = os.getenv("ENABLE_CACHE", "true").lower() in ("true", "1", "yes")
    
    _cache_enabled = enabled
    
    if not _cache_enabled:
        return None
    
    if _cache_instance is None:
        ttl_hours = int(os.getenv("CACHE_TTL_HOURS", "24"))
        _cache_instance = Cache(ttl_hours=ttl_hours)
    
    return _cache_instance

