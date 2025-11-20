import streamlit as st
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
import tools
import time

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="AI Entertainment Hub", page_icon="🍿", layout="wide")

# Dark Mode & Premium Card Styling
st.markdown("""
<style>
    .stApp {background-color: #0e1117;}
    div[data-testid="stImage"] {transition: transform 0.2s; border-radius: 10px; overflow: hidden;}
    div[data-testid="stImage"]:hover {transform: scale(1.03); cursor: pointer;}
    .movie-title {font-weight: bold; font-size: 16px; margin-top: 5px; color: #fff;}
    .movie-meta {font-size: 12px; color: #aaa;}
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

# --- 3. FUNCTION HANDLER (The Brain) ---
# Hum tools ko "Dictionary" format mai convert kar rahe hain manual handling ke liye
tools_map = {
    'search_media': tools.search_media,
    'get_trending': tools.get_trending,
    'get_recommendations': tools.get_recommendations,
    'discover_media': tools.discover_media
}

# System Instruction: Agent ko batana ki kab kya use karna hai
sys_instruct = """
You are a Movie Expert.
1. Use `search_media` for specific titles ("Inception").
2. Use `get_recommendations` for "Movies like X". First find X's ID via search, then recommend.
3. Use `discover_media` for Filters (Hindi, Runtime < 90min).
   - For "Hindi", use language='hi'.
   - For "Upcoming/Future", set include_upcoming=True. Otherwise keep it False.
   
IMPORTANT: When a tool returns data, do NOT output the JSON. Just say "Here are the top picks:" and let the UI handle the images.
"""

if "chat" not in st.session_state:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", # Ya 1.5-flash agar error aaye
        tools=list(tools_map.values()),
        system_instruction=sys_instruct
    )
    st.session_state.chat = model.start_chat(enable_automatic_function_calling=False) # Manual Mode ON
    st.session_state.history = [] # Custom History store karenge

# --- 4. UI LAYOUT ---
st.title("🍿 AI Entertainment Hub")

# Display History
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "grid":
            # PREMIUM GRID RENDERER
            cols = st.columns(4)
            for idx, item in enumerate(msg["content"]):
                with cols[idx % 4]:
                    st.image(item['poster_url'], use_container_width=True)
                    st.markdown(f"<div class='movie-title'>{item['title']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='movie-meta'>⭐ {item['rating']} | 📅 {item['date']}</div>", unsafe_allow_html=True)

# --- 5. MAIN LOGIC LOOP ---
user_input = st.chat_input("Search movies, actors, or recommendations...")

if user_input:
    # 1. User ka msg dikhao
    st.session_state.history.append({"role": "user", "type": "text", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Gemini se baat karo
    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            try:
                # Step A: Send message
                response = st.session_state.chat.send_message(user_input)
                part = response.candidates[0].content.parts[0]

                # Step B: Check if Gemini wants to run a TOOL
                if part.function_call:
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args)
                    
                    # Execute Python Function
                    if fn_name in tools_map:
                        data = tools_map[fn_name](**fn_args) # Asli Tool Chala
                        
                        # Step C: Show GRID (No JSON Text!)
                        if data:
                            st.session_state.history.append({"role": "assistant", "type": "grid", "content": data})
                            # Grid abhi render karo
                            cols = st.columns(4)
                            for idx, item in enumerate(data):
                                with cols[idx % 4]:
                                    st.image(item['poster_url'], use_container_width=True)
                                    st.markdown(f"<div class='movie-title'>{item['title']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div class='movie-meta'>⭐ {item['rating']} | 📅 {item['date']}</div>", unsafe_allow_html=True)
                            
                            # Gemini ko batao ki kaam ho gaya (Context update)
                            # Hum data wapis nahi bhejenge taaki wo JSON na ugal de.
                            # Bas ek chhota acknowledgment bhejenge.
                            st.session_state.chat.send_message(
                                genai.content_types.to_content(
                                    {"role": "user", "parts": [{"text": "Display these movies to the user in a grid."}]}
                                )
                            )
                        else:
                            st.error("No results found for filters.")
                else:
                    # Step D: Agar normal text hai (Hi/Hello)
                    st.markdown(response.text)
                    st.session_state.history.append({"role": "assistant", "type": "text", "content": response.text})

            except Exception as e:
                st.error(f"Error: {e}")
