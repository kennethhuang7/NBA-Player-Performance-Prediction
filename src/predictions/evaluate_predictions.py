import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_collection.utils import get_db_connection
import pandas as pd
from datetime import datetime, timedelta

import warnings
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')
warnings.filterwarnings('ignore', category=FutureWarning)

def evaluate_predictions(target_date=None):
    print("Evaluating prediction accuracy...\n")
    
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).date()
    else:
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    
    print(f"Evaluating predictions for: {target_date}\n")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get predictions for target date
    cur.execute("""
        SELECT 
            p.prediction_id,
            p.game_id,
            p.player_id,
            p.predicted_points,
            p.predicted_rebounds,
            p.predicted_assists,
            p.predicted_steals,
            p.predicted_blocks,
            p.predicted_turnovers,
            p.predicted_three_pointers_made
        FROM predictions p
        JOIN games g ON p.game_id = g.game_id
        WHERE p.prediction_date = %s
        AND g.game_status = 'completed'
    """, (target_date,))
    
    predictions = cur.fetchall()
    
    if len(predictions) == 0:
        print(f"No completed games found with predictions for {target_date}")
        cur.close()
        conn.close()
        return
    
    print(f"Found {len(predictions)} predictions to evaluate\n")
    
    updated = 0
    errors = 0
    
    stats_columns = ['points', 'rebounds_total', 'assists', 'steals', 'blocks', 'turnovers', 'three_pointers_made']
    
    for pred in predictions:
        (prediction_id, game_id, player_id, pred_points, pred_rebounds, pred_assists, 
         pred_steals, pred_blocks, pred_turnovers, pred_threes) = pred
        
        try:
            # Get actual stats
            cur.execute("""
                SELECT points, rebounds_total, assists, steals, blocks, turnovers, three_pointers_made
                FROM player_game_stats
                WHERE game_id = %s AND player_id = %s
            """, (game_id, player_id))
            
            actual = cur.fetchone()
            
            if not actual:
                print(f"  No stats found for player {player_id} in game {game_id}")
                continue
            
            (actual_points, actual_rebounds, actual_assists, actual_steals, 
             actual_blocks, actual_turnovers, actual_threes) = actual
            
            # Calculate errors
            point_error = abs(pred_points - actual_points)
            rebound_error = abs(pred_rebounds - actual_rebounds)
            assist_error = abs(pred_assists - actual_assists)
            steal_error = abs(pred_steals - actual_steals)
            block_error = abs(pred_blocks - actual_blocks)
            turnover_error = abs(pred_turnovers - actual_turnovers)
            three_error = abs(pred_threes - actual_threes)
            
            # Average error across all stats
            avg_error = (point_error + rebound_error + assist_error + 
                        steal_error + block_error + turnover_error + three_error) / 7
            
            # Update prediction with actuals
            cur.execute("""
                UPDATE predictions SET
                    actual_points = %s,
                    actual_rebounds = %s,
                    actual_assists = %s,
                    actual_steals = %s,
                    actual_blocks = %s,
                    actual_turnovers = %s,
                    actual_three_pointers_made = %s,
                    prediction_error = %s
                WHERE prediction_id = %s
            """, (
                actual_points, actual_rebounds, actual_assists,
                actual_steals, actual_blocks, actual_turnovers, actual_threes,
                round(avg_error, 2),
                prediction_id
            ))
            
            updated += 1
            
            if updated % 10 == 0:
                print(f"Progress: {updated}/{len(predictions)} evaluated")
                conn.commit()
            
        except Exception as e:
            print(f"  Error evaluating prediction {prediction_id}: {e}")
            errors += 1
            continue
    
    conn.commit()
    
    # Calculate overall accuracy metrics
    cur.execute("""
        SELECT 
            AVG(ABS(predicted_points - actual_points)) as points_mae,
            AVG(ABS(predicted_rebounds - actual_rebounds)) as rebounds_mae,
            AVG(ABS(predicted_assists - actual_assists)) as assists_mae,
            AVG(ABS(predicted_steals - actual_steals)) as steals_mae,
            AVG(ABS(predicted_blocks - actual_blocks)) as blocks_mae,
            AVG(ABS(predicted_turnovers - actual_turnovers)) as turnovers_mae,
            AVG(ABS(predicted_three_pointers_made - actual_three_pointers_made)) as threes_mae,
            AVG(prediction_error) as overall_mae
        FROM predictions
        WHERE prediction_date = %s
        AND actual_points IS NOT NULL
    """, (target_date,))
    
    metrics = cur.fetchone()
    
    cur.close()
    conn.close()
    
    print(f"\n{'='*50}")
    print("EVALUATION COMPLETE!")
    print(f"{'='*50}")
    print(f"Updated: {updated}")
    print(f"Errors: {errors}")
    
    if metrics and metrics[0]:
        print(f"\n{'='*50}")
        print("ACCURACY METRICS (MAE)")
        print(f"{'='*50}")
        print(f"Points:       {metrics[0]:.2f}")
        print(f"Rebounds:     {metrics[1]:.2f}")
        print(f"Assists:      {metrics[2]:.2f}")
        print(f"Steals:       {metrics[3]:.2f}")
        print(f"Blocks:       {metrics[4]:.2f}")
        print(f"Turnovers:    {metrics[5]:.2f}")
        print(f"3-Pointers:   {metrics[6]:.2f}")
        print(f"Overall:      {metrics[7]:.2f}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        evaluate_predictions(target_date)
    else:
        evaluate_predictions()