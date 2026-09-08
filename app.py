import os
import glob
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="FPL Analytics Dashboard",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ FPL Analytics Dashboard")

# Find available Excel files in current working directory
excel_files = glob.glob("*.xlsx")
if not excel_files:
    st.error("No Excel workbooks (*.xlsx) found in the current directory.")
    st.stop()

# Sidebar controls
st.sidebar.header("Data Source & Settings")
selected_file = st.sidebar.selectbox("Select Workbook", sorted(excel_files))

@st.cache_data
def load_sheets(file_path):
    excel_app = pd.ExcelFile(file_path)
    return excel_app.sheet_names, excel_app

sheet_names, excel_obj = load_sheets(selected_file)
selected_sheet = st.sidebar.selectbox("Select Sheet", sheet_names)

# Load selected sheet data
df = pd.read_excel(excel_obj, sheet_name=selected_sheet)

if df.empty:
    st.warning("The selected sheet contains no data.")
    st.stop()

# Search / Filter Control
st.sidebar.header("Filters")
search_query = st.sidebar.text_input("Search (any column text):", "")

filtered_df = df.copy()
if search_query:
    mask = filtered_df.astype(str).apply(
        lambda row: row.str.contains(search_query, case=False, na=False).any(),
        axis=1,
    )
    filtered_df = filtered_df[mask]

# Stats Summary Bar
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Rows", len(filtered_df))
with col2:
    st.metric("Total Columns", len(filtered_df.columns))
with col3:
    st.metric("Active Sheet", selected_sheet)

# Dataframe Rendering with Dynamic First Column Freeze
if not filtered_df.empty:
    first_col = filtered_df.columns[0]

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            first_col: st.column_config.Column(pinned=True)
        },
    )
else:
    st.info("No records matched your search query.")
