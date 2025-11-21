import os
import requests
import streamlit as st
from datetime import datetime

# Setup API Key
try:
    TMDB_API_KEY = st.secrets["TMDB_API_KEY"]
except:
    from dotenv import load_dotenv
    load_dotenv()
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

def fetch_data(endpoint, params={}):
    params['api_key'] = TMDB_API_KEY
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, params=params)
    return response.json()

def format_results(data, default_media_type="movie"):
    results = []
    if 'results' in data:
        for item in data['results'][:10]: # Top 10 results layenge
            # Ignore people/actors in search results
            if item.get('media_type') == 'person':
                continue

            path = item.get('poster_path')
            full_img = f"{IMAGE_BASE_URL}{path}" if path else "https://via.placeholder.com/500x750?text=No+Poster"
            title = item.get('title') if 'title' in item else item.get('name')
            date = item.get('release_date') if 'release_date' in item else item.get('first_air_date')
            rating = round(item.get('vote_average', 0), 1)
            
            # CRITICAL FIX: Ensure Media Type is captured correctly
            media_type = item.get('media_type') or default_media_type
            
            results.append({
                "id": item.get('id'),
                "title": title,
                "overview": item.get('overview'),
                "rating": rating,
                "date": date,
                "poster_url": full_img,
                "type": media_type  # Ye batayega ki Movie hai ya Series
            })
    return results

# --- TOOLS ---
def search_media(query):
    data = fetch_data("/search/multi", {"query": query})
    return format_results(data)

def get_trending():
    data = fetch_data("/trending/all/day")
    return format_results(data)

def get_recommendations(media_id, media_type="movie"):
    endpoint = f"/{media_type}/{media_id}/recommendations"
    data = fetch_data(endpoint)
    return format_results(data, media_type)

def discover_media(media_type="movie", genre_id=None, language=None, max_runtime=None, include_upcoming=False):
    endpoint = f"/discover/{media_type}"
    params = {"sort_by": "popularity.desc"}
    if language: params['with_original_language'] = language
    if max_runtime and media_type == 'movie': params['with_runtime.lte'] = max_runtime
    if not include_upcoming:
        today = datetime.now().strftime("%Y-%m-%d")
        params['primary_release_date.lte'] = today
        params['air_date.lte'] = today
    data = fetch_data(endpoint, params)
    return format_results(data, media_type)

# --- UPDATED SMART TOOL (Strict Filtering) ---
def get_ai_picks(movie_names_list, specific_type=None):
    """
    Fetches data for movies suggested by Gemini.
    specific_type: 'movie', 'tv', or 'anime' (to filter strictly)
    """
    results = []
    for name in movie_names_list:
        # Hum zyada results mangenge taaki filter kar sakein
        data = fetch_data("/search/multi", {"query": name})
        
        found_match = False
        if 'results' in data:
            for item in data['results']:
                # Skip people
                if item.get('media_type') == 'person': continue
                
                # --- STRICT FILTERING LOGIC ---
                is_valid = True
                
                if specific_type == 'anime':
                    # Anime hona chahiye (Genre ID 16 = Animation)
                    genre_ids = item.get('genre_ids', [])
                    if 16 not in genre_ids: 
                        is_valid = False # Ye Animation nahi hai, skip karo
                
                elif specific_type == 'movie':
                    if item.get('media_type') != 'movie': is_valid = False
                    
                elif specific_type == 'tv':
                    if item.get('media_type') != 'tv': is_valid = False

                # Agar valid hai, toh isse add karo aur loop break karo
                if is_valid:
                    formatted = format_results({'results': [item]})
                    if formatted:
                        results.append(formatted[0])
                        found_match = True
                        break 
            
            # Agar strict filter ke baad bhi kuch nahi mila, toh fallback (First result)
            # Lekin Anime ke case mai fallback nahi karenge taaki galti na ho
            if not found_match and specific_type != 'anime':
                 if len(data['results']) > 0:
                    formatted = format_results({'results': [data['results'][0]]})
                    if formatted: results.append(formatted[0])

    return results

def get_media_details(media_id, media_type="movie"):
    """ Fetches Deep Details (Budget, Trailer, OTT, Cast, Runtime) """
    details = fetch_data(f"/{media_type}/{media_id}")
    
    # 1. Cast / Credits
    credits = fetch_data(f"/{media_type}/{media_id}/credits")
    cast = []
    if 'cast' in credits:
        cast = [c['name'] for c in credits['cast'][:5]] # Top 5 actors

    # 2. Trailer
    videos = fetch_data(f"/{media_type}/{media_id}/videos")
    trailer_key = None
    if 'results' in videos:
        for v in videos['results']:
            if v['site'] == 'YouTube' and v['type'] == 'Trailer':
                trailer_key = v['key']
                break
    
    # 3. OTT Providers (India)
    providers = fetch_data(f"/{media_type}/{media_id}/watch/providers")
    ott_platforms = []
    if 'results' in providers and 'IN' in providers['results']:
        in_providers = providers['results']['IN']
        if 'flatrate' in in_providers:
            ott_platforms = [p['provider_name'] for p in in_providers['flatrate']]
    
    # 4. Runtime Logic (Series vs Movie)
    runtime_val = "N/A"
    if 'runtime' in details and details['runtime']:
        runtime_val = f"{details['runtime']} min"
    elif 'episode_run_time' in details and details['episode_run_time']:
        runtime_val = f"{details['episode_run_time'][0]} min"
    
    # Data Packaging
    return {
        "id": details.get('id'),
        "title": details.get('title') or details.get('name'),
        "overview": details.get('overview'),
        "poster_url": f"{IMAGE_BASE_URL}{details.get('poster_path')}" if details.get('poster_path') else None,
        "rating": round(details.get('vote_average', 0), 1),
        "date": details.get('release_date') or details.get('first_air_date'),
        "runtime": runtime_val, # Fixed Runtime
        "genres": [g['name'] for g in details.get('genres', [])], # Fixed Genres
        "trailer_url": f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else None,
        "ott": ott_platforms,
        "type": media_type,
        "cast": cast,
        # MOVIE Specific
        "budget": f"${details.get('budget'):,}" if details.get('budget') else None,
        "revenue": f"${details.get('revenue'):,}" if details.get('revenue') else None,
        # TV Specific
        "seasons": details.get('number_of_seasons'),
        "episodes": details.get('number_of_episodes')
    }
