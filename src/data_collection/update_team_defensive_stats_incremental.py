import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_db_connection
from datetime import datetime, timedelta

def update_team_defensive_stats_for_yesterday(target_date=None):
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).date()
    else:
        target_date = datetime.strptime(str(target_date), '%Y-%m-%d').date()
    
    print(f"Updating team defensive stats for teams that played on {target_date}...\n")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    season_year = target_date.year
    season_month = target_date.month
    
    if season_month >= 10:
        season = f"{season_year}-{str(season_year+1)[-2:]}"
    else:
        season = f"{season_year-1}-{str(season_year)[-2:]}"
    
    cur.execute("""
        SELECT DISTINCT home_team_id as team_id FROM games WHERE game_date = %s
        UNION
        SELECT DISTINCT away_team_id as team_id FROM games WHERE game_date = %s
    """, (target_date, target_date))
    
    teams = [row[0] for row in cur.fetchall()]
    
    if len(teams) == 0:
        print(f"No teams found for {target_date}")
        cur.close()
        conn.close()
        return
    
    print(f"Found {len(teams)} teams to update for season {season}\n")
    
    for team_id in teams:
        cur.execute("""
            SELECT 
                pgs.points,
                pgs.rebounds_total,
                pgs.assists,
                pgs.steals,
                pgs.blocks,
                pgs.turnovers,
                pgs.field_goals_made,
                pgs.field_goals_attempted,
                pgs.three_pointers_made,
                pgs.three_pointers_attempted,
                pgs.free_throws_made,
                pgs.free_throws_attempted
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id
            WHERE g.season = %s
                AND g.game_status = 'completed'
                AND g.game_type = 'regular_season'
                AND pgs.team_id != %s
                AND (g.home_team_id = %s OR g.away_team_id = %s)
        """, (season, team_id, team_id, team_id))
        
        opponent_stats = cur.fetchall()
        
        if len(opponent_stats) == 0:
            continue
        
        cur.execute("""
            SELECT COUNT(DISTINCT g.game_id)
            FROM games g
            WHERE g.season = %s
                AND (g.home_team_id = %s OR g.away_team_id = %s)
                AND g.game_status = 'completed'
                AND g.game_type = 'regular_season'
        """, (season, team_id, team_id))
        
        games_played = cur.fetchone()[0]
        
        total_points = sum(row[0] or 0 for row in opponent_stats)
        total_rebounds = sum(row[1] or 0 for row in opponent_stats)
        total_assists = sum(row[2] or 0 for row in opponent_stats)
        total_steals = sum(row[3] or 0 for row in opponent_stats)
        total_blocks = sum(row[4] or 0 for row in opponent_stats)
        total_turnovers = sum(row[5] or 0 for row in opponent_stats)
        total_fgm = sum(row[6] or 0 for row in opponent_stats)
        total_fga = sum(row[7] or 0 for row in opponent_stats)
        total_3pm = sum(row[8] or 0 for row in opponent_stats)
        total_3pa = sum(row[9] or 0 for row in opponent_stats)
        total_ftm = sum(row[10] or 0 for row in opponent_stats)
        total_fta = sum(row[11] or 0 for row in opponent_stats)
        
        opp_ppg = round(total_points / games_played, 1) if games_played > 0 else 0
        opp_rpg = round(total_rebounds / games_played, 1) if games_played > 0 else 0
        opp_apg = round(total_assists / games_played, 1) if games_played > 0 else 0
        opp_spg = round(total_steals / games_played, 1) if games_played > 0 else 0
        opp_bpg = round(total_blocks / games_played, 1) if games_played > 0 else 0
        opp_tpg = round(total_turnovers / games_played, 1) if games_played > 0 else 0
        
        opp_fg_pct = round((total_fgm / total_fga) * 100, 1) if total_fga > 0 else 0
        opp_3p_pct = round((total_3pm / total_3pa) * 100, 1) if total_3pa > 0 else 0
        opp_ft_pct = round((total_ftm / total_fta) * 100, 1) if total_fta > 0 else 0
        
        opp_3pa_pg = round(total_3pa / games_played, 1) if games_played > 0 else 0
        opp_fta_pg = round(total_fta / games_played, 1) if games_played > 0 else 0
        
        two_pm = total_fgm - total_3pm
        two_pa = total_fga - total_3pa
        opp_2p_pct = round((two_pm / two_pa) * 100, 1) if two_pa > 0 else 0
        
        opp_ft_rate = round((total_fta / total_fga), 3) if total_fga > 0 else 0
        
        cur.execute("""
            INSERT INTO team_defensive_stats (
                team_id, season, games_played,
                opp_points_per_game, opp_rebounds_per_game, opp_assists_per_game,
                opp_steals_per_game, opp_blocks_per_game, opp_turnovers_per_game,
                opp_field_goal_pct, opp_three_point_pct, opp_two_point_pct,
                opp_free_throw_pct, opp_three_point_attempts_pg,
                opp_free_throw_attempts_pg, opp_free_throw_rate
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (team_id, season) DO UPDATE SET
                games_played = EXCLUDED.games_played,
                opp_points_per_game = EXCLUDED.opp_points_per_game,
                opp_rebounds_per_game = EXCLUDED.opp_rebounds_per_game,
                opp_assists_per_game = EXCLUDED.opp_assists_per_game,
                opp_steals_per_game = EXCLUDED.opp_steals_per_game,
                opp_blocks_per_game = EXCLUDED.opp_blocks_per_game,
                opp_turnovers_per_game = EXCLUDED.opp_turnovers_per_game,
                opp_field_goal_pct = EXCLUDED.opp_field_goal_pct,
                opp_three_point_pct = EXCLUDED.opp_three_point_pct,
                opp_two_point_pct = EXCLUDED.opp_two_point_pct,
                opp_free_throw_pct = EXCLUDED.opp_free_throw_pct,
                opp_three_point_attempts_pg = EXCLUDED.opp_three_point_attempts_pg,
                opp_free_throw_attempts_pg = EXCLUDED.opp_free_throw_attempts_pg,
                opp_free_throw_rate = EXCLUDED.opp_free_throw_rate
        """, (
            team_id, season, games_played,
            opp_ppg, opp_rpg, opp_apg, opp_spg, opp_bpg, opp_tpg,
            opp_fg_pct, opp_3p_pct, opp_2p_pct, opp_ft_pct,
            opp_3pa_pg, opp_fta_pg, opp_ft_rate
        ))
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("="*50)
    print(f"Updated {len(teams)} teams defensive stats for {season}")
    print("="*50)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        update_team_defensive_stats_for_yesterday(target_date)
    else:
        update_team_defensive_stats_for_yesterday()