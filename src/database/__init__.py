import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import get_db_connection
import pandas as pd
from datetime import datetime, timedelta

def build_features_for_training():
    print("Building features for model training...")
    print("This creates all contextual factors from raw data\n")
    
    conn = get_db_connection()
    
    print("Loading player game stats...")
    query = """
        SELECT 
            pgs.*,
            g.game_date,
            g.season,
            g.home_team_id,
            g.away_team_id,
            g.game_type,
            p.position,
            p.height,
            p.weight
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        JOIN players p ON pgs.player_id = p.player_id
        WHERE g.game_status = 'completed'
            AND g.game_type = 'regular_season'
        ORDER BY pgs.player_id, g.game_date
    """
    
    df = pd.read_sql(query, conn)
    print(f"Loaded {len(df)} player-game records\n")
    
    print("Calculating features...")
    
    # FEATURE 1: Recent Form (L5, L10, L20 rolling averages)
    print("  - Recent form (L5, L10, L20)...")
    for window in [5, 10, 20]:
        for stat in ['points', 'rebounds_total', 'assists', 'steals', 'blocks']:
            df[f'{stat}_l{window}'] = df.groupby('player_id')[stat].transform(
                lambda x: x.rolling(window=window, min_periods=1).mean().shift(1)
            )
    
    # FEATURE 2: Home/Away Split
    print("  - Home/away indicators...")
    df['is_home'] = (df['team_id'] == df['home_team_id']).astype(int)
    df['is_away'] = (df['team_id'] == df['away_team_id']).astype(int)
    
    # FEATURE 3: Days Rest
    print("  - Days rest calculation...")
    df['game_date'] = pd.to_datetime(df['game_date'])
    df['days_rest'] = df.groupby('player_id')['game_date'].diff().dt.days
    df['days_rest'] = df['days_rest'].fillna(3)  # First game assumption
    df['is_back_to_back'] = (df['days_rest'] == 1).astype(int)
    
    # FEATURE 4: Games played this season (sample size)
    print("  - Games played count...")
    df['games_played_season'] = df.groupby(['player_id', 'season']).cumcount()
    
    # FEATURE 5: Player consistency (rolling std dev)
    print("  - Player consistency scores...")
    for stat in ['points', 'rebounds_total', 'assists']:
        df[f'{stat}_std_l10'] = df.groupby('player_id')[stat].transform(
            lambda x: x.rolling(window=10, min_periods=3).std().shift(1)
        )
    
    # FEATURE 6: Load team ratings
    print("  - Loading team ratings...")
    team_ratings = pd.read_sql("""
        SELECT team_id, season, offensive_rating, defensive_rating, net_rating, pace
        FROM team_ratings
    """, conn)
    
    # Merge team's own ratings
    df = df.merge(
        team_ratings,
        left_on=['team_id', 'season'],
        right_on=['team_id', 'season'],
        how='left',
        suffixes=('', '_team')
    )
    
    # Merge opponent ratings
    df['opponent_id'] = df.apply(
        lambda row: row['away_team_id'] if row['is_home'] == 1 else row['home_team_id'],
        axis=1
    )
    
    df = df.merge(
        team_ratings,
        left_on=['opponent_id', 'season'],
        right_on=['team_id', 'season'],
        how='left',
        suffixes=('', '_opp')
    )
    
    # FEATURE 7: Opponent defensive stats
    print("  - Loading opponent defensive stats...")
    opp_defense = pd.read_sql("""
        SELECT team_id, season, 
               opp_points_per_game, 
               opp_field_goal_pct,
               opp_three_point_pct,
               opp_free_throw_rate
        FROM team_defensive_stats
    """, conn)
    
    df = df.merge(
        opp_defense,
        left_on=['opponent_id', 'season'],
        right_on=['team_id', 'season'],
        how='left',
        suffixes=('', '_oppdef')
    )
    
    # FEATURE 8: Position-specific defense
    print("  - Loading position defense stats...")
    pos_defense = pd.read_sql("""
        SELECT team_id, season, position,
               opp_points_per_game as pos_opp_ppg,
               opp_field_goal_pct as pos_opp_fg_pct
        FROM position_defense_stats
    """, conn)
    
    # Simplify position for matching (G, F, C)
    df['position_simple'] = df['position'].str[0]  # First character
    
    df = df.merge(
        pos_defense,
        left_on=['opponent_id', 'season', 'position_simple'],
        right_on=['team_id', 'season', 'position'],
        how='left',
        suffixes=('', '_posdef')
    )
    
    # FEATURE 9: Altitude (Denver effect)
    print("  - Loading altitude data...")
    teams_altitude = pd.read_sql("""
        SELECT team_id, arena_altitude
        FROM teams
    """, conn)
    
    df = df.merge(
        teams_altitude,
        left_on='opponent_id',
        right_on='team_id',
        how='left',
        suffixes=('', '_altitude')
    )
    
    df['is_altitude_game'] = (df['arena_altitude'] > 3000).astype(int)
    df['altitude_away'] = ((df['is_away'] == 1) & (df['arena_altitude'] > 3000)).astype(int)
    
    # FEATURE 10: Month of season (fatigue/rhythm)
    print("  - Temporal features...")
    df['month'] = df['game_date'].dt.month
    df['day_of_week'] = df['game_date'].dt.dayofweek
    
    # FEATURE 11: Usage indicators (minutes, shot attempts)
    print("  - Usage features...")
    df['usage_l5'] = df.groupby('player_id')['field_goals_attempted'].transform(
        lambda x: x.rolling(window=5, min_periods=1).mean().shift(1)
    )
    df['minutes_l5'] = df.groupby('player_id')['minutes'].transform(
        lambda x: x.rolling(window=5, min_periods=1).mean().shift(1)
    )
    
    # FEATURE 12: Shot distribution (3PT rate, FT rate)
    print("  - Shot distribution...")
    df['three_pt_rate'] = df['three_pointers_attempted'] / df['field_goals_attempted'].replace(0, 1)
    df['ft_rate'] = df['free_throws_attempted'] / df['field_goals_attempted'].replace(0, 1)
    
    df['three_pt_rate_l10'] = df.groupby('player_id')['three_pt_rate'].transform(
        lambda x: x.rolling(window=10, min_periods=1).mean().shift(1)
    )
    df['ft_rate_l10'] = df.groupby('player_id')['ft_rate'].transform(
        lambda x: x.rolling(window=10, min_periods=1).mean().shift(1)
    )
    
    conn.close()
    
    print("\n" + "="*50)
    print("FEATURE ENGINEERING COMPLETE!")
    print("="*50)
    print(f"Total features created: {len(df.columns)}")
    print(f"Total records: {len(df)}")
    
    # Save to CSV for model training
    output_path = '../../data/processed/training_features.csv'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nSaved to: {output_path}")
    
    # Show feature summary
    print("\nFeature columns created:")
    feature_cols = [col for col in df.columns if any(x in col for x in 
                   ['_l5', '_l10', '_l20', 'is_', 'opp_', 'rating', 'pace', 
                    'days_rest', 'std', 'usage', 'altitude', 'month', 'pos_'])]
    print(f"  - {len(feature_cols)} contextual features")
    for col in sorted(feature_cols)[:20]:  # Show first 20
        print(f"    • {col}")
    if len(feature_cols) > 20:
        print(f"    ... and {len(feature_cols) - 20} more")
    
    return df

if __name__ == "__main__":
    build_features_for_training()