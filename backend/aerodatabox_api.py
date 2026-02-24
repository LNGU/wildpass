"""
AeroDataBox API Integration for Real-Time Flight Status

Replaces AviationStack API which has HTTP-only on free tier (mixed content issues).
AeroDataBox via RapidAPI provides HTTPS on free tier with 300 requests/month.

API Documentation: https://rapidapi.com/aedbx-aedbx/api/aerodatabox
Free tier: 300 requests/month, HTTPS included
"""
import os
import random
import requests
from datetime import datetime, timedelta


# =============================================================================
# Mock data generators (fallback when API is unavailable)
# =============================================================================

MOCK_DESTINATIONS = {
    'DEN': [
        ('LAS', 'Las Vegas'), ('PHX', 'Phoenix'), ('LAX', 'Los Angeles'),
        ('SFO', 'San Francisco'), ('SEA', 'Seattle'), ('ORD', 'Chicago'),
        ('ATL', 'Atlanta'), ('MCO', 'Orlando'), ('MIA', 'Miami'), ('DFW', 'Dallas')
    ],
    'LAS': [
        ('DEN', 'Denver'), ('LAX', 'Los Angeles'), ('SFO', 'San Francisco'),
        ('PHX', 'Phoenix'), ('SEA', 'Seattle'), ('ORD', 'Chicago')
    ],
    'PHX': [
        ('DEN', 'Denver'), ('LAS', 'Las Vegas'), ('LAX', 'Los Angeles'),
        ('SFO', 'San Francisco'), ('ORD', 'Chicago'), ('ATL', 'Atlanta')
    ],
}

DEFAULT_DESTINATIONS = [
    ('DEN', 'Denver'), ('LAS', 'Las Vegas'), ('PHX', 'Phoenix'),
    ('LAX', 'Los Angeles'), ('ORD', 'Chicago'), ('ATL', 'Atlanta')
]

AIRPORT_NAMES = {
    'DEN': 'Denver International Airport',
    'LAS': 'Harry Reid International Airport',
    'PHX': 'Phoenix Sky Harbor International Airport',
    'LAX': 'Los Angeles International Airport',
    'SFO': 'San Francisco International Airport',
    'SEA': 'Seattle-Tacoma International Airport',
    'ORD': "O'Hare International Airport",
    'ATL': 'Hartsfield-Jackson Atlanta International Airport',
    'MCO': 'Orlando International Airport',
    'MIA': 'Miami International Airport',
    'DFW': 'Dallas/Fort Worth International Airport',
    'FLL': 'Fort Lauderdale-Hollywood International Airport',
    'TPA': 'Tampa International Airport',
    'SAN': 'San Diego International Airport',
}


def _generate_mock_flights(airport_code, flight_type='departures', count=8):
    """Generate realistic mock flight data for fallback."""
    destinations = MOCK_DESTINATIONS.get(airport_code, DEFAULT_DESTINATIONS)
    destinations = [(code, name) for code, name in destinations if code != airport_code]

    flights = []
    statuses = ['scheduled', 'scheduled', 'scheduled', 'active', 'landed', 'delayed']
    base_time = datetime.now()

    for i in range(min(count, len(destinations) * 2)):
        dest_code, dest_name = destinations[i % len(destinations)]
        flight_num = f"F9{random.randint(100, 2999)}"
        status = random.choice(statuses)

        dep_offset = timedelta(minutes=random.randint(-60, 180))
        scheduled_dep = base_time + dep_offset
        flight_duration = timedelta(hours=random.randint(1, 4), minutes=random.randint(0, 59))
        scheduled_arr = scheduled_dep + flight_duration

        delay_minutes = random.choice([0, 0, 0, 15, 30, 45]) if status == 'delayed' else 0

        flight = {
            'flight_number': flight_num,
            'origin': airport_code if flight_type == 'departures' else dest_code,
            'origin_city': 'Denver' if airport_code == 'DEN' else airport_code,
            'destination': dest_code if flight_type == 'departures' else airport_code,
            'destination_city': dest_name if flight_type == 'departures' else (
                'Denver' if airport_code == 'DEN' else airport_code),
            'status': status,
            'status_display': _get_status_display(status),
            'scheduled_time': scheduled_dep.strftime('%I:%M %p'),
            'scheduled': {'local': scheduled_dep.strftime('%I:%M %p')},
            'actual': {
                'local': (scheduled_dep + timedelta(minutes=delay_minutes)).strftime('%I:%M %p')
            } if status in ['active', 'landed', 'delayed'] else None,
            'delay': f"+{delay_minutes} min" if delay_minutes > 0 else 'On time',
            'terminal': random.choice(['A', 'B', 'C']),
            'gate': f"{random.choice(['A', 'B', 'C'])}{random.randint(1, 50)}",
            'aircraft': random.choice(['A320', 'A321', 'A319']),
        }
        flights.append(flight)

    flights.sort(key=lambda x: x.get('scheduled_time', ''))
    return flights


def _generate_mock_single_flight(flight_number):
    """Generate mock data for a single flight lookup."""
    now = datetime.now()
    dep_time = now - timedelta(hours=random.randint(0, 2))
    arr_time = dep_time + timedelta(hours=random.randint(2, 5))

    origins = [('DEN', 'Denver'), ('LAS', 'Las Vegas'), ('PHX', 'Phoenix')]
    dests = [('LAX', 'Los Angeles'), ('ORD', 'Chicago'), ('ATL', 'Atlanta')]

    origin = random.choice(origins)
    dest = random.choice(dests)
    status = random.choice(['scheduled', 'active', 'landed'])

    return {
        'flight_number': flight_number.upper(),
        'origin': origin[0],
        'origin_city': origin[1],
        'destination': dest[0],
        'destination_city': dest[1],
        'status': status,
        'status_display': _get_status_display(status),
        'departure': {
            'airport': AIRPORT_NAMES.get(origin[0], origin[1]),
            'airport_code': origin[0],
            'scheduled': {'local': dep_time.strftime('%I:%M %p')},
            'actual': {'local': dep_time.strftime('%I:%M %p')} if status != 'scheduled' else None,
            'terminal': 'A',
            'gate': 'A23',
        },
        'arrival': {
            'airport': AIRPORT_NAMES.get(dest[0], dest[1]),
            'airport_code': dest[0],
            'scheduled': {'local': arr_time.strftime('%I:%M %p')},
            'actual': {'local': arr_time.strftime('%I:%M %p')} if status == 'landed' else None,
            'terminal': 'B',
            'gate': 'B15',
        },
        'delay': 'On time',
    }


def _get_status_display(status):
    """Get display-friendly status string with emoji."""
    status_map = {
        'scheduled': '🕐 Scheduled',
        'active': '✈️ In Flight',
        'landed': '✅ Landed',
        'cancelled': '❌ Cancelled',
        'incident': '⚠️ Incident',
        'diverted': '↪️ Diverted',
        'delayed': '⏰ Delayed',
        'unknown': '❓ Unknown',
    }
    return status_map.get(status, status_map['unknown'])


# Common ICAO 3-letter to IATA 2-letter airline code mapping
ICAO_TO_IATA = {
    'AAL': 'AA', 'DAL': 'DL', 'UAL': 'UA', 'SWA': 'WN', 'FFT': 'F9',
    'NKS': 'NK', 'JBU': 'B6', 'ASA': 'AS', 'AAY': 'G4', 'HAL': 'HA',
    'SCX': 'SY', 'BAW': 'BA', 'AFR': 'AF', 'DLH': 'LH', 'ACA': 'AC',
    'KLM': 'KL', 'EIN': 'EI', 'RYR': 'FR', 'EZY': 'U2', 'VOI': 'VY',
    'ANA': 'NH', 'JAL': 'JL', 'CPA': 'CX', 'QFA': 'QF', 'UAE': 'EK',
    'ETH': 'ET', 'THY': 'TK', 'SIA': 'SQ', 'CSN': 'CZ', 'CCA': 'CA',
}


def _icao_to_iata(flight_num):
    """Convert ICAO airline prefix to IATA if matched (e.g., AAL3075 → AA3075)."""
    import re
    match = re.match(r'^([A-Z]{3})(\d+)$', flight_num)
    if match:
        icao_code = match.group(1)
        number = match.group(2)
        iata = ICAO_TO_IATA.get(icao_code)
        if iata:
            return f"{iata}{number}"
    return flight_num


# =============================================================================
# AeroDataBox Real-Time Flight Service
# =============================================================================

class RealTimeFlightService:
    """
    Real-time flight status using AeroDataBox API (via RapidAPI).

    Replaces AviationStack (HTTP-only on free tier).
    AeroDataBox: 300 req/month free, HTTPS included, covers all US airlines.
    """

    RAPIDAPI_HOST = "aerodatabox.p.rapidapi.com"
    BASE_URL = f"https://{RAPIDAPI_HOST}"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('AERODATABOX_API_KEY')
        self.headers = {
            'X-RapidAPI-Key': self.api_key or '',
            'X-RapidAPI-Host': self.RAPIDAPI_HOST,
        }

    def is_configured(self):
        return bool(self.api_key)

    # -----------------------------------------------------------------
    # Public API methods
    # -----------------------------------------------------------------

    def get_flight_status(self, flight_number):
        """
        Get real-time status for a specific flight number.

        AeroDataBox endpoint: GET /flights/number/{flightNumber}/{date}

        Args:
            flight_number: e.g. 'F9777', 'AA3075', 'AAL3075' (ICAO ok, converted to IATA)

        Returns:
            Flight status dict or mock data
        """
        flight_num = flight_number.replace('-', '').replace(' ', '').upper()

        # Convert 3-letter ICAO airline prefix to 2-letter IATA
        flight_num = _icao_to_iata(flight_num)

        if not self.api_key:
            print("⚠️ AeroDataBox API key not configured — using mock data")
            return _generate_mock_single_flight(flight_num)

        try:
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"{self.BASE_URL}/flights/number/{flight_num}/{today}"

            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code == 404:
                return {'error': f'No flight found for {flight_number}'}
            if response.status_code != 200:
                print(f"⚠️ AeroDataBox API error ({response.status_code}) — using mock data")
                return _generate_mock_single_flight(flight_num)

            flights = response.json()
            if not flights or (isinstance(flights, list) and len(flights) == 0):
                return {'error': f'No flight found for {flight_number}'}

            # AeroDataBox returns a list; take the first entry
            flight_data = flights[0] if isinstance(flights, list) else flights
            return self._format_aerodatabox_flight(flight_data, flight_num)

        except Exception as e:
            print(f"⚠️ AeroDataBox exception: {e} — using mock data")
            return _generate_mock_single_flight(flight_num)

    def get_route_flights(self, origin, destination, airline_code='F9'):
        """
        Get all flights for a specific route today.

        Uses departures endpoint filtered by destination.
        """
        def _mock():
            mock_flights = [
                _generate_mock_single_flight(f"F9{random.randint(100, 2999)}")
                for _ in range(random.randint(1, 3))
            ]
            return {
                'route': f"{origin} → {destination}",
                'airline': airline_code,
                'count': len(mock_flights),
                'flights': mock_flights,
                'last_updated': datetime.now().isoformat(),
                'mock_data': True,
            }

        if not self.api_key:
            print("⚠️ AeroDataBox API key not configured — using mock data")
            return _mock()

        try:
            # Get departures from origin, then filter by destination
            now = datetime.now()
            from_local = now.replace(hour=0, minute=0).strftime('%Y-%m-%dT%H:%M')
            to_local = now.replace(hour=23, minute=59).strftime('%Y-%m-%dT%H:%M')

            url = f"{self.BASE_URL}/flights/airports/iata/{origin}/{from_local}/{to_local}"
            params = {
                'direction': 'Departure',
                'withCancelled': 'true',
                'withCodeshared': 'false',
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=15)

            if response.status_code != 200:
                print(f"⚠️ AeroDataBox error ({response.status_code}) — using mock data")
                return _mock()

            data = response.json()
            departures = data.get('departures', [])

            # Filter by destination and airline
            route_flights = []
            for flight in departures:
                arr_code = flight.get('arrival', {}).get('airport', {}).get('iata', '')
                airline = flight.get('airline', {}).get('iata', '')
                if arr_code == destination and (not airline_code or airline == airline_code):
                    route_flights.append(self._format_aerodatabox_departure(flight))

            return {
                'route': f"{origin} → {destination}",
                'airline': airline_code,
                'count': len(route_flights),
                'flights': route_flights,
                'last_updated': datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"⚠️ AeroDataBox exception: {e} — using mock data")
            return _mock()

    def get_departures(self, airport_code, airline_code='F9'):
        """
        Get all departing flights from an airport today.

        AeroDataBox endpoint: GET /flights/airports/iata/{code}/{fromLocal}/{toLocal}
        """
        def _mock():
            mock_flights = _generate_mock_flights(airport_code, 'departures')
            return {
                'airport': airport_code,
                'airline': airline_code,
                'type': 'departures',
                'count': len(mock_flights),
                'flights': mock_flights,
                'last_updated': datetime.now().isoformat(),
                'mock_data': True,
            }

        if not self.api_key:
            print("⚠️ AeroDataBox API key not configured — using mock data")
            return _mock()

        try:
            now = datetime.now()
            from_local = now.replace(hour=0, minute=0).strftime('%Y-%m-%dT%H:%M')
            to_local = now.replace(hour=23, minute=59).strftime('%Y-%m-%dT%H:%M')

            url = f"{self.BASE_URL}/flights/airports/iata/{airport_code}/{from_local}/{to_local}"
            params = {
                'direction': 'Departure',
                'withCancelled': 'true',
                'withCodeshared': 'false',
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=15)

            if response.status_code != 200:
                print(f"⚠️ AeroDataBox error ({response.status_code}) — using mock data")
                return _mock()

            data = response.json()
            departures = data.get('departures', [])

            # Filter by airline if specified
            formatted = []
            for flight in departures:
                airline = flight.get('airline', {}).get('iata', '')
                if not airline_code or airline == airline_code:
                    formatted.append(self._format_aerodatabox_departure(flight))

            # Sort by scheduled time
            formatted.sort(key=lambda x: x.get('scheduled_time', '') or '')

            return {
                'airport': airport_code,
                'airline': airline_code,
                'type': 'departures',
                'count': len(formatted),
                'flights': formatted,
                'last_updated': datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"⚠️ AeroDataBox exception: {e} — using mock data")
            return _mock()

    def get_arrivals(self, airport_code, airline_code='F9'):
        """
        Get all arriving flights to an airport today.

        AeroDataBox endpoint: GET /flights/airports/iata/{code}/{fromLocal}/{toLocal}
        """
        def _mock():
            mock_flights = _generate_mock_flights(airport_code, 'arrivals')
            return {
                'airport': airport_code,
                'airline': airline_code,
                'type': 'arrivals',
                'count': len(mock_flights),
                'flights': mock_flights,
                'last_updated': datetime.now().isoformat(),
                'mock_data': True,
            }

        if not self.api_key:
            print("⚠️ AeroDataBox API key not configured — using mock data")
            return _mock()

        try:
            now = datetime.now()
            from_local = now.replace(hour=0, minute=0).strftime('%Y-%m-%dT%H:%M')
            to_local = now.replace(hour=23, minute=59).strftime('%Y-%m-%dT%H:%M')

            url = f"{self.BASE_URL}/flights/airports/iata/{airport_code}/{from_local}/{to_local}"
            params = {
                'direction': 'Arrival',
                'withCancelled': 'true',
                'withCodeshared': 'false',
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=15)

            if response.status_code != 200:
                print(f"⚠️ AeroDataBox error ({response.status_code}) — using mock data")
                return _mock()

            data = response.json()
            arrivals = data.get('arrivals', [])

            formatted = []
            for flight in arrivals:
                airline = flight.get('airline', {}).get('iata', '')
                if not airline_code or airline == airline_code:
                    formatted.append(self._format_aerodatabox_arrival(flight))

            formatted.sort(key=lambda x: x.get('scheduled_time', '') or '')

            return {
                'airport': airport_code,
                'airline': airline_code,
                'type': 'arrivals',
                'count': len(formatted),
                'flights': formatted,
                'last_updated': datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"⚠️ AeroDataBox exception: {e} — using mock data")
            return _mock()

    # -----------------------------------------------------------------
    # Response format converters
    # -----------------------------------------------------------------

    def _format_aerodatabox_flight(self, flight_data, flight_number=None):
        """
        Format AeroDataBox single-flight response to app format.

        AeroDataBox response shape (GET /flights/number/{num}/{date}):
        {
            "departure": {"airport": {"iata": "DEN", "name": "..."}, "scheduledTimeLocal": "...", "terminal": "A", "gate": "A23", ...},
            "arrival": {"airport": {"iata": "LAX", "name": "..."}, ...},
            "number": "F9 777",
            "status": "Scheduled",
            "aircraft": {"model": "Airbus A320"}
        }
        """
        dep = flight_data.get('departure', {})
        arr = flight_data.get('arrival', {})
        dep_airport = dep.get('airport', {})
        arr_airport = arr.get('airport', {})

        # Flight number
        fn = flight_data.get('number', flight_number or 'N/A').replace(' ', '')

        # Status mapping
        raw_status = (flight_data.get('status', 'Unknown') or 'Unknown').lower()
        status = self._map_status(raw_status)

        # Times
        dep_scheduled = self._parse_time(dep.get('scheduledTimeLocal'))
        dep_actual = self._parse_time(dep.get('actualTimeLocal') or dep.get('estimatedTimeLocal'))
        arr_scheduled = self._parse_time(arr.get('scheduledTimeLocal'))
        arr_actual = self._parse_time(arr.get('actualTimeLocal') or arr.get('estimatedTimeLocal'))

        # Delay
        dep_delay = dep.get('delay', 0) or 0  # in minutes from AeroDataBox
        # AeroDataBox returns delay as "PT15M" ISO 8601 duration sometimes
        if isinstance(dep_delay, str):
            dep_delay = self._parse_iso_duration_minutes(dep_delay)

        return {
            'flight_number': fn,
            'flight_icao': flight_data.get('callSign'),
            'airline': {
                'name': flight_data.get('airline', {}).get('name', 'Frontier Airlines'),
                'iata': flight_data.get('airline', {}).get('iata', 'F9'),
            },
            'status': status,
            'status_display': _get_status_display(status),
            'departure': {
                'airport': dep_airport.get('name', dep_airport.get('iata', 'N/A')),
                'airport_code': dep_airport.get('iata', 'N/A'),
                'terminal': dep.get('terminal'),
                'gate': dep.get('gate'),
                'scheduled': dep_scheduled,
                'estimated': self._parse_time(dep.get('estimatedTimeLocal')),
                'actual': self._parse_time(dep.get('actualTimeLocal')),
                'delay_minutes': dep_delay if dep_delay else None,
                'delay_display': f"+{dep_delay} min" if dep_delay and dep_delay > 0 else None,
            },
            'arrival': {
                'airport': arr_airport.get('name', arr_airport.get('iata', 'N/A')),
                'airport_code': arr_airport.get('iata', 'N/A'),
                'terminal': arr.get('terminal'),
                'gate': arr.get('gate'),
                'baggage': arr.get('baggageBelt'),
                'scheduled': arr_scheduled,
                'estimated': self._parse_time(arr.get('estimatedTimeLocal')),
                'actual': self._parse_time(arr.get('actualTimeLocal')),
                'delay_minutes': None,
                'delay_display': None,
            },
            'live': None,  # AeroDataBox doesn't provide live ADS-B tracking on free tier
            'flight_date': datetime.now().strftime('%Y-%m-%d'),
        }

    def _format_aerodatabox_departure(self, flight_data):
        """Format an AeroDataBox departures-list item for the flight board."""
        dep = flight_data.get('departure', {})
        arr = flight_data.get('arrival', {})
        dep_airport = dep.get('airport', {})
        arr_airport = arr.get('airport', {})

        fn = (flight_data.get('number', 'N/A') or 'N/A').replace(' ', '')
        raw_status = (flight_data.get('status', 'Unknown') or 'Unknown').lower()
        status = self._map_status(raw_status)

        dep_scheduled = self._parse_time(dep.get('scheduledTimeLocal'))
        dep_actual = self._parse_time(dep.get('actualTimeLocal'))

        dep_delay = dep.get('delay', 0) or 0
        if isinstance(dep_delay, str):
            dep_delay = self._parse_iso_duration_minutes(dep_delay)

        return {
            'flight_number': fn,
            'origin': dep_airport.get('iata', 'N/A'),
            'origin_city': dep_airport.get('name', dep_airport.get('iata', '')),
            'destination': arr_airport.get('iata', 'N/A'),
            'destination_city': arr_airport.get('name', arr_airport.get('iata', '')),
            'status': status,
            'status_display': _get_status_display(status),
            'scheduled_time': dep_scheduled.get('time', '') if dep_scheduled else '',
            'scheduled': dep_scheduled,
            'actual': dep_actual,
            'delay': f"+{dep_delay} min" if dep_delay and dep_delay > 0 else 'On time',
            'terminal': dep.get('terminal'),
            'gate': dep.get('gate'),
            'aircraft': (flight_data.get('aircraft', {}) or {}).get('model', 'N/A'),
        }

    def _format_aerodatabox_arrival(self, flight_data):
        """Format an AeroDataBox arrivals-list item for the flight board."""
        dep = flight_data.get('departure', {})
        arr = flight_data.get('arrival', {})
        dep_airport = dep.get('airport', {})
        arr_airport = arr.get('airport', {})

        fn = (flight_data.get('number', 'N/A') or 'N/A').replace(' ', '')
        raw_status = (flight_data.get('status', 'Unknown') or 'Unknown').lower()
        status = self._map_status(raw_status)

        arr_scheduled = self._parse_time(arr.get('scheduledTimeLocal'))
        arr_actual = self._parse_time(arr.get('actualTimeLocal'))

        return {
            'flight_number': fn,
            'origin': dep_airport.get('iata', 'N/A'),
            'origin_city': dep_airport.get('name', dep_airport.get('iata', '')),
            'destination': arr_airport.get('iata', 'N/A'),
            'destination_city': arr_airport.get('name', arr_airport.get('iata', '')),
            'status': status,
            'status_display': _get_status_display(status),
            'scheduled_time': arr_scheduled.get('time', '') if arr_scheduled else '',
            'scheduled': arr_scheduled,
            'actual': arr_actual,
            'delay': 'On time',
            'terminal': arr.get('terminal'),
            'gate': arr.get('gate'),
            'aircraft': (flight_data.get('aircraft', {}) or {}).get('model', 'N/A'),
        }

    # -----------------------------------------------------------------
    # Utility methods
    # -----------------------------------------------------------------

    def _parse_time(self, time_str):
        """Parse AeroDataBox local time string (ISO 8601) to app format."""
        if not time_str:
            return None
        try:
            # AeroDataBox format: "2026-02-23 14:30+01:00" or "2026-02-23T14:30:00"
            clean = time_str.replace(' ', 'T')
            # Handle timezone offset
            if '+' in clean and 'T' in clean:
                dt_part = clean.split('+')[0]
            elif clean.endswith('Z'):
                dt_part = clean[:-1]
            else:
                dt_part = clean

            dt = datetime.fromisoformat(dt_part)
            return {
                'iso': time_str,
                'time': dt.strftime('%I:%M %p'),
                'date': dt.strftime('%Y-%m-%d'),
                'full': dt.strftime('%b %d, %I:%M %p'),
            }
        except (ValueError, TypeError):
            return {'iso': time_str, 'time': time_str, 'date': None, 'full': time_str}

    def _map_status(self, raw_status):
        """Map AeroDataBox status strings to our standard status codes."""
        raw = raw_status.lower().strip()
        mapping = {
            'scheduled': 'scheduled',
            'expected': 'scheduled',
            'departed': 'active',
            'en route': 'active',
            'airborne': 'active',
            'approaching': 'active',
            'arrived': 'landed',
            'landed': 'landed',
            'cancelled': 'cancelled',
            'canceled': 'cancelled',
            'diverted': 'diverted',
            'delayed': 'delayed',
            'unknown': 'unknown',
        }
        return mapping.get(raw, 'unknown')

    def _parse_iso_duration_minutes(self, duration_str):
        """Parse ISO 8601 duration like 'PT15M' to minutes."""
        if not duration_str or not isinstance(duration_str, str):
            return 0
        try:
            duration_str = duration_str.upper().replace('PT', '')
            minutes = 0
            if 'H' in duration_str:
                parts = duration_str.split('H')
                minutes += int(parts[0]) * 60
                duration_str = parts[1] if len(parts) > 1 else ''
            if 'M' in duration_str:
                minutes += int(duration_str.replace('M', ''))
            return minutes
        except (ValueError, IndexError):
            return 0
