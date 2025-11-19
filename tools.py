import os
import requests
from dotenv import load_dotenv

# Load API keys
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

def fetch_tmdb_data(endpoint, params={}):
    """
    Universal function to talk to TMDB
    """
    base_url = "https://api.themoviedb.org/3"
    url = f"{base_url}{endpoint}"
    params['api_key'] = TMDB_API_KEY
    params['language'] = 'en-US'
    
    response = requests.get(url, params=params)
    return response.json()

def search_media(query, media_type="movie"):
    """
    Searches for movies or tv shows based on query.
    media_type can be 'movie' or 'tv'
    """
    endpoint = f"/search/{media_type}"
    params = {"query": query}
    data = fetch_tmdb_data(endpoint, params)
    
    results = []
    if 'results' in data:
        # Sirf top 5 results lenge taaki agent confuse na ho
        for item in data['results'][:5]:
            title = item.get('title') if media_type == 'movie' else item.get('name')
            date = item.get('release_date') if media_type == 'movie' else item.get('first_air_date')
            
            results.append({
                "id": item.get('id'),
                "title": title,
                "overview": item.get('overview'),
                "rating": item.get('vote_average'),
                "date": date,
                "poster_path": item.get('poster_path'), # UI ke liye image url
                "type": media_type
            })
    return results

def get_trending():
    """
    Fetches trending content (mix of movies and tv)
    """
    endpoint = "/trending/all/day"
    data = fetch_tmdb_data(endpoint)
    results = []
    if 'results' in data:
        for item in data['results'][:5]:
            media_type = item.get('media_type') # movie or tv
            title = item.get('title') if media_type == 'movie' else item.get('name')
            results.append({
                "title": title,
                "type": media_type,
                "rating": item.get('vote_average'),
                "overview": item.get('overview')
            })
    return results

# --- TESTING AREA (Ye code tabhi chalega jab hum directly is file ko run karenge) ---
if __name__ == "__main__":
    print("Testing TMDB Tools...")
    print("Searching for 'Breaking Bad' (TV)...")
    print(search_media("Breaking Bad", "tv"))