"""
Test script for streaming API endpoint
"""
import requests
import json
import sys

url = 'http://localhost:5001/api/search/stream'
data = {
    'origins': ['DEN', 'MDW'],
    'destinations': ['MCO', 'LAS'],
    'tripType': 'one-way',
    'departureDate': '2026-02-05'
}

print(f"Testing streaming search: {data['origins']} -> {data['destinations']}")
print("=" * 60)

try:
    response = requests.post(url, json=data, stream=True, timeout=60)
    response.raise_for_status()

    total_flights = 0
    routes_received = 0

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')

            # SSE format: "data: {...}"
            if line_str.startswith('data: '):
                json_str = line_str[6:]  # Remove "data: " prefix
                event_data = json.loads(json_str)

                if event_data.get('complete'):
                    print("\n" + "=" * 60)
                    print(f"✓ Search complete!")
                    print(f"  Total flights: {event_data['total_flights']}")
                    print(f"  Routes searched: {routes_received}")
                else:
                    routes_received += 1
                    route = event_data.get('route')
                    count = event_data.get('count', 0)
                    total_flights += count

                    print(f"\n[Route {routes_received}] {route}")
                    print(f"  Flights found: {count}")

                    # Show first flight as sample
                    if event_data.get('flights'):
                        first_flight = event_data['flights'][0]
                        print(f"  Sample: {first_flight.get('airline')} {first_flight.get('flight_number')}")
                        print(f"          {first_flight.get('departure_time')} -> {first_flight.get('arrival_time')}")
                        print(f"          ${first_flight.get('price')} {first_flight.get('currency')}")

                sys.stdout.flush()

    print("\n" + "=" * 60)
    print(f"Streaming test completed successfully!")

except requests.exceptions.RequestException as e:
    print(f"\n✗ Error: {e}")
    sys.exit(1)
