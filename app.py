import json
import os
import time
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

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
        "429",
        "503",
        "ResourceExhausted",
        "APIError",
        "Unable to reach Gemini models",
        "GEMINI_API_KEY is missing",
        "quota",
        "rate limit",
    ]

    for thread_name, messages in threads.items():
        clean_messages = []
        for msg in messages:
            content = str(msg.get("content", ""))
            is_error = any(
                err.lower() in content.lower() for err in error_keywords
            )
            if not is_error:
                clean_messages.append(msg)
        valid_threads[thread_name] = clean_messages

    try:
        with open(SHARED_CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump(valid_threads, f, indent=2)
    except Exception as e:
        st.error(f"Failed to persist chat data: {e}")


# Complete CSV Data Loader — ALL ROWS AND COLUMNS PRESERVED WITHOUT TRUNCATION
@st.cache_data
def load_all_excel_context(sort_metric: str = "total_points"):
    files = ["fpl_stats.xlsx", "fpl_analytics.xlsx"]
    context_dict = {}

    for fname in files:
        if os.path.exists(fname):
            xl = pd.ExcelFile(fname)
            for sheet in xl.sheet_names:
                df = xl.parse(sheet)

                # Remove unnamed pandas index headers if present
                df = df.loc[
                    :, ~df.columns.astype(str).str.contains("^Unnamed")
                ]

                # --- OPTIONAL SORTING WITHOUT ROW TRUNCATION ---
                target_sort = None
                for col in df.columns:
                    if str(col).lower() == sort_metric.lower():
                        target_sort = col
                        break

                if target_sort and pd.api.types.is_numeric_dtype(
                    df[target_sort]
                ):
                    df = df.sort_values(by=target_sort, ascending=False)

                # Convert entire DataFrame (all rows & all columns intact) to CSV text
                csv_data = df.to_csv(index=False)
                context_dict[f"FILE: {fname} | TAB: {sheet}"] = csv_data

    return context_dict


# Smart router function loading complete dataset context across all sheets
def get_routed_context(user_prompt: str) -> str:
    prompt_lower = user_prompt.lower()

    sort_metric = "total_points"
    if "dc" in prompt_lower or "defensive contribution" in prompt_lower:
        sort_metric = "DC"
    elif "xg" in prompt_lower:
        sort_metric = "xG"
    elif "xa" in prompt_lower:
        sort_metric = "xA"
    elif "xgi" in prompt_lower:
        sort_metric = "xGI"
    elif "bonus" in prompt_lower or "bps" in prompt_lower:
        sort_metric = "bonus"

    all_context = load_all_excel_context(sort_metric=sort_metric)

    analytics_sections = []
    stats_sections = []

    is_mid = any(
        k in prompt_lower
        for k in ["mid", "midfielder", "wing", "mids", "midfielders"]
    )
    is_def = any(
        k in prompt_lower
        for k in ["def", "defender", "back", "cb", "lb", "rb", "defenders"]
    )
    is_fwd = any(
        k in prompt_lower for k in ["fwd", "forward", "striker", "att", "forwards"]
    )
    is_gk = any(
        k in prompt_lower for k in ["gk", "keeper", "goalkeeper", "goalkeepers"]
    )

    has_specific_filter = is_mid or is_def or is_fwd or is_gk

    for key, csv_data in all_context.items():
        key_lower = key.lower()

        if "fpl_analytics.xlsx" in key:
            if has_specific_filter:
                if is_mid and (
                    "mid" in key_lower
                    or "all" in key_lower
                    or "overall" in key_lower
                ):
                    analytics_sections.append(f"=== {key} ===\n{csv_data}")
                elif is_def and (
                    "def" in key_lower
                    or "all" in key_lower
                    or "overall" in key_lower
                ):
                    analytics_sections.append(f"=== {key} ===\n{csv_data}")
                elif is_fwd and (
                    "fwd" in key_lower
                    or "all" in key_lower
                    or "overall" in key_lower
                ):
                    analytics_sections.append(f"=== {key} ===\n{csv_data}")
                elif is_gk and (
                    "gk" in key_lower
                    or "all" in key_lower
                    or "overall" in key_lower
                ):
                    analytics_sections.append(f"=== {key} ===\n{csv_data}")
            else:
                analytics_sections.append(f"=== {key} ===\n{csv_data}")
        else:
            if has_specific_filter:
                if is_mid and (
                    "mid" in key_lower
                    or "all" in key_lower
                    or "overall" in key_lower
                ):
                    stats_sections.append(f"=== {key} ===\n{csv_data}")
                elif is_def and (
                    "def" in key_lower
                    or "all" in key_lower
                    or "overall" in key_lower
                ):
                    stats_sections.append(f"=== {key} ===\n{csv_data}")
                elif is_fwd and (
                    "fwd" in key_lower
                    or "all" in key_lower
                    or "overall" in key_lower
                ):
                    stats_sections.append(f"=== {key} ===\n{csv_data}")
                elif is_gk and (
                    "gk" in key_lower
                    or "all" in key_lower
                    or "overall" in key_lower
                ):
                    stats_sections.append(f"=== {key} ===\n{csv_data}")

    combined_sections = analytics_sections + stats_sections

    if not combined_sections:
        combined_sections = [
            f"=== {k} ===\n{v}" for k, v in all_context.items()
        ]

    return "\n\n".join(combined_sections)


# Helper function to load dataset dictionary structured by file
@st.cache_data
def load_excel_workbook(fname: str) -> dict[str, pd.DataFrame]:
    if os.path.exists(fname):
        xl = pd.ExcelFile(fname)
        return {sheet: xl.parse(sheet) for sheet in xl.sheet_names}
    return {}


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
            return (
                "background-color: #ffb74d; color: #000000; font-weight: bold;"
            )

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
                    df_clean[col] = pd.to_numeric(
                        df_clean[col], errors="ignore"
                    )
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
        if st.button("📋 Copy Text", key=f"btn_copy_{key_suffix}"):
            st.toast(
                "Response text ready! Select and copy from the code section below."
            )
            st.code(text_to_copy, language=None)


# Render reusable spreadsheet viewer per file
def render_sheet_viewer(fname: str, label: str):
    st.header(f"📊 {label}")
    sheets_dict = load_excel_workbook(fname)

    if not sheets_dict:
        st.error(f"File `{fname}` was not found in the project root.")
        return

    st.sidebar.markdown("---")
    st.sidebar.title(f"📁 {label} Options")
    available_sheets = list(sheets_dict.keys())
    selected_sheet = st.sidebar.selectbox(
        f"Select Sheet / Tab ({label}):",
        options=available_sheets,
        key=f"select_sheet_{fname}",
    )

    df = sheets_dict[selected_sheet]
    st.subheader(f"Current View: {fname} ➔ {selected_sheet}")

    st.sidebar.markdown("### Data Filters")
    filtered_df = df.copy()

    categorical_cols = filtered_df.select_dtypes(
        include=["object", "category"]
    ).columns

    if len(categorical_cols) > 0:
        for col in categorical_cols:
            unique_vals = filtered_df[col].dropna().unique().tolist()
            selected_vals = st.sidebar.multiselect(
                f"Filter {col}",
                options=unique_vals,
                default=[],
                key=f"filter_{fname}_{selected_sheet}_{col}",
            )
            if selected_vals:
                filtered_df = filtered_df[
                    filtered_df[col].isin(selected_vals)
                ]

    filtered_df = format_percentage_column(filtered_df)

    first_col = filtered_df.columns[0] if not filtered_df.empty else None
    column_config = (
        {first_col: st.column_config.Column(pinned=True)} if first_col else {}
    )

    for col in filtered_df.columns:
        if "%" in col or "percent" in col.lower():
            if pd.api.types.is_numeric_dtype(filtered_df[col]):
                column_config[col] = st.column_config.NumberColumn(
                    col, format="%.2f"
                )

    is_fpl_stats_file = "fpl_stats.xlsx" in fname
    target_sheets = [
        "GK",
        "DEF",
        "MID",
        "FWD",
        "Defense",
        "Attack",
        "player ownership",
    ]
    is_target_sheet = any(
        t.lower() in selected_sheet.lower() for t in target_sheets
    )

    if is_fpl_stats_file and is_target_sheet:
        change_cols = [
            c
            for c in filtered_df.columns
            if "% change" in c.lower()
            or "change" in c.lower()
            or "diff" in c.lower()
        ]

        if change_cols:
            styled_df = filtered_df.style.map(
                style_ownership, subset=change_cols
            ).format(
                "{:.2f}",
                subset=[
                    c
                    for c in change_cols
                    if pd.api.types.is_numeric_dtype(filtered_df[c])
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
        height=650,
        column_config=column_config,
    )
    st.caption(f"Showing {len(filtered_df)} of {len(df)} total rows")


# --- SIDEBAR RADIO NAVIGATION ---
st.sidebar.title("📌 Navigation")
app_mode = st.sidebar.radio(
    "Choose View",
    options=[
        "📊 FPL Stats (fpl_stats.xlsx)",
        "📈 FPL Analytics (fpl_analytics.xlsx)",
        "💬 FPL AI Assistant",
    ],
)

# ==============================================================================
# VIEW 1: FPL STATS
# ==============================================================================
if app_mode == "📊 FPL Stats (fpl_stats.xlsx)":
    render_sheet_viewer("fpl_stats.xlsx", "FPL Stats")

# ==============================================================================
# VIEW 2: FPL ANALYTICS
# ==============================================================================
elif app_mode == "📈 FPL Analytics (fpl_analytics.xlsx)":
    render_sheet_viewer("fpl_analytics.xlsx", "FPL Analytics")

# ==============================================================================
# VIEW 3: MULTI-CHAT AI ASSISTANT
# ==============================================================================
elif app_mode == "💬 FPL AI Assistant":
    st.sidebar.markdown("---")
    st.sidebar.title("💬 Shared Chat Threads")

    all_threads = load_all_threads()

    with st.sidebar.expander("➕ Create New Chat Thread", expanded=False):
        new_thread_name = st.text_input(
            "Thread Topic Name", placeholder="e.g., GW5 DEF Analysis"
        )
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

    thread_names = list(all_threads.keys())

    if (
        "active_thread" not in st.session_state
        or st.session_state.active_thread not in thread_names
    ):
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
                        "You are an expert, stat-driven Fantasy Premier League (FPL) Data Analyst.\n\n"
                        "CONTEXT FROM DATASET (CSV FORMAT WITH ALL ROWS AND COLUMNS):\n"
                        f"{context_data}\n\n"
                        "STRICT MANDATES FOR YOUR RESPONSE:\n"
                        "1. EXHAUSTIVE EVALUATION: Read through the complete CSV data provided across all sheets without omitting players present in the context.\n"
                        "2. DISPLAY ACTUAL PLAYER NAMES: Map player names correctly from columns (e.g., 'name', 'web_name', or column 0). Never use placeholder names.\n"
                        "3. ACCURATE STAT MATCHING: Verify points, goals, assists, minutes, and team data for every queried player directly from the loaded CSV string.\n"
                        "4. SAMPLE SIZE FILTERING: Always check total minutes played and starts before recommending a player or utilizing per-90 metrics. Ignore or heavily discount players with low minutes (e.g., <180–270 minutes or under 2–3 starts) when making transfer recommendations or rank comparisons.\n"
                        "5. PER 90 RATE NORMALIZATION: Do NOT rely on DC90 (Defensive Contribution per 90), xG90, xA90, xGI90, or saves per 90 for decision-making if a player has limited minutes/starts. Small sample sizes cause severe statistical noise (e.g., a sub getting 1 goal in 15 minutes = 6.00 xG90). Always mention if a high per-90 score is distorted by low minutes, and prioritize absolute totals and regular starters.\n"
                    )

                    contents_payload = []
                    for msg in current_thread_messages:
                        api_role = "user" if msg["role"] == "user" else "model"
                        contents_payload.append(
                            types.Content(
                                role=api_role,
                                parts=[
                                    types.Part.from_text(text=msg["content"])
                                ],
                            )
                        )

                    contents_payload.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=user_prompt)],
                        )
                    )

                    candidate_models = [selected_model_id]
                    for fallback in [
                        "gemini-3.6-flash",
                        "gemini-3.6-pro",
                        "gemini-3.5-flash-lite",
                    ]:
                        if fallback not in candidate_models:
                            candidate_models.append(fallback)

                    last_error = None

                    for model_id in candidate_models:
                        try:
                            response_stream = (
                                client.models.generate_content_stream(
                                    model=model_id,
                                    contents=contents_payload,
                                    config=types.GenerateContentConfig(
                                        system_instruction=system_instruction,
                                        temperature=temperature,
                                        top_p=top_p,
                                    ),
                                )
                            )

                            def stream_generator():
                                for chunk in response_stream:
                                    if chunk.text:
                                        yield chunk.text

                            full_response = st.write_stream(stream_generator())

                            all_threads[selected_thread].append(
                                {"role": "user", "content": user_prompt}
                            )
                            all_threads[selected_thread].append(
                                {"role": "assistant", "content": full_response}
                            )
                            save_all_threads(all_threads)
                            render_copy_button(
                                full_response, f"live_{time.time()}"
                            )

                            last_error = None
                            break
                        except Exception as e:
                            last_error = e
                            continue

                    if last_error is not None:
                        error_msg = f"Unable to reach Gemini models. Error: {last_error}"
                        st.error(error_msg)
                        all_threads[selected_thread].append(
                            {"role": "user", "content": user_prompt}
                        )
                        all_threads[selected_thread].append(
                            {"role": "assistant", "content": error_msg}
                        )
                        save_all_threads(all_threads)