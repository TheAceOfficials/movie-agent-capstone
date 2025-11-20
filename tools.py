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

def format_results(data, media_type="movie"):
    results = []
    if 'results' in data:
        for item in data['results'][:8]: 
            path = item.get('poster_path')
            full_img = f"{IMAGE_BASE_URL}{path}" if path else "https://via.placeholder.com/500x750?text=No+Poster"
            title = item.get('title') if 'title' in item else item.get('name')
            date = item.get('release_date') if 'release_date' in item else item.get('first_air_date')
            rating = round(item.get('vote_average', 0), 1)
            
            results.append({
                "id": item.get('id'),
                "title": title,
                "overview": item.get('overview'),
                "rating": rating,
                "date": date,
                "poster_url": full_img,
                "type": media_type or item.get('media_type')
            })
    return results

# --- BASIC TOOLS ---
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

# --- SMART TOOLS ---
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

def get_ai_picks(movie_names_list):
    """ Fetches data for movies suggested by Gemini's Brain """
    results = []
    for name in movie_names_list:
        data = fetch_data("/search/multi", {"query": name})
        if 'results' in data and len(data['results']) > 0:
            formatted = format_results(data) 
            if formatted:
                results.append(formatted[0]) 
    return results

def get_media_details(media_id, media_type="movie"):
    """ Fetches Deep Details (Budget, Trailer, OTT) """
    details = fetch_data(f"/{media_type}/{media_id}")
    videos = fetch_data(f"/{media_type}/{media_id}/videos")
    
    trailer_key = None
    if 'results' in videos:
        for v in videos['results']:
            if v['site'] == 'YouTube' and v['type'] == 'Trailer':
                trailer_key = v['key']
                break
    
    providers = fetch_data(f"/{media_type}/{media_id}/watch/providers")
    ott_platforms = []
    if 'results' in providers and 'IN' in providers['results']:
        in_providers = providers['results']['IN']
        if 'flatrate' in in_providers:
            ott_platforms = [p['provider_name'] for p in in_providers['flatrate']]
    
    return {
        "id": details.get('id'),
        "title": details.get('title') or details.get('name'),
        "overview": details.get('overview'),
        "poster_url": f"{IMAGE_BASE_URL}{details.get('poster_path')}" if details.get('poster_path') else None,
        "rating": round(details.get('vote_average', 0), 1),
        "date": details.get('release_date') or details.get('first_air_date'),
        "runtime": f"{details.get('runtime')} min" if 'runtime' in details else "N/A",
        "budget": f"${details.get('budget'):,}" if details.get('budget') else "N/A",
        "revenue": f"${details.get('revenue'):,}" if details.get('revenue') else "N/A",
        "genres": [g['name'] for g in details.get('genres', [])],
        "trailer_url": f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else None,
        "ott": ott_platforms,
        "type": media_type
    }
