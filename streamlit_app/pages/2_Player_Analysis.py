import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
import re

import warnings
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')
warnings.filterwarnings('ignore', category=FutureWarning)

def normalize_name(name):
    char_map = {
        'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a', 'ã': 'a', 'å': 'a', 'ā': 'a', 'ă': 'a', 'ą': 'a', 'ǎ': 'a',
        'Á': 'a', 'À': 'a', 'Ä': 'a', 'Â': 'a', 'Ã': 'a', 'Å': 'a', 'Ā': 'a', 'Ă': 'a', 'Ą': 'a', 'Ǎ': 'a',
        'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e', 'ē': 'e', 'ė': 'e', 'ę': 'e', 'ě': 'e',
        'É': 'e', 'È': 'e', 'Ë': 'e', 'Ê': 'e', 'Ē': 'e', 'Ė': 'e', 'Ę': 'e', 'Ě': 'e',
        'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i', 'ī': 'i', 'į': 'i', 'ı': 'i',
        'Í': 'i', 'Ì': 'i', 'Ï': 'i', 'Î': 'i', 'Ī': 'i', 'Į': 'i', 'İ': 'i',
        'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o', 'õ': 'o', 'ø': 'o', 'ō': 'o', 'ő': 'o', 'ǫ': 'o',
        'Ó': 'o', 'Ò': 'o', 'Ö': 'o', 'Ô': 'o', 'Õ': 'o', 'Ø': 'o', 'Ō': 'o', 'Ő': 'o', 'Ǫ': 'o',
        'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u', 'ū': 'u', 'ů': 'u', 'ű': 'u', 'ų': 'u',
        'Ú': 'u', 'Ù': 'u', 'Ü': 'u', 'Û': 'u', 'Ū': 'u', 'Ů': 'u', 'Ű': 'u', 'Ų': 'u',
        'ý': 'y', 'ÿ': 'y', 'ŷ': 'y', 'Ý': 'y', 'Ÿ': 'y', 'Ŷ': 'y',
        'ç': 'c', 'ć': 'c', 'č': 'c', 'ĉ': 'c', 'ċ': 'c',
        'Ç': 'c', 'Ć': 'c', 'Č': 'c', 'Ĉ': 'c', 'Ċ': 'c',
        'đ': 'd', 'Đ': 'd',
        'ñ': 'n', 'ń': 'n', 'ň': 'n', 'ņ': 'n',
        'Ñ': 'n', 'Ń': 'n', 'Ň': 'n', 'Ņ': 'n',
        'š': 's', 'ś': 's', 'ş': 's',
        'Š': 's', 'Ś': 's', 'Ş': 's',
        'ž': 'z', 'ź': 'z', 'ż': 'z',
        'Ž': 'z', 'Ź': 'z', 'Ż': 'z',
        'ģ': 'g', 'Ģ': 'g',
        'ķ': 'k', 'Ķ': 'k',
        'ļ': 'l', 'Ļ': 'l',
    }
    normalized = ''.join(char_map.get(c, c) for c in str(name))
    normalized = normalized.lower().strip()
    return normalized

load_dotenv()

st.set_page_config(
    page_title="Player Analysis - NBA Predictions",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_db_connection():
    try:
        if os.getenv('DATABASE_URL'):
            return psycopg2.connect(os.getenv('DATABASE_URL'))
        else:
            return psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        raise

def load_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', sans-serif;
        }
        
        .main {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            padding: 1.5rem 2rem 2rem 2rem;
            margin-top: 1.5rem;
        }
        
        h1 {
            color: #d4af37 !important;
            font-weight: 700;
            font-size: 2.5rem;
            margin: 0 0 0.5rem 0 !important;
            letter-spacing: -0.02em;
            padding-top: 0 !important;
        }

        [data-testid="stAppViewContainer"] {
            padding-top: 0rem !important;
            margin-top: 0rem !important;
        }

        .block-container {
            padding-top: 0.25rem !important;
            margin-top: 0 !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        .subtitle {
            color: #888;
            font-size: 1rem;
            margin-bottom: 0.5rem;
            margin-top: 0.25rem;
        }
        
        .player-info-card {
            background: #1e1e1e;
            border: 2px solid #2d2d2d;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2.5rem;
        }
        
        .player-info-card h3 {
            color: #d4af37;
            font-size: 1.2rem;
            margin-bottom: 1rem;
            font-weight: 700;
        }
        
        .player-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .player-photo-large {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: 3px solid #d4af37;
            object-fit: cover;
            background: #1e1e1e;
            box-shadow: 0 2px 8px rgba(212, 175, 55, 0.3);
        }
        
        .player-name-large {
            color: #ffffff;
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0;
        }
        
        .player-meta {
            color: #cccccc;
            font-size: 0.95rem;
            margin-top: 0.25rem;
        }
        
        .stats-section {
            margin-top: 1rem;
        }
        
        .stats-section-title {
            color: #d4af37;
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
            font-size: 0.85rem;
        }
        
        .stat-item {
            color: #cccccc;
        }
        
        .stat-item strong {
            color: #ffffff;
            font-weight: 600;
        }
        
        div[data-testid="column"]:nth-child(2),
        div[data-testid="column"]:nth-child(3) {
            padding-left: 2rem !important;
        }
        
        .stSelectbox label, .stSlider label, .stRadio label {
            color: #ffffff !important;
        }
        
        .stCheckbox label {
            color: #cccccc !important;
        }
        </style>
    """, unsafe_allow_html=True)

def get_player_photo_url(player_id):
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

def get_player_info(player_id):
    conn = get_db_connection()
    player_id_int = int(player_id)
    
    query = """
        SELECT 
            p.full_name,
            p.position,
            t.full_name as team_name,
            t.abbreviation as team_abbr,
            pcs.career_games,
            pcs.career_points,
            pcs.career_rebounds,
            pcs.career_assists,
            pcs.career_steals,
            pcs.career_blocks
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        LEFT JOIN player_career_stats pcs ON p.player_id = pcs.player_id
        WHERE p.player_id = %s
        ORDER BY pcs.updated_date DESC NULLS LAST
        LIMIT 1
    """
    
    result = pd.read_sql(query, conn, params=(player_id_int,))
    conn.close()
    
    if len(result) > 0:
        return result.iloc[0].to_dict()
    return None

def get_season_averages(player_id, season='2025-26'):
    conn = get_db_connection()
    player_id_int = int(player_id)
    
    query = """
        SELECT 
            AVG(points) as avg_points,
            AVG(rebounds_total) as avg_rebounds,
            AVG(assists) as avg_assists,
            AVG(steals) as avg_steals,
            AVG(blocks) as avg_blocks,
            AVG(turnovers) as avg_turnovers,
            AVG(three_pointers_made) as avg_three_pointers,
            COUNT(*) as games_played
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE pgs.player_id = %s
        AND g.season = %s
        AND g.game_status = 'completed'
    """
    
    result = pd.read_sql(query, conn, params=(player_id_int, season))
    conn.close()
    
    if len(result) > 0 and result.iloc[0]['games_played'] > 0:
        return result.iloc[0].to_dict()
    return None

def get_todays_games():
    conn = get_db_connection()
    today = datetime.now().date()
    
    query = """
        SELECT DISTINCT
            g.game_id,
            g.game_date,
            t1.full_name as home_team,
            t2.full_name as away_team,
            t1.team_id as home_team_id,
            t2.team_id as away_team_id
        FROM games g
        JOIN teams t1 ON g.home_team_id = t1.team_id
        JOIN teams t2 ON g.away_team_id = t2.team_id
        WHERE g.game_date = %s
        AND g.game_status = 'scheduled'
        ORDER BY g.game_id
    """
    
    df = pd.read_sql(query, conn, params=(today,))
    conn.close()
    return df

def get_players_for_game(game_id):
    conn = get_db_connection()
    
    query = """
        SELECT DISTINCT
            p.player_id,
            p.full_name,
            p.position,
            t.abbreviation as team_abbr
        FROM predictions pred
        JOIN players p ON pred.player_id = p.player_id
        JOIN teams t ON p.team_id = t.team_id
        WHERE pred.game_id = %s
        ORDER BY p.full_name
    """
    
    df = pd.read_sql(query, conn, params=(game_id,))
    conn.close()
    return df

def get_player_historical_stats(player_id, opponent_id, is_home, window_size, filter_h2h, filter_home_away, current_team_only, player_team_id, exclude_dnp=True):
    conn = get_db_connection()
    
    player_id_int = int(player_id)
    
    filter_conditions = []
    query_params = []
    
    if filter_h2h and opponent_id:
        opponent_id_int = int(opponent_id)
        filter_conditions.append("""
            ((g.home_team_id = %s AND pgs.team_id = g.away_team_id)
             OR (g.away_team_id = %s AND pgs.team_id = g.home_team_id))
        """)
        query_params.extend([opponent_id_int, opponent_id_int])
    
    if filter_home_away:
        if is_home:
            filter_conditions.append("pgs.team_id = g.home_team_id")
        else:
            filter_conditions.append("pgs.team_id = g.away_team_id")
    
    if current_team_only and player_team_id:
        filter_conditions.append("pgs.team_id = %s")
        query_params.append(player_team_id)
    
    if exclude_dnp:
        filter_conditions.append("pgs.minutes_played > 0")
        filter_conditions.append("pgs.minutes_played IS NOT NULL")
    
    filter_condition = ""
    if filter_conditions:
        filter_condition = "AND " + " AND ".join(filter_conditions)
    
    limit_size = window_size * 3 if exclude_dnp else window_size
    
    query = f"""
        SELECT 
            g.game_date,
            pgs.points,
            pgs.rebounds_total,
            pgs.assists,
            pgs.steals,
            pgs.blocks,
            pgs.turnovers,
            pgs.three_pointers_made,
            pgs.team_id as player_team_id,
            g.home_team_id,
            g.away_team_id,
            t_home.abbreviation as home_team_abbr,
            t_away.abbreviation as away_team_abbr,
            pgs.minutes_played
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        JOIN teams t_home ON g.home_team_id = t_home.team_id
        JOIN teams t_away ON g.away_team_id = t_away.team_id
        WHERE pgs.player_id = %s
        AND g.game_status = 'completed'
        {filter_condition}
        ORDER BY g.game_date DESC
        LIMIT %s
    """
    
    all_params = (player_id_int,) + tuple(query_params) + (limit_size,)
    df = pd.read_sql(query, conn, params=all_params)
    conn.close()
    
    if exclude_dnp:
        df = df[(df['minutes_played'] > 0) & (df['minutes_played'].notna())].copy()
    
    df = df.head(window_size).copy()
    
    return df

def get_player_prediction(player_id, game_id, stat_name):
    conn = get_db_connection()
    
    stat_column_map = {
        'points': 'predicted_points',
        'rebounds': 'predicted_rebounds',
        'assists': 'predicted_assists',
        'steals': 'predicted_steals',
        'blocks': 'predicted_blocks',
        'turnovers': 'predicted_turnovers',
        'three_pointers_made': 'predicted_three_pointers_made'
    }
    
    column = stat_column_map.get(stat_name)
    if not column:
        return None
    
    query = f"""
        SELECT {column} as prediction
        FROM predictions
        WHERE player_id = %s AND game_id = %s
    """
    
    player_id_int = int(player_id)
    game_id_str = str(game_id)
    
    result = pd.read_sql(query, conn, params=(player_id_int, game_id_str))
    conn.close()
    
    if len(result) > 0:
        return result.iloc[0]['prediction']
    return None

def calculate_over_under_percentage(stats_df, stat_name, line_value, over_under):
    if len(stats_df) == 0:
        return 0.0
    
    stat_column_map = {
        'points': 'points',
        'rebounds': 'rebounds_total',
        'assists': 'assists',
        'steals': 'steals',
        'blocks': 'blocks',
        'turnovers': 'turnovers',
        'three_pointers_made': 'three_pointers_made'
    }
    
    column = stat_column_map.get(stat_name)
    if column not in stats_df.columns:
        return 0.0
    
    if over_under == "Over":
        hits = (stats_df[column] > line_value).sum()
    else:
        hits = (stats_df[column] < line_value).sum()
    
    return (hits / len(stats_df)) * 100

def main():
    load_custom_css()
    
    st.markdown("""
    <h1>Player Analysis</h1>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <p class="subtitle">Analyze player performance trends and compare against betting lines</p>
    """, unsafe_allow_html=True)
    
    today = datetime.now().date()
    games_df = get_todays_games()
    
    if len(games_df) == 0:
        st.warning(f"No scheduled games found for today ({today})")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        game_options = [f"{row['away_team']} @ {row['home_team']}" for _, row in games_df.iterrows()]
        selected_game_idx = st.selectbox("Select Game", range(len(game_options)), format_func=lambda x: game_options[x])
        selected_game = games_df.iloc[selected_game_idx]
        game_id = selected_game['game_id']
        home_team_id = selected_game['home_team_id']
        away_team_id = selected_game['away_team_id']
    
    players_df = get_players_for_game(game_id)
    
    if len(players_df) == 0:
        st.warning("No players found for this game")
        return
    
    with col2:
        player_options = [f"{row['full_name']} ({row['team_abbr']})" for _, row in players_df.iterrows()]
        selected_player_idx = st.selectbox("Select Player", range(len(player_options)), format_func=lambda x: player_options[x])
        selected_player = players_df.iloc[selected_player_idx]
        player_id = selected_player['player_id']
        player_name = selected_player['full_name']
        player_team_abbr = selected_player['team_abbr']
    
    with col3:
        stat_options = ['points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers', 'three_pointers_made']
        stat_display = {
            'points': 'Points',
            'rebounds': 'Rebounds',
            'assists': 'Assists',
            'steals': 'Steals',
            'blocks': 'Blocks',
            'turnovers': 'Turnovers',
            'three_pointers_made': '3-Pointers Made'
        }
        selected_stat = st.selectbox("Select Stat", stat_options, format_func=lambda x: stat_display[x])
    
    conn = get_db_connection()
    player_id_int = int(player_id)
    player_team_query = "SELECT team_id FROM players WHERE player_id = %s"
    player_team_df = pd.read_sql(player_team_query, conn, params=(player_id_int,))
    conn.close()
    
    if len(player_team_df) > 0:
        player_team_id = int(player_team_df.iloc[0]['team_id'])
        is_home = (player_team_id == home_team_id)
        opponent_id = away_team_id if is_home else home_team_id
    else:
        is_home = False
        opponent_id = away_team_id
        player_team_id = None
    
    st.markdown("---")
    
    player_info = get_player_info(player_id)
    season_avgs = get_season_averages(player_id)
    
    col_info, col_options, col_filters = st.columns([1.2, 1, 1])
    
    with col_info:
        if player_info:
            photo_url = get_player_photo_url(player_id)
            
            season_html = ""
            if season_avgs and season_avgs.get('games_played', 0) > 0:
                season_html = f"""<div class="stats-section">
<div class="stats-section-title">Current Season Averages</div>
<div class="stats-grid">
<div class="stat-item">PTS: <strong>{season_avgs.get('avg_points', 0):.1f}</strong></div>
<div class="stat-item">REB: <strong>{season_avgs.get('avg_rebounds', 0):.1f}</strong></div>
<div class="stat-item">AST: <strong>{season_avgs.get('avg_assists', 0):.1f}</strong></div>
<div class="stat-item">STL: <strong>{season_avgs.get('avg_steals', 0):.1f}</strong></div>
<div class="stat-item">BLK: <strong>{season_avgs.get('avg_blocks', 0):.1f}</strong></div>
<div class="stat-item">TO: <strong>{season_avgs.get('avg_turnovers', 0):.1f}</strong></div>
<div class="stat-item">3PM: <strong>{season_avgs.get('avg_three_pointers', 0):.1f}</strong></div>
<div class="stat-item">GP: <strong>{int(season_avgs.get('games_played', 0))}</strong></div>
</div>
</div>"""
            
            career_html = ""
            if player_info.get('career_games') and player_info.get('career_games', 0) > 0:
                career_ppg = player_info.get('career_points', 0) / player_info.get('career_games', 1)
                career_rpg = player_info.get('career_rebounds', 0) / player_info.get('career_games', 1)
                career_apg = player_info.get('career_assists', 0) / player_info.get('career_games', 1)
                career_spg = player_info.get('career_steals', 0) / player_info.get('career_games', 1)
                career_bpg = player_info.get('career_blocks', 0) / player_info.get('career_games', 1)
                
                career_html = f"""<div class="stats-section">
<div class="stats-section-title">Career Averages</div>
<div class="stats-grid">
<div class="stat-item">PTS: <strong>{career_ppg:.1f}</strong></div>
<div class="stat-item">REB: <strong>{career_rpg:.1f}</strong></div>
<div class="stat-item">AST: <strong>{career_apg:.1f}</strong></div>
<div class="stat-item">STL: <strong>{career_spg:.1f}</strong></div>
<div class="stat-item">BLK: <strong>{career_bpg:.1f}</strong></div>
<div class="stat-item">GP: <strong>{int(player_info.get('career_games', 0))}</strong></div>
</div>
</div>"""
            
            full_html = f"""<div class="player-info-card">
<div class="player-header">
<img src="{photo_url}" class="player-photo-large" onerror="this.src='https://cdn.nba.com/headshots/nba/latest/1040x760/fallback.png'">
<div>
<div class="player-name-large">{player_info.get('full_name', player_name)}</div>
<div class="player-meta">{player_info.get('position', 'N/A')} | {player_info.get('team_name', player_team_abbr)}</div>
</div>
</div>
{season_html}
{career_html}
</div>"""
            st.markdown(full_html, unsafe_allow_html=True)
    
    with col_options:
        st.markdown("<div style='color: #d4af37; font-size: 1rem; font-weight: 600; margin-bottom: 1rem;'>Options</div>", unsafe_allow_html=True)
        
        st.markdown("<div style='color: #d4af37; font-weight: 600; margin-bottom: 0.5rem;'>Time Window</div>", unsafe_allow_html=True)
        window_options = ['L5', 'L10', 'L20', 'L50', 'All']
        selected_window = st.radio("Time Window", window_options, horizontal=False, key="time_window", label_visibility="collapsed")
        window_size = {'L5': 5, 'L10': 10, 'L20': 20, 'L50': 50, 'All': 100}[selected_window]
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("<div style='color: #d4af37; font-weight: 600; margin-bottom: 0.5rem;'>Over/Under</div>", unsafe_allow_html=True)
        over_under = st.radio("Over/Under", ["Over", "Under"], horizontal=False, key="over_under", label_visibility="collapsed")
    
    with col_filters:
        st.markdown("<div style='color: #d4af37; font-size: 1rem; font-weight: 600; margin-bottom: 1rem;'>Filters</div>", unsafe_allow_html=True)
        
        filter_h2h = st.checkbox("H2H (Head-to-Head)", value=False)
        home_away_label = "Home" if is_home else "Away"
        filter_home_away = st.checkbox(f"{home_away_label} Games", value=False)
        current_team_only = st.checkbox("Current Team Only", value=False)
        exclude_dnp = st.checkbox("Exclude DNP", value=True)
        
        filter_labels = []
        if filter_h2h:
            filter_labels.append("H2H")
        if filter_home_away:
            filter_labels.append(home_away_label)
        if current_team_only:
            filter_labels.append("Current Team")
        filter_str = ", ".join(filter_labels) if filter_labels else "All"
    
    historical_stats = get_player_historical_stats(
        player_id, opponent_id, is_home, window_size, filter_h2h, filter_home_away, current_team_only, player_team_id, exclude_dnp
    )
    
    if len(historical_stats) == 0:
        st.warning(f"No historical data found for {player_name} with the selected filters")
        return
    
    prediction = get_player_prediction(player_id, game_id, selected_stat)
    
    stat_column_map = {
        'points': 'points',
        'rebounds': 'rebounds_total',
        'assists': 'assists',
        'steals': 'steals',
        'blocks': 'blocks',
        'turnovers': 'turnovers',
        'three_pointers_made': 'three_pointers_made'
    }
    
    stat_column = stat_column_map[selected_stat]
    
    historical_stats = historical_stats.sort_values('game_date')
    historical_stats['game_number'] = range(1, len(historical_stats) + 1)
    
    historical_stats['is_home_game'] = historical_stats['player_team_id'] == historical_stats['home_team_id']
    historical_stats['opponent_abbr'] = historical_stats.apply(
        lambda row: row['away_team_abbr'] if row['is_home_game'] else row['home_team_abbr'], axis=1
    )
    historical_stats['game_label'] = historical_stats.apply(
        lambda row: f"{row['game_date'].strftime('%m/%d').lstrip('0').replace('/0', '/')} vs {row['opponent_abbr']}", axis=1
    )
    
    if prediction is not None:
        prediction_row = pd.DataFrame({
            'game_date': [today],
            stat_column: [prediction],
            'game_number': [len(historical_stats) + 1],
            'is_prediction': [True],
            'game_label': ['Prediction']
        })
        historical_stats['is_prediction'] = False
        chart_df = pd.concat([historical_stats, prediction_row], ignore_index=True)
    else:
        chart_df = historical_stats.copy()
        chart_df['is_prediction'] = False
    
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### Betting Line")
        
        line_key = f"line_{player_id}_{game_id}_{selected_stat}"
        if line_key not in st.session_state:
            mean_val = float(historical_stats[stat_column].mean())
            st.session_state[line_key] = round(mean_val * 2) / 2
        
        line_value = st.number_input("Line Value", min_value=0.0, value=st.session_state[line_key], step=0.5, format="%.1f", key=f"line_input_{line_key}")
        st.session_state[line_key] = round(line_value * 2) / 2
        
        hit_rate = calculate_over_under_percentage(historical_stats, selected_stat, st.session_state[line_key], over_under)
        
        st.markdown("### Hit Rate")
        st.metric("", f"{hit_rate:.1f}%", delta=f"{over_under} the line")
        
        if prediction is not None:
            st.markdown("### Our Prediction")
            st.metric("", f"{prediction:.1f}")
    
    with col1:
        fig = go.Figure()
        
        line_value = st.session_state[line_key]
        
        actual_games = chart_df[chart_df['is_prediction'] == False].copy()
        if len(actual_games) > 0:
            actual_games['bar_color'] = actual_games[stat_column].apply(
                lambda x: '#4a9b5f' if x >= line_value else '#c85a5a'
            )
            
            for idx, row in actual_games.iterrows():
                fig.add_trace(go.Bar(
                    x=[row['game_number']],
                    y=[row[stat_column]],
                    name='',
                    marker_color=row['bar_color'],
                    text=[f"{row[stat_column]:.1f}"],
                    textposition='outside',
                    hovertemplate=f"<b>{row['game_label']}</b><br>" +
                                f"Date: {row['game_date'].strftime('%Y-%m-%d')}<br>" +
                                f"{stat_display[selected_stat]}: {row[stat_column]:.1f}<extra></extra>",
                    showlegend=False
                ))
        
        if prediction is not None:
            pred_row = chart_df[chart_df['is_prediction'] == True]
            if len(pred_row) > 0:
                pred_val = pred_row.iloc[0][stat_column]
                fig.add_trace(go.Bar(
                    x=pred_row['game_number'],
                    y=pred_row[stat_column],
                    name='',
                    marker_color='#d4af37',
                    text=[f"{pred_val:.1f}"],
                    textposition='outside',
                    hovertemplate=f"<b>Prediction</b><br>" +
                                f"Date: {today.strftime('%Y-%m-%d')}<br>" +
                                f"{stat_display[selected_stat]}: {pred_val:.1f}<extra></extra>",
                    showlegend=False
                ))
        
        xaxis_labels = chart_df['game_label'].tolist()
        
        fig.add_hline(
            y=line_value,
            line_dash="dash",
            line_color="white",
            annotation_text=f"Line: {line_value:.1f}",
            annotation_position="right"
        )
        
        fig.update_layout(
            title=f"{player_name} - {stat_display[selected_stat]} ({selected_window}, {filter_str})",
            xaxis=dict(
                title="Game (Most Recent →)",
                tickmode='array',
                tickvals=chart_df['game_number'].tolist(),
                ticktext=xaxis_labels,
                tickangle=0
            ),
            yaxis_title=stat_display[selected_stat],
            height=500,
            showlegend=False,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        st.plotly_chart(
            fig, 
            use_container_width=True,
            config={
                'displayModeBar': True,
                'modeBarButtonsToAdd': ['resetScale2d'],
                'displaylogo': False
            }
        )
    
    st.markdown("---")
    
    st.markdown("### Historical Data")
    display_df = historical_stats[['game_date', stat_column]].copy()
    display_df.columns = ['Game Date', stat_display[selected_stat]]
    display_df = display_df.sort_values('Game Date', ascending=False)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()

