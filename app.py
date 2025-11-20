import streamlit as st
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
import tools
import time

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="AI Entertainment Hub", page_icon="🍿", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #0e1117;}
    /* Movie Card Styling */
    div[data-testid="stImage"] {border-radius: 10px; overflow: hidden;}
    .movie-title {font-weight: bold; font-size: 15px; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
    .movie-meta {font-size: 12px; color: #aaa;}
    
    /* Detail Page Styling */
    .detail-title {font-size: 40px; font-weight: bold; color: #E50914;}
    .tag {background-color: #333; padding: 5px 10px; border-radius: 20px; font-size: 12px; margin-right: 5px;}
</style>
""", unsafe_allow_html=True)

# --- 2. SETUP GEMINI ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

# --- 3. SESSION STATE INITIALIZATION ---
# Ye track karega ki hum Grid par hain ya Detail page par
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None # Initially koi movie select nahi hai

if "history" not in st.session_state:
    st.session_state.history = []

if "chat" not in st.session_state:
    tools_map = {
        'search_media': tools.search_media,
        'get_trending': tools.get_trending,
        'get_recommendations': tools.get_recommendations,
        'discover_media': tools.discover_media
    }
    sys_instruct = """
    You are a Movie Expert.
    1. Use `search_media` for specific titles.
    2. Use `get_recommendations` for "Like X".
    3. Use `discover_media` for Filters.
    IMPORTANT: Just execute the tool. Do not describe the results in JSON. Say "Here are the results."
    """
    model = genai.GenerativeModel(model_name="gemini-2.0-flash", tools=list(tools_map.values()), system_instruction=sys_instruct)
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=False)

# --- 4. FUNCTIONS FOR UI ---

def show_details_page():
    """ Renders the Single Movie Detail View """
    movie = st.session_state.selected_movie
    
    # Back Button
    if st.button("← Back to Search"):
        st.session_state.selected_movie = None
        st.rerun()

    # Layout: Left (Poster) | Right (Info)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if movie['poster_url']:
            st.image(movie['poster_url'], use_container_width=True)
            
    with col2:
        st.markdown(f"<div class='detail-title'>{movie['title']}</div>", unsafe_allow_html=True)
        st.markdown(f"⭐ **{movie['rating']}** | 📅 **{movie['date']}** | ⏳ **{movie['runtime']}**")
        
        # Genres Tags
        if movie['genres']:
            tags_html = "".join([f"<span class='tag'>{g}</span>" for g in movie['genres']])
            st.markdown(f"<div style='margin: 10px 0;'>{tags_html}</div>", unsafe_allow_html=True)
            
        st.write(f"**Overview:** {movie['overview']}")
        
        st.divider()
        
        # Statistics
        c1, c2 = st.columns(2)
        c1.metric("Budget", movie['budget'])
        c2.metric("Revenue", movie['revenue'])
        
        st.divider()
        
        # OTT Availability
        st.subheader("📺 Where to Watch (India)")
        if movie['ott']:
            st.success(f"Available on: {', '.join(movie['ott'])}")
        else:
            st.warning("Not streaming on major platforms in India right now.")

    # Trailer Section
    if movie['trailer_url']:
        st.divider()
        st.subheader("🎥 Official Trailer")
        st.video(movie['trailer_url'])


# --- 5. MAIN APP LOGIC ---

if st.session_state.selected_movie:
    # --- VIEW MODE: DETAILS PAGE ---
    show_details_page()

else:
    # --- VIEW MODE: CHAT & GRID ---
    st.title("🍿 AI Entertainment Hub")

    # History Loop
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            if msg["type"] == "text":
                st.markdown(msg["content"])
            elif msg["type"] == "grid":
                cols = st.columns(4)
                for idx, item in enumerate(msg["content"]):
                    with cols[idx % 4]:
                        st.image(item['poster_url'], use_container_width=True)
                        st.markdown(f"<div class='movie-title'>{item['title']}</div>", unsafe_allow_html=True)
                        # THE MAGIC BUTTON
                        if st.button("View Details", key=f"btn_{item['id']}_{idx}"):
                            # Fetch Full Details NOW
                            full_details = tools.get_media_details(item['id'], item['type'])
                            st.session_state.selected_movie = full_details
                            st.rerun()

    # Input Box
    user_input = st.chat_input("Search movies, actors, or recommendations...")

    if user_input:
        st.session_state.history.append({"role": "user", "type": "text", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Searching..."):
                try:
                    tools_map = {'search_media': tools.search_media, 'get_trending': tools.get_trending, 'get_recommendations': tools.get_recommendations, 'discover_media': tools.discover_media}
                    
                    response = st.session_state.chat.send_message(user_input)
                    part = response.candidates[0].content.parts[0]

                    if part.function_call:
                        fn_name = part.function_call.name
                        fn_args = dict(part.function_call.args)
                        
                        if fn_name in tools_map:
                            data = tools_map[fn_name](**fn_args)
                            if data:
                                st.session_state.history.append({"role": "assistant", "type": "grid", "content": data})
                                st.rerun() # Rerun to show grid immediately
                            else:
                                st.error("No results found.")
                    else:
                        st.markdown(response.text)
                        st.session_state.history.append({"role": "assistant", "type": "text", "content": response.text})

                except Exception as e:
                    st.error(f"Error: {e}")
