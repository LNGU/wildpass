"""
Kiwi.com Tequila API Integration for Flight Search

Replaces Amadeus API which does not include low-cost carriers like Frontier Airlines (F9).
Kiwi.com Tequila API aggregates flights from all airlines including LCCs.

API Documentation: https://tequila.kiwi.com/portal/docs
Free tier: ~3,000 searches/month via partner program
"""
import os
import requests
from datetime import datetime
from gowild_blackout import GoWildBlackoutDates


class KiwiFlightSearch:
    """Flight search using Kiwi.com Tequila API — includes Frontier Airlines (F9)"""

    BASE_URL = "https://api.tequila.kiwi.com"

    # IATA code to city name mapping for Frontier destinations
    AIRPORT_CITIES = {
        'DEN': 'Denver', 'LAS': 'Las Vegas', 'PHX': 'Phoenix', 'LAX': 'Los Angeles',
        'SFO': 'San Francisco', 'SEA': 'Seattle', 'ORD': 'Chicago', 'ATL': 'Atlanta',
        'MCO': 'Orlando', 'MIA': 'Miami', 'DFW': 'Dallas', 'MSP': 'Minneapolis',
        'DTW': 'Detroit', 'PHL': 'Philadelphia', 'CLT': 'Charlotte', 'IAH': 'Houston',
        'BOS': 'Boston', 'JFK': 'New York JFK', 'EWR': 'Newark', 'LGA': 'New York LGA',
        'FLL': 'Fort Lauderdale', 'TPA': 'Tampa', 'SAN': 'San Diego', 'AUS': 'Austin',
        'RDU': 'Raleigh-Durham', 'CLE': 'Cleveland', 'STL': 'St. Louis',
        'SLC': 'Salt Lake City', 'BNA': 'Nashville', 'IND': 'Indianapolis',
        'CUN': 'Cancun', 'SJU': 'San Juan', 'PUJ': 'Punta Cana',
        'CVG': 'Cincinnati', 'MCI': 'Kansas City', 'SAT': 'San Antonio',
        'MDW': 'Chicago Midway', 'BWI': 'Baltimore', 'ISP': 'Islip',
        'PIT': 'Pittsburgh', 'RSW': 'Fort Myers', 'PDX': 'Portland',
        'OAK': 'Oakland', 'ONT': 'Ontario', 'SMF': 'Sacramento',
    }

    # Airline code to name mapping
    AIRLINE_NAMES = {
        'F9': 'Frontier Airlines', 'AA': 'American Airlines', 'UA': 'United Airlines',
        'DL': 'Delta Air Lines', 'WN': 'Southwest Airlines', 'B6': 'JetBlue Airways',
        'NK': 'Spirit Airlines', 'AS': 'Alaska Airlines', 'G4': 'Allegiant Air',
        'SY': 'Sun Country Airlines', 'HA': 'Hawaiian Airlines',
    }

    def __init__(self, api_key=None):
        """
        Initialize Kiwi Tequila API client.

        Args:
            api_key: Tequila API key. Falls back to KIWI_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get('KIWI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Kiwi API key not provided. Set KIWI_API_KEY environment variable "
                "or pass api_key to constructor. Sign up at https://tequila.kiwi.com"
            )
        self.headers = {
            'apikey': self.api_key,
            'Content-Type': 'application/json',
        }
        print("🔗 Kiwi Tequila API initialized")

    def search_flights(self, origins, destinations, departure_date, return_date=None,
                       adults=1, airline_filter='F9', callback=None):
        """
        Search for flights using Kiwi Tequila API.

        Args:
            origins: List of origin airport IATA codes
            destinations: List of destination airport IATA codes (or ['ANY'])
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Optional return date for round-trip
            adults: Number of adult passengers
            airline_filter: Airline IATA code to filter (default 'F9' for Frontier)
            callback: Optional callback(route, flights) called per route with results

        Returns:
            List of flight dictionaries in the app's standard format
        """
        all_flights = []

        # Handle "ANY" destination — search popular Frontier destinations
        if destinations == ['ANY']:
            destinations = self._get_popular_destinations(origins)

        for origin in origins:
            for destination in destinations:
                if origin == destination:
                    continue

                try:
                    flights = self._search_route(
                        origin, destination, departure_date,
                        return_date=return_date, adults=adults,
                        airline_filter=airline_filter
                    )
                    all_flights.extend(flights)

                    if callback and flights:
                        callback(f"{origin}->{destination}", flights)

                except Exception as e:
                    print(f"Error searching {origin} -> {destination}: {e}")
                    continue

        return all_flights

    def _search_route(self, origin, destination, departure_date,
                      return_date=None, adults=1, airline_filter='F9'):
        """
        Search a single origin-destination route.

        Returns:
            List of flight dictionaries
        """
        # Tequila uses DD/MM/YYYY format
        dep_formatted = self._format_date_for_api(departure_date)

        params = {
            'fly_from': origin,
            'fly_to': destination,
            'date_from': dep_formatted,
            'date_to': dep_formatted,
            'adults': adults,
            'curr': 'USD',
            'locale': 'en',
            'limit': 50,
            'sort': 'price',
            'vehicle_type': 'aircraft',
        }

        # Filter by airline if specified
        if airline_filter:
            params['select_airlines'] = airline_filter
            params['select_airlines_exclude'] = 'false'

        # Round-trip
        if return_date:
            ret_formatted = self._format_date_for_api(return_date)
            params['return_from'] = ret_formatted
            params['return_to'] = ret_formatted
            params['flight_type'] = 'round'
        else:
            params['flight_type'] = 'oneway'

        response = requests.get(
            f"{self.BASE_URL}/v2/search",
            headers=self.headers,
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            error_detail = response.text[:200] if response.text else 'No details'
            print(f"⚠️  Kiwi API error ({response.status_code}) for {origin}->{destination}: {error_detail}")
            return []

        data = response.json()
        results = data.get('data', [])

        print(f"✈️  Found {len(results)} {airline_filter or 'all'} flights for {origin}->{destination}")

        return [self._convert_to_app_format(result, origin, destination) for result in results]

    def _convert_to_app_format(self, kiwi_flight, origin, destination):
        """
        Convert a Kiwi Tequila flight result to the app's standard format.

        Kiwi response fields used:
            - price, bags_price, availability
            - route[] (segments with departure/arrival times, airline, flight_no, etc.)
            - duration.departure, duration.return, duration.total
            - deep_link (booking URL)
        """
        route_segments = kiwi_flight.get('route', [])
        is_round_trip = kiwi_flight.get('return', 0) > 0

        # Separate outbound and return segments
        outbound_segments = [s for s in route_segments if s.get('return') == 0]
        return_segments = [s for s in route_segments if s.get('return') == 1]

        # Parse outbound
        outbound = self._parse_segments(outbound_segments, origin, destination)

        # Check blackout dates
        dep_date = outbound['departure_date']
        ret_date = None
        if is_round_trip and return_segments:
            ret_date = self._parse_segments(return_segments, destination, origin)['departure_date']

        blackout_info = GoWildBlackoutDates.is_flight_affected_by_blackout(dep_date, ret_date)

        # Price
        price = kiwi_flight.get('price', 0)

        # GoWild eligibility — Frontier economy flights
        first_carrier = outbound_segments[0].get('airline', '') if outbound_segments else ''
        gowild_eligible = self._is_gowild_eligible(first_carrier, price, kiwi_flight)

        # Seats remaining
        seats = kiwi_flight.get('availability', {}).get('seats', None)

        flight = {
            **outbound,
            'price': round(price, 2),
            'currency': 'USD',
            'is_round_trip': is_round_trip,
            'seats_remaining': seats,
            'gowild_eligible': gowild_eligible,
            'blackout_dates': blackout_info,
            'booking_link': kiwi_flight.get('deep_link'),
        }

        if is_round_trip and return_segments:
            return_flight = self._parse_segments(return_segments, destination, origin)
            flight['return_flight'] = return_flight
            flight['total_price'] = round(price, 2)

        return flight

    def _parse_segments(self, segments, origin, destination):
        """Parse a list of route segments (one direction of travel)."""
        if not segments:
            return {
                'origin': origin, 'destination': destination,
                'departure_date': '', 'departure_time': '',
                'arrival_date': '', 'arrival_time': '',
                'duration': 'N/A', 'airline': 'Unknown',
                'flight_number': 'N/A', 'stops': 0, 'aircraft': 'N/A',
            }

        first = segments[0]
        last = segments[-1]

        # Parse UTC timestamps from Kiwi
        dep_utc = datetime.utcfromtimestamp(first.get('dTimeUTC', first.get('dTime', 0)))
        arr_utc = datetime.utcfromtimestamp(last.get('aTimeUTC', last.get('aTime', 0)))

        # Use local times if available
        dep_local = datetime.utcfromtimestamp(first.get('dTime', first.get('dTimeUTC', 0)))
        arr_local = datetime.utcfromtimestamp(last.get('aTime', last.get('aTimeUTC', 0)))

        # Duration (seconds to hours/minutes)
        total_seconds = last.get('aTimeUTC', 0) - first.get('dTimeUTC', 0)
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)

        # Airline info
        airline_code = first.get('airline', 'F9')
        airline_name = self.AIRLINE_NAMES.get(airline_code, airline_code)
        flight_number = f"{airline_code}{first.get('flight_no', '')}"

        # Aircraft
        aircraft = first.get('equipment', 'N/A')
        # Kiwi sometimes returns None for equipment
        if not aircraft:
            aircraft = 'N/A'

        return {
            'origin': first.get('flyFrom', origin),
            'destination': last.get('flyTo', destination),
            'departure_date': dep_local.strftime('%Y-%m-%d'),
            'departure_time': dep_local.strftime('%I:%M %p'),
            'arrival_date': arr_local.strftime('%Y-%m-%d'),
            'arrival_time': arr_local.strftime('%I:%M %p'),
            'duration': f"{hours}h {minutes}m" if hours else f"{minutes}m",
            'airline': airline_name,
            'flight_number': flight_number,
            'stops': max(0, len(segments) - 1),
            'aircraft': aircraft,
        }

    def _is_gowild_eligible(self, carrier_code, price, kiwi_flight):
        """
        Determine if a flight is eligible for GoWild pass redemption.

        GoWild eligibility:
        - Must be Frontier Airlines (F9)
        - Must be Economy fare (lowest tier)
        - GoWild seats are last-available economy seats
        """
        if carrier_code != 'F9':
            return False

        # Check fare category if available
        fare_category = kiwi_flight.get('fare', {}).get('category', '')
        if fare_category and fare_category.lower() in ('economy', 'basic', 'economy_basic'):
            return True

        # Heuristic: low-price Frontier flights are likely GoWild eligible
        # GoWild pass typically covers flights that would cost ~$19-$99
        if price <= 99:
            return True

        # Check seat availability — GoWild uses last-available seats
        seats = kiwi_flight.get('availability', {}).get('seats', None)
        if seats is not None and seats <= 5:
            return True

        return False

    def _format_date_for_api(self, date_str):
        """Convert YYYY-MM-DD to DD/MM/YYYY for Kiwi API."""
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            return date_str

    def _get_popular_destinations(self, origins):
        """Get popular Frontier destinations for 'ANY' search."""
        popular = [
            'MCO', 'LAS', 'MIA', 'PHX', 'ATL', 'LAX', 'DFW', 'ORD', 'DEN',
            'SEA', 'SFO', 'FLL', 'TPA', 'SAN', 'AUS', 'CLE', 'BNA', 'SLC',
        ]
        return [d for d in popular if d not in origins][:12]

    def get_frontier_destinations(self):
        """
        Get list of airports served by Frontier Airlines.

        Uses Kiwi's locations API to find Frontier routes.

        Returns:
            List of destination dictionaries with code, city, country.
        """
        try:
            # Use routes endpoint to find Frontier destinations
            params = {
                'term': 'Frontier',
                'location_types': 'airport',
                'limit': 100,
                'active_only': 'true',
            }
            response = requests.get(
                f"{self.BASE_URL}/locations/query",
                headers=self.headers,
                params=params,
                timeout=15
            )

            if response.status_code != 200:
                return self._get_hardcoded_destinations()

            data = response.json()
            locations = data.get('locations', [])

            destinations = []
            for loc in locations:
                code = loc.get('code', '')
                if code and len(code) == 3:
                    destinations.append({
                        'code': code,
                        'city': loc.get('city', {}).get('name', self.AIRPORT_CITIES.get(code, code)),
                        'country': loc.get('city', {}).get('country', {}).get('name', 'US'),
                    })

            return destinations if destinations else self._get_hardcoded_destinations()

        except Exception as e:
            print(f"Error fetching Frontier destinations: {e}")
            return self._get_hardcoded_destinations()

    def _get_hardcoded_destinations(self):
        """Fallback: hardcoded list of known Frontier Airlines destinations."""
        return [
            {'code': code, 'city': city, 'country': 'US'}
            for code, city in self.AIRPORT_CITIES.items()
        ]
