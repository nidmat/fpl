import streamlit as st
from fpl_utils import apply_custom_theme, get_sqlite_engine

st.set_page_config(page_title="FPL Analytics Suite", page_icon="⚽", layout="wide")
apply_custom_theme()

st.title("⚽ FPL Analytics Suite")
st.markdown(
    """
    Welcome to the **Fantasy Premier League (FPL) Analytics Suite**.

    * 📊 **FPL Ownership:** Analyze player ownership statistics, recent transfers, and ownership changes to stay ahead of the curve.
    * 📈 **PL Player Statistics:** Dive deep into comprehensive player data, including expected goals (xG), expected assists (xA), and defensive contributions.
    * 💬 **Ask Me:** Chat with our state-of-the-art AI assistant, powered by Gemini, to get instant, data-backed answers to your FPL dilemmas.

    """
)

with st.spinner("Initializing data engine..."):
    conn = get_sqlite_engine()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
    count = cursor.fetchone()[0]

st.success("Data engine initialized and ready!")