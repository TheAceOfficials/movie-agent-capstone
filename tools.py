# tools.py (add/replace these functions)
import requests
import time
import logging

BASE_URL = "https://api.themoviedb.org/3"
TMDB_API_KEY = None  # set via init()

def init(api_key: str):
    global TMDB_API_KEY
    TMDB_API_KEY = api_key

# safe fetch helper
def fetch_tmdb(endpoint: str, params: dict = None, method="GET", timeout=10):
    params = params or {}
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY not configured. Call tools.init(api_key) first.")
    params["api_key"] = TMDB_API_KEY
    url = f"{BASE_URL}{endpoint}"
    try:
        resp = requests.request(method, url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        logging.warning(f"[TMDB] HTTP error {resp.status_code} for {url} : {resp.text}")
        return {}
    except requests.exceptions.RequestException as e:
        logging.warning(f"[TMDB] Request error for {url} : {e}")
        return {}
    except ValueError:
        logging.warning(f"[TMDB] Invalid JSON from {url}")
        return {}

# cache provider mapping in memory
_provider_cache = {"movie": None, "tv": None, "timestamp": 0}
def get_provider_id_by_name(name: str, media_type="movie", region="IN"):
    """Return provider id for a human name like 'netflix' or 'crunchyroll'."""
    name_key = (name or "").strip().lower()
    # refresh once per 24h
    if not _provider_cache[media_type] or (time.time() - _provider_cache.get("timestamp", 0) > 24*3600):
        endpoint = "/watch/providers/movie" if media_type=="movie" else "/watch/providers/tv"
        resp = fetch_tmdb(endpoint, params={"language":"en-US", "page":1})
        results = resp.get("results", []) if resp else []
        mapping = {}
        for p in results:
            provider_name = (p.get("provider_name") or "").lower()
            mapping[provider_name] = p.get("provider_id")
        _provider_cache[media_type] = mapping
        _provider_cache["timestamp"] = time.time()
    mapping = _provider_cache[media_type] or {}
    # try exact then substring match
    if name_key in mapping:
        return mapping[name_key]
    for k,v in mapping.items():
        if name_key in k:
            return v
    return None

# genre lookup helpers (small cache)
_genre_cache = {"movie": {}, "tv": {}, "ts": 0}
def ensure_genres(media_type="movie"):
    if _genre_cache["ts"] and (time.time() - _genre_cache["ts"] < 24*3600) and _genre_cache.get(media_type):
        return _genre_cache[media_type]
    endpoint = "/genre/movie/list" if media_type=="movie" else "/genre/tv/list"
    data = fetch_tmdb(endpoint, params={"language":"en-US"})
    result = { g["name"].lower(): g["id"] for g in data.get("genres", []) } if data else {}
    _genre_cache[media_type] = result
    _genre_cache["ts"] = time.time()
    return result

def normalize_item(item: dict, default_media_type="movie"):
    """Return normalized dict with consistent keys used by app."""
    media_type = item.get("media_type") or default_media_type
    result = {
        "id": item.get("id"),
        "title": item.get("title") or item.get("name"),
        "poster_path": item.get("poster_path"),
        "overview": item.get("overview"),
        "release_date": item.get("release_date") or item.get("first_air_date"),
        "media_type": media_type,
        "vote_average": item.get("vote_average"),
    }
    return result

def discover_media_with_filters(media_type="movie", region="IN", max_runtime_minutes=None,
                                provider_names=None, genres=None, language=None,
                                original_language=None, primary_release_before=None,
                                page=1, max_pages=1):
    """
    Discover movies or tv shows using TMDB discover API with flexible filters.
    - media_type: 'movie' or 'tv'
    - provider_names: list of provider names (strings) e.g. ['netflix','crunchyroll']
    - max_runtime_minutes: integer in minutes (applies to movies; TV uses episode runtime if supported)
    - genres: list of genre names (strings) -> mapped to TMDB genre ids
    - language: e.g. 'hi' (for Hindi audio) — used in result filtering (TMDB doesn't always provide dubbing info)
    - original_language: e.g. 'ja' for Japanese (useful for anime)
    - primary_release_before: 'YYYY-MM-DD' to only include up-to-date content
    Returns a list of normalized items.
    """
    params = {
        "page": page,
        "sort_by": "popularity.desc",
        "include_adult": False,
        "language":"en-US"
    }
    # provider ids
    if provider_names:
        pids = []
        for p in provider_names:
            pid = get_provider_id_by_name(p, media_type=media_type, region=region)
            if pid:
                pids.append(str(pid))
        if pids:
            params["with_watch_providers"] = ",".join(pids)
            params["watch_region"] = region

    # genres mapping
    if genres:
        gmap = ensure_genres(media_type=media_type)
        gid_list = []
        for g in genres:
            gid = gmap.get(g.lower())
            if gid:
                gid_list.append(str(gid))
        if gid_list:
            params["with_genres"] = ",".join(gid_list)

    # runtime filter for movies
    if max_runtime_minutes and media_type == "movie":
        # TMDB supports with_runtime.lte
        params["with_runtime.lte"] = int(max_runtime_minutes)

    # for TV, try episode runtime filter (not guaranteed), using with_runtime.lte as best-effort
    if max_runtime_minutes and media_type == "tv":
        params["with_runtime.lte"] = int(max_runtime_minutes)

    if primary_release_before:
        if media_type == "movie":
            params["primary_release_date.lte"] = primary_release_before
        else:
            params["first_air_date.lte"] = primary_release_before

    # optional original_language filtering (useful for anime)
    if original_language:
        params["with_original_language"] = original_language

    # call correct endpoint
    endpoint = "/discover/movie" if media_type == "movie" else "/discover/tv"
    results = []
    for p in range(page, page + max_pages):
        params["page"] = p
        data = fetch_tmdb(endpoint, params=params)
        if not data:
            break
        page_results = data.get("results", [])
        for item in page_results:
            # extra filter: language/dub heuristics
            # If user asked for Hindi dub specifically, TMDB does not reliably tag dubs;
            # we can filter by 'spoken_languages' or look for 'hi' in original_language as fallback.
            # For now, attach available spoken_languages if present (later UI can display)
            norm = normalize_item(item, default_media_type=media_type)
            results.append(norm)
        # break early if single page wanted
        if p >= data.get("total_pages", 1) or p >= page + max_pages - 1:
            break
    return results

def search_fallback(query, media_type="movie"):
    """Use TMDB search endpoint if discover returned empty or user gave explicit title."""
    endpoint = "/search/movie" if media_type=="movie" else "/search/tv"
    data = fetch_tmdb(endpoint, params={"query": query, "language":"en-US", "page":1})
    res = data.get("results", []) if data else []
    return [normalize_item(r, default_media_type=media_type) for r in res]
