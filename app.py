import streamlit as st
import google.generativeai as genai
import tools

# --- CONFIG ---
st.set_page_config(page_title="AI Entertainment Hub", page_icon="🍿", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #0e1117;}
    div[data-testid="stImage"] {border-radius: 10px; transition: transform 0.2s;}
    div[data-testid="stImage"]:hover {transform: scale(1.03);}
    .detail-title {font-size: 40px; font-weight: bold; color: #E50914;}
    .tag {background-color: #333; padding: 5px 10px; border-radius: 20px; font-size: 12px; margin-right: 5px;}
</style>
""", unsafe_allow_html=True)

# --- API SETUP ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Secrets not found. Please check Streamlit settings.")
    st.stop()

genai.configure(api_key=api_key)

# --- SESSION STATE ---
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None
if "history" not in st.session_state:
    st.session_state.history = []

# --- CACHED MODEL LOADER ---
@st.cache_resource
def get_chat_session():
    tools_map = {
        'search_media': tools.search_media,
        'get_trending': tools.get_trending,
        'get_recommendations': tools.get_recommendations,
        'discover_media': tools.discover_media,
        'get_ai_picks': tools.get_ai_picks
    }
    
    # UPDATED BRAIN LOGIC (Point 4 Added)
    sys_instruct = """
    You are a Smart Movie & Anime Expert.
    RULES:
    1. Simple Search: "Search Inception" -> `search_media`.
    2. Vibe/Complex: "Thriller like Death Note" -> THINK of 5 matches -> USE `get_ai_picks`.
    3. Filters: "Hindi movies < 90min" -> `discover_media`.
    
    4. BINGE/DURATION REQUESTS: 
       - If user asks "Anime to watch in 1 day" or "Short series":
       - DO NOT use `discover_media` (Math fails here).
       - THINK: Which animes are short (10-13 eps) or movies? (e.g., Cyberpunk Edgerunners, JJK 0, Erasased, FLCL).
       - USE `get_ai_picks` with that list.
       
    IMPORTANT: Just execute the tool. Do not output JSON. Say "Here are some action-packed recommendations perfect for a 1-day binge:".
    """
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", 
        tools=list(tools_map.values()), 
        system_instruction=sys_instruct
    )
    return model.start_chat(enable_automatic_function_calling=False)

chat = get_chat_session()

# --- HELPER: DETAIL PAGE ---
def show_details_page():
    movie = st.session_state.selected_movie
    if st.button("← Back to Search"):
        st.session_state.selected_movie = None
        st.rerun()

    col1, col2 = st.columns([1, 2])
    with col1:
        if movie['poster_url']: st.image(movie['poster_url'], use_container_width=True)
    with col2:
        st.markdown(f"<div class='detail-title'>{movie['title']}</div>", unsafe_allow_html=True)
        st.markdown(f"⭐ **{movie['rating']}** | 📅 **{movie['date']}** | ⏳ **{movie['runtime']}**")
        if movie['genres']:
            tags = "".join([f"<span class='tag'>{g}</span>" for g in movie['genres']])
            st.markdown(f"<div style='margin: 10px 0;'>{tags}</div>", unsafe_allow_html=True)
        st.write(f"**Overview:** {movie['overview']}")
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Budget", movie['budget'])
        c2.metric("Revenue", movie['revenue'])
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
    
    for msg_idx, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            if msg["type"] == "text":
                st.markdown(msg["content"])
            elif msg["type"] == "grid":
                cols = st.columns(4)
                for item_idx, item in enumerate(msg["content"]):
                    with cols[item_idx % 4]:
                        st.image(item['poster_url'], use_container_width=True)
                        st.markdown(f"**{item['title']}**")
                        if st.button("View Details", key=f"btn_{msg_idx}_{item['id']}_{item_idx}"):
                            full_details = tools.get_media_details(item['id'], item['type'])
                            st.session_state.selected_movie = full_details
                            st.rerun()

    user_input = st.chat_input("Try: 'Action anime to watch in 1 day' or 'Short thriller series'")
    if user_input:
        st.session_state.history.append({"role": "user", "type": "text", "content": user_input})
        with st.chat_message("user"): st.markdown(user_input)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Local tool mapping
                    tools_map = {'search_media': tools.search_media, 'get_trending': tools.get_trending, 'get_recommendations': tools.get_recommendations, 'discover_media': tools.discover_media, 'get_ai_picks': tools.get_ai_picks}
                    
                    response = chat.send_message(user_input)
                    
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
                                # Context update with user-friendly message
                                chat.history.append(genai.protos.Content(parts=[genai.protos.Part(text="I have shown the recommendations.")], role="model"))
                                st.rerun()
                            else: st.error("No results found. Try a simpler query.")
                    else:
                        st.markdown(response.text)
                        st.session_state.history.append({"role": "assistant", "type": "text", "content": response.text})
                        
                except Exception as e:
                    st.error(f"Oops: {str(e)}")
