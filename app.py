import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
import tools
import time

# 1. Setup
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

st.set_page_config(page_title="AI Entertainment Agent", page_icon="🎬", layout="wide")

# 2. Gemini Model Setup
if api_key:
    genai.configure(api_key=api_key)

# Agent ko batayenge ki wo kaun hai (System Instruction)
sys_instruct = """
You are a helpful Movie and TV Show Recommendation Agent.
You have access to real-time data using tools.
When a user asks for a movie/show:
1. ALWAYS use the 'search_media' tool to get details.
2. If they ask for suggestions generally, use 'get_trending'.
3. When showing results, formatting is crucial:
   - Use Markdown for bold text (**Title**).
   - Use HTML <img> tags for posters with width='150'. 
   - Example: <img src="URL" width="150">
4. Be concise and friendly.
5. If asked about streaming availability (Netflix/Prime), honestly say you can't check that yet.
"""

agent_tools = [tools.search_media, tools.get_trending]

# 3. Session State
if "chat_session" not in st.session_state:
    try:
        # Model hum 1.5-flash hi rakhenge, ye sabse stable hai
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=agent_tools,
            system_instruction=sys_instruct
        )
        st.session_state.chat_session = model.start_chat(enable_automatic_function_calling=True)
    except Exception as e:
        st.error(f"Setup Error: {e}")

# 4. UI Layout
st.title("🎬 AI Entertainment Assistant")
st.caption("Powered by Google Gemini & TMDB")

# Chat History Display
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # YAHAN FIX HAI: unsafe_allow_html=True taaki images dikhe
        st.markdown(msg["content"], unsafe_allow_html=True)

# 5. User Input Handling
user_input = st.chat_input("Kya dekhna chahte ho aaj? (e.g., 'Movies like Death Note')")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Searching TMDB database..."):
            try:
                # Retry logic for Airtel/Network issues
                response = st.session_state.chat_session.send_message(user_input)
                
                # Image Fix yahan bhi
                st.markdown(response.text, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            except Exception as e:
                except Exception as e:
                st.error(f"ASLI ERROR: {e}")
