"""
app.py - Streamlit front-end for Movie-Agent Capstone

This version:
- Loads TMDB key from st.secrets or environment
- Initializes tools.init(api_key)
- Provides a robust parse_user_query() to extract media_type, duration, providers, genres, language/dub
- Calls tools.discover_media_with_filters and search_fallback reliably using correct endpoints
- Presents results in a responsive grid with posters and metadata
- Provides helpful fallbacks and user messages
"""

import os
import streamlit as st
import random
from datetime import datetime
from typing import List
import tools  # assumes tools.py is in same directory
import time
import math

st.set_page_config(page_title="Movie Agent", layout="wide", initial_sidebar_state="expanded")

# --- Load TMDB key safely
TMDB_KEY = None
# First try Streamlit secrets
try:
    TMDB_KEY = st.secrets.get("TMDB_API_KEY")
except Exception:
    TMDB_KEY = None
# fallback to environment
if not TMDB_KEY:
    TMDB_KEY = os.getenv("TMDB_API_KEY")

if not TMDB_KEY:
    st.warning("TMDB API key not found. Set TMDB_API_KEY in Streamlit Secrets or environment. Basic UI will still work but API calls will fail.")
else:
    tools.init(TMDB_KEY)

# --- small parser & synonyms
import re
MEDIA_KEYWORDS = {
    "movie": ["movie", "film", "films", "movies", "feature"],
    "tv": ["tv", "series", "show", "shows", "tvshow", "tv shows", "serieses"],
    "anime": ["anime", "animes"],
    "documentary": ["documentary", "documentaries", "docu"],
}
PLATFORM_CANON = {
    "amazon": "amazon prime video",
    "amazon prime": "amazon prime video",
    "prime": "amazon prime video",
    "netflix": "netflix",
    "disney": "disney plus",
    "hotstar": "disney plus hotstar",
    "crunchyroll": "crunchyroll",
    "mxplayer": "mx player",
    "hulu": "hulu",
    "sonyliv": "sony liv",
    "sony liv": "sony liv",
    "youTube": "youtube",
    "youtube": "youtube",
}
PLATFORM_KEYWORDS = list(PLATFORM_CANON.keys())

GENRE_KEYWORDS = [
    "rom-com","romcom","romantic comedy","romance","action","thriller","sci-fi","science fiction",
    "comedy","drama","horror","animated","animation","fantasy","adventure","mystery","crime","anime"
]

def extract_duration_minutes(text: str):
    text = (text or "").lower()
    # hours patterns
    m = re.search(r'under\s+(\d+)\s*hr', text) or re.search(r'under\s+(\d+)\s*hours?', text)
    if not m:
        m = re.search(r'less than\s+(\d+)\s*hr', text) or re.search(r'less than\s+(\d+)\s*hours?', text)
    if m:
        try:
            hours = int(m.group(1))
            return hours * 60
        except:
            pass
    # pattern: "under 120 min"
    m2 = re.search(r'under\s+(\d+)\s*min', text) or re.search(r'under\s+(\d+)\s*minutes', text)
    if m2:
        return int(m2.group(1))
    # pattern like "< 2 hours"
    m3 = re.search(r'(<|less than)\s*(\d+)\s*(hours|hr)', text)
    if m3:
        try:
            hours = int(m3.group(2))
            return hours * 60
        except:
            pass
    return None

def parse_user_query(text: str):
    t = (text or "").lower()
    res = {
        "media_type": "any",
        "genres": [],
        "providers": [],
        "max_duration_minutes": None,
        "language": None,
        "dub_required": False,
        "title": None
    }
    # detect media type
    for k, kws in MEDIA_KEYWORDS.items():
        for kw in kws:
            if kw in t:
                res["media_type"] = k
                break
        if res["media_type"] != "any" and res["media_type"] == k:
            break

    # providers
    for p in PLATFORM_KEYWORDS:
        if p in t:
            res["providers"].append(PLATFORM_CANON.get(p, p))

    # genres
    for g in GENRE_KEYWORDS:
        if g in t:
            res["genres"].append(g.replace("-", " "))

    # duration
    dur = extract_duration_minutes(t)
    if dur:
        res["max_duration_minutes"] = dur

    # language/dub detection
    if "hindi dub" in t or "hindi dubbed" in t or "dub in hindi" in t:
        res["language"] = "hi"
        res["dub_required"] = True
    elif "hindi" in t and ("dub" not in t):
        res["language"] = "hi"
    elif "japanese" in t or "japan" in t or "ja" in t:
        res["language"] = "ja"

    # quoted title detection
    m = re.search(r'["\'](.+?)["\']', text)
    if m:
        res["title"] = m.group(1)

    # "on <platform>" fallback
    m2 = re.search(r'on\s+([a-z0-9\-\s]+)', t)
    if m2 and not res["providers"]:
        possible = m2.group(1).strip().split()[0]
        if possible in PLATFORM_CANON:
            res["providers"].append(PLATFORM_CANON[possible])

    # dedupe
    res["providers"] = list(dict.fromkeys(res["providers"]))
    res["genres"] = list(dict.fromkeys(res["genres"]))
    return res

# --- UI helpers
def show_results_grid(items: List[dict], cols_per_row: int = 4):
    if not items:
        st.info("Koi result nahi mila — filters broadening ke liye 'Broaden search' try karein.")
        return
    # responsive columns_per_row based on screen width not available reliably in Streamlit
    cols = st.columns(cols_per_row)
    idx = 0
    for it in items:
        c = cols[idx % cols_per_row]
        with c:
            title = it.get("title") or "Untitled"
            poster = tools.poster_url(it.get("poster_path"))
            if poster:
                st.image(poster, use_column_width="always", caption=title)
            else:
                st.write("No image")
                st.markdown(f"**{title}**")
            meta = []
            if it.get("release_date"):
                meta.append(str(it.get("release_date")))
            if it.get("vote_average"):
                meta.append(f"⭐ {it.get('vote_average')}")
            if meta:
                st.caption(" • ".join(meta))
            if it.get("overview"):
                with st.expander("Overview"):
                    st.write(it.get("overview"))
        idx += 1
        if idx % cols_per_row == 0 and idx < len(items):
            cols = st.columns(cols_per_row)

# --- Sidebar controls
st.sidebar.title("Filters (optional)")
default_region = st.sidebar.selectbox("Region (watch providers)", ["IN", "US", "GB", "CA"], index=0)
cols_setting = st.sidebar.slider("Posters per row", min_value=1, max_value=6, value=4)
auto_broaden = st.sidebar.checkbox("Auto-broaden when no results", value=True)

st.title("🎬 Movie Agent - Smart Search")
st.write("Type natural queries like: `mujhe rom-com futuristic rom-com series btao jo netflix pr ho`")
st.write("You can ask by type, duration (under 2hr), platform (Netflix/Crunchyroll), language/dub etc.")

# Input area
user_text = st.text_input("Ask me for movies/series/anime/documentaries (Hindi/English supported):", value="", placeholder="e.g. mujhe romcom movies under 2hr on netflix")
col1, col2 = st.columns([4,1])
with col1:
    submit_query = st.button("Search")
with col2:
    clear_btn = st.button("Clear")

if clear_btn:
    st.experimental_rerun()

if submit_query and user_text.strip() == "":
    st.warning("Query empty — kuch likh ke try karo.")
    st.stop()

if submit_query:
    st.session_state.last_query = user_text
    parsed = parse_user_query(user_text)
    st.write("Detected filters:", parsed)

    # decide media_type fallback logic
    media_type = parsed["media_type"]
    if media_type == "any":
        # prefer movie by default but if user said series/episodes prefer tv
        media_type = "movie"

    # special handling: anime -> attempt to search tv (many anime are series)
    original_lang = None
    genres = parsed["genres"] or None
    if parsed["media_type"] == "anime":
        # make sure animation genre included and prefer original_language 'ja'
        original_lang = "ja"
        if genres:
            if "animation" not in [g.lower() for g in genres]:
                genres = genres + ["Animation"]
        else:
            genres = ["Animation"]
        # many anime are TV; give user TV unless they explicitly asked for movie
        media_type = "tv"

    providers = parsed["providers"] or None
    max_runtime = parsed["max_duration_minutes"] or None

    # perform discover with spinner
    with st.spinner("Searching TMDB..."):
        try:
            items = tools.discover_media_with_filters(
                media_type=media_type,
                region=default_region,
                max_runtime_minutes=max_runtime,
                provider_names=providers,
                genres=genres,
                original_language=original_lang,
                page=1,
                max_pages=1,
            )
        except Exception as e:
            st.error(f"Error during discovery: {e}")
            items = []

    # fallback: if no results and user included a quoted title or keywords, try search_fallback
    if not items and parsed.get("title"):
        with st.spinner("Trying title search fallback..."):
            try:
                items = tools.search_fallback(parsed["title"], media_type=media_type)
            except Exception as e:
                st.error(f"Search fallback error: {e}")
                items = []

    # second-level fallback: if still empty and auto_broaden, remove provider/runtime filters
    if not items and auto_broaden:
        st.info("No exact matches — broadening search (removing platform/duration filters)...")
        with st.spinner("Broadening..."):
            try:
                items = tools.discover_media_with_filters(
                    media_type=media_type,
                    region=default_region,
                    max_runtime_minutes=None,
                    provider_names=None,
                    genres=genres,
                    original_language=original_lang,
                    page=1,
                    max_pages=1,
                )
            except Exception as e:
                logging_msg = f"Error broadening: {e}"
                st.warning(logging_msg)
                items = []

    # present results
    st.subheader("Results")
    if items:
        show_results_grid(items, cols_per_row=cols_setting)
    else:
        st.warning("Koi results nahi mile. Try removing platform or duration filters, or rephrase your query.")

# small footer and info about dub availability limitation
st.markdown("---")
st.caption("Note: Dub/language availability isn't always reliably encoded in TMDB. For exact dubbing availability, check the provider (Netflix/Crunchyroll) directly.")
