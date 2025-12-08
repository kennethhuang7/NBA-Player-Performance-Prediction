import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import re

url = "https://www.espn.com/nba/transactions"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=15)
response.raise_for_status()

soup = BeautifulSoup(response.content, 'html.parser')

all_text = soup.get_text()

print("="*60)
print("ESPN TRANSACTIONS PAGE DEBUG")
print("="*60)
print(f"\nFirst 2000 characters of text:")
print(all_text[:2000])
print("\n" + "="*60)

lines = all_text.split('\n')
print(f"\nTotal lines: {len(lines)}")
print("\nFirst 50 non-empty lines:")
for i, line in enumerate(lines[:100]):
    line_stripped = line.strip()
    if line_stripped:
        print(f"{i}: {line_stripped[:100]}")

print("\n" + "="*60)
print("Looking for date patterns...")
print("="*60)

date_pattern = r'(\w+day),?\s+(\w+)\s+(\d{1,2})'
month_map = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

today = datetime.now().date()
current_date = None
dates_found = []

for i, line in enumerate(lines):
    line_stripped = line.strip()
    if not line_stripped:
        continue
    
    date_match = re.search(date_pattern, line_stripped, re.IGNORECASE)
    if date_match:
        _, month_name, day = date_match.groups()
        month = month_map.get(month_name.lower(), None)
        if month:
            try:
                year = today.year
                parsed_date = date(year, month, int(day))
                if parsed_date > today:
                    parsed_date = date(year - 1, month, int(day))
                dates_found.append((i, line_stripped, parsed_date))
                print(f"Line {i}: Found date '{line_stripped}' -> {parsed_date}")
            except Exception as e:
                print(f"Line {i}: Error parsing date '{line_stripped}': {e}")

print(f"\nFound {len(dates_found)} date matches")

print("\n" + "="*60)
print("Looking for transaction keywords...")
print("="*60)

keywords_found = []
for i, line in enumerate(lines):
    line_stripped = line.strip()
    if not line_stripped:
        continue
    
    line_lower = line_stripped.lower()
    if 'traded' in line_lower or 'signed' in line_lower or 'waived' in line_lower:
        keywords_found.append((i, line_stripped))
        print(f"Line {i}: {line_stripped[:150]}")

print(f"\nFound {len(keywords_found)} lines with transaction keywords")

