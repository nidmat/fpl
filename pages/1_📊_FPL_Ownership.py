import streamlit as st
from fpl_utils import render_option2_page, render_top_nav

st.set_page_config(page_title="FPL Ownership", page_icon="📊", layout="wide")
render_top_nav("ownership")
render_option2_page("fpl_stats.xlsx", "FPL Ownership")