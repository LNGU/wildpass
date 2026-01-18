from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
# from scraper import FrontierScraper  # Commented out - using Amadeus API instead
from amadeus_api import AmadeusFlightSearch
from realtime_flights import RealTimeFlightService
from trip_planner import find_optimal_trips
from gowild_blackout import GoWildBlackoutDates
from blackout_updater import update_if_needed, get_blackout_data
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import os
import random
import time

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Root route for health checks (Render, etc.)
@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'service': 'WildPass Flight Search API',
        'version': '1.2.0'  # Added real-time flight status
    })

# Health check at /health for Render
@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# Update blackout dates on startup
print("🚀 Starting WildPass Backend...")
update_if_needed()

# Initialize scraper (commented out - using Amadeus API)
# scraper = FrontierScraper()

# Initialize Amadeus API client
amadeus_client = None
AMADEUS_ENABLED = False
try:
    amadeus_client = AmadeusFlightSearch(
        api_key=os.environ.get('AMADEUS_API_KEY'),
        api_secret=os.environ.get('AMADEUS_API_SECRET')
    )
    AMADEUS_ENABLED = True
except ValueError as e:
    print(f"Warning: Amadeus API not configured: {e}")

# Initialize Real-Time Flight Service (AviationStack)
realtime_service = RealTimeFlightService()

# Development mode - set to True to return mock data instead of scraping
# If Amadeus is enabled, DEV_MODE defaults to False (use real data)
DEV_MODE = os.environ.get('DEV_MODE', 'false' if AMADEUS_ENABLED else 'true').lower() == 'true'

# Simple in-memory cache
cache = {}
CACHE_DURATION = timedelta(hours=1)  # Cache results for 1 hour

def get_cache_key(origins, destinations, departure_date, return_date, trip_type):
    """Generate a unique cache key for the search parameters"""
    return f"{','.join(sorted(origins))}_{','.join(sorted(destinations))}_{departure_date}_{return_date}_{trip_type}"

def is_cache_valid(cache_entry):
    """Check if cached entry is still valid"""
    if not cache_entry:
        return False
    cache_time = datetime.fromisoformat(cache_entry['timestamp'])
    return datetime.now() - cache_time < CACHE_DURATION

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    amadeus_env = os.environ.get('AMADEUS_ENV', 'test').lower()
    return jsonify({
        'status': 'ok',
        'message': 'Flight Search API is running',
        'amadeus_enabled': AMADEUS_ENABLED,
        'amadeus_environment': amadeus_env,
        'dev_mode': DEV_MODE,
        'realtime_service_enabled': realtime_service.is_configured(),
        'note': 'Real-time flight status powered by AviationStack'
    })

@app.route('/api/debug/amadeus-test', methods=['GET'])
def amadeus_test():
    """
    Test Amadeus API connection directly
    This helps diagnose if credentials are working
    """
    if not AMADEUS_ENABLED or not amadeus_client:
        return jsonify({
            'status': 'error',
            'message': 'Amadeus not configured',
            'amadeus_enabled': AMADEUS_ENABLED
        }), 503
    
    try:
        # Try a simple flight search for tomorrow to test API
        from datetime import datetime, timedelta
        test_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        response = amadeus_client.amadeus.shopping.flight_offers_search.get(
            originLocationCode='DEN',
            destinationLocationCode='LAX',
            departureDate=test_date,
            adults=1,
            max=3
        )
        
        # Extract airlines found
        airlines = set()
        for offer in response.data:
            for itin in offer.get('itineraries', []):
                for seg in itin.get('segments', []):
                    airlines.add(seg.get('carrierCode'))
        
        return jsonify({
            'status': 'ok',
            'message': 'Amadeus API is working',
            'test_date': test_date,
            'route': 'DEN -> LAX',
            'offers_found': len(response.data),
            'airlines_found': list(airlines),
            'sample_price': response.data[0]['price']['total'] if response.data else None
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

def generate_mock_flights(origins, destinations, departure_date, return_date=None):
    """Generate mock flight data for development/testing"""
    flights = []

    # If destinations is ['ANY'], use a few sample destinations
    dest_list = destinations if destinations != ['ANY'] else ['MCO', 'LAS', 'MIA', 'PHX', 'ATL']

    # Check for blackout dates
    blackout_info = GoWildBlackoutDates.is_flight_affected_by_blackout(departure_date, return_date)

    for origin in origins:
        for destination in dest_list[:5]:  # Limit to 5 destinations
            if origin == destination:
                continue

            # Generate 1-2 mock flights per route
            for _ in range(random.randint(1, 2)):
                hour = random.randint(6, 20)
                minute = random.choice(['00', '15', '30', '45'])
                departure_time = f"{hour:02d}:{minute} {'AM' if hour < 12 else 'PM'}"
                duration_hours = random.randint(2, 6)
                duration_mins = random.choice([0, 15, 30, 45])

                flight = {
                    'origin': origin,
                    'destination': destination,
                    'departureDate': departure_date,
                    'departureTime': departure_time,
                    'arrivalDate': departure_date,
                    'arrivalTime': f"{(hour + duration_hours) % 24:02d}:{duration_mins:02d} {'AM' if (hour + duration_hours) < 12 else 'PM'}",
                    'duration': f"{duration_hours}h {duration_mins}m",
                    'stops': random.choice([0, 0, 0, 1]),  # Mostly nonstop
                    'price': round(random.uniform(29, 199), 2),
                    'seatsRemaining': random.randint(1, 15),
                    'airline': 'Frontier Airlines',
                    'flightNumber': f"F9-{random.randint(1000, 9999)}",
                    'gowild_eligible': random.choice([True, True, False]),  # Mostly eligible
                    'blackout_dates': blackout_info
                }
                flights.append(flight)

    return flights

@app.route('/api/search', methods=['POST'])
def search_flights():
    """
    Search for flights based on provided parameters

    Expected JSON body:
    {
        "origins": ["DEN", "LAX"],
        "destinations": ["MCO", "MIA"],
        "tripType": "round-trip",
        "departureDate": "2025-06-15",
        "returnDate": "2025-06-20"
    }
    """
    try:
        data = request.get_json()

        origins = data.get('origins', [])
        destinations = data.get('destinations', [])
        trip_type = data.get('tripType', 'round-trip')
        departure_date = data.get('departureDate')
        return_date = data.get('returnDate')

        # Validate required fields
        if not origins or not destinations or not departure_date:
            return jsonify({
                'error': 'Missing required fields: origins, destinations, departureDate'
            }), 400

        # Check cache first
        cache_key = get_cache_key(origins, destinations, departure_date, return_date, trip_type)

        if cache_key in cache and is_cache_valid(cache[cache_key]):
            print(f"Returning cached results for {cache_key}")
            return jsonify({
                'flights': cache[cache_key]['flights'],
                'cached': True,
                'searchParams': data,
                'devMode': DEV_MODE
            })

        # Use mock data for flight search (Amadeus doesn't have Frontier F9)
        # Real-time flight status is available via /api/realtime/* endpoints
        print(f"[MOCK DATA] Generating flights for {origins} -> {destinations}")
        flights = generate_mock_flights(origins, destinations, departure_date, return_date)
        data_source = 'mock'

        # Cache the results
        cache[cache_key] = {
            'flights': flights,
            'timestamp': datetime.now().isoformat()
        }

        response_data = {
            'flights': flights,
            'cached': False,
            'searchParams': data,
            'count': len(flights),
            'devMode': DEV_MODE,
            'data_source': data_source,
            'realtime_available': realtime_service.is_configured(),
            'realtime_hint': 'Use /api/realtime/route for live flight status'
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error in search_flights: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/search/stream', methods=['POST'])
def search_flights_stream():
    """
    Search for flights with streaming results (Server-Sent Events)

    Returns results as they become available for each route
    """
    try:
        data = request.get_json()

        origins = data.get('origins', [])
        destinations = data.get('destinations', [])
        trip_type = data.get('tripType', 'round-trip')
        departure_date = data.get('departureDate')
        return_date = data.get('returnDate')

        # Validate required fields
        if not origins or not destinations or not departure_date:
            return jsonify({
                'error': 'Missing required fields: origins, destinations, departureDate'
            }), 400

        def generate():
            """Generator function for streaming results"""
            all_flights = []

            # Generate mock data and stream it
            dest_list = destinations if destinations != ['ANY'] else ['MCO', 'LAS', 'MIA', 'PHX', 'ATL']

            # Check for blackout dates
            blackout_info = GoWildBlackoutDates.is_flight_affected_by_blackout(departure_date, return_date)

            for origin in origins:
                for destination in dest_list[:5]:
                    if origin == destination:
                        continue

                    # Generate mock flights for this route
                    route_flights = []
                    for _ in range(random.randint(1, 3)):
                        hour = random.randint(6, 20)
                        minute = random.choice(['00', '15', '30', '45'])
                        flight = {
                            'origin': origin,
                            'destination': destination,
                            'departure_date': departure_date,
                            'departure_time': f"{hour:02d}:{minute}",
                            'arrival_time': f"{(hour+3):02d}:{minute}",
                            'duration': '3h 0m',
                            'price': round(random.uniform(29, 199), 2),
                            'currency': 'USD',
                            'airline': 'Frontier Airlines',
                            'flight_number': f"F9-{random.randint(1000, 9999)}",
                            'stops': 0,
                            'aircraft': '320',
                            'booking_class': 'Economy',
                            'gowild_eligible': random.choice([True, True, False]),
                            'blackout_dates': blackout_info
                        }
                        route_flights.append(flight)

                    all_flights.extend(route_flights)

                    # Stream this route's results
                    event_data = {
                        'route': f"{origin}->{destination}",
                        'flights': route_flights,
                        'count': len(route_flights)
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    time.sleep(0.1)  # Simulate API delay

            # Send completion event
            completion_data = {
                'complete': True,
                'total_flights': len(all_flights),
                'realtime_available': realtime_service.is_configured()
            }
            yield f"data: {json.dumps(completion_data)}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        print(f"Error in search_flights_stream: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/destinations', methods=['GET'])
def get_destinations():
    """Get list of all Frontier destinations"""
    # Scraper not available - return empty list or implement Amadeus destination search
    destinations = []
    return jsonify({
        'destinations': destinations,
        'count': len(destinations),
        'message': 'Destination search not implemented with Amadeus API'
    })

@app.route('/api/trip-planner', methods=['POST'])
def trip_planner():
    """
    Plan trips based on desired trip length

    Finds flight combinations that best match the requested trip duration
    """
    try:
        data = request.get_json()

        origins = data.get('origins', [])
        destinations = data.get('destinations', [])
        departure_date = data.get('departureDate')
        trip_length = data.get('tripLength')
        trip_length_unit = data.get('tripLengthUnit', 'days')
        nonstop_preferred = data.get('nonstopPreferred', False)
        max_trip_duration = data.get('maxTripDuration')
        max_trip_duration_unit = data.get('maxTripDurationUnit', 'days')

        # Validate required fields
        if not origins or not destinations or not departure_date or not trip_length:
            return jsonify({
                'error': 'Missing required fields: origins, destinations, departureDate, tripLength'
            }), 400

        # Calculate return date window (search several days to find options)
        depart_dt = datetime.strptime(departure_date, '%Y-%m-%d')
        trip_hours = float(trip_length) * (24 if trip_length_unit == 'days' else 1)

        all_flights = []
        optimal_trips = []
        days_searched = 0
        max_days_to_search = 30

        # Keep searching future dates until we find results or hit 30 days
        while len(optimal_trips) == 0 and days_searched < max_days_to_search:
            current_depart_dt = depart_dt + timedelta(days=days_searched)
            current_departure_date = current_depart_dt.strftime('%Y-%m-%d')
            target_return = current_depart_dt + timedelta(hours=trip_hours)

            # Search a range of dates around target (±2 days for flexibility)
            return_dates = [
                (target_return - timedelta(days=2)).strftime('%Y-%m-%d'),
                (target_return - timedelta(days=1)).strftime('%Y-%m-%d'),
                target_return.strftime('%Y-%m-%d'),
                (target_return + timedelta(days=1)).strftime('%Y-%m-%d'),
                (target_return + timedelta(days=2)).strftime('%Y-%m-%d'),
            ]

            print(f"Searching departure date: {current_departure_date} (day {days_searched + 1}/{max_days_to_search})")

            # Search for round trips with each return date
            batch_flights = []
            for return_date in return_dates:
                if AMADEUS_ENABLED:
                    flights = amadeus_client.search_flights(
                        origins=origins,
                        destinations=destinations,
                        departure_date=current_departure_date,
                        return_date=return_date,
                        adults=1
                    )
                    batch_flights.extend(flights)

            all_flights.extend(batch_flights)

            # Use trip planner to find optimal combinations
            optimal_trips = find_optimal_trips(
                all_flights,
                trip_length=trip_length,
                trip_length_unit=trip_length_unit,
                nonstop_preferred=nonstop_preferred,
                max_duration=max_trip_duration,
                max_duration_unit=max_trip_duration_unit
            )

            if len(optimal_trips) > 0:
                print(f"Found {len(optimal_trips)} matching trips on day {days_searched + 1}")
                break

            days_searched += 1

        # Return top 20 best matches
        return jsonify({
            'flights': optimal_trips[:20],
            'total_options': len(optimal_trips),
            'target_duration': f"{trip_length} {trip_length_unit}",
            'days_searched': days_searched + 1,
            'earliest_departure': (depart_dt + timedelta(days=days_searched)).strftime('%Y-%m-%d') if optimal_trips else None
        })

    except Exception as e:
        print(f"Error in trip_planner: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the flight cache"""
    global cache
    cache = {}
    return jsonify({'message': 'Cache cleared successfully'})

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    valid_entries = sum(1 for entry in cache.values() if is_cache_valid(entry))
    return jsonify({
        'total_entries': len(cache),
        'valid_entries': valid_entries,
        'expired_entries': len(cache) - valid_entries
    })

@app.route('/api/debug/search', methods=['POST'])
def debug_search():
    """
    Debug endpoint to diagnose search issues
    Returns detailed information about the search process
    """
    try:
        data = request.get_json()
        debug_info = {
            'request_received': data,
            'amadeus_enabled': AMADEUS_ENABLED,
            'dev_mode': DEV_MODE,
            'amadeus_client_status': 'initialized' if amadeus_client else 'not initialized',
            'steps': [],
            'flights': [],
            'errors': []
        }
        
        origins = data.get('origins', [])
        destinations = data.get('destinations', [])
        departure_date = data.get('departureDate')
        return_date = data.get('returnDate')
        
        debug_info['steps'].append(f"Searching {origins} -> {destinations} on {departure_date}")
        
        if AMADEUS_ENABLED and amadeus_client:
            try:
                # Try searching without Frontier filter to see all available flights
                from amadeus import ResponseError
                for origin in origins[:1]:  # Just test first origin
                    for destination in destinations[:1]:  # Just test first destination
                        try:
                            # Search without airline filter first
                            response = amadeus_client.amadeus.shopping.flight_offers_search.get(
                                originLocationCode=origin,
                                destinationLocationCode=destination,
                                departureDate=departure_date,
                                adults=1,
                                max=5  # Just get a few for debug
                            )
                            debug_info['steps'].append(f"Raw Amadeus response: {len(response.data)} offers found (no filter)")
                            
                            # Show what airlines are available
                            airlines_found = set()
                            for offer in response.data:
                                for itin in offer.get('itineraries', []):
                                    for seg in itin.get('segments', []):
                                        airlines_found.add(seg.get('carrierCode'))
                            debug_info['airlines_available'] = list(airlines_found)
                            
                            # Now try with Frontier filter
                            try:
                                response_f9 = amadeus_client.amadeus.shopping.flight_offers_search.get(
                                    originLocationCode=origin,
                                    destinationLocationCode=destination,
                                    departureDate=departure_date,
                                    adults=1,
                                    max=5,
                                    includedAirlineCodes='F9'
                                )
                                debug_info['steps'].append(f"Frontier-filtered results: {len(response_f9.data)} offers")
                                debug_info['frontier_flights_raw'] = len(response_f9.data)
                            except ResponseError as e:
                                debug_info['errors'].append(f"Frontier filter error: {str(e)}")
                            
                        except ResponseError as e:
                            debug_info['errors'].append(f"Amadeus API error for {origin}->{destination}: {str(e)}")
            except Exception as e:
                debug_info['errors'].append(f"Amadeus search exception: {str(e)}")
        else:
            debug_info['steps'].append("Amadeus not enabled, would use mock data in dev mode")
            
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# =============================================================================
# REAL-TIME FLIGHT STATUS ENDPOINTS (powered by AviationStack)
# =============================================================================

@app.route('/api/realtime/flight/<flight_number>', methods=['GET'])
def get_realtime_flight_status(flight_number):
    """
    Get real-time status for a specific flight
    
    Example: GET /api/realtime/flight/F9777
    
    Returns live flight info including:
    - Flight status (scheduled, active, landed, cancelled)
    - Actual vs scheduled departure/arrival times
    - Delays
    - Gate and terminal information
    """
    if not realtime_service.is_configured():
        return jsonify({
            'error': 'Real-time flight service not configured',
            'hint': 'Set AVIATIONSTACK_API_KEY in environment'
        }), 503
    
    result = realtime_service.get_flight_status(flight_number)
    
    if 'error' in result:
        return jsonify(result), 404
    
    return jsonify(result)

@app.route('/api/realtime/route', methods=['GET'])
def get_realtime_route_flights():
    """
    Get all real-time flights for a route
    
    Query params:
    - origin: Origin airport code (required)
    - destination: Destination airport code (required)
    - airline: Airline code (default: F9)
    
    Example: GET /api/realtime/route?origin=DEN&destination=LAS&airline=F9
    """
    if not realtime_service.is_configured():
        return jsonify({
            'error': 'Real-time flight service not configured',
            'hint': 'Set AVIATIONSTACK_API_KEY in environment'
        }), 503
    
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    airline = request.args.get('airline', 'F9')
    
    if not origin or not destination:
        return jsonify({
            'error': 'Missing required parameters: origin, destination'
        }), 400
    
    result = realtime_service.get_route_flights(origin.upper(), destination.upper(), airline.upper())
    
    if 'error' in result and not result.get('flights'):
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/api/realtime/departures/<airport_code>', methods=['GET'])
def get_realtime_departures(airport_code):
    """
    Get all real-time departures from an airport
    
    Query params:
    - airline: Airline code (default: F9)
    
    Example: GET /api/realtime/departures/DEN?airline=F9
    """
    if not realtime_service.is_configured():
        return jsonify({
            'error': 'Real-time flight service not configured',
            'hint': 'Set AVIATIONSTACK_API_KEY in environment'
        }), 503
    
    airline = request.args.get('airline', 'F9')
    
    result = realtime_service.get_departures(airport_code.upper(), airline.upper())
    
    if 'error' in result and not result.get('flights'):
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/api/realtime/arrivals/<airport_code>', methods=['GET'])
def get_realtime_arrivals(airport_code):
    """
    Get all real-time arrivals to an airport
    
    Query params:
    - airline: Airline code (default: F9)
    
    Example: GET /api/realtime/arrivals/LAS?airline=F9
    """
    if not realtime_service.is_configured():
        return jsonify({
            'error': 'Real-time flight service not configured',
            'hint': 'Set AVIATIONSTACK_API_KEY in environment'
        }), 503
    
    airline = request.args.get('airline', 'F9')
    
    result = realtime_service.get_arrivals(airport_code.upper(), airline.upper())
    
    if 'error' in result and not result.get('flights'):
        return jsonify(result), 500
    
    return jsonify(result)

# =============================================================================
# BLACKOUT DATES ENDPOINTS
# =============================================================================

@app.route('/api/blackout-dates', methods=['GET'])
def get_blackout_dates():
    """Get current blackout dates"""
    try:
        blackout_data = get_blackout_data()
        return jsonify(blackout_data)
    except Exception as e:
        print(f"Error fetching blackout dates: {e}")
        return jsonify({
            'error': str(e),
            'blackout_periods': {'2026': [], '2027': [], '2028': []},
            'last_updated': datetime.now().isoformat()
        }), 500

@app.route('/api/blackout-dates/refresh', methods=['POST'])
def refresh_blackout_dates():
    """Manually refresh blackout dates from Frontier website"""
    try:
        from blackout_updater import fetch_blackout_dates
        data = fetch_blackout_dates()
        return jsonify({
            'message': 'Blackout dates refreshed successfully',
            'data': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run on port 5001 locally (5000 is often used by macOS AirPlay)
    # In production, PORT is set by the hosting platform
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(debug=debug, port=port, host='0.0.0.0')
