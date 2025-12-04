import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_collection.utils import get_db_connection
import pandas as pd

conn = get_db_connection()
df = pd.read_sql("""
    SELECT DISTINCT game_date, COUNT(*) as games 
    FROM games 
    WHERE season = '2024-25' 
        AND game_type = 'regular_season'
    GROUP BY game_date 
    ORDER BY game_date DESC 
    LIMIT 20
""", conn)
print(df)
conn.close()