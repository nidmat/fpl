import time
import streamlit as st
from google.genai import types
from fpl_utils import (
    apply_custom_theme,
    get_gemini_client,
    load_all_threads,
    save_all_threads,
    get_routed_db_context,
    render_copy_button,
)

st.set_page_config(page_title="Ask Me", page_icon="💬", layout="wide")
apply_custom_theme()

client = get_gemini_client()
all_threads = load_all_threads()

st.sidebar.markdown("### 💬 Workspaces")

with st.sidebar.expander("➕ New Thread", expanded=False):
    new_thread_name = st.text_input("Thread Name")
    if st.button("Create", use_container_width=True):
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

st.title("🤖 Ask Me")
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
                    "You are an expert FPL Data Analyst. Answer using the provided data dumps.\n\n"
                    f"DATASET CONTEXT:\n{context_data}\n"
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