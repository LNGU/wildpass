"""
SerpApi Google Flights Integration for Flight Search

Replaces Kiwi Tequila API. Google Flights includes ALL airlines including
low-cost carriers like Frontier Airlines (F9), Spirit (NK), Allegiant (G4).

API Documentation: https://serpapi.com/google-flights-api
Free tier: 250 searches/month
"""
import os
import requests
from datetime import datetime
from gowild_blackout import GoWildBlackoutDates


class SerpApiFlightSearch:
    """Flight search using SerpApi Google Flights — includes Frontier Airlines (F9)"""

    BASE_URL = "https://serpapi.com/search.json"

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
        Initialize SerpApi Google Flights client.

        Args:
            api_key: SerpApi key. Falls back to SERPAPI_KEY env var.
        """
        self.api_key = api_key or os.environ.get('SERPAPI_KEY')
        if not self.api_key:
            raise ValueError(
                "SerpApi key not provided. Set SERPAPI_KEY environment variable "
                "or pass api_key to constructor. Sign up at https://serpapi.com"
            )
        print("SerpApi Google Flights initialized")

    def search_flights(self, origins, destinations, departure_date, return_date=None,
                       adults=1, airline_filter='F9', callback=None):
        """
        Search for flights using SerpApi Google Flights.

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

        # Handle "ANY" destination
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
        Search a single origin-destination route via SerpApi Google Flights.

        Returns:
            List of flight dictionaries
        """
        params = {
            'engine': 'google_flights',
            'departure_id': origin,
            'arrival_id': destination,
            'outbound_date': departure_date,  # YYYY-MM-DD
            'currency': 'USD',
            'hl': 'en',
            'adults': adults,
            'api_key': self.api_key,
        }

        # Round-trip vs one-way
        if return_date:
            params['type'] = '1'  # 1 = round trip
            params['return_date'] = return_date
        else:
            params['type'] = '2'  # 2 = one way

        # Filter to specific airline
        if airline_filter:
            params['include_airlines'] = airline_filter

        response = requests.get(self.BASE_URL, params=params, timeout=30)

        if response.status_code != 200:
            error_detail = response.text[:200] if response.text else 'No details'
            print(f"SerpApi error ({response.status_code}) for {origin}->{destination}: {error_detail}")
            return []

        data = response.json()

        # Check for API errors
        if 'error' in data:
            print(f"SerpApi error for {origin}->{destination}: {data['error']}")
            return []

        # Google Flights returns best_flights and other_flights
        best = data.get('best_flights', [])
        other = data.get('other_flights', [])
        all_results = best + other

        print(f"Found {len(all_results)} {airline_filter or 'all'} flights for {origin}->{destination}")

        flights = []
        for result in all_results:
            try:
                converted = self._convert_to_app_format(
                    result, origin, destination, departure_date, return_date
                )
                if converted:
                    flights.append(converted)
            except Exception as e:
                print(f"Error converting flight result: {e}")
                continue

        return flights

    def _convert_to_app_format(self, gf_result, origin, destination,
                               departure_date, return_date=None):
        """
        Convert a Google Flights result to the app's standard format.

        Google Flights response structure:
            - flights[] — array of flight segments (legs)
              - departure_airport.id, departure_airport.time
              - arrival_airport.id, arrival_airport.time
              - airline, airline_logo, flight_number
              - duration, airplane, travel_class, legroom
              - often_delayed_by_over_30_min (bool)
            - layovers[] — layover info between segments
            - total_duration — total minutes
            - price — integer USD
            - type — e.g. "Round trip"
            - carbon_emissions
        """
        segments = gf_result.get('flights', [])
        if not segments:
            return None

        first_seg = segments[0]
        last_seg = segments[-1]

        # Departure info (from first segment)
        dep_airport = first_seg.get('departure_airport', {})
        dep_time_str = dep_airport.get('time', '')  # "2026-03-15 06:30"

        # Arrival info (from last segment)
        arr_airport = last_seg.get('arrival_airport', {})
        arr_time_str = arr_airport.get('time', '')

        # Parse date/time
        dep_date, dep_time = self._parse_datetime(dep_time_str, departure_date)
        arr_date, arr_time = self._parse_datetime(arr_time_str, departure_date)

        # Duration
        total_minutes = gf_result.get('total_duration', 0)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"

        # Airline info
        airline_name = first_seg.get('airline', 'Unknown')
        flight_number = first_seg.get('flight_number', 'N/A')

        # Aircraft
        aircraft = first_seg.get('airplane', 'N/A')
        if not aircraft:
            aircraft = 'N/A'

        # Price
        price = gf_result.get('price', 0)

        # Stops
        stops = max(0, len(segments) - 1)

        # Blackout check
        ret_date_for_blackout = return_date
        blackout_info = GoWildBlackoutDates.is_flight_affected_by_blackout(
            dep_date, ret_date_for_blackout
        )

        # GoWild eligibility
        is_frontier = 'Frontier' in airline_name or flight_number.startswith('F9')
        gowild_eligible = self._is_gowild_eligible(is_frontier, price, gf_result)

        # Travel class / legroom
        travel_class = first_seg.get('travel_class', 'Economy')
        legroom = first_seg.get('legroom', '')

        # Carbon emissions
        carbon = gf_result.get('carbon_emissions', {})
        carbon_kg = carbon.get('this_flight', 0)

        # Build booking link (Google Flights URL)
        booking_token = gf_result.get('booking_token', '')

        flight = {
            'origin': dep_airport.get('id', origin),
            'destination': arr_airport.get('id', destination),
            'departure_date': dep_date,
            'departure_time': dep_time,
            'arrival_date': arr_date,
            'arrival_time': arr_time,
            'duration': duration_str,
            'stops': stops,
            'price': price,
            'currency': 'USD',
            'airline': airline_name,
            'flight_number': flight_number,
            'aircraft': aircraft,
            'travel_class': travel_class,
            'legroom': legroom,
            'is_round_trip': return_date is not None,
            'seats_remaining': None,  # Google Flights doesn't expose seat count
            'gowild_eligible': gowild_eligible,
            'blackout_dates': blackout_info,
            'carbon_emissions_kg': carbon_kg // 1000 if carbon_kg > 1000 else carbon_kg,
            'booking_token': booking_token,
        }

        # Layover info
        layovers = gf_result.get('layovers', [])
        if layovers:
            flight['layovers'] = [
                {
                    'airport': lo.get('name', ''),
                    'airport_code': lo.get('id', ''),
                    'duration_minutes': lo.get('duration', 0),
                    'overnight': lo.get('overnight', False),
                }
                for lo in layovers
            ]

        return flight

    def _parse_datetime(self, datetime_str, fallback_date):
        """
        Parse Google Flights datetime string 'YYYY-MM-DD HH:MM' into
        separate date and formatted time strings.

        Returns:
            (date_str, time_str) — ('2026-03-15', '06:30 AM')
        """
        if not datetime_str:
            return fallback_date, 'N/A'

        try:
            # Google Flights format: "2026-03-15 06:30"
            dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%I:%M %p')
            return date_str, time_str
        except ValueError:
            # Try alternate formats
            try:
                # Sometimes just time: "6:30 AM"
                if ' ' not in datetime_str or '-' not in datetime_str:
                    return fallback_date, datetime_str
                # ISO format
                dt = datetime.fromisoformat(datetime_str)
                return dt.strftime('%Y-%m-%d'), dt.strftime('%I:%M %p')
            except (ValueError, TypeError):
                return fallback_date, datetime_str

    def _is_gowild_eligible(self, is_frontier, price, gf_result):
        """
        Determine if a flight is eligible for GoWild pass redemption.

        GoWild eligibility:
        - Must be Frontier Airlines (F9)
        - Must be Economy fare (lowest tier)
        - GoWild seats are last-available economy seats
        """
        if not is_frontier:
            return False

        # Check travel class
        segments = gf_result.get('flights', [])
        if segments:
            travel_class = segments[0].get('travel_class', '').lower()
            if travel_class and travel_class in ('economy', 'basic economy'):
                return True

        # Heuristic: low-price Frontier flights are likely GoWild eligible
        if price and price <= 99:
            return True

        return False

    def _get_popular_destinations(self, origins):
        """Get popular Frontier destinations for 'ANY' search."""
        popular = [
            'MCO', 'LAS', 'MIA', 'PHX', 'ATL', 'LAX', 'DFW', 'ORD', 'DEN',
            'SEA', 'SFO', 'FLL', 'TPA', 'SAN', 'AUS', 'CLE', 'BNA', 'SLC',
        ]
        return [d for d in popular if d not in origins][:12]

    def get_frontier_destinations(self):
        """
        Return list of airports served by Frontier Airlines.

        Since Google Flights doesn't have a destinations API,
        we return the hardcoded list of known Frontier hubs/destinations.

        Returns:
            List of destination dictionaries with code, city, country.
        """
        return [
            {'code': code, 'city': city, 'country': 'US'}
            for code, city in self.AIRPORT_CITIES.items()
        ]
