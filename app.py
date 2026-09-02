import time

# --- Inside tab_chat where you call client.models.generate_content_stream ---

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

    # Models list to try sequentially if one gives a 503 error
    candidate_models = ["gemini-3.7-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]
    
    response_stream = None
    last_error = None

    for model_id in candidate_models:
        try:
            response_stream = client.models.generate_content_stream(
                model=model_id,
                contents=f"SPREADSHEET DATA:\n{context_data}\n\nUSER QUESTION:\n{user_prompt}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0
                )
            )
            # If successful, break out of fallback loop
            break
        except Exception as e:
            last_error = e
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                time.sleep(1) # Brief 1-second pause before trying the secondary model
                continue
            else:
                # If it's another error (e.g. invalid key), fail immediately
                raise e

    if response_stream:
        # Helper generator to render streaming text
        def stream_text():
            for chunk in response_stream:
                yield chunk.text

        full_response = st.write_stream(stream_text)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    else:
        err_text = f"Google servers are experiencing heavy load across models. Error: {last_error}"
        st.error(err_text)
        st.session_state.messages.append({"role": "assistant", "content": err_text})
