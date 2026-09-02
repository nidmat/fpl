import os
import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FPL Analytics & AI Chat", layout="wide")

# Initialize Gemini Client (Reads key from Streamlit Secrets or Environment Variable)
api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
client = genai.Client(api_key=api_key) if api_key else None

# Helper function to read Excel files and compile Markdown context for Gemini
@st.cache_data
def load_all_excel_context():
    files = ["fpl_stats.xlsx", "fpl_analytics.xlsx"]
    context_str = ""
    
    for fname in files:
        if os.path.exists(fname):
            xl = pd.ExcelFile(fname)
            for sheet in xl.sheet_names:
                df = xl.parse(sheet)
                context_str += f"\n--- FILE: {fname} | TAB: {sheet} ---\n"
                context_str += df.to_markdown(index=False) + "\n"
    return context_str

# Helper function to load dataset dictionary for the UI spreadsheet viewer
@st.cache_data
def load_excel_tables():
    files = {"Stats": "fpl_stats.xlsx", "Analytics": "fpl_analytics.xlsx"}
    loaded_data = {}
    for prefix, fname in files.items():
        if os.path.exists(fname):
            xl = pd.ExcelFile(fname)
            for sheet in xl.sheet_names:
                loaded_data[f"[{prefix}] {sheet}"] = xl.parse(sheet)
    return loaded_data

# --- TOP NAVIGATION TABS ---
tab_data, tab_chat = st.tabs(["📊 Spreadsheet Viewer", "💬 FPL AI Assistant"])

# ==============================================================================
# TAB 1: SPREADSHEET VIEWER
# ==============================================================================
with tab_data:
    st.title("⚽ FPL Spreadsheet Viewer")
    tables = load_excel_tables()
    
    if not tables:
        st.error("Neither `fpl_stats.xlsx` nor `fpl_analytics.xlsx` was found in the project root.")
    else:
        # Sidebar Sheet Selection
        selected_sheet = st.sidebar.radio("Select Sheet View", list(tables.keys()))
        df = tables[selected_sheet]

        st.subheader(f"Current Sheet: {selected_sheet}")

        # Dynamic Sidebar Filters
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filters")
        filtered_df = df.copy()

        categorical_cols = filtered_df.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            unique_vals = filtered_df[col].dropna().unique().tolist()
            selected_vals = st.sidebar.multiselect(f"Filter by {col}", options=unique_vals, default=[])
            if selected_vals:
                filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]

        # Display Interactive Grid
        st.dataframe(filtered_df, use_container_width=True, hide_index=True, height=600)
        st.caption(f"Showing {len(filtered_df)} of {len(df)} total rows")

# ==============================================================================
# TAB 2: CHATGPT-STYLE AI ASSISTANT (GEMINI 2.5 FLASH)
# ==============================================================================
with tab_chat:
    st.title("🤖 FPL Data Analyst Assistant")
    st.caption("Ask questions strictly based on data from `fpl_stats.xlsx` and `fpl_analytics.xlsx`.")

    if not api_key:
        st.warning("⚠️ `GEMINI_API_KEY` is not configured. Please add it to your Streamlit secrets or environment variables.")
    
    # Initialize Persistent Session Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "Hello! I am your FPL data agent. Ask me anything about player ownership, positions, chips, or defensive contribution stats across your spreadsheets!"
            }
        ]

    # Render Historical Messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input Box at Bottom
    if user_prompt := st.chat_input("e.g., Which midfielder has the best DC potential in fpl_analytics?"):
        
        # 1. Render and store user message
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # 2. Query Gemini 2.5 Flash and stream response
        with st.chat_message("assistant"):
            if not client:
                error_msg = "Cannot execute request: GEMINI_API_KEY is missing."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                with st.spinner("Analyzing spreadsheet data..."):
                    context_data = load_all_excel_context()
                    
                    system_instruction = (
                        "You are an expert Fantasy Premier League Data Analyst.\n"
                        "Your ONLY job is to answer the user's question using the provided Excel context.\n\n"
                        "STRICT RULES:\n"
                        "1. Answer ONLY using facts explicitly present in the provided context from fpl_stats.xlsx and fpl_analytics.xlsx.\n"
                        "2. Do NOT use outside web search, external FPL knowledge, or real-world assumptions.\n"
                        "3. If the data to answer the query is missing from the tables, reply exact words: "
                        "'The provided spreadsheets do not contain enough data to answer this question.'\n"
                        "4. Keep your answer clear, structured, and reference the specific tab name or numbers used."
                    )

                    try:
                        # Request using gemini-2.5-flash
                        response_stream = client.models.generate_content_stream(
                            model="gemini-2.5-flash",
                            contents=f"SPREADSHEET DATA:\n{context_data}\n\nUSER QUESTION:\n{user_prompt}",
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=0.0  # Zero temperature ensures pure factual responses
                            )
                        )
                        
                        # Helper generator to render streaming text
                        def stream_text():
                            for chunk in response_stream:
                                yield chunk.text

                        full_response = st.write_stream(stream_text)
                        
                        # Store assistant response in session memory
                        st.session_state.messages.append({"role": "assistant", "content": full_response})

                    except Exception as e:
                        err_text = f"An error occurred while querying Gemini: {e}"
                        st.error(err_text)
                        st.session_state.messages.append({"role": "assistant", "content": err_text})
