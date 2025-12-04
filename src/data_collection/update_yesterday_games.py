import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nba_api.stats.endpoints import leaguegamefinder, boxscoretraditionalv3
from utils import get_db_connection
import time
import pandas as pd

def safe_int(val):
    if pd.isna(val) or val == '':
        return None
    try:
        return int(val)
    except:
        return None

def parse_minutes(minutes_str):
    if pd.isna(minutes_str) or minutes_str == '' or minutes_str == 'None':
        return None
    try:
        if ':' in str(minutes_str):
            parts = str(minutes_str).split(':')
            mins = int(parts[0])
            secs = int(parts[1])
            return round(mins + (secs / 60.0), 2)
        else:
            return float(minutes_str)
    except:
        return None

def update_yesterday_games(target_date=None):
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).date()
    else:
        target_date = datetime.strptime(str(target_date), '%Y-%m-%d').date()
    
    print(f"Updating games for {target_date}...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    season = get_season_from_date(target_date)
    
    gamefinder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        date_from_nullable=target_date.strftime('%m/%d/%Y'),
        date_to_nullable=target_date.strftime('%m/%d/%Y'),
        league_id_nullable='00'
    )
    
    games = gamefinder.get_data_frames()[0]
    
    if len(games) == 0:
        print(f"No games found for {target_date}")
        conn.close()
        return
    
    game_ids = games['GAME_ID'].unique()
    print(f"Found {len(game_ids)} games\n")
    
    for game_id in game_ids:
        print(f"Processing {game_id}...")
        
        cur.execute("SELECT game_id FROM games WHERE game_id = %s", (game_id,))
        exists = cur.fetchone()
        
        if not exists:
            print(f"  Game {game_id} not in database, collecting...")
            collect_single_game(cur, conn, game_id, target_date, season)
        else:
            print(f"  Game {game_id} already exists, updating stats...")
            update_game_stats(cur, conn, game_id)
        
        conn.commit()
        time.sleep(1)
    
    cur.close()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"Updated {len(game_ids)} games for {target_date}")
    print(f"{'='*50}")

def collect_single_game(cur, conn, game_id, game_date, season):
    try:
        boxscore = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
        time.sleep(1)
        
        player_stats = boxscore.get_data_frames()[0]
        
        if len(player_stats) == 0:
            print(f"  No player stats found for {game_id}")
            return
        
        home_team_id = None
        away_team_id = None
        home_score = 0
        away_score = 0
        
        for _, player in player_stats.iterrows():
            team_id = safe_int(player.get('teamId'))
            points = safe_int(player.get('points')) or 0
            
            if home_team_id is None:
                home_team_id = team_id
                home_score = points
            elif team_id == home_team_id:
                home_score += points
            elif away_team_id is None:
                away_team_id = team_id
                away_score = points
            else:
                away_score += points
        
        cur.execute("""
            INSERT INTO games (
                game_id, game_date, season, home_team_id, away_team_id,
                home_score, away_score, game_status, game_type
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (game_id) DO UPDATE SET
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                game_status = EXCLUDED.game_status
        """, (
            game_id,
            game_date,
            season,
            home_team_id,
            away_team_id,
            home_score,
            away_score,
            'completed',
            'regular_season'
        ))
        
        for _, player in player_stats.iterrows():
            player_id = safe_int(player.get('personId'))
            team_id = safe_int(player.get('teamId'))
            
            if not player_id or not team_id:
                continue
            
            minutes = parse_minutes(player.get('minutes'))
            if minutes == 0 or minutes is None:
                continue
            
            start_position = str(player.get('position', ''))
            is_starter = start_position != '' and start_position != 'None' and start_position != 'nan'
            
            cur.execute("""
                INSERT INTO player_game_stats (
                    game_id, player_id, team_id, is_starter, minutes_played,
                    points, rebounds_offensive, rebounds_defensive, rebounds_total,
                    assists, steals, blocks, turnovers, personal_fouls,
                    field_goals_made, field_goals_attempted,
                    three_pointers_made, three_pointers_attempted,
                    free_throws_made, free_throws_attempted, plus_minus
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_id, player_id) DO NOTHING
            """, (
                game_id,
                player_id,
                team_id,
                is_starter,
                minutes,
                safe_int(player.get('points')),
                safe_int(player.get('reboundsOffensive')),
                safe_int(player.get('reboundsDefensive')),
                safe_int(player.get('reboundsTotal')),
                safe_int(player.get('assists')),
                safe_int(player.get('steals')),
                safe_int(player.get('blocks')),
                safe_int(player.get('turnovers')),
                safe_int(player.get('foulsPersonal')),
                safe_int(player.get('fieldGoalsMade')),
                safe_int(player.get('fieldGoalsAttempted')),
                safe_int(player.get('threePointersMade')),
                safe_int(player.get('threePointersAttempted')),
                safe_int(player.get('freeThrowsMade')),
                safe_int(player.get('freeThrowsAttempted')),
                safe_int(player.get('plusMinusPoints'))
            ))
        
        print(f"  Collected game {game_id}")
        
    except Exception as e:
        print(f"  Error collecting game {game_id}: {e}")

def update_game_stats(cur, conn, game_id):
    try:
        boxscore = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
        time.sleep(1)
        
        player_stats = boxscore.get_data_frames()[0]
        
        if len(player_stats) == 0:
            print(f"  No player stats found for {game_id}")
            return
        
        home_team_id = None
        away_team_id = None
        home_score = 0
        away_score = 0
        
        for _, player in player_stats.iterrows():
            team_id = safe_int(player.get('teamId'))
            points = safe_int(player.get('points')) or 0
            
            if home_team_id is None:
                home_team_id = team_id
                home_score = points
            elif team_id == home_team_id:
                home_score += points
            elif away_team_id is None:
                away_team_id = team_id
                away_score = points
            else:
                away_score += points
        
        cur.execute("""
            UPDATE games SET
                home_score = %s,
                away_score = %s,
                game_status = 'completed'
            WHERE game_id = %s
        """, (
            home_score,
            away_score,
            game_id
        ))
        
        for _, player in player_stats.iterrows():
            player_id = safe_int(player.get('personId'))
            team_id = safe_int(player.get('teamId'))
            
            if not player_id or not team_id:
                continue
            
            minutes = parse_minutes(player.get('minutes'))
            if minutes == 0 or minutes is None:
                continue
            
            start_position = str(player.get('position', ''))
            is_starter = start_position != '' and start_position != 'None' and start_position != 'nan'
            
            cur.execute("""
                INSERT INTO player_game_stats (
                    game_id, player_id, team_id, is_starter, minutes_played,
                    points, rebounds_offensive, rebounds_defensive, rebounds_total,
                    assists, steals, blocks, turnovers, personal_fouls,
                    field_goals_made, field_goals_attempted,
                    three_pointers_made, three_pointers_attempted,
                    free_throws_made, free_throws_attempted, plus_minus
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_id, player_id) DO NOTHING
            """, (
                game_id,
                player_id,
                team_id,
                is_starter,
                minutes,
                safe_int(player.get('points')),
                safe_int(player.get('reboundsOffensive')),
                safe_int(player.get('reboundsDefensive')),
                safe_int(player.get('reboundsTotal')),
                safe_int(player.get('assists')),
                safe_int(player.get('steals')),
                safe_int(player.get('blocks')),
                safe_int(player.get('turnovers')),
                safe_int(player.get('foulsPersonal')),
                safe_int(player.get('fieldGoalsMade')),
                safe_int(player.get('fieldGoalsAttempted')),
                safe_int(player.get('threePointersMade')),
                safe_int(player.get('threePointersAttempted')),
                safe_int(player.get('freeThrowsMade')),
                safe_int(player.get('freeThrowsAttempted')),
                safe_int(player.get('plusMinusPoints'))
            ))
        
        print(f"  Updated game {game_id}")
        
    except Exception as e:
        print(f"  Error updating game {game_id}: {e}")

def get_season_from_date(date):
    year = date.year
    month = date.month
    
    if month >= 10:
        return f"{year}-{str(year+1)[-2:]}"
    else:
        return f"{year-1}-{str(year)[-2:]}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        update_yesterday_games(target_date)
    else:
        update_yesterday_games()