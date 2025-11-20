import streamlit as st
import os
import google.generativeai as genai
import tools  # Importing tools.py
import time

# 1. API Key Setup (Streamlit Secrets se lega)
# Agar secrets nahi mile (local run), toh environment variable try karega
api_key = st.secrets.get("GOOGLE_API_KEY")
tmdb_key = st.secrets.get("TMDB_API_KEY")

# Fallback for local testing if secrets fail
if not api_key:
    # Local testing ke liye dotenv try karte hain
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

st.set_page_config(page_title="AI Entertainment Agent", page_icon="🎬", layout="wide")

# 2. Gemini Configuration
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("API Key missing! Please check Streamlit Secrets.")

# System Instructions
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
5. If asked about streaming availability, say you can't check that yet.
"""

agent_tools = [tools.search_media, tools.get_trending]

# 3. Session State Setup
if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=agent_tools,
            system_instruction=sys_instruct
        )
        st.session_state.chat_session = model.start_chat(enable_automatic_function_calling=True)
    except Exception as e:
        st.error(f"Error initializing Gemini: {e}")

# 4. UI Layout
st.title("🎬 AI Entertainment Assistant")
st.caption("Powered by Google Gemini & TMDB")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# 5. User Input Handling
user_input = st.chat_input("Kya dekhna chahte ho aaj? (e.g., 'Movies like Death Note')")

if user_input:
    # User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Agent Response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Send message to Gemini
                response = st.session_state.chat_session.send_message(user_input)
                
                # Display Result
                st.markdown(response.text, unsafe_allow_html=True)
                
                # Save to History
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            except Exception as e:
                # Error Handling (Ye hume batayega asli galti kya hai)
                st.error(f"An error occurred: {e}")
