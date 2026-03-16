"""
ICN-SEA Flight Price Tracker
Scrapes Google Flights via fast-flights for nonstop ICN→SEA prices.
Stores daily snapshots in a JSON file.
"""

import json
import os
from datetime import datetime, timedelta
from fast_flights import FlightData, Passengers, get_flights

PRICES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'icn_sea_prices.json')


def load_prices():
    if os.path.exists(PRICES_FILE):
        with open(PRICES_FILE, 'r') as f:
            return json.load(f)
    return {'snapshots': []}


def save_prices(data):
    os.makedirs(os.path.dirname(PRICES_FILE), exist_ok=True)
    with open(PRICES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def scrape_prices(search_dates=None):
    """Scrape ICN-SEA nonstop prices for given dates.
    
    Args:
        search_dates: List of date strings (YYYY-MM-DD) to search. 
                      Defaults to ~30, 60, 90 days out.
    """
    if not search_dates:
        today = datetime.now()
        search_dates = [
            (today + timedelta(days=d)).strftime('%Y-%m-%d')
            for d in [30, 60, 90]
        ]

    results = []
    for date in search_dates:
        try:
            result = get_flights(
                flight_data=[FlightData(date=date, from_airport='ICN', to_airport='SEA')],
                trip='one-way',
                passengers=Passengers(adults=1),
                seat='economy',
                max_stops=0,
            )
            flights = []
            seen = set()
            for f in result.flights:
                key = f"{f.name}|{f.departure}"
                if key in seen:
                    continue
                seen.add(key)
                price_str = f.price or ''
                price_num = None
                if price_str:
                    price_num = int(''.join(c for c in price_str if c.isdigit()) or '0') or None
                flights.append({
                    'airline': f.name,
                    'departure': f.departure,
                    'arrival': f.arrival,
                    'duration': f.duration,
                    'price': price_str,
                    'price_usd': price_num,
                })
            
            if flights:
                lowest = min((f['price_usd'] for f in flights if f['price_usd']), default=None)
                results.append({
                    'travel_date': date,
                    'lowest_price': lowest,
                    'flights': flights,
                })
        except Exception as e:
            print(f"Error scraping {date}: {e}")

    return results


def run_daily_scrape():
    """Run a daily scrape and append to history."""
    data = load_prices()
    results = scrape_prices()
    
    snapshot = {
        'scraped_at': datetime.now().isoformat(),
        'route': 'ICN-SEA',
        'dates': results,
    }
    data['snapshots'].append(snapshot)
    save_prices(data)
    
    print(f"Scraped {len(results)} dates at {snapshot['scraped_at']}")
    for r in results:
        print(f"  {r['travel_date']}: ${r['lowest_price']} lowest ({len(r['flights'])} flights)")
    
    return snapshot


if __name__ == '__main__':
    run_daily_scrape()
