import streamlit as st
import google.generativeai as genai
import tools
import random

# --- CONFIG ---
st.set_page_config(page_title="AI Entertainment Hub", page_icon="🍿", layout="wide")

# --- PREMIUM CSS STYLING (The Fix) ---
st.markdown("""
<style>
    .stApp {background-color: #0e1117;}
    
    /* 1. IMAGE FIX: Force all images to have consistent aspect ratio */
    div[data-testid="stImage"] img {
        border-radius: 10px;
        object-fit: cover; /* Taaki image stretch na ho */
        width: 100%;
        height: auto;
        aspect-ratio: 2/3; /* Standard Movie Poster Ratio */
    }
    
    /* 2. TITLE FIX: Fixed Height for Titles (Max 2 lines) */
    .movie-title {
        font-weight: bold;
        font-size: 14px;
        margin-top: 5px;
        height: 40px; /* Fixed height (approx 2 lines) */
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2; /* Sirf 2 lines dikhayega */
        -webkit-box-orient: vertical;
        text-overflow: ellipsis;
        color: #fff;
    }
    
    /* 3. BUTTON FIX: Uniform Buttons */
    div[data-testid="stButton"] button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #333;
        background-color: #1E1E1E;
        color: white;
    }
    div[data-testid="stButton"] button:hover {
        border-color: #E50914;
        color: #E50914;
    }

    /* 4. Type Icon Styling */
    .type-icon {
        font-size: 12px; 
        color: #aaa; 
        margin-bottom: 2px;
    }

    /* Detail Page Styling */
    .detail-title {font-size: 40px; font-weight: bold; color: #E50914;}
    .tag {background-color: #333; padding: 5px 10px; border-radius: 20px; font-size: 12px; margin-right: 5px;}
    .type-badge {font-size: 10px; background-color: #E50914; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;}
    .watchlist-item {padding: 10px; background-color: #1E1E1E; margin-bottom: 5px; border-radius: 5px; border-left: 3px solid #E50914;}
</style>
""", unsafe_allow_html=True)

# --- API SETUP ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Secrets not found.")
    st.stop()

genai.configure(api_key=api_key)

# --- SESSION STATE ---
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None
if "history" not in st.session_state:
    st.session_state.history = []
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

# --- CHIPS STATE ---
if "chips" not in st.session_state:
    suggestion_pool = [
        "🔥 Trending movies today", "🤯 Mind-bending thrillers like Inception",
        "🤣 Comedy movies to lift mood", "🏎️ High octane action movies",
        "👻 Horror movies based on true stories", "🇮🇳 Best Bollywood movies of 90s",
        "🚀 Sci-fi movies about space", "🥺 Emotional movies that make you cry",
        "👊 Action anime for beginners", "🧠 Psychological anime like Death Note",
        "⏳ Short anime series (12 episodes)", "🧟 Zombie apocalypse movies",
        "🤠 Best Western movies", "🤖 Movies about AI taking over",
        "💰 Heist movies like Money Heist", "🥊 Sports drama movies"
    ]
    st.session_state.chips = random.sample(suggestion_pool, 4)

# --- CACHED MODEL ---
@st.cache_resource
def get_chat_session():
    tools_map = {
        'search_media': tools.search_media,
        'get_trending': tools.get_trending,
        'get_recommendations': tools.get_recommendations,
        'discover_media': tools.discover_media,
        'get_ai_picks': tools.get_ai_picks
    }
    # UPDATED BRAIN LOGIC (All Fixes Combined)
    sys_instruct = """
    You are a Smart Movie & Anime Expert.
    
    RULES FOR TOOL USAGE:
    
    1. **Simple Search:** "Search Inception" -> `search_media`.
    
    2. **Vibe/Complex Recommendations:**
       - IF User asks for "Anime": USE `get_ai_picks(..., specific_type='anime')`.
       - IF User asks for "Movies": USE `get_ai_picks(..., specific_type='movie')`.
       - IF User asks for "TV Shows": USE `get_ai_picks(..., specific_type='tv')`.
       - IF Generic ("Thriller like Death Note"): USE `get_ai_picks(..., specific_type=None)`.

    3. **Franchise / Universe / Watch Order (THE FIX):**
       - IF User asks "Sandman universe", "The Boys spin-offs", "Marvel watch order":
       - THINK BROADLY: Include Main Shows + Spin-offs + Movies.
       - Example: "Sandman" -> Include "Dead Boy Detectives", "Lucifer".
       - Example: "The Boys" -> Include "Gen V".
       - USE: `get_ai_picks(movie_names_list=["The Sandman", "Dead Boy Detectives", "Lucifer", ...])`.

    4. **Filters:** "Hindi movies < 90min" -> `discover_media`.
    
    5. **Binge/Short:** "Anime in 1 day", "Short series" -> 
       - THINK: Erased, FLCL, Cyberpunk Edgerunners.
       - USE: `get_ai_picks(movie_names_list=['Erased', ...], specific_type='anime')`
    
    IMPORTANT: Just execute the tool. Do not output JSON. Say "Here are the top picks:".
    """
    model = genai.GenerativeModel("gemini-2.0-flash", tools=list(tools_map.values()), system_instruction=sys_instruct)
    return model.start_chat(enable_automatic_function_calling=False)

chat = get_chat_session()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🍿 My Watchlist")
    if st.session_state.watchlist:
        for item in st.session_state.watchlist:
            st.markdown(f"<div class='watchlist-item'>{item['title']} ({item['rating']}⭐)</div>", unsafe_allow_html=True)
        if st.button("Clear Watchlist"):
            st.session_state.watchlist = []
            st.rerun()
    else:
        st.caption("Empty list.")
    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.history = []
        st.session_state.chips = random.sample(suggestion_pool, 4)
        st.rerun()

# --- HELPER: DETAIL PAGE ---
def show_details_page():
    movie = st.session_state.selected_movie
    if st.button("← Back to Search"):
        st.session_state.selected_movie = None
        st.rerun()

    col1, col2 = st.columns([1, 2])
    with col1:
        if movie['poster_url']: st.image(movie['poster_url'], use_container_width=True)
        
        is_in_list = any(m['id'] == movie['id'] for m in st.session_state.watchlist)
        if is_in_list:
            st.button("✅ In Watchlist", disabled=True)
        else:
            if st.button("➕ Add to Watchlist"):
                st.session_state.watchlist.append(movie)
                st.rerun()

    with col2:
        media_label = "📺 TV SERIES" if movie['type'] == 'tv' else "🎬 MOVIE"
        st.markdown(f"<span class='type-badge'>{media_label}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-title'>{movie['title']}</div>", unsafe_allow_html=True)
        st.markdown(f"⭐ **{movie['rating']}** | 📅 **{movie['date']}**")
        
        if movie['genres']:
            tags = "".join([f"<span class='tag'>{g}</span>" for g in movie['genres']])
            st.markdown(f"<div style='margin: 10px 0;'>{tags}</div>", unsafe_allow_html=True)
            
        st.write(f"**Overview:** {movie['overview']}")
        if movie['cast']: st.write(f"**Cast:** {', '.join(movie['cast'])}")
        st.divider()
        
        c1, c2 = st.columns(2)
        if movie['type'] == 'movie':
            c1.metric("Budget", movie['budget'] if movie['budget'] else "N/A")
            c2.metric("Revenue", movie['revenue'] if movie['revenue'] else "N/A")
        else:
            c1.metric("Seasons", movie['seasons'])
            c2.metric("Episodes", movie['episodes'])
            
        st.divider()
        st.subheader("📺 Where to Watch (India)")
        if movie['ott']: st.success(f"Available on: {', '.join(movie['ott'])}")
        else: st.warning("Not streaming on major platforms in India right now.")

    if movie['trailer_url']:
        st.divider()
        st.subheader("🎥 Official Trailer")
        st.video(movie['trailer_url'])

# --- MAIN APP ---
if st.session_state.selected_movie:
    show_details_page()
else:
    st.title("🍿 AI Entertainment Hub")
    
    # DYNAMIC CHIPS
    cols = st.columns(4)
    query_input = None
    for i, prompt in enumerate(st.session_state.chips):
        with cols[i]:
            if st.button(prompt, use_container_width=True):
                query_input = prompt

    # HISTORY
    for msg_idx, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            if msg["type"] == "text":
                st.markdown(msg["content"])
            elif msg["type"] == "grid":
                cols = st.columns(5)
                for item_idx, item in enumerate(msg["content"]):
                    with cols[item_idx % 5]:
                        st.image(item['poster_url'], use_container_width=True)
                        
                        # Title Container (Fixed Height for Alignment)
                        type_icon = "📺" if item['type'] == 'tv' else "🎬"
                        st.markdown(f"<div class='type-icon'>{type_icon} {item['type'].upper()}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='movie-title'>{item['title']}</div>", unsafe_allow_html=True)
                        
                        if st.button("View Details", key=f"btn_{msg_idx}_{item['id']}_{item_idx}"):
                            full_details = tools.get_media_details(item['id'], item['type'])
                            st.session_state.selected_movie = full_details
                            st.rerun()

    # INPUT
    if query_input:
        user_text = query_input
    else:
        user_text = st.chat_input("Try: 'Sci-fi movies about space' or 'Comedy anime'")

    if user_text:
        st.session_state.history.append({"role": "user", "type": "text", "content": user_text})
        with st.chat_message("user"): st.markdown(user_text)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    tools_map = {'search_media': tools.search_media, 'get_trending': tools.get_trending, 'get_recommendations': tools.get_recommendations, 'discover_media': tools.discover_media, 'get_ai_picks': tools.get_ai_picks}
                    
                    response = chat.send_message(user_text)
                    
                    function_call = None
                    for part in response.candidates[0].content.parts:
                        if part.function_call:
                            function_call = part.function_call
                            break
                    
                    if function_call:
                        fn_name = function_call.name
                        fn_args = dict(function_call.args)
                        if fn_name in tools_map:
                            data = tools_map[fn_name](**fn_args)
                            if data:
                                st.session_state.history.append({"role": "assistant", "type": "grid", "content": data})
                                chat.history.append(genai.protos.Content(parts=[genai.protos.Part(text="Grid shown.")], role="model"))
                                st.rerun()
                            else: st.error("No results found.")
                    else:
                        st.markdown(response.text)
                        st.session_state.history.append({"role": "assistant", "type": "text", "content": response.text})
                        
                except Exception as e:
                    st.error(f"Oops: {str(e)}")

