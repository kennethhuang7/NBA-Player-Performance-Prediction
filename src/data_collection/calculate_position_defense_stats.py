from utils import get_db_connection
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def calculate_position_defense_stats():
    print("Calculating position-specific defense stats...")
    print("This shows how each team defends each position (PG, SG, SF, PF, C)\n")
    
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
    print(f"Found {len(season_teams)} season-team combinations to process")
    
    positions = ['G', 'F', 'C', 'G-F', 'F-C']
    
    count = 0
    total_inserts = 0
    
    for season, team_id in season_teams:
        for position in positions:
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT pgs.game_id) as games,
                    AVG(pgs.points) as avg_points,
                    AVG(pgs.field_goals_made) as avg_fgm,
                    AVG(pgs.field_goals_attempted) as avg_fga,
                    AVG(pgs.three_pointers_made) as avg_3pm,
                    AVG(pgs.three_pointers_attempted) as avg_3pa
                FROM player_game_stats pgs
                JOIN games g ON pgs.game_id = g.game_id
                JOIN players p ON pgs.player_id = p.player_id
                WHERE g.season = %s
                    AND g.game_status = 'completed'
                    AND g.game_type = 'regular_season'
                    AND pgs.team_id != %s
                    AND (g.home_team_id = %s OR g.away_team_id = %s)
                    AND p.position LIKE %s
            """, (season, team_id, team_id, team_id, f'%{position}%'))
            
            result = cur.fetchone()
            
            if not result or result[0] == 0:
                continue
            
            games_count = result[0] or 0
            avg_points = round(result[1] or 0, 1)
            avg_fgm = result[2] or 0
            avg_fga = result[3] or 0
            avg_3pm = result[4] or 0
            avg_3pa = result[5] or 0
            
            opp_fg_pct = round((avg_fgm / avg_fga) * 100, 1) if avg_fga > 0 else 0
            opp_3p_pct = round((avg_3pm / avg_3pa) * 100, 1) if avg_3pa > 0 else 0
            
            try:
                cur.execute("""
                    INSERT INTO position_defense_stats (
                        team_id,
                        season,
                        position,
                        games_played,
                        opp_points_per_game,
                        opp_field_goal_pct,
                        opp_three_point_pct
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    team_id,
                    season,
                    position,
                    games_count,
                    avg_points,
                    opp_fg_pct,
                    opp_3p_pct
                ))
                
                total_inserts += 1
                
            except Exception as e:
                print(f"Error inserting team {team_id} season {season} position {position}: {e}")
                continue
        
        count += 1
        if count % 30 == 0:
            print(f"Processed {count}/{len(season_teams)} teams...")
            conn.commit()
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "="*50)
    print("POSITION DEFENSE STATS CALCULATION COMPLETE!")
    print("="*50)
    print(f"Calculated defense for {total_inserts} team-position combinations")
    
    print("\nExample: Best Guard Defense (2024-25):")
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT t.full_name, pds.opp_points_per_game, pds.opp_field_goal_pct
        FROM position_defense_stats pds
        JOIN teams t ON pds.team_id = t.team_id
        WHERE pds.season = '2024-25' AND pds.position = 'G'
        ORDER BY pds.opp_points_per_game ASC
        LIMIT 5
    """)
    
    for i, row in enumerate(cur.fetchall(), 1):
        print(f"{i}. {row[0]}: {row[1]} PPG allowed to guards (FG%: {row[2]})")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    calculate_position_defense_stats()