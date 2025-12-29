"""
Test script for Amadeus API integration
"""
import os
from amadeus_api import AmadeusFlightSearch

# Set credentials
os.environ['AMADEUS_API_KEY'] = 'KvLzPEP6BRhRTEC3AYlNBrCN6LQ4H5j1'
os.environ['AMADEUS_API_SECRET'] = 'eeFkyyFcdGVFW39m'

# Initialize client
print("Initializing Amadeus client...")
try:
    client = AmadeusFlightSearch()
    print("✓ Client initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize: {e}")
    exit(1)

# Test search with a closer date (test API usually supports up to 330 days)
from datetime import datetime, timedelta
test_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

print(f"\nSearching for flights: DEN -> LAX on {test_date}...")
try:
    flights = client.search_flights(
        origins=['DEN'],
        destinations=['LAX'],
        departure_date=test_date,
        return_date=None,
        adults=1
    )
    print(f"✓ Search completed: Found {len(flights)} flights")

    if flights:
        print("\nFirst 3 flights:")
        for i, flight in enumerate(flights[:3], 1):
            print(f"\n  Flight {i}:")
            print(f"    Route: {flight['origin']} -> {flight['destination']}")
            print(f"    Airline: {flight['airline']} ({flight['flight_number']})")
            print(f"    Departs: {flight['departure_time']} on {flight['departure_date']}")
            print(f"    Arrives: {flight['arrival_time']} on {flight['arrival_date']}")
            print(f"    Duration: {flight['duration']}")
            print(f"    Price: {flight['currency']} {flight['price']}")
            print(f"    Stops: {flight['stops']}")
    else:
        print("\nNo flights found. This could mean:")
        print("  - No flights available on this route/date")
        print("  - API credentials issue")
        print("  - Date format issue")

except Exception as e:
    print(f"✗ Search failed: {e}")
    import traceback
    traceback.print_exc()
