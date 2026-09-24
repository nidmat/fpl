import streamlit as st
from fpl_utils import render_top_nav, get_sqlite_engine

st.set_page_config(page_title="FPL Analytics Suite", page_icon="⚽", layout="wide")

# Render Horizontal Navigation Tabs
render_top_nav("home")

# Hero Section
st.title("⚽ FPL Analytics Suite")
st.markdown(
    """
    Welcome to your **Fantasy Premier League (FPL) Analytics Suite**.
    Use the navigation tiles below or the top tabs to explore ownership trends, player performance data, and our AI assistant.
    """
)

st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

# 3 Navigation Tiles
col1, col2, col3 = st.columns(3)

with col1:
    with st.container(key="tile_ownership"):
        st.markdown(
            """
            <span class="tile-badge">Ownership & Transfers</span>
            <div class="tile-title">📊 FPL Ownership</div>
            <div class="tile-desc">
                Analyze player & team ownership trends across gameweeks. Monitor rising stars, falling differentials, and interactive charts.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/1_📊_FPL_Ownership.py",
            label="Explore Ownership →",
            icon="📊",
            width="stretch",
        )

with col2:
    with st.container(key="tile_stats"):
        st.markdown(
            """
            <span class="tile-badge">Player Metrics</span>
            <div class="tile-title">📈 PL Player Statistics</div>
            <div class="tile-desc">
                Comprehensive data across positions: expected goals (xG), expected assists (xA), bonus points, and attacking/defensive contributions.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/2_📈_PL_Player_Statistics.py",
            label="Explore Statistics →",
            icon="📈",
            width="stretch",
        )

with col3:
    with st.container(key="tile_chat"):
        st.markdown(
            """
            <span class="tile-badge">Gemini AI Advisor</span>
            <div class="tile-title">⚡ Kneejerk Analyst</div>
            <div class="tile-desc">
                Consult your AI assistant before you make that late-night transfer or take a -8 hit. Get instant, data-backed second opinions.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/3_⚡_Kneejerk_Analyst.py",
            label="Consult Analyst →",
            icon="⚡",
            width="stretch",
        )

st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

with st.spinner("Initializing data engine..."):
    conn = get_sqlite_engine()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
    count = cursor.fetchone()[0]

st.info(f"⚡ Data Engine active with **{count}** indexed tables ready for analysis.", icon="ℹ️")