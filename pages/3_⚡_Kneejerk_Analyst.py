import json
import time
import streamlit as st
from google.genai import types
from fpl_utils import (
    apply_custom_theme,
    render_top_nav,
    get_gemini_client,
    load_all_threads,
    save_all_threads,
    get_routed_db_context,
    render_copy_button,
)

st.set_page_config(page_title="Kneejerk Analyst", page_icon="⚡", layout="wide")
render_top_nav("chat")

client = get_gemini_client()
all_threads = load_all_threads()

st.sidebar.markdown("### 💬 Workspaces")

with st.sidebar.expander("➕ New Thread", expanded=False):
    new_thread_name = st.text_input("Thread Name")
    if st.button("Create", width="stretch"):
        if new_thread_name.strip():
            clean_name = new_thread_name.strip()
            if clean_name not in all_threads:
                all_threads[clean_name] = [
                    {"role": "assistant", "content": f"Initialized **{clean_name}**."}
                ]
                save_all_threads(all_threads)
                st.session_state.active_thread = clean_name
                st.rerun()

thread_names = list(all_threads.keys())
if "active_thread" not in st.session_state or st.session_state.active_thread not in thread_names:
    st.session_state.active_thread = thread_names[0]

selected_thread = st.sidebar.radio(
    "Active Thread",
    options=thread_names,
    index=thread_names.index(st.session_state.active_thread),
)
st.session_state.active_thread = selected_thread

with st.sidebar.expander("💾 Backup & Restore", expanded=False):
    st.caption("Preserve your threads across app reboots or transfer between devices.")
    threads_json = json.dumps(all_threads, indent=2)
    st.download_button(
        label="📥 Download Threads (JSON)",
        data=threads_json,
        file_name=f"fpl_chat_backup_{time.strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        width="stretch",
    )
    st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Restore from Backup (.json)",
        type=["json"],
        key="chat_backup_uploader",
    )
    if uploaded_file is not None:
        try:
            imported_threads = json.load(uploaded_file)
            if isinstance(imported_threads, dict) and imported_threads:
                all_threads.update(imported_threads)
                save_all_threads(all_threads)
                st.sidebar.success(f"Restored {len(imported_threads)} thread(s)!")
                time.sleep(0.8)
                st.rerun()
            else:
                st.sidebar.error("Invalid backup: expected JSON object.")
        except Exception as e:
            st.sidebar.error(f"Failed to restore: {e}")

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
    if st.button("🗑️ Reset Thread", width="stretch"):
        all_threads[selected_thread] = [
            {
                "role": "assistant",
                "content": f"Thread **{selected_thread}** has been reset.",
            }
        ]
        save_all_threads(all_threads)
        st.rerun()
with col2:
    if st.button("🧹 Clear Cache", width="stretch"):
        st.cache_data.clear()
        st.success("Cache cleared!")

st.title("⚡ Kneejerk Analyst")
st.caption(
    f"Active Thread: **{selected_thread}** | Active Model: **{selected_model_id}**"
)

current_messages = all_threads.get(selected_thread, [])
for idx, msg in enumerate(current_messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_copy_button(msg["content"], f"hist_{idx}")

if user_prompt := st.chat_input("Ask a question about the FPL data..."):
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        if not client:
            st.error("Missing GEMINI_API_KEY.")
        else:
            with st.spinner("Fetching data context..."):
                context_data = get_routed_db_context(user_prompt)
                system_instruction = (
                    "You are the '⚡ Kneejerk Analyst' — an expert, witty, and stat-driven Fantasy Premier League (FPL) Data Analyst.\n\n"
                    "CONTEXT FROM DATASET (CSV FORMAT WITH ALL ROWS AND COLUMNS):\n"
                    f"{context_data}\n\n"
                    "STRICT MANDATES FOR YOUR RESPONSE:\n"
                    "1. EXHAUSTIVE EVALUATION: Read through the complete CSV data provided across all sheets without omitting players present in the context.\n"
                    "2. DISPLAY ACTUAL PLAYER NAMES: Map player names correctly from columns (e.g., 'name', 'web_name', or column 0). Never use placeholder names.\n"
                    "3. ACCURATE STAT MATCHING: Verify points, goals, assists, minutes, and team data for every queried player directly from the loaded CSV string.\n"
                    "4. SAMPLE SIZE FILTERING: Always check total minutes played and starts before recommending a player or utilizing per-90 metrics. Ignore or heavily discount players with low minutes (e.g., <180–270 minutes or under 2–3 starts) when making transfer recommendations or rank comparisons.\n"
                    "5. PER 90 RATE NORMALIZATION: Do NOT rely on DC90 (Defensive Contribution per 90), xG90, xA90, xGI90, or saves per 90 for decision-making if a player has limited minutes/starts. Small sample sizes cause severe statistical noise (e.g., a sub getting 1 goal in 15 minutes = 6.00 xG90). Always mention if a high per-90 score is distorted by low minutes, and prioritize absolute totals and regular starters.\n"
                    "6. WITTY & HUMOROUS DELIVERY: Deliver your analysis with dry football humor, witty banter, and classic FPL tropes (e.g., Pep roulette dread, late-night kneejerk transfers, -8 hit regrets, bench points agony). While your statistics, numbers, and evaluation MUST strictly adhere to mandates 1–5, make your delivery sharp, funny, and entertaining.\n"
                )

                contents_payload = [
                    types.Content(
                        role="user" if m["role"] == "user" else "model",
                        parts=[types.Part.from_text(text=m["content"])],
                    )
                    for m in current_messages
                ]
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
                        response_stream = client.models.generate_content_stream(
                            model=model_id,
                            contents=contents_payload,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=temperature,
                                top_p=top_p,
                            ),
                        )

                        def stream_generator():
                            for chunk in response_stream:
                                if chunk.text:
                                    yield chunk.text

                        full_response = st.write_stream(stream_generator())
                        all_threads[selected_thread].append({"role": "user", "content": user_prompt})
                        all_threads[selected_thread].append({"role": "assistant", "content": full_response})
                        save_all_threads(all_threads)
                        render_copy_button(full_response, f"live_{time.time()}")
                        
                        last_error = None
                        break
                    except Exception as e:
                        last_error = e
                        continue
                
                if last_error is not None:
                    error_msg = f"Unable to reach Gemini models. Error: {last_error}"
                    st.error(error_msg)
                    all_threads[selected_thread].append({"role": "user", "content": user_prompt})
                    all_threads[selected_thread].append({"role": "assistant", "content": error_msg})
                    save_all_threads(all_threads)