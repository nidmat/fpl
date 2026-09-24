import json
import os
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import numpy as np
from google import genai

SHARED_CHAT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "all_chat_threads.json"
)

try:
    from st_copy_button import st_copy_button
    HAS_ST_COPY = True
except ImportError:
    HAS_ST_COPY = False

def style_ownership(val):
    if pd.isna(val):
        return None

    numeric_val = val
    if isinstance(val, str):
        val_clean = val.replace("%", "").strip()
        try:
            numeric_val = float(val_clean)
        except ValueError:
            return None

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

    return None


def apply_custom_theme():
    """Applies theme-aware styling that works seamlessly across both Light and Dark modes."""
    st.markdown(
        """
        <style>
        /* Adapt dynamically to Streamlit's base light/dark mode */
        .stApp {
            color: var(--text-color);
        }

        /* Hide the default multi-page sidebar navigation */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Top Horizontal Nav Bar Container separator */
        .top-nav-container {
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Style all page_link buttons in the top navbar */
        div[class*="st-key-nav_"] a[data-testid="stPageLink-NavLink"] {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            border-radius: 10px !important;
            padding: 8px 14px !important;
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
            text-align: center !important;
            text-decoration: none !important;
        }

        /* Active Navigation Tab */
        div[class*="st-key-nav_active"] a[data-testid="stPageLink-NavLink"] {
            background: rgba(0, 255, 135, 0.16) !important;
            border: 1.5px solid #00ff87 !important;
            color: #00ff87 !important;
            box-shadow: 0 0 14px rgba(0, 255, 135, 0.25) !important;
        }

        /* Inactive Navigation Tabs */
        div[class*="st-key-nav_inactive"] a[data-testid="stPageLink-NavLink"] {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.09) !important;
            color: #d1d5db !important;
        }

        div[class*="st-key-nav_inactive"] a[data-testid="stPageLink-NavLink"]:hover {
            background: rgba(255, 255, 255, 0.1) !important;
            border-color: rgba(0, 255, 135, 0.45) !important;
            color: #ffffff !important;
            transform: translateY(-1px) !important;
        }

        /* Navigation Tiles styling for Home page */
        div[class*="st-key-tile_"] {
            background: linear-gradient(145deg, #181c24, #12151b) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 14px !important;
            padding: 1.25rem !important;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3) !important;
        }

        div[class*="st-key-tile_"]:hover {
            transform: translateY(-4px) !important;
            border-color: rgba(0, 255, 135, 0.45) !important;
            box-shadow: 0 10px 28px rgba(0, 255, 135, 0.15) !important;
        }

        /* Tile inner badges & typography */
        .tile-badge {
            display: inline-block;
            background: rgba(0, 255, 135, 0.12);
            color: #00ff87;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 3px 9px;
            border-radius: 20px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .tile-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .tile-desc {
            font-size: 0.9rem;
            color: #94a3b8;
            line-height: 1.5;
            min-height: 3.8rem;
            margin-bottom: 1rem;
        }

        /* Styled containers for metrics and assistant cards */
        .fpl-card {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
        }

        /* Color-coded Sheet Tab System: wrap into neat pill rows within the window */
        div[data-baseweb="tab-list"] {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 6px !important;
            max-width: 100% !important;
            overflow-x: visible !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
            padding-bottom: 8px !important;
            margin-bottom: 12px !important;
        }

        div[data-baseweb="tab-highlight"],
        div[data-baseweb="tab-border"] {
            display: none !important;
        }

        button[data-baseweb="tab"] {
            border-radius: 8px !important;
            padding: 6px 14px !important;
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: #d1d5db !important;
            white-space: nowrap !important;
            margin: 2px 0 !important;
            transition: all 0.2s ease-in-out !important;
        }

        button[data-baseweb="tab"]:hover {
            background: rgba(255, 255, 255, 0.09) !important;
            border-color: rgba(0, 255, 135, 0.4) !important;
            color: #ffffff !important;
        }

        /* Active Tab indicator highlight */
        button[data-baseweb="tab"][aria-selected="true"] {
            background: rgba(0, 255, 135, 0.15) !important;
            border: 1.5px solid #00ff87 !important;
            color: #00ff87 !important;
            box-shadow: 0 0 10px rgba(0, 255, 135, 0.2) !important;
        }

        /* Mobile responsive optimizations */
        @media (max-width: 768px) {
            /* Top page navigation: 2x2 grid so all 4 buttons are immediately visible without any horizontal sliding */
            div[class*="st-key-top_nav_bar"] [data-testid="stHorizontalBlock"] {
                display: grid !important;
                grid-template-columns: 1fr 1fr !important;
                gap: 8px !important;
                width: 100% !important;
                overflow-x: visible !important;
            }

            div[class*="st-key-top_nav_bar"] [data-testid="column"] {
                width: 100% !important;
                min-width: 0 !important;
                flex: 1 1 auto !important;
            }

            div[class*="st-key-nav_"] a[data-testid="stPageLink-NavLink"] {
                padding: 10px 8px !important;
                font-size: 0.82rem !important;
                white-space: normal !important;
                line-height: 1.25 !important;
                text-align: center !important;
                justify-content: center !important;
                min-height: 44px !important;
            }

            /* Sheet tabs buttons on mobile: wrap compactly */
            div[data-baseweb="tab-list"] {
                gap: 5px !important;
            }

            button[data-baseweb="tab"] {
                padding: 5px 10px !important;
                font-size: 0.78rem !important;
            }

            /* Responsive tiles on mobile */
            div[class*="st-key-tile_"] {
                margin-bottom: 12px !important;
                padding: 1rem !important;
            }

            .tile-desc {
                min-height: auto !important;
                font-size: 0.85rem !important;
                margin-bottom: 0.75rem !important;
            }

            .tile-title {
                font-size: 1.1rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_nav(current_page: str):
    """
    Renders horizontal navigation tabs at the top of every page.
    current_page: 'home' | 'ownership' | 'stats' | 'leaderboard' | 'chat'
    """
    apply_custom_theme()

    pages = [
        {"id": "home", "label": "Home", "icon": "🏠", "path": "Home.py"},
        {"id": "ownership", "label": "FPL Ownership", "icon": "📊", "path": "pages/1_📊_FPL_Ownership.py"},
        {"id": "stats", "label": "PL Player Statistics", "icon": "📈", "path": "pages/2_📈_PL_Player_Statistics.py"},
        {"id": "leaderboard", "label": "Leaderboard", "icon": "🏆", "path": "pages/3_🏆_Leaderboard.py"},
        {"id": "chat", "label": "Kneejerk Analyst", "icon": "⚡", "path": "pages/4_⚡_Kneejerk_Analyst.py"},
    ]

    with st.container(key="top_nav_bar"):
        cols = st.columns(len(pages))
        for i, p in enumerate(pages):
            is_active = (p["id"] == current_page)
            with cols[i]:
                with st.container(key=f"nav_active_{p['id']}" if is_active else f"nav_inactive_{p['id']}"):
                    st.page_link(
                        p["path"],
                        label=p["label"],
                        icon=p["icon"],
                        width="stretch",
                    )

    st.markdown("<div class='top-nav-container'></div>", unsafe_allow_html=True)



def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    return genai.Client(api_key=api_key) if api_key else None


@st.cache_resource
def get_sqlite_engine():
    """Indexes fpl_stats.xlsx and fpl_analytics.xlsx into in-memory SQLite tables."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    files = ["fpl_stats.xlsx", "fpl_analytics.xlsx"]

    for fname in files:
        if os.path.exists(fname):
            xl = pd.ExcelFile(fname)
            prefix = fname.replace(".xlsx", "")
            for sheet in xl.sheet_names:
                df = xl.parse(sheet)
                df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed")]
                clean_sheet = sheet.replace(" ", "_").replace("%", "pct")
                table_name = f"{prefix}_{clean_sheet}"
                df.to_sql(table_name, conn, if_exists="replace", index=False)
    return conn


def load_all_threads() -> dict[str, list[dict]]:
    if os.path.exists(SHARED_CHAT_FILE):
        try:
            with open(SHARED_CHAT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            pass

    # Fallback: check if an existing backup file exists in parent/system paths
    fallbacks = [
        "all_chat_threads.json",
        os.path.join("..", "all_chat_threads.json"),
        r"C:\FPL\all_chat_threads.json",
    ]
    for fallback in fallbacks:
        if os.path.exists(fallback):
            try:
                with open(fallback, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and data:
                        save_all_threads(data)
                        return data
            except Exception:
                pass

    return {
        "General FPL Chat": [
            {
                "role": "assistant",
                "content": "Welcome to the FPL Data Assistant!",
            }
        ]
    }



def save_all_threads(threads: dict[str, list[dict]]):
    valid_threads = {}
    error_keywords = ["429", "503", "ResourceExhausted", "APIError", "quota"]

    for thread_name, messages in threads.items():
        clean_messages = []
        for msg in messages:
            content = str(msg.get("content", ""))
            if not any(err.lower() in content.lower() for err in error_keywords):
                clean_messages.append(msg)
        valid_threads[thread_name] = clean_messages

    try:
        with open(SHARED_CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump(valid_threads, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save threads: {e}")


def get_routed_db_context(user_prompt: str) -> str:
    conn = get_sqlite_engine()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]

    context_str = []
    for table in tables:
        df = pd.read_sql(f"SELECT * FROM `{table}` LIMIT 20", conn)
        context_str.append(f"=== TABLE: {table} ===\n" + df.to_csv(index=False))

    return "\n\n".join(context_str)


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
            st.toast("Copied!")
            st.code(text_to_copy, language=None)


# 20 visually distinct colors for up to 20 PL teams
_TEAM_COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9a6324", "#fffac8", "#800000", "#aaffc3",
    "#808000", "#ffd8b1", "#000075", "#a9a9a9", "#00ffff",
]


def _parse_numeric(val):
    try:
        return float(str(val).replace("%", "").strip())
    except (ValueError, TypeError):
        return None

def _render_ownership_charts(df: pd.DataFrame, tab_label: str):
    """Renders 3 ownership charts (Line / Grouped Bar / Lollipop) above the data table."""

    team_col = df.columns[0]
    own_cols  = [c for c in df.columns if "% own" in c.lower()]
    change_cols = [
        c for c in df.columns
        if "% change" in c.lower() and pd.api.types.is_numeric_dtype(df[c])
    ]

    if not own_cols:
        return

    gw_labels        = [c.split(" ")[0].upper() for c in own_cols]
    change_gw_labels = [c.split(" ")[0].upper() for c in change_cols]

    st.markdown(f"### 📊 {tab_label} — Ownership Analytics")

    chart_type = st.radio(
        "Select Chart",
        options=[
            "📉 Line — Ownership Trend",
            "📊 Grouped Bar — GW Comparison",
            "🍭 Lollipop — % Change",
        ],
        horizontal=True,
        key=f"chart_type_{tab_label}",
    )

    # ── Chart 1: Line — Ownership % Trend ───────────────────────────────────
    if chart_type == "📉 Line — Ownership Trend":
        st.caption("Hover over a line to see team name and exact ownership %.")
        fig = go.Figure()
        for i, (_, row) in enumerate(df.iterrows()):
            team   = row[team_col]
            values = [_parse_numeric(row[c]) for c in own_cols]
            color  = _TEAM_COLORS[i % len(_TEAM_COLORS)]
            fig.add_trace(go.Scatter(
                x=gw_labels, y=values,
                mode="lines+markers", name=str(team),
                line=dict(color=color, width=2.5),
                marker=dict(size=9, color=color, line=dict(width=1, color="white")),
                hovertemplate=f"<b>{team}</b><br>%{{x}}: <b>%{{y:.1f}}%</b><extra></extra>",
            ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Gameweek", yaxis_title="Ownership %",
            legend=dict(orientation="v", x=1.01, y=1),
            height=500, margin=dict(t=20, b=40, r=180),
            hovermode="closest",
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_own_line_{tab_label}")

    # ── Chart 2: Grouped Bar — Ownership % for a selected GW ────────────────
    elif chart_type == "📊 Grouped Bar — GW Comparison":
        st.caption("Pick a gameweek to compare all teams side by side. Sorted lowest → highest.")
        selected_gw = st.selectbox(
            "Gameweek",
            options=gw_labels,
            index=len(gw_labels) - 1,          # default = latest GW
            key=f"bar_gw_{tab_label}",
        )
        selected_own_col = own_cols[gw_labels.index(selected_gw)]
        plot_df = df[[team_col, selected_own_col]].copy()
        plot_df["_val"] = plot_df[selected_own_col].apply(_parse_numeric)
        plot_df = plot_df.dropna(subset=["_val"]).sort_values("_val", ascending=True)
        bar_colors = [_TEAM_COLORS[i % len(_TEAM_COLORS)] for i in range(len(plot_df))]
        fig = go.Figure(go.Bar(
            x=plot_df[team_col].astype(str), y=plot_df["_val"],
            marker_color=bar_colors,
            hovertemplate="<b>%{x}</b><br>Ownership: <b>%{y:.1f}%</b><extra></extra>",
            text=[f"{v:.1f}%" for v in plot_df["_val"]],
            textposition="outside",
        ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Team", yaxis_title=f"Ownership % ({selected_gw})",
            height=450, margin=dict(t=20, b=90),
            xaxis=dict(tickangle=-35),
            yaxis=dict(range=[0, max(plot_df["_val"]) * 1.18]),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_own_bar_{tab_label}")

    # ── Chart 3: Lollipop — % Change for a selected GW ──────────────────────
    elif chart_type == "🍭 Lollipop — % Change":
        if not change_cols:
            st.info("No % change columns found for this dataset.")
            return
        st.caption("🟢 Green = gaining ownership  |  🔴 Red = losing ownership")
        selected_change_gw = st.selectbox(
            "Gameweek",
            options=change_gw_labels,
            index=len(change_gw_labels) - 1,   # default = latest GW
            key=f"lolli_gw_{tab_label}",
        )
        selected_col = change_cols[change_gw_labels.index(selected_change_gw)]
        cdf = df[[team_col, selected_col]].copy()
        cdf[selected_col] = pd.to_numeric(cdf[selected_col], errors="coerce")
        cdf = cdf.dropna(subset=[selected_col]).sort_values(selected_col, ascending=True)
        dot_colors = ["#00ff87" if v >= 0 else "#ff6b6b" for v in cdf[selected_col]]

        fig = go.Figure()
        for _, row in cdf.iterrows():
            team  = str(row[team_col])
            val   = row[selected_col]
            color = "#00ff87" if val >= 0 else "#ff6b6b"
            fig.add_trace(go.Scatter(
                x=[0, val], y=[team, team], mode="lines",
                line=dict(color=color, width=2),
                showlegend=False, hoverinfo="skip",
            ))
        fig.add_trace(go.Scatter(
            x=cdf[selected_col], y=cdf[team_col].astype(str),
            mode="markers+text",
            marker=dict(size=12, color=dot_colors, line=dict(width=1.5, color="white")),
            text=[f"{v:+.2f}%" for v in cdf[selected_col]],
            textposition=["middle left" if v < 0 else "middle right" for v in cdf[selected_col]],
            textfont=dict(size=10),
            hovertemplate="<b>%{y}</b><br>Change: <b>%{x:+.2f}%</b><extra></extra>",
            showlegend=False,
        ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title=f"% Change ({selected_change_gw})", yaxis_title="Team",
            height=max(460, len(cdf) * 26),
            margin=dict(t=20, b=40, r=100, l=130),
            xaxis=dict(zeroline=True, zerolinecolor="rgba(255,255,255,0.4)", zerolinewidth=2),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_own_lolli_{tab_label}")

    st.divider()






def _render_player_ownership_charts(df: pd.DataFrame, tab_label: str):
    """Charts for player_ownership tab with position/team filtering and top-N selector."""

    player_col   = "Player"
    pos_col      = "Position" if "Position" in df.columns else None
    team_col_p   = "Team"     if "Team"     in df.columns else None

    # Detect GW ownership columns (gw1, gw2, gw3 ...) and change columns
    gw_own_cols    = [c for c in df.columns if c.lower().startswith("gw") and "change" not in c.lower() and "own" not in c.lower()]
    change_cols    = [c for c in df.columns if "% change" in c.lower() and pd.api.types.is_numeric_dtype(df[c])]
    gw_labels      = [c.upper() for c in gw_own_cols]
    change_gw_lbls = [c.split(" ")[0].upper() for c in change_cols]

    if not gw_own_cols:
        return

    latest_gw_col = gw_own_cols[-1]

    st.markdown(f"### 📊 {tab_label} — Player Ownership Analytics")

    # ── Filters ──────────────────────────────────────────────────────────────
    f_col1, f_col2, f_col3 = st.columns([2, 2, 1])
    with f_col1:
        pos_options = sorted(df[pos_col].dropna().unique().tolist()) if pos_col else []
        sel_positions = st.multiselect("Filter by Position", options=pos_options, default=[], key=f"pos_filter_{tab_label}")
    with f_col2:
        team_options = sorted(df[team_col_p].dropna().unique().tolist()) if team_col_p else []
        sel_teams = st.multiselect("Filter by Team", options=team_options, default=[], key=f"team_filter_{tab_label}")
    with f_col3:
        top_n = st.number_input("Top N players", min_value=5, max_value=100, value=10, step=5, key=f"topn_{tab_label}")

    # Apply filters
    fdf = df.copy()
    if sel_positions:
        fdf = fdf[fdf[pos_col].isin(sel_positions)]
    if sel_teams:
        fdf = fdf[fdf[team_col_p].isin(sel_teams)]

    # Convert latest GW to numeric and sort, take top N
    fdf[latest_gw_col] = pd.to_numeric(fdf[latest_gw_col], errors="coerce")
    fdf = fdf.sort_values(latest_gw_col, ascending=False).head(int(top_n))

    if fdf.empty:
        st.warning("No players match the current filters.")
        return

    player_list = fdf[player_col].astype(str).tolist()

    # ── Chart radio ──────────────────────────────────────────────────────────
    chart_type = st.radio(
        "Select Chart",
        options=[
            "📉 Line — Ownership Trend",
            "📊 Grouped Bar — GW Comparison",
            "🍭 Lollipop — % Change",
        ],
        horizontal=True,
        key=f"chart_type_{tab_label}",
    )

    # ── Chart 1: Line ─────────────────────────────────────────────────────────
    if chart_type == "📉 Line — Ownership Trend":
        st.caption("Hover over a line to see the player name and exact ownership %.")
        fig = go.Figure()
        for i, (_, row) in enumerate(fdf.iterrows()):
            player = row[player_col]
            values = [_parse_numeric(row[c]) for c in gw_own_cols]
            color  = _TEAM_COLORS[i % len(_TEAM_COLORS)]
            fig.add_trace(go.Scatter(
                x=gw_labels, y=values,
                mode="lines+markers", name=str(player),
                line=dict(color=color, width=2.5),
                marker=dict(size=8, color=color, line=dict(width=1, color="white")),
                hovertemplate=f"<b>{player}</b><br>%{{x}}: <b>%{{y:.2f}}%</b><extra></extra>",
            ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Gameweek", yaxis_title="Ownership %",
            legend=dict(orientation="v", x=1.01, y=1),
            height=500, margin=dict(t=20, b=40, r=200),
            hovermode="closest",
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_pown_line_{tab_label}")

    # ── Chart 2: Grouped Bar ──────────────────────────────────────────────────
    elif chart_type == "📊 Grouped Bar — GW Comparison":
        st.caption("Pick a gameweek to compare the top players side by side.")
        selected_gw = st.selectbox(
            "Gameweek", options=gw_labels,
            index=len(gw_labels) - 1,
            key=f"bar_gw_{tab_label}",
        )
        sel_own_col = gw_own_cols[gw_labels.index(selected_gw)]
        bdf = fdf[[player_col, sel_own_col]].copy()
        bdf["_val"] = bdf[sel_own_col].apply(_parse_numeric)
        bdf = bdf.dropna(subset=["_val"]).sort_values("_val", ascending=True)
        bar_colors = [_TEAM_COLORS[i % len(_TEAM_COLORS)] for i in range(len(bdf))]
        fig = go.Figure(go.Bar(
            x=bdf[player_col].astype(str), y=bdf["_val"],
            marker_color=bar_colors,
            hovertemplate="<b>%{x}</b><br>Ownership: <b>%{y:.2f}%</b><extra></extra>",
            text=[f"{v:.2f}%" for v in bdf["_val"]],
            textposition="outside",
        ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Player", yaxis_title=f"Ownership % ({selected_gw})",
            height=460, margin=dict(t=20, b=110),
            xaxis=dict(tickangle=-40),
            yaxis=dict(range=[0, max(bdf["_val"]) * 1.18]),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_pown_bar_{tab_label}")

    # ── Chart 3: Lollipop — % Change ─────────────────────────────────────────
    elif chart_type == "🍭 Lollipop — % Change":
        if not change_cols:
            st.info("No % change columns found for player ownership.")
            return
        st.caption("🟢 Green = gaining ownership  |  🔴 Red = losing ownership")
        selected_change_gw = st.selectbox(
            "Gameweek", options=change_gw_lbls,
            index=len(change_gw_lbls) - 1,
            key=f"lolli_gw_{tab_label}",
        )
        sel_chg_col = change_cols[change_gw_lbls.index(selected_change_gw)]
        cdf = fdf[[player_col, sel_chg_col]].copy()
        cdf[sel_chg_col] = pd.to_numeric(cdf[sel_chg_col], errors="coerce")
        cdf = cdf.dropna(subset=[sel_chg_col]).sort_values(sel_chg_col, ascending=True)
        dot_colors = ["#00ff87" if v >= 0 else "#ff6b6b" for v in cdf[sel_chg_col]]

        fig = go.Figure()
        for _, row in cdf.iterrows():
            player = str(row[player_col])
            val    = row[sel_chg_col]
            color  = "#00ff87" if val >= 0 else "#ff6b6b"
            fig.add_trace(go.Scatter(
                x=[0, val], y=[player, player], mode="lines",
                line=dict(color=color, width=2),
                showlegend=False, hoverinfo="skip",
            ))
        fig.add_trace(go.Scatter(
            x=cdf[sel_chg_col], y=cdf[player_col].astype(str),
            mode="markers+text",
            marker=dict(size=11, color=dot_colors, line=dict(width=1.5, color="white")),
            text=[f"{v:+.2f}%" for v in cdf[sel_chg_col]],
            textposition=["middle left" if v < 0 else "middle right" for v in cdf[sel_chg_col]],
            textfont=dict(size=10),
            hovertemplate="<b>%{y}</b><br>Change: <b>%{x:+.2f}%</b><extra></extra>",
            showlegend=False,
        ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title=f"% Change ({selected_change_gw})", yaxis_title="Player",
            height=max(460, len(cdf) * 26),
            margin=dict(t=20, b=40, r=100, l=160),
            xaxis=dict(zeroline=True, zerolinecolor="rgba(255,255,255,0.4)", zerolinewidth=2),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_pown_lolli_{tab_label}")

    st.divider()


_POS_COLORS = {
    "FWD": "#ff4b4b",  # Coral / Red
    "MID": "#00ff87",  # FPL Electric Green
    "DEF": "#00b4d8",  # Sky Blue
    "GK": "#ffd166",   # Amber / Gold
}


def _load_combined_players(conn) -> pd.DataFrame:
    """Loads and unifies GK, DEF, MID, FWD from fpl_analytics into a single rich DataFrame."""
    dfs = []
    for pos in ["GK", "DEF", "MID", "FWD"]:
        try:
            d = pd.read_sql(f"SELECT * FROM fpl_analytics_{pos}", conn)
            d["Position"] = pos
            dfs.append(d)
        except Exception:
            pass

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    numeric_cols = [
        "price", "total points", "form", "gw points", "ppg", "ownership",
        "trf in", "trf out", "Min", "G", "A", "xG", "xA", "xGI", "xG90", "xA90", "xGI90",
        "CS", "GC", "Bonus", "bps"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["Actual_GI"] = df["G"] + df["A"]
    df["Delta_xGI"] = (df["Actual_GI"] - df["xGI"]).round(2)
    df["Delta_xG"] = (df["G"] - df["xG"]).round(2)
    df["net_transfers"] = df["trf in"] - df["trf out"]
    safe_price = df["price"].replace(0, np.nan)
    df["PPM"] = (df["total points"] / safe_price).fillna(0).round(2)
    return df


def _render_pl_underlying_stats(df: pd.DataFrame, key_prefix: str = "hub"):
    """Chart 1: Underlying Stats & Unlucky Buys (xG / xGI vs Actual Return)."""
    st.markdown("### 🎯 Underlying Stats vs Reality: The 'Unlucky Buys' & Regression Detector")
    st.caption("Compare expected returns (xGI/xG) against actual returns. Players below the diagonal line are underperforming their underlying numbers (unlucky, prime buy targets), while players above are riding a hot finishing streak (clinical / due regression).")

    m_col1, m_col2 = st.columns([2, 3])
    with m_col1:
        metric_choice = st.radio(
            "Metric Mode",
            options=["🎯 xGI vs Goal Involvements (G + A)", "⚽ xG vs Actual Goals (G)"],
            horizontal=True,
            key=f"{key_prefix}_und_metric",
        )
    is_xgi = "xGI" in metric_choice
    x_col = "xGI" if is_xgi else "xG"
    y_col = "Actual_GI" if is_xgi else "G"
    delta_col = "Delta_xGI" if is_xgi else "Delta_xG"
    x_title = "Expected Goal Involvement (xGI)" if is_xgi else "Expected Goals (xG)"
    y_title = "Actual Goal Involvements (Goals + Assists)" if is_xgi else "Actual Goals (G)"

    # Filters
    f1, f2, f3, f4 = st.columns([1.5, 1.5, 2, 1.5])
    with f1:
        pos_opts = [p for p in ["FWD", "MID", "DEF", "GK"] if p in df["Position"].unique()]
        sel_pos = st.multiselect("Position", options=pos_opts, default=[p for p in ["FWD", "MID", "DEF"] if p in pos_opts], key=f"{key_prefix}_und_pos")
    with f2:
        team_opts = sorted(df["Team"].dropna().unique().tolist())
        sel_teams = st.multiselect("Team", options=team_opts, default=[], key=f"{key_prefix}_und_team")
    with f3:
        max_mins = int(df["Min"].max()) if not df.empty else 1000
        min_mins = st.slider("Min Minutes Played", 0, max_mins, min(180, max_mins), step=45, key=f"{key_prefix}_und_mins")
    with f4:
        min_p = float(df["price"].min()) if not df.empty else 4.0
        max_p = float(df["price"].max()) if not df.empty else 15.0
        price_range = st.slider("Price (£m)", min_p, max_p, (min_p, max_p), step=0.1, key=f"{key_prefix}_und_price")

    fdf = df.copy()
    if sel_pos:
        fdf = fdf[fdf["Position"].isin(sel_pos)]
    if sel_teams:
        fdf = fdf[fdf["Team"].isin(sel_teams)]
    fdf = fdf[(fdf["Min"] >= min_mins) & (fdf["price"] >= price_range[0]) & (fdf["price"] <= price_range[1])]

    if fdf.empty:
        st.warning("No players match the current filters.")
        return

    max_val = max(fdf[x_col].max(), fdf[y_col].max(), 1.0) * 1.08
    fig = go.Figure()

    # 45-degree reference line
    fig.add_trace(go.Scatter(
        x=[0, max_val], y=[0, max_val],
        mode="lines",
        line=dict(color="rgba(255, 255, 255, 0.35)", dash="dash", width=1.5),
        name="Expected = Actual",
        hoverinfo="skip",
    ))

    # Scatter traces per position
    for pos in ["FWD", "MID", "DEF", "GK"]:
        pdf = fdf[fdf["Position"] == pos]
        if pdf.empty:
            continue
        color = _POS_COLORS.get(pos, "#ffffff")
        sizes = np.clip(pdf["total points"] * 0.35 + 7, 7, 22)
        fig.add_trace(go.Scatter(
            x=pdf[x_col],
            y=pdf[y_col],
            mode="markers",
            name=f"{pos} ({len(pdf)})",
            marker=dict(
                size=sizes,
                color=color,
                opacity=0.85,
                line=dict(width=1, color="white"),
            ),
            hovertext=pdf["Name"],
            customdata=list(zip(pdf["Position"], pdf["Team"], pdf["price"], pdf["Min"], pdf[delta_col], pdf["total points"])),
            hovertemplate="<b>%{hovertext}</b> (%{customdata[0]}) · %{customdata[1]}<br>"
                          "Price: £%{customdata[2]:.1f}m | Minutes: %{customdata[3]} | Pts: %{customdata[5]}<br>"
                          f"{x_title}: <b>%{{x:.2f}}</b><br>"
                          f"{y_title}: <b>%{{y}}</b><br>"
                          "Delta (Actual - Exp): <b>%{customdata[4]:+.2f}</b><extra></extra>",
        ))

    # Visual annotations for quadrants
    fig.add_annotation(
        x=max_val * 0.22, y=max_val * 0.90,
        text="🔴 Overperforming (Clinical / Due Regression)",
        showarrow=False,
        font=dict(color="#ff6b6b", size=11),
        bgcolor="rgba(255, 107, 107, 0.12)",
        bordercolor="rgba(255, 107, 107, 0.3)",
        borderpad=5,
    )
    fig.add_annotation(
        x=max_val * 0.78, y=max_val * 0.12,
        text="🟢 Underperforming (Unlucky / Buy Target)",
        showarrow=False,
        font=dict(color="#00ff87", size=11),
        bgcolor="rgba(0, 255, 135, 0.12)",
        bordercolor="rgba(0, 255, 135, 0.3)",
        borderpad=5,
    )

    fig.update_layout(
        template="plotly_dark",
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=540,
        margin=dict(t=30, b=40, l=50, r=30),
        legend=dict(orientation="h", y=1.06, x=0.01),
        hovermode="closest",
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_underlying_chart")

    # Key takeaway cards
    st.markdown("#### 🔍 Key Takeaways")
    c_unlucky, c_clinical = st.columns(2)
    unlucky_top = fdf.sort_values(delta_col, ascending=True).head(3)
    clinical_top = fdf.sort_values(delta_col, ascending=False).head(3)

    with c_unlucky:
        st.markdown("**🟢 Top 3 Underperforming (Prime 'Buy Low' Targets):**")
        for _, r in unlucky_top.iterrows():
            st.markdown(
                f"- **{r['Name']}** ({r['Team']} · {r['Position']}) — "
                f"Exp: `{r[x_col]:.2f}` vs Act: `{int(r[y_col])}` | "
                f"**Delta: `{r[delta_col]:+.2f}`** (£{r['price']:.1f}m)"
            )

    with c_clinical:
        st.markdown("**🔴 Top 3 Overperforming (Clinical Finishers / Regression Risk):**")
        for _, r in clinical_top.iterrows():
            st.markdown(
                f"- **{r['Name']}** ({r['Team']} · {r['Position']}) — "
                f"Exp: `{r[x_col]:.2f}` vs Act: `{int(r[y_col])}` | "
                f"**Delta: `{r[delta_col]:+.2f}`** (£{r['price']:.1f}m)"
            )


def _render_pl_value_matrix(df: pd.DataFrame, key_prefix: str = "hub"):
    """Chart 2: The Value & Budget Gem Matrix (Price vs Points / PPM)."""
    st.markdown("### 💎 The Value & Budget Gem Matrix")
    st.caption("Identify high-efficiency budget enablers (top-left), dependable premiums (top-right), and avoid overpriced underperformers (bottom-right).")

    v1, v2 = st.columns([2, 2])
    with v1:
        y_metric = st.radio(
            "Y-Axis Return Metric",
            options=["Total Points", "Points Per Game (PPG)", "Points Per Million (PPM)"],
            horizontal=True,
            key=f"{key_prefix}_val_ymetric",
        )
    with v2:
        size_metric = st.radio(
            "Marker Size Scaled By",
            options=["Form", "Ownership %", "Minutes"],
            horizontal=True,
            key=f"{key_prefix}_val_size",
        )

    y_col_map = {"Total Points": "total points", "Points Per Game (PPG)": "ppg", "Points Per Million (PPM)": "PPM"}
    y_col = y_col_map[y_metric]

    size_col_map = {"Form": "form", "Ownership %": "ownership", "Minutes": "Min"}
    s_col = size_col_map[size_metric]

    # Filters
    f1, f2, f3, f4 = st.columns([1.5, 1.5, 2, 1.5])
    with f1:
        pos_opts = [p for p in ["FWD", "MID", "DEF", "GK"] if p in df["Position"].unique()]
        sel_pos = st.multiselect("Position", options=pos_opts, default=pos_opts, key=f"{key_prefix}_val_pos")
    with f2:
        team_opts = sorted(df["Team"].dropna().unique().tolist())
        sel_teams = st.multiselect("Team", options=team_opts, default=[], key=f"{key_prefix}_val_team")
    with f3:
        max_mins = int(df["Min"].max()) if not df.empty else 1000
        min_mins = st.slider("Min Minutes Played", 0, max_mins, min(90, max_mins), step=45, key=f"{key_prefix}_val_mins")
    with f4:
        min_p = float(df["price"].min()) if not df.empty else 4.0
        max_p = float(df["price"].max()) if not df.empty else 15.0
        price_range = st.slider("Price Range (£m)", min_p, max_p, (min_p, max_p), step=0.1, key=f"{key_prefix}_val_price")

    fdf = df.copy()
    if sel_pos:
        fdf = fdf[fdf["Position"].isin(sel_pos)]
    if sel_teams:
        fdf = fdf[fdf["Team"].isin(sel_teams)]
    fdf = fdf[(fdf["Min"] >= min_mins) & (fdf["price"] >= price_range[0]) & (fdf["price"] <= price_range[1])]

    if fdf.empty:
        st.warning("No players match the current filters.")
        return

    med_price = fdf["price"].median()
    med_y = fdf[y_col].median()

    fig = go.Figure()

    # Median Benchmark Lines
    fig.add_vline(x=med_price, line_dash="dash", line_color="rgba(255, 255, 255, 0.25)", annotation_text=f"Med Price: £{med_price:.1f}m", annotation_position="top")
    fig.add_hline(y=med_y, line_dash="dash", line_color="rgba(255, 255, 255, 0.25)", annotation_text=f"Med {y_metric}: {med_y:.1f}", annotation_position="right")

    for pos in ["FWD", "MID", "DEF", "GK"]:
        pdf = fdf[fdf["Position"] == pos]
        if pdf.empty:
            continue
        color = _POS_COLORS.get(pos, "#ffffff")
        sizes = np.clip(pdf[s_col] * (1.8 if s_col == "form" else 0.5 if s_col == "ownership" else 0.015) + 6, 6, 24)
        fig.add_trace(go.Scatter(
            x=pdf["price"],
            y=pdf[y_col],
            mode="markers",
            name=f"{pos} ({len(pdf)})",
            marker=dict(
                size=sizes,
                color=color,
                opacity=0.85,
                line=dict(width=1, color="white"),
            ),
            hovertext=pdf["Name"],
            customdata=list(zip(pdf["Position"], pdf["Team"], pdf["total points"], pdf["ppg"], pdf["PPM"], pdf["form"], pdf["ownership"])),
            hovertemplate="<b>%{hovertext}</b> (%{customdata[0]}) · %{customdata[1]}<br>"
                          "Price: £%{x:.1f}m | Total Points: %{customdata[2]}<br>"
                          "PPG: %{customdata[3]:.1f} | PPM: %{customdata[4]:.2f} pts/£m<br>"
                          "Form: %{customdata[5]} | Ownership: %{customdata[6]}%<extra></extra>",
        ))

    # Quadrant corner labels
    x_min, x_max = fdf["price"].min(), fdf["price"].max()
    y_min, y_max = fdf[y_col].min(), fdf[y_col].max()
    fig.add_annotation(x=x_min + (med_price - x_min) * 0.3, y=y_max * 0.95, text="🌟 Budget Gems", showarrow=False, font=dict(color="#00ff87", size=12, family="sans-serif"), bgcolor="rgba(0, 255, 135, 0.1)")
    fig.add_annotation(x=med_price + (x_max - med_price) * 0.7, y=y_max * 0.95, text="👑 Elite Premiums", showarrow=False, font=dict(color="#ffd166", size=12, family="sans-serif"), bgcolor="rgba(255, 209, 102, 0.1)")
    fig.add_annotation(x=med_price + (x_max - med_price) * 0.7, y=y_min + (med_y - y_min) * 0.2, text="⚠️ Overpriced / Traps", showarrow=False, font=dict(color="#ff4b4b", size=12, family="sans-serif"), bgcolor="rgba(255, 75, 75, 0.1)")
    fig.add_annotation(x=x_min + (med_price - x_min) * 0.3, y=y_min + (med_y - y_min) * 0.2, text="🪑 Cheap Bench", showarrow=False, font=dict(color="#94a3b8", size=12, family="sans-serif"), bgcolor="rgba(148, 163, 184, 0.1)")

    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Price (£m)",
        yaxis_title=y_metric,
        height=540,
        margin=dict(t=30, b=40, l=50, r=30),
        legend=dict(orientation="h", y=1.06, x=0.01),
        hovermode="closest",
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_value_matrix_chart")

    # Key Takeaways
    st.markdown("#### 🔍 Value Spotlights")
    c1, c2 = st.columns(2)
    # Budget gems: outfield <= 6.0m or GK <= 4.5m
    gems_filter = ((fdf["Position"] != "GK") & (fdf["price"] <= 6.0)) | ((fdf["Position"] == "GK") & (fdf["price"] <= 4.5))
    top_gems = fdf[gems_filter].sort_values("total points", ascending=False).head(3)
    top_ppm = fdf.sort_values("PPM", ascending=False).head(3)

    with c1:
        st.markdown("**🌟 Top 3 Budget Enablers (Highest Points $\le$ £6.0m):**")
        for _, r in top_gems.iterrows():
            st.markdown(f"- **{r['Name']}** ({r['Team']} · {r['Position']}) — **{int(r['total points'])} pts** at **£{r['price']:.1f}m** (PPG: `{r['ppg']:.1f}`, PPM: `{r['PPM']:.2f}`)")

    with c2:
        st.markdown("**💰 Top 3 Value Efficiency Kings (Highest Points Per Million):**")
        for _, r in top_ppm.iterrows():
            st.markdown(f"- **{r['Name']}** ({r['Team']} · {r['Position']}) — **{r['PPM']:.2f} pts/£m** ({int(r['total points'])} pts · £{r['price']:.1f}m)")


def _render_pl_team_finishing_efficiency(conn, key_prefix: str = "hub"):
    """Chart 3: Team Finishing Efficiency & Regression (Team xG vs Goals & xGI vs Involvements)."""
    st.markdown("### 🏟️ Team Finishing Efficiency & Regression (Team xGI vs Actual Returns)")
    st.caption("Compare team expected output (xG / xGI) against real goal returns across the league. Identify which attacks are underperforming (unlucky coiled springs due a scoring burst) and which are overperforming (clinical / regression risk).")

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        metric_choice = st.radio(
            "Metric Mode",
            options=["⚽ Expected Goals (xG) vs Actual Goals", "⚡ Expected Involvements (xGI) vs Actual (G + A)"],
            horizontal=True,
            key=f"{key_prefix}_team_fin_metric",
        )
    with c2:
        venue_choice = st.radio(
            "Venue Split",
            options=["🏟️ Overall (All Matches)", "🏠 Home Matches Only", "✈️ Away Matches Only"],
            horizontal=True,
            key=f"{key_prefix}_team_fin_venue",
        )
    with c3:
        view_mode = st.radio(
            "Display Format",
            options=["📊 Side-by-Side Comparison", "⚖️ Finishing Delta (Actual - Expected)"],
            horizontal=True,
            key=f"{key_prefix}_team_fin_view",
        )

    table_map = {
        "🏟️ Overall (All Matches)": "fpl_analytics_TEAM_STATS",
        "🏠 Home Matches Only": "fpl_analytics_TEAM_STATS_HOME",
        "✈️ Away Matches Only": "fpl_analytics_TEAM_STATS_AWAY",
    }
    table_name = table_map[venue_choice]

    try:
        tdf = pd.read_sql(f"SELECT * FROM `{table_name}`", conn)
    except Exception as e:
        st.error(f"Failed to load table `{table_name}`: {e}")
        return

    # Ensure numeric types
    for col in ["Goals", "Assists", "xG", "xA", "xGI"]:
        if col in tdf.columns:
            tdf[col] = pd.to_numeric(tdf[col], errors="coerce").fillna(0)

    is_xgi = "xGI" in metric_choice
    exp_col = "xGI" if is_xgi else "xG"
    tdf["Actual_Val"] = (tdf["Goals"] + tdf["Assists"]) if is_xgi else tdf["Goals"]
    tdf["Delta"] = (tdf["Actual_Val"] - tdf[exp_col]).round(2)
    exp_label = "Expected Goal Involvement (xGI)" if is_xgi else "Expected Goals (xG)"
    act_label = "Actual Involvements (G + A)" if is_xgi else "Actual Goals (G)"

    if "Side-by-Side" in view_mode:
        tdf_sorted = tdf.sort_values(exp_col, ascending=False)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=tdf_sorted["Team"],
            y=tdf_sorted[exp_col],
            name=exp_label,
            marker_color="#00b4d8",
            text=[f"{v:.1f}" for v in tdf_sorted[exp_col]],
            textposition="outside",
            customdata=list(zip(tdf_sorted["Actual_Val"], tdf_sorted["Delta"])),
            hovertemplate="<b>%{x}</b><br>"
                          f"{exp_label}: <b>%{{y:.2f}}</b><br>"
                          f"{act_label}: <b>%{{customdata[0]}}</b><br>"
                          "Finishing Delta: <b>%{customdata[1]:+.2f}</b><extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=tdf_sorted["Team"],
            y=tdf_sorted["Actual_Val"],
            name=act_label,
            marker_color="#00ff87",
            text=[f"{int(v)}" for v in tdf_sorted["Actual_Val"]],
            textposition="outside",
            customdata=list(zip(tdf_sorted[exp_col], tdf_sorted["Delta"])),
            hovertemplate="<b>%{x}</b><br>"
                          f"{act_label}: <b>%{{y}}</b><br>"
                          f"{exp_label}: <b>%{{customdata[0]:.2f}}</b><br>"
                          "Finishing Delta: <b>%{customdata[1]:+.2f}</b><extra></extra>",
        ))
        fig.update_layout(
            barmode="group",
            template="plotly_dark",
            xaxis_title="Team",
            yaxis_title="Count / Value",
            height=520,
            margin=dict(t=30, b=40, l=50, r=30),
            legend=dict(orientation="h", y=1.06, x=0.01),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_team_fin_grouped_chart")

    else:
        tdf_sorted = tdf.sort_values("Delta", ascending=True)
        bar_colors = ["#00ff87" if v >= 0 else "#ff4b4b" for v in tdf_sorted["Delta"]]
        fig = go.Figure(go.Bar(
            y=tdf_sorted["Team"],
            x=tdf_sorted["Delta"],
            orientation="h",
            marker_color=bar_colors,
            text=[f"{v:+.2f}" for v in tdf_sorted["Delta"]],
            textposition="outside",
            customdata=list(zip(tdf_sorted[exp_col], tdf_sorted["Actual_Val"])),
            hovertemplate="<b>%{y}</b><br>"
                          "Finishing Delta (Act - Exp): <b>%{x:+.2f}</b><br>"
                          f"{exp_label}: <b>%{{customdata[0]:.2f}}</b><br>"
                          f"{act_label}: <b>%{{customdata[1]}}</b><extra></extra>",
        ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title=f"Finishing Delta ({act_label} minus {exp_label})",
            yaxis_title="Team",
            height=max(500, len(tdf_sorted) * 26),
            margin=dict(t=20, b=40, l=80, r=80),
            xaxis=dict(zeroline=True, zerolinecolor="rgba(255,255,255,0.4)", zerolinewidth=2),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_team_fin_delta_chart")

    # Key Takeaways
    st.markdown("#### 🔍 Tactical Insights: Who to Target")
    c_unlucky, c_clinical = st.columns(2)
    top_unlucky = tdf.sort_values("Delta", ascending=True).head(3)
    top_clinical = tdf.sort_values("Delta", ascending=False).head(3)

    with c_unlucky:
        st.markdown("**🟢 Top 3 Underperforming Attacks (Unlucky / 'Buy Low' Fixtures):**")
        for _, r in top_unlucky.iterrows():
            st.markdown(
                f"- **{r['Team']}** — Exp: `{r[exp_col]:.2f}` vs Act: `{int(r['Actual_Val'])}` | "
                f"**Delta: `{r['Delta']:+.2f}`** (High chance creation, finishing slump due to break!)"
            )
    with c_clinical:
        st.markdown("**🔴 Top 3 Overperforming Attacks (Clinical Finishers / Due Regression):**")
        for _, r in top_clinical.iterrows():
            st.markdown(
                f"- **{r['Team']}** — Exp: `{r[exp_col]:.2f}` vs Act: `{int(r['Actual_Val'])}` | "
                f"**Delta: `{r['Delta']:+.2f}`** (Scoring significantly above underlying chance quality)"
            )


def _render_pl_transfer_momentum(df: pd.DataFrame, key_prefix: str = "hub"):
    """Chart 4: Transfer Bandwagon & Price Momentum (Net Transfers)."""
    st.markdown("### 🌊 Transfer Bandwagon & Price Momentum")
    st.caption("Monitor net community transfers (Transfers In minus Transfers Out) to jump onto high-performing bandwagons or offload falling assets before price drops.")

    c1, c2, c3 = st.columns([2, 1.5, 2.5])
    with c1:
        view_mode = st.radio(
            "View Format",
            options=["📊 Diverging Bar Chart (Top Inflows vs Outflows)", "📈 Scatter Plot (Net Transfers vs Form)"],
            horizontal=True,
            key=f"{key_prefix}_trf_view",
        )
    with c2:
        top_n = st.selectbox("Top N Players", options=[10, 15, 20], index=1, key=f"{key_prefix}_trf_topn")
    with c3:
        pos_opts = [p for p in ["FWD", "MID", "DEF", "GK"] if p in df["Position"].unique()]
        sel_pos = st.multiselect("Filter Position", options=pos_opts, default=pos_opts, key=f"{key_prefix}_trf_pos")

    fdf = df.copy()
    if sel_pos:
        fdf = fdf[fdf["Position"].isin(sel_pos)]

    if fdf.empty:
        st.warning("No players match the current filters.")
        return

    top_in = fdf.sort_values("net_transfers", ascending=False).head(top_n)
    top_out = fdf.sort_values("net_transfers", ascending=True).head(top_n)

    if "Diverging Bar" in view_mode:
        combined = pd.concat([top_out, top_in]).sort_values("net_transfers", ascending=True)
        bar_colors = ["#00ff87" if v >= 0 else "#ff4b4b" for v in combined["net_transfers"]]
        bar_text = [f"+{v/1000:,.0f}k" if v >= 0 else f"{v/1000:,.0f}k" for v in combined["net_transfers"]]

        fig = go.Figure(go.Bar(
            y=combined["Name"] + " (" + combined["Team"] + " · " + combined["Position"] + ")",
            x=combined["net_transfers"],
            orientation="h",
            marker_color=bar_colors,
            text=bar_text,
            textposition="outside",
            customdata=list(zip(combined["Position"], combined["Team"], combined["trf in"], combined["trf out"], combined["price"], combined["form"])),
            hovertemplate="<b>%{y}</b><br>"
                          "Net Transfers: <b>%{x:,}</b><br>"
                          "Transfers In: <b>%{customdata[2]:,}</b><br>"
                          "Transfers Out: <b>%{customdata[3]:,}</b><br>"
                          "Price: £%{customdata[4]:.1f}m | Form: %{customdata[5]}<extra></extra>",
        ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Net Transfers (In - Out)",
            yaxis_title="Player",
            height=max(500, len(combined) * 24),
            margin=dict(t=20, b=40, l=180, r=90),
            xaxis=dict(zeroline=True, zerolinecolor="rgba(255,255,255,0.4)", zerolinewidth=2),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_trf_bar_chart")

    else:
        fig = go.Figure()
        for pos in ["FWD", "MID", "DEF", "GK"]:
            pdf = fdf[fdf["Position"] == pos]
            if pdf.empty:
                continue
            color = _POS_COLORS.get(pos, "#ffffff")
            fig.add_trace(go.Scatter(
                x=pdf["net_transfers"],
                y=pdf["form"],
                mode="markers",
                name=f"{pos} ({len(pdf)})",
                marker=dict(size=9, color=color, opacity=0.85, line=dict(width=1, color="white")),
                hovertext=pdf["Name"],
                customdata=list(zip(pdf["Position"], pdf["Team"], pdf["price"], pdf["total points"], pdf["trf in"], pdf["trf out"])),
                hovertemplate="<b>%{hovertext}</b> (%{customdata[0]}) · %{customdata[1]}<br>"
                              "Net Transfers: <b>%{x:,}</b><br>"
                              "Form: <b>%{y}</b> | Total Pts: %{customdata[3]}<br>"
                              "Price: £%{customdata[2]:.1f}m<extra></extra>",
            ))
        fig.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Net Transfers (In - Out)",
            yaxis_title="Player Form (Points per Match)",
            height=500,
            margin=dict(t=30, b=40, l=50, r=30),
            legend=dict(orientation="h", y=1.06, x=0.01),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_trf_scatter_chart")

    # Key Takeaways
    st.markdown("#### 🔍 Bandwagon Radar")
    c_hot, c_cold = st.columns(2)
    with c_hot:
        st.markdown("**🚀 Top 3 Most Bought Players (Price Rise Watch):**")
        for _, r in top_in.head(3).iterrows():
            st.markdown(f"- **{r['Name']}** ({r['Team']} · {r['Position']}) — **`+{r['net_transfers']:,}`** net transfers (Form: `{r['form']}`, Price: `£{r['price']:.1f}m`)")
    with c_cold:
        st.markdown("**🧊 Top 3 Most Sold Players (Price Fall Watch):**")
        for _, r in top_out.head(3).iterrows():
            st.markdown(f"- **{r['Name']}** ({r['Team']} · {r['Position']}) — **`{r['net_transfers']:,}`** net transfers (Form: `{r['form']}`, Price: `£{r['price']:.1f}m`)")


def _render_pl_defensive_luck_bailout(conn, key_prefix: str = "hub"):
    """Chart 5: Defensive Luck & Keeper Bailout (Team xGC vs GC & Clean Sheets)."""
    st.markdown("### 🛡️ Defensive Luck & Keeper Bailout (xGC vs Goals Conceded)")
    st.caption("Evaluate which defenses are genuinely solid, which are getting bailed out by heroic goalkeeping, and which are leaking goals beyond expected chance quality.")

    c1, c2 = st.columns([2, 2])
    with c1:
        view_mode = st.radio(
            "Display Mode",
            options=["🧤 Goals Prevented (Keeper Bailout Delta)", "📊 Side-by-Side (xGC vs GC)"],
            horizontal=True,
            key=f"{key_prefix}_def_luck_view",
        )
    with c2:
        venue_choice = st.radio(
            "Venue Split",
            options=["🏟️ Overall (All Matches)", "🏠 Home Matches Only", "✈️ Away Matches Only"],
            horizontal=True,
            key=f"{key_prefix}_def_luck_venue",
        )

    table_map = {
        "🏟️ Overall (All Matches)": "fpl_analytics_TEAM_STATS",
        "🏠 Home Matches Only": "fpl_analytics_TEAM_STATS_HOME",
        "✈️ Away Matches Only": "fpl_analytics_TEAM_STATS_AWAY",
    }
    table_name = table_map[venue_choice]

    try:
        tdf = pd.read_sql(f"SELECT * FROM `{table_name}`", conn)
    except Exception as e:
        st.error(f"Failed to load table `{table_name}`: {e}")
        return

    for col in ["GC", "xGC", "CS", "Saves"]:
        if col in tdf.columns:
            tdf[col] = pd.to_numeric(tdf[col], errors="coerce").fillna(0)

    # Goals Prevented = xGC - GC (Positive = Keeper saved more goals than expected / bailed out)
    tdf["Goals_Prevented"] = (tdf["xGC"] - tdf["GC"]).round(2)

    if "Goals Prevented" in view_mode:
        tdf_sorted = tdf.sort_values("Goals_Prevented", ascending=True)
        bar_colors = ["#00ff87" if v >= 0 else "#ff4b4b" for v in tdf_sorted["Goals_Prevented"]]

        fig = go.Figure(go.Bar(
            y=tdf_sorted["Team"],
            x=tdf_sorted["Goals_Prevented"],
            orientation="h",
            marker_color=bar_colors,
            text=[f"{v:+.2f} ({int(cs)} CS)" for v, cs in zip(tdf_sorted["Goals_Prevented"], tdf_sorted["CS"])],
            textposition="outside",
            customdata=list(zip(tdf_sorted["xGC"], tdf_sorted["GC"], tdf_sorted["CS"], tdf_sorted["Saves"])),
            hovertemplate="<b>%{y}</b><br>"
                          "Goals Prevented (xGC - GC): <b>%{x:+.2f}</b><br>"
                          "Expected GC: <b>%{customdata[0]:.2f}</b> | Actual GC: <b>%{customdata[1]}</b><br>"
                          "Clean Sheets: <b>%{customdata[2]}</b> | Saves: <b>%{customdata[3]}</b><extra></extra>",
        ))
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Goals Prevented (xGC - Actual GC) — Positive = Goalkeeper Bailout",
            yaxis_title="Team",
            height=max(500, len(tdf_sorted) * 26),
            margin=dict(t=20, b=40, l=80, r=110),
            xaxis=dict(zeroline=True, zerolinecolor="rgba(255,255,255,0.4)", zerolinewidth=2),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_def_prevented_chart")

    else:
        tdf_sorted = tdf.sort_values("xGC", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=tdf_sorted["Team"],
            y=tdf_sorted["xGC"],
            name="Expected Goals Conceded (xGC)",
            marker_color="#ffd166",
            text=[f"{v:.1f}" for v in tdf_sorted["xGC"]],
            textposition="outside",
            customdata=list(zip(tdf_sorted["GC"], tdf_sorted["CS"], tdf_sorted["Saves"])),
            hovertemplate="<b>%{x}</b><br>"
                          "xGC: <b>%{y:.2f}</b><br>"
                          "Actual GC: <b>%{customdata[0]}</b> | CS: <b>%{customdata[1]}</b><br>"
                          "Saves: <b>%{customdata[2]}</b><extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=tdf_sorted["Team"],
            y=tdf_sorted["GC"],
            name="Actual Goals Conceded (GC)",
            marker_color="#ff4b4b",
            text=[f"{int(v)}" for v in tdf_sorted["GC"]],
            textposition="outside",
            customdata=list(zip(tdf_sorted["xGC"], tdf_sorted["CS"], tdf_sorted["Saves"])),
            hovertemplate="<b>%{x}</b><br>"
                          "Actual GC: <b>%{y}</b><br>"
                          "xGC: <b>%{customdata[0]:.2f}</b> | CS: <b>%{customdata[1]}</b><br>"
                          "Saves: <b>%{customdata[2]}</b><extra></extra>",
        ))
        fig.update_layout(
            barmode="group",
            template="plotly_dark",
            xaxis_title="Team",
            yaxis_title="Goals Conceded (Lower is better)",
            height=520,
            margin=dict(t=30, b=40, l=50, r=30),
            legend=dict(orientation="h", y=1.06, x=0.01),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_def_grouped_chart")

    # Key Takeaways
    st.markdown("#### 🔍 Defensive Reality Check")
    c_bailed, c_solid, c_leaky = st.columns(3)
    top_bailed = tdf.sort_values("Goals_Prevented", ascending=False).head(3)
    top_solid = tdf.sort_values("xGC", ascending=True).head(3)
    top_leaky = tdf.sort_values("Goals_Prevented", ascending=True).head(3)

    with c_bailed:
        st.markdown("**🧤 Top 3 Bailed-Out Defenses (Heroic Keepers):**")
        for _, r in top_bailed.iterrows():
            st.markdown(
                f"- **{r['Team']}** — Prev: `+{r['Goals_Prevented']:.2f}` goals "
                f"({int(r['CS'])} CS, {int(r['Saves'])} saves)"
            )
    with c_solid:
        st.markdown("**🧱 Top 3 Genuinely Solid Defenses (Lowest xGC):**")
        for _, r in top_solid.iterrows():
            st.markdown(
                f"- **{r['Team']}** — `{r['xGC']:.2f}` xGC conceded "
                f"({int(r['GC'])} actual GC, {int(r['CS'])} CS)"
            )
    with c_leaky:
        st.markdown("**🚨 Top 3 Punished Defenses (Leaking beyond xGC):**")
        for _, r in top_leaky.iterrows():
            st.markdown(
                f"- **{r['Team']}** — Delta: `{r['Goals_Prevented']:.2f}` "
                f"({int(r['GC'])} GC from `{r['xGC']:.2f}` xGC)"
            )


def _render_pl_leaderboards(df: pd.DataFrame, key_prefix: str = "lead"):
    """Tab: Top 15 Player Leaderboards for G, A, G+A, GC, CS, xGI, DC, Total Points, etc."""
    st.markdown("### 🏆 Premier League Player Leaderboards")
    st.caption("Official Top 15 leaderboards across key fantasy, attacking, creative, and defensive statistics.")

    metric_configs = {
        "🌟 Total Points": {"col": "total points", "name": "Total Points", "fmt": "{:,.0f}", "icon": "🌟"},
        "⚽ Goals (G)": {"col": "G", "name": "Goals", "fmt": "{:,.0f}", "icon": "⚽"},
        "🅰️ Assists (A)": {"col": "A", "name": "Assists", "fmt": "{:,.0f}", "icon": "🅰️"},
        "🎯 Goal Involvements (G + A)": {"col": "Actual_GI", "name": "G + A", "fmt": "{:,.0f}", "icon": "🎯"},
        "🔮 Expected Involvements (xGI)": {"col": "xGI", "name": "xGI", "fmt": "{:.2f}", "icon": "🔮"},
        "🛡️ Clean Sheets (CS)": {"col": "CS", "name": "Clean Sheets", "fmt": "{:,.0f}", "icon": "🛡️"},
        "🥊 Goals Conceded (GC)": {"col": "GC", "name": "Goals Conceded", "fmt": "{:,.0f}", "icon": "🥊"},
        "🧱 Defensive Contrib (DC)": {"col": "DC", "name": "Defensive Contrib", "fmt": "{:,.0f}", "icon": "🧱"},
        "🎁 Bonus Points": {"col": "Bonus", "name": "Bonus Points", "fmt": "{:,.0f}", "icon": "🎁"},
        "🧤 Goalkeeper Saves": {"col": "Saves", "name": "Saves", "fmt": "{:,.0f}", "icon": "🧤"},
    }

    v_col1, v_col2 = st.columns([2.5, 3.5])
    with v_col1:
        view_type = st.radio(
            "Leaderboard Format",
            options=["🎯 Single Category Deep-Dive", "📊 Multi-Category Matrix Overview"],
            horizontal=True,
            key=f"{key_prefix}_view_type",
        )

    if view_type == "🎯 Single Category Deep-Dive":
        c_sel, c_pos, c_min, c_pr = st.columns([2.2, 1.4, 1.8, 1.6])
        with c_sel:
            selected_metric_label = st.selectbox(
                "Select Leaderboard Category",
                options=list(metric_configs.keys()),
                index=0,
                key=f"{key_prefix}_metric_choice",
            )
        cfg = metric_configs[selected_metric_label]
        col_name = cfg["col"]

        with c_pos:
            pos_opts = [p for p in ["FWD", "MID", "DEF", "GK"] if p in df["Position"].unique()]
            def_default = ["DEF", "GK"] if col_name in ["CS", "Saves"] else pos_opts
            sel_pos = st.multiselect("Position", options=pos_opts, default=def_default, key=f"{key_prefix}_pos")
        with c_min:
            max_mins = int(df["Min"].max()) if not df.empty else 1000
            min_mins = st.slider("Min Minutes", 0, max_mins, 0, step=45, key=f"{key_prefix}_mins")
        with c_pr:
            min_p = float(df["price"].min()) if not df.empty else 4.0
            max_p = float(df["price"].max()) if not df.empty else 15.0
            sel_price = st.slider("Max Price (£m)", min_p, max_p, max_p, step=0.1, key=f"{key_prefix}_price")

        fdf = df.copy()
        if sel_pos:
            fdf = fdf[fdf["Position"].isin(sel_pos)]
        fdf = fdf[(fdf["Min"] >= min_mins) & (fdf["price"] <= sel_price)]

        if fdf.empty:
            st.warning("No players match the current filters.")
            return

        top15 = fdf.sort_values(by=[col_name, "total points"], ascending=[False, False]).head(15).copy().reset_index(drop=True)

        # Podium highlight cards
        st.markdown(f"#### {cfg['icon']} Top 3 Podium — {cfg['name']}")
        p1, p2, p3 = st.columns(3)
        medals = ["🥇 1st", "🥈 2nd", "🥉 3rd"]
        for i, col in enumerate([p1, p2, p3]):
            if i < len(top15):
                r = top15.iloc[i]
                val_str = cfg["fmt"].format(r[col_name])
                with col:
                    st.markdown(
                        f"**{medals[i]}: {r['Name']}**\n\n"
                        f"- **{cfg['name']}: `{val_str}`**\n"
                        f"- Team: `{r['Team']}` · Pos: `{r['Position']}`\n"
                        f"- Price: `£{r['price']:.1f}m` | Total Pts: `{int(r['total points'])}`"
                    )

        st.markdown(f"#### 📋 Top 15 {cfg['name']} Leaderboard")

        if col_name == "total points":
            display_cols = ["Name", "Team", "Position", "price", "total points", "form", "Min"]
            tbl_df = top15[display_cols].rename(columns={
                "Name": "Player",
                "Position": "Pos",
                "price": "Price (£m)",
                "total points": "Total Points",
                "form": "Form",
                "Min": "Minutes",
            })
            fmt_dict = {
                "Price (£m)": "£{:.1f}m",
                "Total Points": "{:,.0f}",
                "Form": "{:.1f}",
                "Minutes": "{:,.0f}",
            }
        else:
            display_cols = ["Name", "Team", "Position", "price", col_name, "total points", "form", "Min"]
            tbl_df = top15[display_cols].rename(columns={
                "Name": "Player",
                "Position": "Pos",
                "price": "Price (£m)",
                col_name: cfg["name"],
                "total points": "Total Points",
                "form": "Form",
                "Min": "Minutes",
            })
            fmt_dict = {
                "Price (£m)": "£{:.1f}m",
                cfg["name"]: cfg["fmt"],
                "Total Points": "{:,.0f}",
                "Form": "{:.1f}",
                "Minutes": "{:,.0f}",
            }

        tbl_df.index = range(1, len(tbl_df) + 1)
        styled_tbl = tbl_df.style.format(fmt_dict)
        st.dataframe(styled_tbl, use_container_width=True, height=480)

    else:
        # Multi-category overview: 4 columns x 2 rows of top-15 summary tables
        st.markdown("#### 📊 Top 15 Overview Matrix")
        st.caption("Side-by-side rankings of league leaders across all core metrics.")

        cols_row1 = st.columns(4)
        quick_categories = [
            ("🌟 Total Points", "total points", "{:,.0f}", ["FWD", "MID", "DEF", "GK"]),
            ("⚽ Goals (G)", "G", "{:,.0f}", ["FWD", "MID", "DEF"]),
            ("🅰️ Assists (A)", "A", "{:,.0f}", ["FWD", "MID", "DEF"]),
            ("🎯 Goal Involvements", "Actual_GI", "{:,.0f}", ["FWD", "MID", "DEF"]),
        ]

        for i, (cat_label, c_col, c_fmt, c_positions) in enumerate(quick_categories):
            with cols_row1[i]:
                st.markdown(f"**{cat_label}**")
                sub_df = df[df["Position"].isin(c_positions)].sort_values(by=[c_col, "total points"], ascending=[False, False]).head(15).reset_index(drop=True)
                out_df = sub_df[["Name", "Team", c_col]].rename(columns={"Name": "Player", c_col: "Val"})
                out_df.index = range(1, len(out_df) + 1)
                styled_out = out_df.style.format({"Val": c_fmt})
                st.dataframe(styled_out, use_container_width=True, height=380)

        st.markdown("---")
        cols_row2 = st.columns(4)
        quick_categories_row2 = [
            ("🔮 Expected Involvements (xGI)", "xGI", "{:.2f}", ["FWD", "MID", "DEF"]),
            ("🛡️ Clean Sheets (CS)", "CS", "{:,.0f}", ["DEF", "GK"]),
            ("🧱 Defensive Contrib (DC)", "DC", "{:,.0f}", ["DEF", "MID"]),
            ("🧤 Goalkeeper Saves", "Saves", "{:,.0f}", ["GK"]),
        ]

        for i, (cat_label, c_col, c_fmt, c_positions) in enumerate(quick_categories_row2):
            with cols_row2[i]:
                st.markdown(f"**{cat_label}**")
                sub_df = df[df["Position"].isin(c_positions)].sort_values(by=[c_col, "total points"], ascending=[False, False]).head(15).reset_index(drop=True)
                out_df = sub_df[["Name", "Team", c_col]].rename(columns={"Name": "Player", c_col: "Val"})
                out_df.index = range(1, len(out_df) + 1)
                styled_out = out_df.style.format({"Val": c_fmt})
                st.dataframe(styled_out, use_container_width=True, height=380)


def _render_pl_analytics_hub(conn):
    """Unified master visual hub rendering FPL plots."""
    df_players = _load_combined_players(conn)

    chart_option = st.radio(
        "Select Analytics Visualizer",
        options=[
            "🎯 1. Player Underlying Stats (xGI vs Return)",
            "💎 2. Value Matrix (Price vs Points)",
            "🏟️ 3. Team Finishing & xGI Efficiency (xG vs Goals)",
            "🌊 4. Transfer Momentum (Bandwagons)",
            "🛡️ 5. Defensive Luck & Keeper Bailout (xGC vs GC)",
        ],
        horizontal=True,
        key="pl_hub_chart_choice",
    )
    st.markdown("---")

    if chart_option.startswith("🎯"):
        _render_pl_underlying_stats(df_players, key_prefix="hub_p1")
    elif chart_option.startswith("💎"):
        _render_pl_value_matrix(df_players, key_prefix="hub_p2")
    elif chart_option.startswith("🏟️"):
        _render_pl_team_finishing_efficiency(conn, key_prefix="hub_p3")
    elif chart_option.startswith("🌊"):
        _render_pl_transfer_momentum(df_players, key_prefix="hub_p4")
    elif chart_option.startswith("🛡️"):
        _render_pl_defensive_luck_bailout(conn, key_prefix="hub_p5_def")


def _format_analytics_table(df: pd.DataFrame):
    """Formats numeric columns neatly without awkward decimal places on integers."""
    int_cols = [c for c in df.columns if c in [
        "total points", "gw points", "Min", "G", "A", "CS", "GC", "Saves",
        "Bonus", "bps", "trf in", "trf out", "Starts", "YC", "RC", "CBI",
        "Recoveries", "Tackles", "DC", "PEN Order", "InFK Order", "FK Order",
        "Cost Rank", "Form Rank", "Points GW Rank", "Selected Rank",
        "Influence Rank", "Creativity Rank", "Threat Rank", "ICT Rank",
        "Goals", "Assists", "Recov", "Total Players", "Avg Score", "Top player points",
    ] and pd.api.types.is_numeric_dtype(df[c])]

    float_cols = [c for c in df.columns if c not in int_cols and pd.api.types.is_numeric_dtype(df[c])]

    format_dict = {c: "{:,.0f}" for c in int_cols}
    format_dict.update({c: "{:.2f}" for c in float_cols})
    return df.style.format(format_dict, na_rep="-")


def render_option2_page(fname: str, label: str):
    apply_custom_theme()
    conn = get_sqlite_engine()
    prefix = fname.replace(".xlsx", "")

    st.markdown(f"## 📊 {label}")

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    all_tables = [t[0] for t in cursor.fetchall() if t[0].startswith(prefix)]

    if not all_tables:
        st.error(f"No tables found for `{fname}`. Ensure the file exists in your project directory.")
        return

    is_fpl_analytics = "fpl_analytics" in fname
    is_fpl_stats = "fpl_stats" in fname

    # Generate clean labels for tabs
    raw_sheet_names = [t.replace(f"{prefix}_", "").replace("_", " ") for t in all_tables]

    # Custom FPL Tab Color Accents
    fpl_tab_colors = ["🟢", "🟣", "🔵", "🟡", "🔴", "🟠", "⚪", "🟩"]

    tab_labels = []
    if is_fpl_analytics:
        # Prepend the Visual Analytics Hub tab
        tab_labels.append("📈 Visual Analytics Hub")

    for idx, name in enumerate(raw_sheet_names):
        icon = fpl_tab_colors[idx % len(fpl_tab_colors)]
        tab_labels.append(f"{icon} {name}")

    tabs = st.tabs(tab_labels)

    # If fpl_analytics, render Visual Analytics Hub in tab 0
    start_offset = 0
    if is_fpl_analytics:
        with tabs[0]:
            _render_pl_analytics_hub(conn)
        start_offset = 1

    for idx, table_name in enumerate(all_tables):
        current_tab = tabs[idx + start_offset]
        with current_tab:
            df = pd.read_sql(f"SELECT * FROM `{table_name}`", conn)

            target_sheets = ["gk", "def", "mid", "fwd", "defense", "attack", "player_ownership"]
            is_target_sheet = any(t in table_name.lower() for t in target_sheets)

            if is_fpl_stats and is_target_sheet:
                change_cols = [
                    c for c in df.columns
                    if "% change" in c.lower()
                    or "change" in c.lower()
                    or "diff" in c.lower()
                    or "pct change" in c.lower()
                ]

                if change_cols:
                    styled_df = df.style.map(style_ownership, subset=change_cols)
                    all_numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                    if all_numeric_cols:
                        styled_df = styled_df.format("{:.2f}", subset=all_numeric_cols)
                else:
                    all_numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                    if all_numeric_cols:
                        styled_df = df.style.format("{:.2f}", subset=all_numeric_cols)
                    else:
                        styled_df = df
            elif is_fpl_analytics:
                styled_df = _format_analytics_table(df)
            else:
                styled_df = df

            # ── CHARTS (top) ─────────────────────────────────────────────
            _chart_tabs = ["_GK", "_DEF", "_MID", "_FWD", "_Defense", "_Attack"]
            if is_fpl_stats and any(table_name.endswith(s) for s in _chart_tabs):
                _render_ownership_charts(df, tab_label=table_name.split("_")[-1])

            elif is_fpl_stats and "player_ownership" in table_name.lower():
                _render_player_ownership_charts(df, tab_label="Player Ownership")

            elif is_fpl_analytics and "team_stats" in table_name.lower():
                _render_pl_team_finishing_efficiency(conn, key_prefix=f"sub_{table_name}")

            # ── TABLE (below) ─────────────────────────────────────────────
            st.dataframe(styled_df, use_container_width=True, height=450)
            st.caption(f"Loaded {len(df)} rows from dataset `{table_name}`")