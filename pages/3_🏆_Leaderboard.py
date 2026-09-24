import streamlit as st
from fpl_utils import (
    apply_custom_theme,
    render_top_nav,
    get_sqlite_engine,
    _load_combined_players,
    _render_pl_leaderboards,
)

st.set_page_config(page_title="Player Leaderboards", page_icon="🏆", layout="wide")
apply_custom_theme()
render_top_nav("leaderboard")

conn = get_sqlite_engine()
df_players = _load_combined_players(conn)
_render_pl_leaderboards(df_players, key_prefix="page_leaderboard")
