from utils import get_db_connection
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def calculate_team_ratings():
    print("Calculating team ratings for each season...")
    print("This calculates offensive/defensive/net rating and pace\n")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT g.season, g.home_team_id as team_id
        FROM games g
        WHERE g.game_status = 'completed'
        UNION
        SELECT DISTINCT g.season, g.away_team_id as team_id
        FROM games g
        WHERE g.game_status = 'completed'
        ORDER BY season, team_id
    """)
    
    season_teams = cur.fetchall()
    print(f"Found {len(season_teams)} season-team combinations to process\n")
    
    count = 0
    
    for season, team_id in season_teams:
        cur.execute("""
            SELECT 
                g.game_id,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                CASE 
                    WHEN g.home_team_id = %s THEN g.home_score
                    ELSE g.away_score
                END as team_score,
                CASE 
                    WHEN g.home_team_id = %s THEN g.away_score
                    ELSE g.home_score
                END as opponent_score
            FROM games g
            WHERE g.season = %s 
                AND (g.home_team_id = %s OR g.away_team_id = %s)
                AND g.game_status = 'completed'
                AND g.game_type = 'regular_season'
        """, (team_id, team_id, season, team_id, team_id))
        
        games = cur.fetchall()
        
        if len(games) == 0:
            continue
        
        total_points = sum(g[5] for g in games)
        total_opponent_points = sum(g[6] for g in games)
        games_played = len(games)
        wins = sum(1 for g in games if g[5] > g[6])
        losses = games_played - wins
        
        cur.execute("""
            SELECT 
                SUM(pgs.field_goals_attempted) as fga,
                SUM(pgs.rebounds_offensive) as oreb,
                SUM(pgs.turnovers) as tov,
                SUM(pgs.free_throws_attempted) as fta
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id
            WHERE pgs.team_id = %s 
                AND g.season = %s
                AND g.game_type = 'regular_season'
        """, (team_id, season))
        
        team_stats = cur.fetchone()
        
        if not team_stats or not team_stats[0]:
            continue
        
        fga, oreb, tov, fta = team_stats
        
        possessions = fga - (oreb or 0) + (tov or 0) + 0.44 * (fta or 0)
        
        if possessions == 0:
            continue
        
        offensive_rating = round((total_points / possessions) * 100, 1)
        defensive_rating = round((total_opponent_points / possessions) * 100, 1)
        net_rating = round(offensive_rating - defensive_rating, 1)
        pace = round(possessions / games_played, 1)
        
        try:
            cur.execute("""
                INSERT INTO team_ratings (
                    team_id,
                    season,
                    games_played,
                    wins,
                    losses,
                    offensive_rating,
                    defensive_rating,
                    net_rating,
                    pace
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                team_id,
                season,
                games_played,
                wins,
                losses,
                offensive_rating,
                defensive_rating,
                net_rating,
                pace
            ))
            
            count += 1
            
            if count % 30 == 0:
                print(f"Processed {count}/{len(season_teams)} season-teams...")
                conn.commit()
                
        except Exception as e:
            print(f"Error inserting team {team_id} season {season}: {e}")
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "="*50)
    print("TEAM RATINGS CALCULATION COMPLETE!")
    print("="*50)
    print(f"Calculated ratings for {count} season-teams")
    
    print("\nTop 5 Teams by Net Rating (2024-25):")
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT t.full_name, tr.net_rating, tr.offensive_rating, tr.defensive_rating, tr.wins, tr.losses
        FROM team_ratings tr
        JOIN teams t ON tr.team_id = t.team_id
        WHERE tr.season = '2024-25'
        ORDER BY tr.net_rating DESC
        LIMIT 5
    """)
    
    for i, row in enumerate(cur.fetchall(), 1):
        print(f"{i}. {row[0]}: Net Rating {row[1]} (ORtg: {row[2]}, DRtg: {row[3]}, Record: {row[4]}-{row[5]})")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    calculate_team_ratings()