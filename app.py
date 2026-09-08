import os
import json
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# Page setup
st.set_page_config(page_title="FPL Analytics & AI Assistant", layout="wide")

# Initialize Gemini Client
@st.cache_resource
def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY environment variable is missing!")
        st.stop()
    return genai.Client(api_key=api_key)

client = get_client()

# Chat Persistence Helpers
CHAT_HISTORY_FILE = "all_chat_threads.json"

def load_chat_threads():
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"Default Thread": []}
    return {"Default Thread": []}

def save_chat_threads(threads):
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(threads, f, indent=2, ensure_ascii=False)

# Session state initialization
if "threads" not in st.session_state:
    st.session_state.threads = load_chat_threads()

if "active_thread" not in st.session_state:
    st.session_state.active_thread = list(st.session_state.threads.keys())[0]

# Sidebar Navigation & Chat Thread Management
st.sidebar.title("FPL AI Assistant")

model_choice = st.sidebar.selectbox(
    "Select Model",
    ["gemini-2.5-flash", "gemini-2.5-pro"],
    index=0
)

st.sidebar.subheader("Chat Threads")
thread_names = list(st.session_state.threads.keys())
selected_thread = st.sidebar.radio("Select Thread", thread_names, index=thread_names.index(st.session_state.active_thread))
st.session_state.active_thread = selected_thread

new_thread_name = st.sidebar.text_input("New Thread Name")
if st.sidebar.button("Create Thread"):
    if new_thread_name and new_thread_name not in st.session_state.threads:
        st.session_state.threads[new_thread_name] = []
        st.session_state.active_thread = new_thread_name
        save_chat_threads(st.session_state.threads)
        st.rerun()

if st.sidebar.button("Delete Current Thread") and len(st.session_state.threads) > 1:
    del st.session_state.threads[st.session_state.active_thread]
    st.session_state.active_thread = list(st.session_state.threads.keys())[0]
    save_chat_threads(st.session_state.threads)
    st.rerun()

st.title("FPL Data & AI Strategy Hub")

# Main Interface Tabs
tab_assistant, tab_data = st.tabs(["AI Strategy Assistant", "FPL Data Viewer"])

with tab_data:
    st.header("FPL Datasets")
    data_file = "fpl_data.csv"
    if os.path.exists(data_file):
        df = pd.read_csv(data_file)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No local `fpl_data.csv` found in working directory.")

with tab_assistant:
    st.header(f"Thread: {st.session_state.active_thread}")
    
    current_messages = st.session_state.threads[st.session_state.active_thread]
    
    # Display message history
    for msg in current_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Chat Input
    if user_prompt := st.chat_input("Ask about captaincy choices, transfers, differential picks..."):
        # Display user input immediately
        with st.chat_message("user"):
            st.markdown(user_prompt)
            
        current_messages.append({"role": "user", "content": user_prompt})
        save_chat_threads(st.session_state.threads)
        
        # Prepare context / system instructions
        system_instruction = (
            "You are an expert Fantasy Premier League (FPL) assistant. "
            "Provide insightful, data-driven advice on transfers, captaincy, "
            "fixture difficulty, and squad structure. Keep responses structured and concise."
        )
        
        # Build contents payload from history
        contents = []
        for msg in current_messages:
            contents.append(
                types.Content(
                    role="user" if msg["role"] == "user" else "model",
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # --- FIX FOR LINE 517 SYNTAX ERROR ---
            try:
                response_stream = client.models.generate_content_stream(
                    model=model_choice,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                    )
                )
                
                for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                        
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                st.error(f"Error calling Gemini API: {e}")
                full_response = "Sorry, I encountered an issue generating a response. Please try again."
                message_placeholder.markdown(full_response)
            # -------------------------------------

        # Save assistant message
        current_messages.append({"role": "assistant", "content": full_response})
        save_chat_threads(st.session_state.threads)
        
