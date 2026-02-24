"""
Automated Blackout Date Updater
Fetches latest blackout dates from Frontier's GoWild Pass terms and conditions page
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import re

FRONTIER_URL = "https://www.flyfrontier.com/frontiermiles/terms-and-conditions/#GoWild!_Pass"
CACHE_FILE = "blackout_cache.json"
UPDATE_INTERVAL_DAYS = 30  # Check monthly

def should_update():
    """Check if it's time to update blackout dates"""
    if not os.path.exists(CACHE_FILE):
        return True
    
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
            last_update = datetime.fromisoformat(cache.get('last_updated', '2000-01-01'))
            days_since_update = (datetime.now() - last_update).days
            return days_since_update >= UPDATE_INTERVAL_DAYS
    except Exception as e:
        print(f"Error checking update time: {e}")
        return True

def parse_date(date_str, year):
    """Parse date string like 'January 1' or 'Jan 1' and return ISO format"""
    try:
        # Clean up the date string
        date_str = date_str.strip()
        
        # Try different date formats
        for fmt in ['%B %d', '%b %d', '%B %d-%d', '%b %d-%d']:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return f"{year}-{parsed.month:02d}-{parsed.day:02d}"
            except ValueError:
                continue
        
        # Handle ranges like "January 1-2"
        if '-' in date_str and not date_str.startswith('-'):
            parts = date_str.split('-')
            if len(parts) == 2:
                month_day = parts[0].strip()
                try:
                    parsed = datetime.strptime(month_day, '%B %d')
                    return f"{year}-{parsed.month:02d}-{parsed.day:02d}"
                except ValueError:
                    try:
                        parsed = datetime.strptime(month_day, '%b %d')
                        return f"{year}-{parsed.month:02d}-{parsed.day:02d}"
                    except ValueError:
                        pass
        
        return None
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None

def fetch_blackout_dates():
    """Fetch and parse blackout dates from Frontier's website"""
    try:
        print(f"Fetching blackout dates from {FRONTIER_URL}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(FRONTIER_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the GoWild Pass section
        blackout_data = {
            '2026': [],
            '2027': [],
            '2028': []
        }
        
        # Look for blackout date patterns in the page
        # This is a simplified parser - may need adjustment based on actual HTML structure
        text_content = soup.get_text()
        
        # Search for blackout date sections
        # Pattern: look for "2026", "2027", etc. followed by dates
        for year in ['2026', '2027', '2028']:
            year_pattern = rf'{year}[:\s]*([\s\S]*?)(?=\n{int(year)+1}[:\s]|$)'
            year_match = re.search(year_pattern, text_content, re.IGNORECASE)
            
            if year_match:
                year_section = year_match.group(1)
                
                # Extract date ranges
                # Pattern: Month Day-Day or Month Day
                date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:-(\d{1,2}))?'
                
                for match in re.finditer(date_pattern, year_section, re.IGNORECASE):
                    month = match.group(1)
                    start_day = match.group(2)
                    end_day = match.group(3) if match.group(3) else start_day
                    
                    start_date = parse_date(f"{month} {start_day}", year)
                    end_date = parse_date(f"{month} {end_day}", year)
                    
                    if start_date and end_date:
                        # Try to extract description from surrounding context
                        context_start = max(0, match.start() - 50)
                        context_end = min(len(year_section), match.end() + 50)
                        context = year_section[context_start:context_end].strip()
                        
                        # Extract a reasonable description
                        description = f"{month} Period"
                        
                        blackout_data[year].append({
                            'start': start_date,
                            'end': end_date,
                            'description': description
                        })
        
        # Save to cache
        cache_data = {
            'last_updated': datetime.now().isoformat(),
            'blackout_periods': blackout_data,
            'source': FRONTIER_URL
        }
        
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"✅ Blackout dates updated successfully! Found {sum(len(v) for v in blackout_data.values())} periods")
        return cache_data
        
    except Exception as e:
        print(f"❌ Error fetching blackout dates: {e}")
        print("Using cached data if available...")
        return load_cached_data()

def load_cached_data():
    """Load blackout dates from cache"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
    
    # Return fallback data from gowild_blackout.py
    return get_fallback_data()

def get_fallback_data():
    """Get fallback blackout data from gowild_blackout.py"""
    try:
        from gowild_blackout import GoWildBlackoutDates
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        blackout_data = {
            '2026': [],
            '2027': [],
            '2028': []
        }
        
        # Get all periods from the class, filtering out past periods
        all_periods_2026 = GoWildBlackoutDates.BLACKOUT_PERIODS_2026
        all_periods_2027 = GoWildBlackoutDates.BLACKOUT_PERIODS_2027
        
        for start_date, end_date, description in all_periods_2026:
            if end_date >= today:
                blackout_data['2026'].append({
                    'start': start_date,
                    'end': end_date,
                    'description': description
                })
        
        for start_date, end_date, description in all_periods_2027:
            if end_date >= today:
                blackout_data['2027'].append({
                    'start': start_date,
                    'end': end_date,
                    'description': description
                })
        
        return {
            'last_updated': datetime.now().isoformat(),
            'blackout_periods': blackout_data,
            'source': 'fallback'
        }
    except Exception as e:
        print(f"Error loading fallback data: {e}")
        return {
            'last_updated': datetime.now().isoformat(),
            'blackout_periods': {'2026': [], '2027': [], '2028': []},
            'source': 'empty'
        }

def update_if_needed():
    """Update blackout dates if needed (called on app startup)"""
    # For now, use fallback data only - web scraper needs improvement
    print("✅ Using fallback blackout dates from gowild_blackout.py")
    data = get_fallback_data()
    
    # Save to cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    return data

def get_blackout_data():
    """Get current blackout data (from cache or trigger update if needed)"""
    return load_cached_data() or get_fallback_data()

if __name__ == "__main__":
    # Manual update test
    print("Testing blackout date updater...")
    data = fetch_blackout_dates()
    print(f"\nBlackout periods found:")
    for year, periods in data['blackout_periods'].items():
        print(f"\n{year}: {len(periods)} periods")
        for p in periods[:3]:  # Show first 3
            print(f"  {p['start']} to {p['end']}: {p['description']}")
