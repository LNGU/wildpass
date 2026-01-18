"""
Flight API Fallback System
Uses multiple APIs to ensure Frontier (F9) flight data availability:
1. Amadeus (primary) - but doesn't support LCCs like Frontier
2. AviationStack (fallback) - 100 free requests/month
"""
import os
import requests
from datetime import datetime
from gowild_blackout import GoWildBlackoutDates


class AviationStackAPI:
    """AviationStack API client - https://aviationstack.com/"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('AVIATIONSTACK_API_KEY')
        self.base_url = "http://api.aviationstack.com/v1"
    
    def is_configured(self):
        return bool(self.api_key)
    
    def search_flights(self, origin, destination, date, airline_code='F9'):
        """
        Search for flights using AviationStack API
        
        Note: AviationStack free tier does NOT support flight_date parameter.
        It returns real-time/current day flights only.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code  
            date: Date in YYYY-MM-DD format (used for filtering results)
            airline_code: Airline IATA code (default: F9 for Frontier)
        
        Returns:
            List of flight dictionaries
        """
        if not self.api_key:
            print("⚠️  AviationStack API key not configured")
            return []
        
        try:
            # Note: flight_date is a PAID feature on AviationStack
            # Free tier only returns current/real-time flights
            params = {
                'access_key': self.api_key,
                'dep_iata': origin,
                'arr_iata': destination,
                'airline_iata': airline_code
                # 'flight_date': date  # Paid feature - not available on free tier
            }
            
            print(f"🔍 AviationStack: Searching {airline_code} flights {origin}->{destination}")
            
            response = requests.get(f"{self.base_url}/flights", params=params, timeout=30)
            data = response.json()
            
            if 'error' in data:
                error_msg = data['error'].get('message', str(data['error']))
                print(f"⚠️  AviationStack error: {error_msg}")
                return []
            
            raw_flights = data.get('data', [])
            print(f"📊 AviationStack raw response: {len(raw_flights)} flights found")
            
            flights = self._convert_to_app_format(raw_flights, origin, destination, date)
            print(f"✈️  AviationStack: Returning {len(flights)} {airline_code} flights for {origin}->{destination}")
            return flights
            
        except requests.exceptions.Timeout:
            print(f"⚠️  AviationStack timeout for {origin}->{destination}")
            return []
        except Exception as e:
            print(f"❌ AviationStack API error: {e}")
            return []
    
    def _convert_to_app_format(self, flights_data, origin, destination, target_date=None):
        """Convert AviationStack response to app format"""
        flights = []
        
        for flight in flights_data or []:
            try:
                departure = flight.get('departure', {})
                arrival = flight.get('arrival', {})
                airline = flight.get('airline', {})
                flight_info = flight.get('flight', {})
                
                dep_time = departure.get('scheduled', '')
                arr_time = arrival.get('scheduled', '')
                
                # Parse times
                dep_dt = None
                arr_dt = None
                if dep_time:
                    try:
                        dep_dt = datetime.fromisoformat(dep_time.replace('Z', '+00:00'))
                    except:
                        dep_dt = datetime.strptime(dep_time[:19], '%Y-%m-%dT%H:%M:%S')
                if arr_time:
                    try:
                        arr_dt = datetime.fromisoformat(arr_time.replace('Z', '+00:00'))
                    except:
                        arr_dt = datetime.strptime(arr_time[:19], '%Y-%m-%dT%H:%M:%S')
                
                # Calculate duration
                duration = ""
                if dep_dt and arr_dt:
                    diff = arr_dt - dep_dt
                    total_seconds = diff.total_seconds()
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    duration = f"{hours}h {minutes}m"
                
                # Check blackout dates
                departure_date = dep_dt.strftime('%Y-%m-%d') if dep_dt else None
                blackout_info = GoWildBlackoutDates.is_flight_affected_by_blackout(departure_date) if departure_date else {}
                
                flight_dict = {
                    'origin': origin,
                    'destination': destination,
                    'departure_time': dep_dt.strftime('%I:%M %p') if dep_dt else 'N/A',
                    'arrival_time': arr_dt.strftime('%I:%M %p') if arr_dt else 'N/A',
                    'departure_date': departure_date,
                    'arrival_date': arr_dt.strftime('%Y-%m-%d') if arr_dt else None,
                    'duration': duration,
                    'airline': airline.get('name', 'Frontier Airlines'),
                    'flight_number': flight_info.get('iata', 'N/A'),
                    'stops': 0,  # AviationStack returns direct flights only
                    'aircraft': flight.get('aircraft', {}).get('iata', 'N/A') if flight.get('aircraft') else 'N/A',
                    'booking_class': 'Economy',
                    'price': None,  # AviationStack doesn't provide pricing
                    'currency': 'USD',
                    'is_round_trip': False,
                    'gowild_eligible': True,  # Assume eligible, let blackout dates filter
                    'blackout_dates': blackout_info,
                    'data_source': 'aviationstack'
                }
                
                flights.append(flight_dict)
                
            except Exception as e:
                print(f"Error parsing AviationStack flight: {e}")
                continue
        
        return flights


class FlightSearchWithFallback:
    """
    Unified flight search with automatic fallback between APIs.
    
    Priority order:
    1. Amadeus API (if configured and returns results)
    2. AviationStack (fallback) - 100 free requests/month
    """
    
    def __init__(self, amadeus_client=None):
        """
        Initialize with optional existing Amadeus client
        
        Args:
            amadeus_client: Existing AmadeusFlightSearch instance (optional)
        """
        self.amadeus = amadeus_client
        self.aviationstack = AviationStackAPI()
        
        # Log initialization status
        print("🔄 Flight API Fallback System initialized:")
        print(f"   - Amadeus: {'✅ configured' if self.amadeus else '❌ not configured'}")
        print(f"   - AviationStack: {'✅ configured' if self.aviationstack.is_configured() else '❌ not configured'}")
    
    def search_flights(self, origins, destinations, departure_date, return_date=None, adults=1, callback=None):
        """
        Search for flights with automatic fallback.
        
        Args:
            origins: List of origin airport codes
            destinations: List of destination airport codes
            departure_date: Date in YYYY-MM-DD format
            return_date: Optional return date
            adults: Number of passengers
            callback: Optional callback function(route, flights) for streaming
        
        Returns:
            Tuple of (flights, data_source, fallback_notice)
        """
        all_flights = []
        data_source = None
        fallback_notice = None
        
        # Handle "ANY" destination
        if destinations == ['ANY']:
            destinations = self._get_popular_destinations(origins)
        
        for origin in origins:
            for destination in destinations:
                if origin == destination:
                    continue
                
                flights, source, notice = self._search_route_with_fallback(
                    origin, destination, departure_date, return_date, adults
                )
                
                if flights:
                    all_flights.extend(flights)
                    if not data_source:
                        data_source = source
                    if notice and not fallback_notice:
                        fallback_notice = notice
                    
                    # Call callback if provided
                    if callback and flights:
                        callback(f"{origin}->{destination}", flights)
        
        return all_flights, data_source, fallback_notice
    
    def _search_route_with_fallback(self, origin, destination, departure_date, return_date=None, adults=1):
        """Search a single route with fallback logic"""
        
        # 1. Try Amadeus first (for Frontier flights)
        if self.amadeus:
            try:
                flights = self.amadeus.search_flights(
                    [origin], [destination], departure_date, return_date, adults
                )
                if flights:
                    print(f"✅ Amadeus returned {len(flights)} flights for {origin}->{destination}")
                    return flights, 'amadeus', None
                print(f"⚠️  Amadeus returned 0 Frontier flights for {origin}->{destination}, trying AviationStack...")
            except Exception as e:
                print(f"⚠️  Amadeus failed for {origin}->{destination}: {e}")
        
        # 2. Try AviationStack as fallback
        if self.aviationstack.is_configured():
            flights = self.aviationstack.search_flights(origin, destination, departure_date)
            if flights:
                print(f"✅ AviationStack fallback returned {len(flights)} Frontier flights")
                return flights, 'aviationstack', 'Flight data from AviationStack (Amadeus did not have Frontier flights)'
        
        print(f"❌ No Frontier flights found from any API for {origin}->{destination}")
        return [], None, None
    
    def _get_popular_destinations(self, origins):
        """Get popular destinations for 'ANY' airport search"""
        popular = ['MCO', 'LAS', 'MIA', 'PHX', 'ATL', 'LAX', 'DFW', 'ORD', 'DEN', 'SEA']
        return [dest for dest in popular if dest not in origins][:10]
    
    def get_status(self):
        """Get status of all configured APIs"""
        return {
            'amadeus': bool(self.amadeus),
            'aviationstack': self.aviationstack.is_configured(),
            'fallback_available': self.aviationstack.is_configured()
        }
