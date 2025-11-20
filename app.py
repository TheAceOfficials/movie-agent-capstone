import streamlit as st
import google.generativeai as genai
import tools
import time

# 1. Setup & Config
st.set_page_config(page_title="AI Entertainment Hub", page_icon="🍿", layout="wide")

# Load CSS for Premium UI (Dark Theme tweaks)
st.markdown("""
<style>
    .stChatMessage {background-color: #1E1E1E; border-radius: 15px;}
    div[data-testid="stImage"] img {border-radius: 10px; transition: transform 0.3s;}
    div[data-testid="stImage"] img:hover {transform: scale(1.05);}
    h3 {color: #E50914 !important;} /* Netflix Red Title */
</style>
""", unsafe_allow_html=True)

# API Key Handling
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

# 2. Brain: System Instructions (Updated for new tools)
sys_instruct = """
You are a smart Movie & TV Expert. Your goal is to find the PERFECT match.

HOW TO USE TOOLS:
1. **Specific Title:** If user asks for "Inception", use `search_media("Inception")`.
2. **"Like X" or "Similar to X":** - FIRST, use `search_media("X")` to find the correct ID and Type (Movie/TV) of 'X'.
   - THEN, use `get_recommendations(id, type)` to get the suggestions.
3. **Filters (Runtime, Language):**
   - If user asks for "Hindi movies under 90 mins", use `discover_media`.
   - Language Codes: Hindi='hi', English='en', Korean='ko', Japanese='ja'.
   - Type: 'movie' or 'tv'.
   - Example Call: `discover_media(media_type='movie', language='hi', max_runtime=90)`

RESPONSE FORMAT:
- Do NOT show images in text. Just give a friendly intro summary (e.g., "Here are some short Hindi movies for you:").
- The UI will handle the posters automatically.
- Just return the LIST of JSON objects provided by the tool as the final part of your answer logic, or simply explain what you found.
"""

# Tool definition
agent_tools = [tools.search_media, tools.get_trending, tools.get_recommendations, tools.discover_media]

# 3. Session State
if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel("gemini-2.0-flash", tools=agent_tools, system_instruction=sys_instruct)
        st.session_state.chat_session = model.start_chat(enable_automatic_function_calling=True)
    except Exception as e:
        st.error(f"Model Error: {e}")

# 4. UI Layout
st.title("🍿 AI Entertainment Hub")
st.caption("Premium Recommendations • Powered by Gemini 2.0")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display History
for msg in st.session_state.messages:
    if msg["role"] != "system": # Don't show system calls
        with st.chat_message(msg["role"]):
            # Agar content list (JSON) hai toh Grid show karo, nahi toh Text
            if isinstance(msg["content"], list):
                cols = st.columns(4) # 4 Posters per row
                for idx, item in enumerate(msg["content"]):
                    with cols[idx % 4]:
                        st.image(item['poster_url'], use_container_width=True)
                        st.caption(f"**{item['title']}** ({item['rating']}⭐)")
            else:
                st.markdown(msg["content"])

# 5. User Input
user_input = st.chat_input("Try: 'Suspense movies like Drishyam' or 'Hindi movies under 1h 30min'")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Curating your watchlist..."):
            try:
                response = st.session_state.chat_session.send_message(user_input)
                
                # Check: Kya Agent ne Data (List) return kiya hai ya Text?
                # Gemini function calling ke baad kabhi kabhi text + function_response mix karta hai.
                # Hum simple logic lagayenge: Last part check karenge.
                
                part = response.parts[-1]
                
                # Case A: Function Call ka Result (Data)
                if part.function_response:
                    # Note: Gemini 2.0 sometimes abstracts this. 
                    # Instead, we rely on the tool outputs captured via manual handling logic 
                    # or simply let Gemini summarise.
                    # But for Premium UI, we want raw data.
                    pass 
                
                # Simplification for Capstone:
                # Hum Gemini ko bolenge wo Text Response de, lekin agar usne Tool use kiya,
                # Toh hum manually check nahi kar sakte bina complex logic ke.
                # Isliye hum ek "Easy Hack" use karenge:
                
                # AGENT se puchenge: Kya mila?
                # (Actually, Gemini library automatically tool output ko text mai convert kar deti hai).
                
                # TO MAKE GRID WORK: We need the list of movies.
                # Isliye humne Tools mai `return results` kiya hai.
                # Lekin `enable_automatic_function_calling=True` data ko text mai badal deta hai.
                
                # FIX: Text output hi dikhayenge, lekin formatted.
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
            except Exception as e:
                st.error(f"Oops: {e}")
