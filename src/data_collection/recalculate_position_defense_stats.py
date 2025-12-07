import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_db_connection
from datetime import datetime

def recalculate_all_position_defense_stats(season=None):
    if season is None:
        today = datetime.now().date()
        season_year = today.year
        season_month = today.month
        
        if season_month >= 10:
            season = f"{season_year}-{str(season_year+1)[-2:]}"
        else:
            season = f"{season_year-1}-{str(season_year)[-2:]}"
    else:
        if len(season) == 9 and season[4] == '-' and season[5:].isdigit():
            year1 = season[:4]
            year2 = season[5:]
            season = f"{year1}-{year2[-2:]}"
    
    print("="*50)
    print("RECALCULATING POSITION DEFENSE STATS")
    print(f"Season: {season}")
    print("="*50)
    print()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT g.home_team_id as team_id
        FROM games g
        WHERE g.season = %s AND g.game_status = 'completed'
        UNION
        SELECT DISTINCT g.away_team_id as team_id
        FROM games g
        WHERE g.season = %s AND g.game_status = 'completed'
        ORDER BY team_id
    """, (season, season))
    
    teams = [row[0] for row in cur.fetchall()]
    
    if len(teams) == 0:
        print(f"No teams found for season {season}")
        cur.close()
        conn.close()
        return
    
    print(f"Found {len(teams)} teams to process for season {season}\n")
    
    positions = ['G', 'F', 'C']
    
    total_updates = 0
    total_inserts = 0
    
    for team_id in teams:
        for position in positions:
            cur.execute("""
                SELECT 
                    COUNT(*) as games,
                    AVG(game_totals.points) as avg_points,
                    AVG(game_totals.rebounds) as avg_rebounds,
                    AVG(game_totals.assists) as avg_assists,
                    AVG(game_totals.steals) as avg_steals,
                    AVG(game_totals.blocks) as avg_blocks,
                    AVG(game_totals.turnovers) as avg_turnovers,
                    AVG(game_totals.three_pointers_made) as avg_3pm,
                    AVG(game_totals.field_goals_made) as avg_fgm,
                    AVG(game_totals.field_goals_attempted) as avg_fga,
                    AVG(game_totals.three_pointers_attempted) as avg_3pa
                FROM (
                    SELECT 
                        pgs.game_id,
                        SUM(pgs.points) as points,
                        SUM(pgs.rebounds_total) as rebounds,
                        SUM(pgs.assists) as assists,
                        SUM(pgs.steals) as steals,
                        SUM(pgs.blocks) as blocks,
                        SUM(pgs.turnovers) as turnovers,
                        SUM(pgs.three_pointers_made) as three_pointers_made,
                        SUM(pgs.field_goals_made) as field_goals_made,
                        SUM(pgs.field_goals_attempted) as field_goals_attempted,
                        SUM(pgs.three_pointers_attempted) as three_pointers_attempted
                    FROM player_game_stats pgs
                    JOIN games g ON pgs.game_id = g.game_id
                    JOIN players p ON pgs.player_id = p.player_id
                    WHERE g.season = %s
                        AND g.game_status = 'completed'
                        AND g.game_type = 'regular_season'
                        AND pgs.team_id != %s
                        AND (g.home_team_id = %s OR g.away_team_id = %s)
                        AND p.position LIKE %s
                    GROUP BY pgs.game_id
                ) as game_totals
            """, (season, team_id, team_id, team_id, f'%{position}%'))
            
            result = cur.fetchone()
            
            if not result or result[0] == 0:
                continue
            
            games_count = result[0] or 0
            avg_points = round(result[1] or 0, 1) if result[1] else 0.0
            avg_rebounds = round(result[2] or 0, 1) if result[2] else 0.0
            avg_assists = round(result[3] or 0, 1) if result[3] else 0.0
            avg_steals = round(result[4] or 0, 1) if result[4] else 0.0
            avg_blocks = round(result[5] or 0, 1) if result[5] else 0.0
            avg_turnovers = round(result[6] or 0, 1) if result[6] else 0.0
            avg_3pm = result[7] or 0
            avg_fgm = result[8] or 0
            avg_fga = result[9] or 0
            avg_3pa = result[10] or 0
            
            opp_fg_pct = round((avg_fgm / avg_fga) * 100, 1) if avg_fga > 0 else 0
            opp_3p_pct = round((avg_3pm / avg_3pa) * 100, 1) if avg_3pa > 0 else 0
            avg_3pm_allowed = round(avg_3pm, 1) if avg_3pm else 0.0
            
            try:
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM position_defense_stats 
                        WHERE team_id = %s AND season = %s AND position = %s
                    )
                """, (team_id, season, position))
                exists_before = cur.fetchone()[0]
                
                cur.execute("""
                    INSERT INTO position_defense_stats (
                        team_id, season, position, games_played,
                        points_allowed_per_game, rebounds_allowed_per_game, assists_allowed_per_game,
                        steals_allowed_per_game, blocks_allowed_per_game, turnovers_forced_per_game,
                        three_pointers_made_allowed_per_game, fg_pct_allowed
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (team_id, season, position) DO UPDATE SET
                        games_played = EXCLUDED.games_played,
                        points_allowed_per_game = EXCLUDED.points_allowed_per_game,
                        rebounds_allowed_per_game = EXCLUDED.rebounds_allowed_per_game,
                        assists_allowed_per_game = EXCLUDED.assists_allowed_per_game,
                        steals_allowed_per_game = EXCLUDED.steals_allowed_per_game,
                        blocks_allowed_per_game = EXCLUDED.blocks_allowed_per_game,
                        turnovers_forced_per_game = EXCLUDED.turnovers_forced_per_game,
                        three_pointers_made_allowed_per_game = EXCLUDED.three_pointers_made_allowed_per_game,
                        fg_pct_allowed = EXCLUDED.fg_pct_allowed
                """, (team_id, season, position, games_count, avg_points, avg_rebounds, avg_assists,
                      avg_steals, avg_blocks, avg_turnovers, avg_3pm_allowed, opp_fg_pct))
                
                try:
                    cur.execute("""
                        UPDATE position_defense_stats
                        SET opp_points_per_game = %s,
                            opp_field_goal_pct = %s,
                            opp_three_point_pct = %s
                        WHERE team_id = %s AND season = %s AND position = %s
                    """, (avg_points, opp_fg_pct, opp_3p_pct, team_id, season, position))
                except Exception:
                    pass
                
                if exists_before:
                    total_updates += 1
                else:
                    total_inserts += 1
                
            except Exception as e:
                print(f"Error processing team {team_id} position {position}: {e}")
                continue
        
        if (teams.index(team_id) + 1) % 10 == 0:
            print(f"Processed {teams.index(team_id) + 1}/{len(teams)} teams...")
            conn.commit()
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "="*50)
    print("RECALCULATION COMPLETE!")
    print("="*50)
    print(f"Season: {season}")
    print(f"Total inserts: {total_inserts}")
    print(f"Total updates: {total_updates}")
    print(f"Total processed: {total_inserts + total_updates} team-position combinations")
    print("="*50)
    
    print("\nSample results (Best Guard Defense):")
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT t.full_name, pds.points_allowed_per_game, pds.rebounds_allowed_per_game, 
               pds.assists_allowed_per_game, pds.games_played
        FROM position_defense_stats pds
        JOIN teams t ON pds.team_id = t.team_id
        WHERE pds.season = %s AND pds.position = 'G'
        ORDER BY pds.points_allowed_per_game ASC
        LIMIT 5
    """, (season,))
    
    for i, row in enumerate(cur.fetchall(), 1):
        print(f"{i}. {row[0]}: {row[1]} PPG, {row[2]} RPG, {row[3]} APG allowed to guards ({row[4]} games)")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        season = sys.argv[1]
        recalculate_all_position_defense_stats(season)
    else:
        recalculate_all_position_defense_stats()

