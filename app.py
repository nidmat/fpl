import os
import json
import time
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types, errors

# Standard copy button fallback handler
try:
    from st_copy_button import st_copy_button
    HAS_ST_COPY = True
except ImportError:
    HAS_ST_COPY = False


# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FPL Analytics & AI Chat", page_icon="⚽", layout="wide"
)

# Initialize Gemini Client (Reads key from Streamlit Secrets or Environment Variable)
api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
client = genai.Client(api_key=api_key) if api_key else None

SHARED_CHAT_FILE = "all_chat_threads.json"


# --- MULTI-THREAD SHARED PERSISTENCE HELPERS ---
def load_all_threads() -> dict[str, list[dict]]:
    """Loads all shared chat threads from disk."""
    if os.path.exists(SHARED_CHAT_FILE):
        try:
            with open(SHARED_CHAT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            pass
    
    # Default initial thread if file is missing or empty
    return {
        "General FPL Chat": [
            {
                "role": "assistant",
                "content": "Hello! I am your shared FPL data agent. Select or create a thread in the sidebar to get started!",
            }
        ]
    }


def save_all_threads(threads: dict[str, list[dict]]):
    """Persists all threads to disk, strictly filtering out error messages."""
    valid_threads = {}
    error_keywords = [
        "429", "503", "ResourceExhausted", "APIError", 
        "Unable to reach Gemini models", "GEMINI_API_KEY is missing",
        "quota", "rate limit"
    ]

    for thread_name, messages in threads.items():
        clean_messages = []
        for msg in messages:
            content = str(msg.get("content", ""))
            is_error = any(err.lower() in content.lower() for err in error_keywords)
            if not is_error:
                clean_messages.append(msg)
        valid_threads[thread_name] = clean_messages

    try:
        with open(SHARED_CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump(valid_threads, f, indent=2)
    except Exception as e:
        st.error(f"Failed to persist chat data: {e}")


# Essential analytical columns across Gameweeks to minimize token bloat
ESSENTIAL_COLS = [
    "name", "web_name", "element_type", "position", "team", 
    "now_cost", "DC", "selected_by_percent", "total_points", 
    "minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded", "bonus", "xG", "xA"
]


# Helper function to load datasets as structured JSON sections with TOKEN TRUNCATION
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

                # --- TOKEN OPTIMIZATION: TRUNCATE TO TOP 70 PLAYERS PER TAB ---
                if "total_points" in df.columns:
                    df = df.sort_values(by="total_points", ascending=False).head(70)
                elif "selected_by_percent" in df.columns:
                    df = df.sort_values(by="selected_by_percent", ascending=False).head(70)
                elif "minutes" in df.columns:
                    df = df.sort_values(by="minutes", ascending=False).head(70)
                else:
                    df = df.head(70)

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
            if is_mid and ("mid" in key_lower or "stats" in key_lower):
                selected_sections.append(f"--- {key} ---\n{json_data}")
            elif is_def and ("def" in key_lower or "stats" in key_lower):
                selected_sections.append(f"--- {key} ---\n{json_data}")
            elif is_fwd and ("fwd" in key_lower or "stats" in key_lower):
                # Clean DC metrics from FWD json data payload if evaluating FWD specific sheet
                if "fwd" in key_lower:
                    try:
                        fwd_records = json.loads(json_data)
                        for r in fwd_records:
                            r.pop("DC", None)
                        json_data = json.dumps(fwd_records, separators=(",", ":"))
                    except Exception:
                        pass
                selected_sections.append(f"--- {key} ---\n{json_data}")
            elif is_gk and ("gk" in key_lower or "stats" in key_lower):
                selected_sections.append(f"--- {key} ---\n{json_data}")
        else:
            selected_sections.append(f"--- {key} ---\n{json_data}")

    if not selected_sections:
        selected_sections = [f"--- {k} ---\n{v}" for k, v in all_context.items()]

    return "\n\n".join(selected_sections)


# Helper function to load dataset dictionary structured by file
@st.cache_data
def load_excel_tables():
    files = {
        "FPL Stats (fpl_stats.xlsx)": "fpl_stats.xlsx",
        "FPL Analytics (fpl_analytics.xlsx)": "fpl_analytics.xlsx",
    }
    loaded_data = {}
    for label, fname in files.items():
        if os.path.exists(fname):
            xl = pd.ExcelFile(fname)
            loaded_data[label] = {
                sheet: xl.parse(sheet) for sheet in xl.sheet_names
            }
    return loaded_data


# Style function using exclusively DARK TEXT (#000000) for high readability
def style_ownership(val):
    if pd.isna(val):
        return ""
    
    numeric_val = val
    if isinstance(val, str):
        val_clean = val.replace("%", "").strip()
        try:
            numeric_val = float(val_clean)
        except ValueError:
            return ""

    if isinstance(numeric_val, (int, float)):
        if numeric_val > 20:
            return "background-color: #81c784; color: #000000; font-weight: bold;"
        elif 10 <= numeric_val <= 20:
            return "background-color: #c8e6c9; color: #000000;"
        elif -20 <= numeric_val <= -5:
            return "background-color: #ffe0b2; color: #000000;"
        elif numeric_val < -20:
            return "background-color: #ffb74d; color: #000000; font-weight: bold;"
    
    return ""


# Clean and round percentage numbers or percentage strings to 2 decimal places
def format_percentage_column(df: pd.DataFrame) -> pd.DataFrame:
    df_clean = df.copy()
    for col in df_clean.columns:
        if "%" in col or "percent" in col.lower():
            if df_clean[col].dtype == object:
                try:
                    df_clean[col] = (
                        df_clean[col]
                        .astype(str)
                        .str.replace("%", "", regex=False)
                        .str.strip()
                    )
                    df_clean[col] = pd.to_numeric(df_clean[col], errors="ignore")
                except Exception:
                    pass

            if pd.api.types.is_numeric_dtype(df_clean[col]):
                df_clean[col] = df_clean[col].round(2)
    return df_clean


# Helper to render copy button for text
def render_copy_button(text_to_copy: str, key_suffix: str):
    if HAS_ST_COPY:
        st_copy_button(
            text=text_to_copy,
            before_copy_label="📋 Copy Output",
            after_copy_label="✅ Copied!",
            key=f"copy_{key_suffix}",
        )
    else:
        # Fallback copy mechanism using code box or native button toast
        if st.button("📋 Copy Text", key=f"btn_copy_{key_suffix}"):
            st.toast("Response text ready! Select and copy from the code section below.")
            st.code(text_to_copy, language=None)


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
    workbooks = load_excel_tables()

    if not workbooks:
        st.error(
            "Neither `fpl_stats.xlsx` nor `fpl_analytics.xlsx` was found in the project root."
        )
    else:
        st.sidebar.title("📊 File & Sheet Controls")
        
        selected_workbook = st.sidebar.radio(
            "Select Excel File",
            options=list(workbooks.keys()),
        )
        
        available_sheets = list(workbooks[selected_workbook].keys())

        selected_sheet = st.sidebar.radio(
            "Select Tab / Sheet",
            options=available_sheets,
        )

        df = workbooks[selected_workbook][selected_sheet]

        st.subheader(f"Current View: {selected_workbook} ➔ {selected_sheet}")

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

        filtered_df = format_percentage_column(filtered_df)

        first_col = filtered_df.columns[0] if not filtered_df.empty else None
        column_config = (
            {first_col: st.column_config.Column(pinned=True)}
            if first_col
            else {}
        )

        for col in filtered_df.columns:
            if "%" in col or "percent" in col.lower():
                if pd.api.types.is_numeric_dtype(filtered_df[col]):
                    column_config[col] = st.column_config.NumberColumn(
                        col, format="%.2f"
                    )

        is_fpl_stats_file = "fpl_stats.xlsx" in selected_workbook
        target_sheets = [
            "GK", "DEF", "MID", "FWD", "Defense", "Attack", "player ownership"
        ]
        is_target_sheet = any(
            t.lower() in selected_sheet.lower() for t in target_sheets
        )

        if is_fpl_stats_file and is_target_sheet:
            change_cols = [
                c for c in filtered_df.columns 
                if "% change" in c.lower() or "change" in c.lower() or "diff" in c.lower()
            ]
            
            if change_cols:
                styled_df = filtered_df.style.map(
                    style_ownership, subset=change_cols
                ).format(
                    "{:.2f}",
                    subset=[
                        c for c in change_cols if pd.api.types.is_numeric_dtype(filtered_df[c])
                    ],
                )
            else:
                styled_df = filtered_df
        else:
            styled_df = filtered_df

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            height=600,
            column_config=column_config,
        )
        st.caption(f"Showing {len(filtered_df)} of {len(df)} total rows")

# ==============================================================================
# VIEW 2: MULTI-CHAT AGENT (SHARED ACROSS USERS)
# ==============================================================================
elif st.session_state.active_tab == "💬 FPL AI Assistant":
    st.sidebar.title("💬 Shared Chat Threads")

    all_threads = load_all_threads()

    # --- CREATE NEW THREAD CONTROL ---
    with st.sidebar.expander("➕ Create New Chat Thread", expanded=False):
        new_thread_name = st.text_input("Thread Topic Name", placeholder="e.g., GW5 FWD Analysis")
        if st.button("Create Thread", use_container_width=True):
            if new_thread_name.strip():
                clean_name = new_thread_name.strip()
                if clean_name not in all_threads:
                    all_threads[clean_name] = [
                        {
                            "role": "assistant",
                            "content": f"Started thread: **{clean_name}**. Ask any concise, stat-driven questions!",
                        }
                    ]
                    save_all_threads(all_threads)
                    st.session_state.active_thread = clean_name
                    st.rerun()
                else:
                    st.warning("A thread with that name already exists!")

    # Thread Selection Controls
    thread_names = list(all_threads.keys())
    
    if "active_thread" not in st.session_state or st.session_state.active_thread not in thread_names:
        st.session_state.active_thread = thread_names[0]

    selected_thread = st.sidebar.radio(
        "Select Active Thread",
        options=thread_names,
        index=thread_names.index(st.session_state.active_thread),
    )
    st.session_state.active_thread = selected_thread

    st.sidebar.markdown("---")
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
        value=0.2,
        step=0.1,
    )

    top_p = st.sidebar.slider(
        "Top-P",
        min_value=0.0,
        max_value=1.0,
        value=0.9,
        step=0.05,
    )

    st.sidebar.markdown("---")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🗑️ Reset Thread", use_container_width=True):
            all_threads[selected_thread] = [
                {
                    "role": "assistant",
                    "content": f"Thread **{selected_thread}** has been reset.",
                }
            ]
            save_all_threads(all_threads)
            st.rerun()
    with col2:
        if st.button("🧹 Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared!")

    st.title("🤖 FPL Data Analyst Assistant")
    st.caption(
        f"Active Thread: **{selected_thread}** | Active Model: **{selected_model_id}**"
    )

    if not api_key:
        st.warning(
            "⚠️ `GEMINI_API_KEY` is not configured. Please add it to your Streamlit secrets or environment variables."
        )

    current_thread_messages = all_threads.get(selected_thread, [])
    for idx, msg in enumerate(current_thread_messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                render_copy_button(msg["content"], f"hist_{idx}")

    if user_prompt := st.chat_input(
        f"Ask a question in '{selected_thread}'..."
    ):
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            if not client:
                st.error("Cannot execute request: GEMINI_API_KEY is missing.")
            else:
                with st.spinner(
                    f"Analyzing FPL data via `{selected_model_id}`..."
                ):
                    context_data = get_routed_context(user_prompt)

                    system_instruction = (
                        "You are a strict, stat-oriented Fantasy Premier League (FPL) Data Analyst.\n\n"
                        "FORMAT & OUTPUT REQUIREMENTS:\n"
                        "1. CONCISE & CHAT-SHAREABLE: Minimize fluff/filler text. Structure output cleanly with emojis and concise bullet points so users can easily copy-paste into social chats (e.g. WhatsApp, Discord).\n"
                        "2. EMPHASIS ON #1 OPTION: Always crown the unambiguous #1 standout option first with an explicit title, followed by their full metric breakdown.\n"
                        "3. TABLES FOR DATA: Back up every claim with Markdown tables containing exact stats.\n"
                        "4. SINGLE-LINE TEAM SUMMARIES: Consolidate team-level analysis into brief 1-line bullet summaries.\n\n"
                        "POSITION-SPECIFIC METRIC SELECTION (FROM ANALYTICS DATASET):\n"
                        "- FORWARDS (FWD): Focus strictly on `xG`, `xA`, `goals_scored`, `assists`, `total_points`, and `bonus`. (Do NOT use or mention `DC` for Forwards).\n"
                        "- MIDFIELDERS (MID): Focus heavily on `xG`, `xA`, `goals_scored`, `assists`, `DC`, `total_points`, and `bonus`.\n"
                        "- DEFENDERS (DEF) & GOALKEEPERS (GK): Focus heavily on `total_points`, `clean_sheets` (cs), `goals_conceded` (gc), `DC`, and `bonus`. (Note: `goals_scored` & `assists` are strictly tiebreakers).\n\n"
                        "OWNERSHIP DATA (FROM STATS DATASET):\n"
                        "- Explicitly label ownership values as 'Top 500k Ownership'. Highlight % ownership changes across Gameweeks.\n"
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

              
