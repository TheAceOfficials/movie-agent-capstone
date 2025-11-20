import os
import requests
import streamlit as st

# Setup API Key (Safe handling for both Cloud and Local)
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
    """ Helper to clean data and add full image URLs """
    results = []
    if 'results' in data:
        for item in data['results'][:8]: # Top 8 results for grid
            path = item.get('poster_path')
            full_img = f"{IMAGE_BASE_URL}{path}" if path else "https://via.placeholder.com/500x750?text=No+Image"
            
            title = item.get('title') if 'title' in item else item.get('name')
            date = item.get('release_date') if 'release_date' in item else item.get('first_air_date')
            
            results.append({
                "id": item.get('id'),
                "title": title,
                "overview": item.get('overview'),
                "rating": item.get('vote_average'),
                "date": date,
                "poster_url": full_img,
                "type": media_type or item.get('media_type')
            })
    return results

# --- TOOL 1: Basic Search (Existing) ---
def search_media(query):
    """ Searches for a specific movie or TV show by name. """
    # Pehle movie try karo
    data = fetch_data("/search/multi", {"query": query})
    return format_results(data)

# --- TOOL 2: Trending (Existing) ---
def get_trending():
    """ Gets trending movies/shows today. """
    data = fetch_data("/trending/all/day")
    return format_results(data)

# --- TOOL 3: Deep Recommendations (NEW) ---
def get_recommendations(media_id, media_type="movie"):
    """ 
    Gets similar content based on a specific movie/show ID.
    Use this when user says 'Like Dark' or 'Similar to Inception'.
    """
    endpoint = f"/{media_type}/{media_id}/recommendations"
    data = fetch_data(endpoint)
    return format_results(data, media_type)

# --- TOOL 4: Advanced Filtering (NEW) ---
def discover_media(media_type="movie", genre_id=None, language=None, max_runtime=None, sort_by="popularity.desc"):
    """
    Filters content by criteria.
    - language: 'hi' for Hindi, 'en' for English.
    - max_runtime: minutes (e.g., 90).
    - media_type: 'movie' or 'tv'.
    """
    endpoint = f"/discover/{media_type}"
    params = {"sort_by": sort_by}
    
    if language: params['with_original_language'] = language
    if max_runtime and media_type == 'movie': params['with_runtime.lte'] = max_runtime
    if genre_id: params['with_genres'] = genre_id
    
    data = fetch_data(endpoint, params)
    return format_results(data, media_type)
