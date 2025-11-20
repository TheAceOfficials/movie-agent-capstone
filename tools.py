import os
import requests
import streamlit as st
from datetime import datetime # Date check karne ke liye

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
        for item in data['results'][:8]: # Top 8 results
            path = item.get('poster_path')
            # Agar poster nahi hai toh khali placeholder
            full_img = f"{IMAGE_BASE_URL}{path}" if path else "https://via.placeholder.com/500x750?text=No+Poster"
            
            title = item.get('title') if 'title' in item else item.get('name')
            date = item.get('release_date') if 'release_date' in item else item.get('first_air_date')
            rating = round(item.get('vote_average', 0), 1) # Rating ko round of kiya (e.g 7.2)
            
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

# --- TOOL 1: Search ---
def search_media(query):
    data = fetch_data("/search/multi", {"query": query})
    return format_results(data)

# --- TOOL 2: Trending ---
def get_trending():
    data = fetch_data("/trending/all/day")
    return format_results(data)

# --- TOOL 3: Recommendations ---
def get_recommendations(media_id, media_type="movie"):
    endpoint = f"/{media_type}/{media_id}/recommendations"
    data = fetch_data(endpoint)
    return format_results(data, media_type)

# --- TOOL 4: Advanced Discover (DATE FIX ADDED HERE) ---
def discover_media(media_type="movie", genre_id=None, language=None, max_runtime=None, include_upcoming=False):
    """
    Filters content. 
    IMPORTANT: 'include_upcoming=True' tabhi use karna jab user future movies mange.
    """
    endpoint = f"/discover/{media_type}"
    params = {"sort_by": "popularity.desc"}
    
    # 1. Language Fix
    if language: params['with_original_language'] = language
    
    # 2. Runtime Fix
    if max_runtime and media_type == 'movie': params['with_runtime.lte'] = max_runtime
    
    # 3. DATE FIX: Agar upcoming nahi manga, toh future content hatao
    if not include_upcoming:
        today = datetime.now().strftime("%Y-%m-%d")
        params['primary_release_date.lte'] = today
        params['air_date.lte'] = today

    data = fetch_data(endpoint, params)
    return format_results(data, media_type)
