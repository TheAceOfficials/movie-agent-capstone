import streamlit as st
import google.generativeai as genai
import tools

# --- CONFIG ---
st.set_page_config(page_title="AI Entertainment Hub", page_icon="🍿", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #0e1117;}
    div[data-testid="stImage"] {border-radius: 10px; transition: transform 0.2s;}
    div[data-testid="stImage"]:hover {transform: scale(1.05); z-index: 1;}
    .detail-title {font-size: 40px; font-weight: bold; color: #E50914;}
    .tag {background-color: #333; padding: 5px 10px; border-radius: 20px; font-size: 12px; margin-right: 5px;}
    .type-badge {font-size: 10px; background-color: #E50914; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;}
    
    /* Watchlist Sidebar Style */
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
    st.session_state.watchlist = [] # NEW MEMORY FEATURE

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
    sys_instruct = """
    You are a Smart Movie & Anime Expert.
    RULES:
    1. Simple Search: "Search Inception" -> `search_media`.
    2. Vibe/Complex: "Thriller like Death Note" -> THINK of 5 matches -> USE `get_ai_picks`.
    3. Filters: "Hindi movies < 90min" -> `discover_media`.
    4. Binge/Short: If "1 day watch" or "Short series" -> THINK of specific short animes/shows -> USE `get_ai_picks`.
    IMPORTANT: Just execute the tool. Do not output JSON. Say "Here are the top picks:".
    """
    model = genai.GenerativeModel("gemini-2.0-flash", tools=list(tools_map.values()), system_instruction=sys_instruct)
    return model.start_chat(enable_automatic_function_calling=False)

chat = get_chat_session()

# --- SIDEBAR (Watchlist & Info) ---
with st.sidebar:
    st.header("🍿 My Watchlist")
    if st.session_state.watchlist:
        for item in st.session_state.watchlist:
            st.markdown(f"<div class='watchlist-item'>{item['title']} ({item['rating']}⭐)</div>", unsafe_allow_html=True)
        
        if st.button("Clear Watchlist"):
            st.session_state.watchlist = []
            st.rerun()
    else:
        st.caption("Your watchlist is empty.")
        
    st.divider()
    st.subheader("About")
    st.info("Powered by Google Gemini 2.0 & TMDB API.\nBuilt for Google AI Agents Capstone.")
    if st.button("Clear Chat History"):
        st.session_state.history = []
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
        
        # NEW: ADD TO WATCHLIST BUTTON
        # Check if already in watchlist
        is_in_list = any(m['id'] == movie['id'] for m in st.session_state.watchlist)
        if is_in_list:
            if st.button("✅ Added to Watchlist"):
                pass # Already added
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
    
    # SUGGESTION CHIPS (Clickable Queries)
    sc1, sc2, sc3, sc4 = st.columns(4)
    query_input = None
    
    # --- DYNAMIC SUGGESTION CHIPS (New Feature) ---
    import random
    
    # 1. 50+ Ideas ka Pool
    suggestion_pool = [
        "🔥 Trending movies today",
        "🤯 Mind-bending thrillers like Inception",
        "🤣 Comedy movies to lift mood",
        "🏎️ High octane action movies",
        "👻 Horror movies based on true stories",
        "🇮🇳 Best Bollywood movies of 90s",
        "🕵️‍♂️ Mystery movies with plot twists",
        "🚀 Sci-fi movies about space",
        "🥺 Emotional movies that make you cry",
        "👊 Action anime for beginners",
        "🧠 Psychological anime like Death Note",
        "⏳ Short anime series (12 episodes)",
        "🧟 Zombie apocalypse movies",
        "👮 Crime thrillers like Se7en",
        "🧙‍♂️ Fantasy movies like Harry Potter",
        "🤖 Movies about AI taking over",
        "📅 Upcoming Marvel movies",
        "🤠 Best Western movies",
        "🎸 Music based movies/biopics",
        "🏆 Oscar winning movies 2024",
        "🍿 Family friendly movies for sunday",
        "⏰ Hindi movies under 90 minutes",
        "💰 Heist movies like Money Heist",
        "🥊 Sports drama movies",
        "🦇 Dark superhero movies",
        "💑 Romantic comedies 2023",
        "👽 Alien invasion movies",
        "🗡️ Historical war movies",
        "🐉 Anime like Attack on Titan",
        "🎬 Christopher Nolan best movies",
        "👑 Shah Rukh Khan romantic hits",
        "🩸 Slasher horror movies"
    ]

    # 2. Pick 4 Random Prompts every time app reloads
    selected_prompts = random.sample(suggestion_pool, 4)

    # 3. Display Buttons
    cols = st.columns(4)
    query_input = None
    
    for i, prompt in enumerate(selected_prompts):
        with cols[i]:
            # Button label thoda chhota rakhenge taaki fit ho jaye
            if st.button(prompt, use_container_width=True):
                query_input = prompt

    # HISTORY DISPLAY
    for msg_idx, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            if msg["type"] == "text":
                st.markdown(msg["content"])
            elif msg["type"] == "grid":
                cols = st.columns(5)
                for item_idx, item in enumerate(msg["content"]):
                    with cols[item_idx % 5]:
                        st.image(item['poster_url'], use_container_width=True)
                        type_icon = "📺" if item['type'] == 'tv' else "🎬"
                        st.caption(f"{type_icon} {item['title']}")
                        if st.button("View Details", key=f"btn_{msg_idx}_{item['id']}_{item_idx}"):
                            full_details = tools.get_media_details(item['id'], item['type'])
                            st.session_state.selected_movie = full_details
                            st.rerun()

    # CHAT INPUT
    # Agar button click hua hai toh wo query use karo, warna user input
    if query_input:
        user_text = query_input
    else:
        user_text = st.chat_input("Try: 'Sci-fi movies with mind games'")

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
                                chat.history.append(genai.protos.Content(parts=[genai.protos.Part(text="I have shown the grid.")], role="model"))
                                st.rerun()
                            else: st.error("No results found.")
                    else:
                        st.markdown(response.text)
                        st.session_state.history.append({"role": "assistant", "type": "text", "content": response.text})
                        
                except Exception as e:
                    st.error(f"Oops: {str(e)}")

