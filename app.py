import os
import json
import time
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types, errors

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FPL Analytics & AI Chat", page_icon="⚽", layout="wide"
)

# Initialize Gemini Client (Reads key from Streamlit Secrets or Environment Variable)
api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
client = genai.Client(api_key=api_key) if api_key else None


# Essential analytical columns across Gameweeks to minimize token bloat
ESSENTIAL_COLS = [
    "name", "web_name", "element_type", "position", "team", 
    "now_cost", "DC", "selected_by_percent", "total_points", 
    "minutes", "goals_scored", "assists", "clean_sheets", "bonus", "xG", "xA"
]


# Helper function to load datasets as structured JSON sections
@st.cache_data
def load_all_excel_context():
    files = ["fpl_stats.xlsx", "fpl_analytics.xlsx"]
    context_dict = {}

    for fname in files:
        if os.path.exists(fname):
            xl = pd.ExcelFile(fname)
            for sheet in xl.sheet_names:
                df = xl.parse(sheet)
                
                # Filter out 0-minute bench players to clear dead weight
                if "minutes" in df.columns:
                    df = df[df["minutes"] > 0]

                # Retain only relevant metrics
                cols_to_keep = [c for c in ESSENTIAL_COLS if c in df.columns]
                if cols_to_keep:
                    df = df[cols_to_keep]

                # Store as compact JSON string
                records = df.to_dict(orient="records")
                context_dict[f"FILE: {fname} | TAB: {sheet}"] = json.dumps(
                    records, separators=(",", ":")
                )

    return context_dict


# Smart router function to inject only prompt-relevant context sections
def get_routed_context(user_prompt: str) -> str:
    all_context = load_all_excel_context()
    prompt_lower = user_prompt.lower()
    
    selected_sections = []
    
    # Identify target position or query focus
    is_mid = any(k in prompt_lower for k in ["mid", "midfielder", "wing"])
    is_def = any(k in prompt_lower for k in ["def", "defender", "back", "cb", "lb", "rb"])
    is_fwd = any(k in prompt_lower for k in ["fwd", "forward", "striker", "att"])
    is_gk = any(k in prompt_lower for k in ["gk", "keeper", "goalkeeper"])

    has_specific_filter = is_mid or is_def or is_fwd or is_gk

    for key, json_data in all_context.items():
        key_lower = key.lower()

        if has_specific_filter:
            # Match specific position tabs
            if is_mid and ("mid" in key_lower or "stats" in key_lower):
                selected_sections.append(f"--- {key} ---\n{json_data}")
            elif is_def and ("def" in key_lower or "stats" in key_lower):
                selected_sections.append(f"--- {key} ---\n{json_data}")
            elif is_fwd and ("fwd" in key_lower or "stats" in key_lower):
                selected_sections.append(f"--- {key} ---\n{json_data}")
            elif is_gk and ("gk" in key_lower or "stats" in key_lower):
                selected_sections.append(f"--- {key} ---\n{json_data}")
        else:
            # Fallback for general queries: include all loaded sections
            selected_sections.append(f"--- {key} ---\n{json_data}")

    # Fallback safety if filtering yields no matches
    if not selected_sections:
        selected_sections = [f"--- {k} ---\n{v}" for k, v in all_context.items()]

    return "\n\n".join(selected_sections)


# Helper function to load dataset dictionary for the UI spreadsheet viewer
# Returns plain DataFrames which serialize cleanly in Streamlit caching
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


# --- TOP NAVIGATION ---
st.session_state.active_tab = st.radio(
    "Navigation",
    ["📊 Spreadsheet Viewer", "💬 FPL AI Assistant"],
    horizontal=True,
    label_visibility="collapsed",
)

# ==============================================================================
# VIEW 1: SPREADSHEET VIEWER
# ==============================================================================
if st.session_state.active_tab == "📊 Spreadsheet Viewer":
    st.title("⚽ FPL Spreadsheet Viewer")
    tables = load_excel_tables()

    if not tables:
        st.error(
            "Neither `fpl_stats.xlsx` nor `fpl_analytics.xlsx` was found in the project root."
        )
    else:
        st.sidebar.title("📊 Spreadsheet Controls")
        selected_sheet = st.sidebar.radio(
            "Select Sheet View", list(tables.keys())
        )
        df = tables[selected_sheet]

        st.subheader(f"Current Sheet: {selected_sheet}")

        st.sidebar.markdown("---")
        st.sidebar.subheader("Data Filters")
        filtered_df = df.copy()

        categorical_cols = filtered_df.select_dtypes(
            include=["object", "category"]
        ).columns
        for col in categorical_cols:
            unique_vals = filtered_df[col].dropna().unique().tolist()
            selected_vals = st.sidebar.multiselect(
                f"Filter by {col}", options=unique_vals, default=[]
            )
            if selected_vals:
                filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]

        # Automatically pin/freeze the first column regardless of its name
        first_col = filtered_df.columns[0] if not filtered_df.empty else None
        column_config = (
            {first_col: st.column_config.Column(pinned=True)}
            if first_col
            else {}
        )

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            height=600,
            column_config=column_config,
        )
        st.caption(f"Showing {len(filtered_df)} of {len(df)} total rows")

# ==============================================================================
# VIEW 2: CHATGPT-STYLE AI ASSISTANT
# ==============================================================================
elif st.session_state.active_tab == "💬 FPL AI Assistant":
    st.sidebar.title("🤖 Model Configuration")

    MODEL_OPTIONS = {
        "Gemini 3.6 Flash (Recommended)": "gemini-3.6-flash",
        "Gemini 3.6 Pro (High Performance)": "gemini-3.6-pro",
        "Gemini 3.5 Flash-Lite (Low Latency)": "gemini-3.5-flash-lite",
    }

    selected_model_label = st.sidebar.selectbox(
        "Select Model",
        options=list(MODEL_OPTIONS.keys()),
        index=0,
        help="Choose the Gemini model best suited for your query speed and reasoning needs.",
    )
    selected_model_id = MODEL_OPTIONS[selected_model_label]

    st.sidebar.markdown("---")
    st.sidebar.subheader("Hyperparameters")

    temperature = st.sidebar.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.4,
        step=0.1,
        help="Higher values allow more creative analysis and domain-based insights.",
    )

    top_p = st.sidebar.slider(
        "Top-P",
        min_value=0.0,
        max_value=1.0,
        value=0.95,
        step=0.05,
        help="Controls cumulative probability threshold for token selection.",
    )

    st.title("🤖 FPL Data Analyst Assistant")
    st.caption(
        f"Active Model: **{selected_model_id}** | Token-optimized JSON context with dynamic tab routing."
    )

    if not api_key:
        st.warning(
            "⚠️ `GEMINI_API_KEY` is not configured. Please add it to your Streamlit secrets or environment variables."
        )

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I am your FPL data agent. Ask me anything about player ownership, positions, chips, or defensive contribution stats across your spreadsheets!",
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_prompt := st.chat_input(
        "e.g., Which midfielder has the best DC potential in fpl_analytics?"
    ):
        st.session_state.messages.append(
            {"role": "user", "content": user_prompt}
        )
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            if not client:
                error_msg = "Cannot execute request: GEMINI_API_KEY is missing."
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
            else:
                with st.spinner(
                    f"Analyzing routed data via `{selected_model_id}`..."
                ):
                    # Route and isolate essential context for query
                    context_data = get_routed_context(user_prompt)

                    system_instruction = (
                        "You are an expert Fantasy Premier League (FPL) Data & Strategy Analyst.\n\n"
                        "ANALYSIS RULES:\n"
                        "1. Use the provided JSON spreadsheet data (`fpl_stats.xlsx` and `fpl_analytics.xlsx`) as your primary ground-truth dataset.\n"
                        "2. When a user asks for metrics that are NOT explicitly present in the data (e.g., xG, xA, set-piece duties):\n"
                        "   - Clearly state which metrics are present in the table vs. missing.\n"
                        "   - Present the best options available using available metrics (e.g., sort by DC, baseline bonus, or points).\n"
                        "   - Supplement your analysis with tactical FPL football knowledge to explain potential upside.\n"
                        "3. Format your output cleanly using bullet points or Markdown tables.\n"
                    )

                    candidate_models = [selected_model_id]
                    for fallback in ["gemini-3.6-flash", "gemini-3.6-pro", "gemini-3.5-flash-lite"]:
                        if fallback not in candidate_models:
                            candidate_models.append(fallback)

                    chunks = []
                    last_error = None

                    for model_id in candidate_models:
                        try:
                            response_stream = client.models.generate_content_stream(
                                model=model_id,
                                contents=f"SPREADSHEET DATA (JSON):\n{context_data}\n\nUSER QUESTION:\n{user_prompt}",
                                config=types.GenerateContentConfig(
                                    system_instruction=system_instruction,
                                    temperature=temperature,
                                    top_p=top_p,
                                ),
                            )

                            chunks = []
                            for chunk in response_stream:
                                if chunk.text:
                                    chunks.append(chunk.text)

                            if chunks:
                                break

                        except (errors.APIError, Exception) as e:
                            last_error = e
                            time.sleep(1)
                            continue

                    if chunks:
                        def chunk_generator():
                            for c in chunks:
                                yield c

                        full_response = st.write_stream(chunk_generator())

                        st.session_state.messages.append(
                            {"role": "assistant", "content": full_response}
                        )
                    else:
                        err_text = f"Unable to reach Gemini models. Details: {last_error}"
                        st.error(err_text)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": err_text}
                        )
