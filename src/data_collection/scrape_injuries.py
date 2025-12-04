import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_db_connection
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def scrape_injuries():
    print("Scraping NBA injury reports from ESPN...\n")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    today = datetime.now().date()
    
    url = "https://www.espn.com/nba/injuries"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        injuries_added = 0
        injuries_updated = 0
        
        injury_tables = soup.find_all('div', class_='ResponsiveTable')
        
        if not injury_tables:
            print("Could not find injury tables on ESPN")
            cur.close()
            conn.close()
            return
        
        for table in injury_tables:
            rows = table.find_all('tr')[1:]
            
            for row in rows:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 4:
                        continue
                    
                    player_name = cols[0].text.strip()
                    
                    if not player_name:
                        continue
                    
                    status = cols[2].text.strip()
                    description = cols[3].text.strip()
                    
                    cur.execute("""
                        SELECT player_id FROM players 
                        WHERE LOWER(full_name) = LOWER(%s)
                        LIMIT 1
                    """, (player_name,))
                    
                    player_result = cur.fetchone()
                    
                    if not player_result:
                        print(f"  Player not found: {player_name}")
                        continue
                    
                    player_id = player_result[0]
                    
                    cur.execute("""
                        SELECT injury_id FROM injuries
                        WHERE player_id = %s 
                        AND report_date = %s
                    """, (player_id, today))
                    
                    existing = cur.fetchone()
                    
                    if existing:
                        cur.execute("""
                            UPDATE injuries SET
                                injury_status = %s,
                                injury_description = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE injury_id = %s
                        """, (status, description, existing[0]))
                        injuries_updated += 1
                    else:
                        cur.execute("""
                            INSERT INTO injuries (
                                player_id, report_date, injury_status, 
                                injury_description, source
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (player_id, today, status, description, 'ESPN'))
                        injuries_added += 1
                    
                    print(f"  {player_name}: {status} - {description}")
                    
                except Exception as e:
                    print(f"  Error processing row: {e}")
                    continue
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"\n{'='*50}")
        print("INJURY SCRAPING COMPLETE!")
        print(f"{'='*50}")
        print(f"Added: {injuries_added}")
        print(f"Updated: {injuries_updated}")
        print(f"Total processed: {injuries_added + injuries_updated}")
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            cur.close()
            conn.close()
        except:
            pass

if __name__ == "__main__":
    scrape_injuries()