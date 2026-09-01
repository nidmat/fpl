import os
import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="FPL Analytics Dashboard", layout="wide")
st.title("⚽ Fantasy Premier League Dashboard")

# List available files
DATA_FILES = {
    "FPL Stats": "fpl_stats.xlsx",
    "FPL Analytics": "fpl_analytics.xlsx"
}

# 1. Select Workbook
selected_file_label = st.sidebar.selectbox("Choose Workbook", list(DATA_FILES.keys()))
selected_filepath = DATA_FILES[selected_file_label]

# Load Excel File safely with caching
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None
    excel_file = pd.ExcelFile(file_path)
    return {sheet: excel_file.parse(sheet) for sheet in excel_file.sheet_names}

sheets_dict = load_data(selected_filepath)

if sheets_dict is None:
    st.error(f"`{selected_filepath}` was not found in the project folder. Make sure the file exists!")
else:
    # 2. Select Sheet / Tab
    selected_sheet = st.sidebar.radio("Select Sheet", list(sheets_dict.keys()))
    df = sheets_dict[selected_sheet]

    st.subheader(f"{selected_file_label} ➔ {selected_sheet}")

    # 3. Dynamic Sidebar Filters
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")
    
    filtered_df = df.copy()

    # Automatically create filter controls for text/categorical columns
    categorical_cols = filtered_df.select_dtypes(include=['object', 'category']).columns
    for col in categorical_cols:
        unique_vals = filtered_df[col].dropna().unique().tolist()
        selected_vals = st.sidebar.multiselect(f"Filter by {col}", options=unique_vals, default=[])
        if selected_vals:
            filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]

    # 4. Interactive Data Table
    st.dataframe(
        filtered_df, 
        use_container_width=True, 
        hide_index=True,
        height=650
    )
    
    st.caption(f"Showing {len(filtered_df)} of {len(df)} rows")