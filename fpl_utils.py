import json
import os
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google import genai

SHARED_CHAT_FILE = "all_chat_threads.json"

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

        /* Color-coded Tab System styling */
        button[data-baseweb="tab"] {
            border-radius: 6px 6px 0 0 !important;
            padding: 8px 16px !important;
            font-weight: 600 !important;
        }
        
        /* Active Tab indicator highlight */
        button[data-baseweb="tab"][aria-selected="true"] {
            border-bottom: 3px solid #00ff87 !important;
        }
        /* Mobile responsive optimizations */
        @media (max-width: 768px) {
            /* Keep top nav horizontal with smooth touch swipe/scroll */
            div[class*="st-key-top_nav_bar"] [data-testid="stHorizontalBlock"] {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch !important;
                gap: 8px !important;
                padding-bottom: 6px !important;
                scrollbar-width: none;
            }
            div[class*="st-key-top_nav_bar"] [data-testid="stHorizontalBlock"]::-webkit-scrollbar {
                display: none;
            }

            div[class*="st-key-top_nav_bar"] [data-testid="column"] {
                flex: 0 0 auto !important;
                width: auto !important;
                min-width: 140px !important;
            }

            div[class*="st-key-nav_"] a[data-testid="stPageLink-NavLink"] {
                padding: 8px 12px !important;
                font-size: 0.85rem !important;
                white-space: nowrap !important;
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
    current_page: 'home' | 'ownership' | 'stats' | 'chat'
    """
    apply_custom_theme()

    pages = [
        {"id": "home", "label": "Home", "icon": "🏠", "path": "Home.py"},
        {"id": "ownership", "label": "FPL Ownership", "icon": "📊", "path": "pages/1_📊_FPL_Ownership.py"},
        {"id": "stats", "label": "PL Player Statistics", "icon": "📈", "path": "pages/2_📈_PL_Player_Statistics.py"},
        {"id": "chat", "label": "Ask Me", "icon": "💬", "path": "pages/3_💬_Ask_Me.py"},
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
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

    st.divider()


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

    # Generate clean labels for tabs
    raw_sheet_names = [t.replace(f"{prefix}_", "").replace("_", " ") for t in all_tables]

    # Custom FPL Tab Color Accents
    fpl_tab_colors = ["🟢", "🟣", "🔵", "🟡", "🔴", "🟠", "⚪", "🟩"]
    
    tab_labels = []
    for idx, name in enumerate(raw_sheet_names):
        icon = fpl_tab_colors[idx % len(fpl_tab_colors)]
        tab_labels.append(f"{icon} {name}")

    tabs = st.tabs(tab_labels)

    for idx, tab in enumerate(tabs):
        table_name = all_tables[idx]
        with tab:
            df = pd.read_sql(f"SELECT * FROM `{table_name}`", conn)
            
            is_fpl_stats = "fpl_stats" in fname
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
                    # Format ALL numeric columns to 2 decimal places
                    all_numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                    if all_numeric_cols:
                        styled_df = styled_df.format("{:.2f}", subset=all_numeric_cols)
                else:
                    # No change cols — still format all numerics to 2dp
                    all_numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                    if all_numeric_cols:
                        styled_df = df.style.format("{:.2f}", subset=all_numeric_cols)
                    else:
                        styled_df = df
            else:
                styled_df = df

            # ── CHARTS (top) ─────────────────────────────────────────────
            _chart_tabs = ["_GK", "_DEF", "_MID", "_FWD", "_Defense", "_Attack"]
            if is_fpl_stats and any(table_name.endswith(s) for s in _chart_tabs):
                _render_ownership_charts(df, tab_label=table_name.split("_")[-1])

            elif is_fpl_stats and "player_ownership" in table_name.lower():
                _render_player_ownership_charts(df, tab_label="Player Ownership")

            # ── TABLE (below) ─────────────────────────────────────────────
            st.dataframe(styled_df, use_container_width=True, height=450)
            st.caption(f"Loaded {len(df)} rows from dataset `{table_name}`")