import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nba_api.live.nba.endpoints import scoreboard
from utils import get_db_connection
from datetime import datetime

def collect_schedule(target_date=None):
    if target_date is None:
        target_date = datetime.now().date()
    else:
        target_date = datetime.strptime(str(target_date), '%Y-%m-%d').date()
    
    print(f"Collecting schedule for {target_date}...\n")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    season_year = target_date.year
    season_month = target_date.month
    
    if season_month >= 10:
        season = f"{season_year}-{str(season_year+1)[-2:]}"
    else:
        season = f"{season_year-1}-{str(season_year)[-2:]}"
    
    try:
        board = scoreboard.ScoreBoard()
        games = board.games.get_dict()
        
        if len(games) == 0:
            print(f"No games found for today")
            cur.close()
            conn.close()
            return
        
        print(f"Found {len(games)} games\n")
        
        for game in games:
            game_id = game['gameId']
            home_team_id = int(game['homeTeam']['teamId'])
            away_team_id = int(game['awayTeam']['teamId'])
            game_status = game['gameStatusText']
            
            if 'Final' in game_status:
                status = 'completed'
            else:
                status = 'scheduled'
            
            cur.execute("""
                INSERT INTO games (
                    game_id, game_date, season, home_team_id, away_team_id,
                    game_status, game_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_id) DO UPDATE SET
                    game_status = EXCLUDED.game_status
            """, (
                game_id,
                target_date,
                season,
                home_team_id,
                away_team_id,
                status,
                'regular_season'
            ))
            
            print(f"  Added game {game_id} ({status})")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"\n{'='*50}")
        print(f"Collected {len(games)} games for today")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"Error collecting schedule: {e}")
        try:
            cur.close()
            conn.close()
        except:
            pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        collect_schedule(target_date)
    else:
        collect_schedule()