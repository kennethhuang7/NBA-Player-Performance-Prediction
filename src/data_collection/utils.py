import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    if os.getenv('DATABASE_URL'):
        database_url = os.getenv('DATABASE_URL')
    else:
        host = os.getenv('DB_HOST')
        port = os.getenv('DB_PORT')
        dbname = os.getenv('DB_NAME')
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    
    return psycopg2.connect(database_url)

def rate_limit(seconds=40.0):
    time.sleep(seconds + random.uniform(5.0, 10.0))