"""
tools.py

TMDB helper utilities for Movie-Agent Capstone.
- call tools.init(api_key) once from app.py
- provides discover_media_with_filters, search_fallback, provider & genre helpers
- defensive network handling, simple caching in-memory
"""

import requests
import time
import logging
from typing import List, Optional, Dict

BASE_URL = "https://api.themoviedb.org/3"
TMDB_API_KEY: Optional[str] = None

def init(api_key: str):
    """Initialize module with TMDB API key (call from app start)."""
    global TMDB_API_KEY
    TMDB_API_KEY = api_key

def _ensure_api_key():
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY not set. Call tools.init(api_key) first.")

# --- safe TMDB fetch helper
def fetch_tmdb(endpoint: str, params: Dict = None, method: str = "GET", timeout: int = 10):
    params = dict(params or {})
    _ensure_api_key()
    params["api_key"] = TMDB_API_KEY
    url = f"{BASE_URL}{endpoint}"
    try:
        resp = requests.request(method, url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        try:
            status = resp.status_code
            text = resp.text
        except Exception:
            status = "?"
            text = str(e)
        logging.warning(f"[TMDB] HTTP error {status} for {url} : {text}")
        return {}
    except requests.exceptions.RequestException as e:
        logging.warning(f"[TMDB] Request error for {url} : {e}")
        return {}
    except ValueError:
        logging.warning(f"[TMDB] Invalid JSON from {url}")
        return {}

# --- provider and genre caches
_provider_cache = {"movie": None, "tv": None, "timestamp": 0}
_genre_cache = {"movie": None, "tv": None, "timestamp": 0}

def get_provider_id_by_name(name: str, media_type: str = "movie", region: str = "IN"):
    """Return provider id for a human name like 'netflix' or 'crunchyroll' or None."""
    if not name:
        return None
    name_key = name.strip().lower()
    # refresh mapping once per 24h
    if not _provider_cache.get(media_type) or (time.time() - _provider_cache.get("timestamp", 0) > 24*3600):
        endpoint = "/watch/providers/movie" if media_type == "movie" else "/watch/providers/tv"
        resp = fetch_tmdb(endpoint, params={"language": "en-US", "page": 1})
        results = resp.get("results", []) if resp else []
        mapping = {}
        for p in results:
            provider_name = (p.get("provider_name") or "").lower()
            mapping[provider_name] = p.get("provider_id")
        _provider_cache[media_type] = mapping
        _provider_cache["timestamp"] = time.time()
    mapping = _provider_cache.get(media_type) or {}
    # exact match
    if name_key in mapping:
        return mapping[name_key]
    # substring match
    for k, v in mapping.items():
        if name_key in k:
            return v
    return None

def ensure_genres(media_type: str = "movie"):
    """Return dict name->id for TMDB genres for the media_type."""
    if _genre_cache.get("timestamp") and (time.time() - _genre_cache.get("timestamp", 0) < 24*3600) and _genre_cache.get(media_type):
        return _genre_cache[media_type]
    endpoint = "/genre/movie/list" if media_type == "movie" else "/genre/tv/list"
    data = fetch_tmdb(endpoint, params={"language": "en-US"})
    result = {g["name"].lower(): g["id"] for g in data.get("genres", [])} if data else {}
    _genre_cache[media_type] = result
    _genre_cache["timestamp"] = time.time()
    return result

# --- normalization
def normalize_item(item: dict, default_media_type: str = "movie"):
    """Normalize raw TMDB item into a consistent dict used by the app."""
    media_type = item.get("media_type") or default_media_type
    title = item.get("title") or item.get("name") or item.get("original_title") or item.get("original_name")
    poster = item.get("poster_path")
    return {
        "id": item.get("id"),
        "title": title,
        "poster_path": poster,
        "overview": item.get("overview"),
        "release_date": item.get("release_date") or item.get("first_air_date"),
        "media_type": media_type,
        "vote_average": item.get("vote_average"),
        "raw": item
    }

# --- discover function that uses correct endpoints and filters
def discover_media_with_filters(
    media_type: str = "movie",
    region: str = "IN",
    max_runtime_minutes: Optional[int] = None,
    provider_names: Optional[List[str]] = None,
    genres: Optional[List[str]] = None,
    language: Optional[str] = None,
    original_language: Optional[str] = None,
    primary_release_before: Optional[str] = None,
    page: int = 1,
    max_pages: int = 1,
) -> List[dict]:
    """
    Discover movies or TV shows using TMDB discover API with flexible filters.
    Returns list of normalized items (may be empty).
    """
    params = {
        "page": page,
        "sort_by": "popularity.desc",
        "include_adult": False,
        "language": "en-US",
    }
    # providers -> map names to ids
    if provider_names:
        pids = []
        for p in provider_names:
            pid = get_provider_id_by_name(p, media_type=media_type, region=region)
            if pid:
                pids.append(str(pid))
        if pids:
            params["with_watch_providers"] = ",".join(pids)
            params["watch_region"] = region

    # genres -> map to ids
    if genres:
        gmap = ensure_genres(media_type=media_type)
        gid_list = []
        for g in genres:
            if not g:
                continue
            gid = gmap.get(g.lower())
            if gid:
                gid_list.append(str(gid))
        if gid_list:
            params["with_genres"] = ",".join(gid_list)

    # runtime filter
    if max_runtime_minutes and media_type == "movie":
        params["with_runtime.lte"] = int(max_runtime_minutes)
    if max_runtime_minutes and media_type == "tv":
        # TMDB's runtime filters for TV are not always consistent; try best-effort
        params["with_runtime.lte"] = int(max_runtime_minutes)

    # release date bounds
    if primary_release_before:
        if media_type == "movie":
            params["primary_release_date.lte"] = primary_release_before
        else:
            params["first_air_date.lte"] = primary_release_before

    # original language
    if original_language:
        params["with_original_language"] = original_language

    endpoint = "/discover/movie" if media_type == "movie" else "/discover/tv"
    results = []
    for p in range(page, page + max_pages):
        params["page"] = p
        data = fetch_tmdb(endpoint, params=params)
        if not data:
            break
        page_results = data.get("results", []) or []
        for item in page_results:
            results.append(normalize_item(item, default_media_type=media_type))
        if p >= data.get("total_pages", 1) or p >= page + max_pages - 1:
            break
    return results

def search_fallback(query: str, media_type: str = "movie", max_results: int = 10) -> List[dict]:
    """Search endpoint fallback: use when discover returns empty or when user specified a title."""
    endpoint = "/search/movie" if media_type == "movie" else "/search/tv"
    data = fetch_tmdb(endpoint, params={"query": query, "language": "en-US", "page": 1})
    res = data.get("results", []) if data else []
    return [normalize_item(r, default_media_type=media_type) for r in res[:max_results]]

# convenience: build poster full url
def poster_url(poster_path: Optional[str], size: str = "w342") -> Optional[str]:
    if not poster_path:
        return None
    return f"https://image.tmdb.org/t/p/{size}{poster_path}"
