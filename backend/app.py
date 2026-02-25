from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_caching import Cache
from serpapi_flights import SerpApiFlightSearch
from aerodatabox_api import RealTimeFlightService
from trip_planner import find_optimal_trips
from gowild_blackout import GoWildBlackoutDates
from blackout_updater import update_if_needed, get_blackout_data
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import os
import random
import time
import threading
import urllib.request
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# =============================================================================
# KEEP-ALIVE SELF-PING (prevents Render free-tier from sleeping after 15 min)
# =============================================================================
def _keep_alive_ping():
    """Background thread that pings the public Render URL every 5 minutes.
    Uses the external URL so Render counts it as real inbound traffic."""
    public_url = os.environ.get('RENDER_EXTERNAL_URL')  # Render sets this automatically
    if not public_url:
        print("⏸️  RENDER_EXTERNAL_URL not set — keep-alive self-ping disabled (local dev)")
        return
    health_url = f"{public_url}/health"
    print(f"💓 Keep-alive thread started — pinging {health_url} every 5 min")
    while True:
        time.sleep(300)  # 5 minutes
        try:
            req = urllib.request.Request(health_url, method='GET')
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"💓 Keep-alive ping: {resp.status}")
        except Exception as e:
            print(f"💓 Keep-alive ping failed: {e}")

# Start the keep-alive thread (daemon so it dies with the process)
_ping_thread = threading.Thread(target=_keep_alive_ping, daemon=True)
_ping_thread.start()

# File-based cache that survives restarts
cache_config = {
    'CACHE_TYPE': 'FileSystemCache',
    'CACHE_DIR': os.path.join(os.path.dirname(os.path.abspath(__file__)), '.flask_cache'),
    'CACHE_DEFAULT_TIMEOUT': 3600,  # 1 hour
}
app.config.from_mapping(cache_config)
flask_cache = Cache(app)

# Lazy initialization flag
_startup_done = False
_startup_lock = threading.Lock()

# Root route for health checks (Render, etc.)
@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'service': 'WildPass Flight Search API',
        'version': '2.1.0'  # SerpApi Google Flights + AeroDataBox APIs
    })

# Health check at /health for Render
@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

def _lazy_init():
    """Run startup tasks lazily on first request (in a background thread)."""
    global _startup_done
    if _startup_done:
        return
    with _startup_lock:
        if _startup_done:
            return
        _startup_done = True
        threading.Thread(target=update_if_needed, daemon=True).start()
        print("🚀 WildPass Backend ready (blackout update running in background)")

@app.before_request
def ensure_initialized():
    _lazy_init()

# Initialize SerpApi Google Flights client (flight search — includes Frontier F9)
flight_client = None
FLIGHT_API_ENABLED = False
try:
    flight_client = SerpApiFlightSearch(
        api_key=os.environ.get('SERPAPI_KEY')
    )
    FLIGHT_API_ENABLED = True
except ValueError as e:
    print(f"Warning: SerpApi not configured: {e}")

# Initialize Real-Time Flight Service (AeroDataBox via RapidAPI)
realtime_service = RealTimeFlightService()

# Development mode — returns mock data when API keys are not configured
DEV_MODE = os.environ.get('DEV_MODE', 'false' if FLIGHT_API_ENABLED else 'true').lower() == 'true'

def get_cache_key(origins, destinations, departure_date, return_date, trip_type):
    """Generate a unique cache key for the search parameters"""
    return f"flights_{','.join(sorted(origins))}_{','.join(sorted(destinations))}_{departure_date}_{return_date}_{trip_type}"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Flight Search API is running',
        'flight_api_enabled': FLIGHT_API_ENABLED,
        'dev_mode': DEV_MODE,
        'realtime_service_enabled': realtime_service.is_configured(),
        'note': 'Flight search: SerpApi Google Flights | Real-time status: AeroDataBox'
    })

@app.route('/api/debug/api-test', methods=['GET'])
def api_test():
    """
    Test SerpApi Google Flights connection directly.
    Searches DEN->LAX for Frontier flights 30 days out.
    """
    if not FLIGHT_API_ENABLED or not flight_client:
        return jsonify({
            'status': 'error',
            'message': 'SerpApi not configured',
            'flight_api_enabled': FLIGHT_API_ENABLED
        }), 503

    try:
        test_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        flights = flight_client.search_flights(
            origins=['DEN'],
            destinations=['LAX'],
            departure_date=test_date,
            adults=1,
            airline_filter='F9'
        )

        return jsonify({
            'status': 'ok',
            'message': 'SerpApi Google Flights is working',
            'test_date': test_date,
            'route': 'DEN -> LAX',
            'flights_found': len(flights),
            'sample': flights[0] if flights else None
        })

    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

def generate_mock_flights(origins, destinations, departure_date, return_date=None):
    """Generate mock flight data for development/testing (snake_case format)"""
    flights = []

    dest_list = destinations if destinations != ['ANY'] else ['MCO', 'LAS', 'MIA', 'PHX', 'ATL']
    blackout_info = GoWildBlackoutDates.is_flight_affected_by_blackout(departure_date, return_date)

    for origin in origins:
        for destination in dest_list[:5]:
            if origin == destination:
                continue

            for _ in range(random.randint(1, 2)):
                hour = random.randint(6, 20)
                minute = random.choice(['00', '15', '30', '45'])
                departure_time = f"{hour:02d}:{minute} {'AM' if hour < 12 else 'PM'}"
                duration_hours = random.randint(2, 6)
                duration_mins = random.choice([0, 15, 30, 45])

                flight = {
                    'origin': origin,
                    'destination': destination,
                    'departure_date': departure_date,
                    'departure_time': departure_time,
                    'arrival_date': departure_date,
                    'arrival_time': f"{(hour + duration_hours) % 24:02d}:{duration_mins:02d} {'AM' if (hour + duration_hours) < 12 else 'PM'}",
                    'duration': f"{duration_hours}h {duration_mins}m",
                    'stops': random.choice([0, 0, 0, 1]),
                    'price': round(random.uniform(29, 199), 2),
                    'currency': 'USD',
                    'seats_remaining': random.randint(1, 15),
                    'airline': 'Frontier Airlines',
                    'flight_number': f"F9{random.randint(1000, 9999)}",
                    'aircraft': random.choice(['A320', 'A321', 'A319']),
                    'is_round_trip': False,
                    'gowild_eligible': random.choice([True, True, False]),
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
        cached_result = flask_cache.get(cache_key)

        if cached_result is not None:
            print(f"Returning cached results for {cache_key}")
            return jsonify({
                'flights': cached_result,
                'cached': True,
                'searchParams': data,
                'devMode': DEV_MODE
            })

        # Use SerpApi Google Flights if configured, otherwise fall back to mock data
        if FLIGHT_API_ENABLED and flight_client:
            print(f"[SERPAPI] Searching flights for {origins} -> {destinations}")
            flights = flight_client.search_flights(
                origins=origins,
                destinations=destinations,
                departure_date=departure_date,
                return_date=return_date if trip_type == 'round-trip' else None,
                adults=1,
                airline_filter='F9'
            )
            data_source = 'serpapi'

            # If no Frontier flights, try without airline filter
            if not flights:
                print(f"[SERPAPI] No F9 flights found, searching all airlines...")
                flights = flight_client.search_flights(
                    origins=origins,
                    destinations=destinations,
                    departure_date=departure_date,
                    return_date=return_date if trip_type == 'round-trip' else None,
                    adults=1,
                    airline_filter=None
                )
                data_source = 'serpapi_all_airlines'
        else:
            print(f"[MOCK DATA] Generating flights for {origins} -> {destinations}")
            flights = generate_mock_flights(origins, destinations, departure_date, return_date)
            data_source = 'mock'

        # Cache the results
        flask_cache.set(cache_key, flights)

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

            if FLIGHT_API_ENABLED and flight_client:
                # Use SerpApi — stream results per route
                dest_list = destinations
                if destinations == ['ANY']:
                    dest_list = flight_client._get_popular_destinations(origins)

                for origin in origins:
                    for destination in dest_list:
                        if origin == destination:
                            continue

                        try:
                            route_flights = flight_client._search_route(
                                origin, destination, departure_date,
                                return_date=return_date if trip_type == 'round-trip' else None,
                                adults=1,
                                airline_filter='F9'
                            )
                        except Exception as e:
                            print(f"Error searching {origin}->{destination}: {e}")
                            route_flights = []

                        if route_flights:
                            all_flights.extend(route_flights)
                            event_data = {
                                'route': f"{origin}->{destination}",
                                'flights': route_flights,
                                'count': len(route_flights)
                            }
                            yield f"data: {json.dumps(event_data)}\n\n"
                        time.sleep(0.1)
            else:
                # Fallback to mock data
                dest_list = destinations if destinations != ['ANY'] else ['MCO', 'LAS', 'MIA', 'PHX', 'ATL']
                blackout_info = GoWildBlackoutDates.is_flight_affected_by_blackout(departure_date, return_date)

                for origin in origins:
                    for destination in dest_list[:5]:
                        if origin == destination:
                            continue

                        route_flights = []
                        for _ in range(random.randint(1, 3)):
                            hour = random.randint(6, 20)
                            minute = random.choice(['00', '15', '30', '45'])
                            flight = {
                                'origin': origin,
                                'destination': destination,
                                'departure_date': departure_date,
                                'departure_time': f"{hour:02d}:{minute} {'AM' if hour < 12 else 'PM'}",
                                'arrival_date': departure_date,
                                'arrival_time': f"{(hour+3):02d}:{minute} {'AM' if (hour+3) < 12 else 'PM'}",
                                'duration': '3h 0m',
                                'price': round(random.uniform(29, 199), 2),
                                'currency': 'USD',
                                'airline': 'Frontier Airlines',
                                'flight_number': f"F9{random.randint(1000, 9999)}",
                                'stops': 0,
                                'aircraft': 'A320',
                                'is_round_trip': False,
                                'gowild_eligible': random.choice([True, True, False]),
                                'blackout_dates': blackout_info
                            }
                            route_flights.append(flight)

                        all_flights.extend(route_flights)
                        event_data = {
                            'route': f"{origin}->{destination}",
                            'flights': route_flights,
                            'count': len(route_flights)
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                        time.sleep(0.1)

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
    """Get list of all Frontier Airlines destinations"""
    if FLIGHT_API_ENABLED and flight_client:
        try:
            destinations = flight_client.get_frontier_destinations()
            return jsonify({
                'destinations': destinations,
                'count': len(destinations),
                'source': 'serpapi'
            })
        except Exception as e:
            print(f"Error fetching destinations: {e}")

    # Fallback: hardcoded Frontier destinations
    destinations = [
        {'code': code, 'city': city, 'country': 'US'}
        for code, city in SerpApiFlightSearch.AIRPORT_CITIES.items()
    ] if FLIGHT_API_ENABLED else [
        {'code': 'DEN', 'city': 'Denver', 'country': 'US'},
        {'code': 'LAS', 'city': 'Las Vegas', 'country': 'US'},
        {'code': 'PHX', 'city': 'Phoenix', 'country': 'US'},
        {'code': 'LAX', 'city': 'Los Angeles', 'country': 'US'},
        {'code': 'MCO', 'city': 'Orlando', 'country': 'US'},
        {'code': 'MIA', 'city': 'Miami', 'country': 'US'},
        {'code': 'ATL', 'city': 'Atlanta', 'country': 'US'},
        {'code': 'ORD', 'city': 'Chicago', 'country': 'US'},
        {'code': 'DFW', 'city': 'Dallas', 'country': 'US'},
        {'code': 'SEA', 'city': 'Seattle', 'country': 'US'},
    ]
    return jsonify({
        'destinations': destinations,
        'count': len(destinations),
        'source': 'hardcoded'
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
                if FLIGHT_API_ENABLED and flight_client:
                    flights = flight_client.search_flights(
                        origins=origins,
                        destinations=destinations,
                        departure_date=current_departure_date,
                        return_date=return_date,
                        adults=1,
                        airline_filter='F9'
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
    flask_cache.clear()
    return jsonify({'message': 'Cache cleared successfully'})

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    return jsonify({
        'cache_type': 'FileSystemCache',
        'message': 'File-based cache active — survives restarts'
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
            'flight_api_enabled': FLIGHT_API_ENABLED,
            'dev_mode': DEV_MODE,
            'flight_client_status': 'initialized' if flight_client else 'not initialized',
            'realtime_configured': realtime_service.is_configured(),
            'steps': [],
            'flights': [],
            'errors': []
        }

        origins = data.get('origins', [])
        destinations = data.get('destinations', [])
        departure_date = data.get('departureDate')

        debug_info['steps'].append(f"Searching {origins} -> {destinations} on {departure_date}")

        if FLIGHT_API_ENABLED and flight_client:
            try:
                for origin in origins[:1]:
                    for destination in destinations[:1]:
                        # Search Frontier flights
                        flights_f9 = flight_client.search_flights(
                            origins=[origin],
                            destinations=[destination],
                            departure_date=departure_date,
                            airline_filter='F9'
                        )
                        debug_info['steps'].append(f"Frontier (F9) results: {len(flights_f9)} flights")
                        debug_info['flights'] = flights_f9[:3]

                        # Also search all airlines for comparison
                        flights_all = flight_client.search_flights(
                            origins=[origin],
                            destinations=[destination],
                            departure_date=departure_date,
                            airline_filter=None
                        )
                        debug_info['steps'].append(f"All airlines results: {len(flights_all)} flights")
                        airlines = list(set(f.get('airline', 'Unknown') for f in flights_all))
                        debug_info['airlines_available'] = airlines

            except Exception as e:
                debug_info['errors'].append(f"SerpApi search exception: {str(e)}")
        else:
            debug_info['steps'].append("SerpApi not enabled, would use mock data")

        return jsonify(debug_info)

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# =============================================================================
# REAL-TIME FLIGHT STATUS ENDPOINTS (powered by AeroDataBox)
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
    
    Note: Falls back to mock data if AeroDataBox API is unavailable
    """
    result = realtime_service.get_flight_status(flight_number)
    
    if 'error' in result:
        return jsonify(result), 404
    
    return jsonify({'flight': result})

@app.route('/api/realtime/route', methods=['GET'])
def get_realtime_route_flights():
    """
    Get all real-time flights for a route
    
    Query params:
    - origin: Origin airport code (required)
    - destination: Destination airport code (required)
    - airline: Airline code (default: F9)
    
    Example: GET /api/realtime/route?origin=DEN&destination=LAS&airline=F9
    
    Note: Falls back to mock data if AeroDataBox API is unavailable
    """
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
    
    Note: Falls back to mock data if AeroDataBox API is unavailable
    """
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
    
    Note: Falls back to mock data if AeroDataBox API is unavailable
    """
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
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, port=port, host='0.0.0.0')
