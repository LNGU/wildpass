"""
FlightRadar24 API Integration for Real-Time Flight Status

Replaces AeroDataBox API. Uses the unofficial FlightRadar24 Python SDK.
No API key required. Provides real-time flight tracking data.

Package: FlightRadarAPI (pip install FlightRadarAPI)
"""
import re
import random
from datetime import datetime, timedelta
from FlightRadar24 import FlightRadar24API


# =============================================================================
# Mock data generators (fallback when API is unavailable)
# Copied from aerodatabox_api.py for compatibility
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

IATA_TO_ICAO = {
    'AA': 'AAL', 'DL': 'DAL', 'UA': 'UAL', 'WN': 'SWA', 'F9': 'FFT',
    'NK': 'NKS', 'B6': 'JBU', 'AS': 'ASA', 'G4': 'AAY', 'HA': 'HAL',
    'SY': 'SCX', 'BA': 'BAW', 'AF': 'AFR', 'LH': 'DLH', 'AC': 'ACA',
    'KL': 'KLM', 'EI': 'EIN', 'FR': 'RYR', 'U2': 'EZY', 'VY': 'VOI',
    'NH': 'ANA', 'JL': 'JAL', 'CX': 'CPA', 'QF': 'QFA', 'EK': 'UAE',
    'ET': 'ETH', 'TK': 'THY', 'SQ': 'SIA', 'CZ': 'CSN', 'CA': 'CCA',
}

ICAO_TO_IATA = {v: k for k, v in IATA_TO_ICAO.items()}


def _generate_mock_flights(airport_code, flight_type='departures', count=8):
    """Generate realistic mock flight data for fallback."""
    destinations = MOCK_DESTINATIONS.get(airport_code, DEFAULT_DESTINATIONS)
    destinations = [(code, name) for code, name in destinations if code != airport_code]

    flights = []
    statuses = ['scheduled', 'scheduled', 'scheduled', 'active', 'landed', 'delayed']
    base_time = datetime.now()

    for i in range(min(count, len(destinations) * 2)):
        dest_code, dest_name = destinations[i % len(destinations)]
        mock_airlines = [
            ('F9', 'Frontier Airlines'), ('UA', 'United Airlines'), ('AA', 'American Airlines'),
            ('DL', 'Delta Air Lines'), ('WN', 'Southwest Airlines'), ('NK', 'Spirit Airlines'),
            ('B6', 'JetBlue Airways'), ('AS', 'Alaska Airlines'),
        ]
        al_code, al_name = random.choice(mock_airlines)
        flight_num = f"{al_code}{random.randint(100, 2999)}"
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
            'airline': {'name': al_name, 'iata': al_code},
            'airline_name': al_name,
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


def _timestamp_to_time_str(ts):
    """Convert unix timestamp to formatted time string."""
    if not ts:
        return None
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime('%I:%M %p')
    except (ValueError, TypeError, OSError):
        return None


def _timestamp_to_time_dict(ts):
    """Convert unix timestamp to the time dict format used by the frontend."""
    if not ts:
        return None
    try:
        dt = datetime.fromtimestamp(ts)
        return {
            'iso': dt.isoformat(),
            'time': dt.strftime('%I:%M %p'),
            'date': dt.strftime('%Y-%m-%d'),
            'full': dt.strftime('%b %d, %I:%M %p'),
            'local': dt.strftime('%I:%M %p'),
        }
    except (ValueError, TypeError, OSError):
        return None


def _map_fr24_status(generic_status):
    """Map FlightRadar24 status to our standard status codes."""
    if not generic_status:
        return 'unknown'
    status_info = generic_status.get('status', {})
    text = (status_info.get('text', '') or '').lower().strip()
    diverted = status_info.get('diverted')
    if diverted:
        return 'diverted'
    mapping = {
        'scheduled': 'scheduled',
        'estimated': 'scheduled',
        'delayed': 'delayed',
        'departed': 'active',
        'en route': 'active',
        'airborne': 'active',
        'landed': 'landed',
        'arrived': 'landed',
        'canceled': 'cancelled',
        'cancelled': 'cancelled',
        'diverted': 'diverted',
    }
    return mapping.get(text, 'unknown')


# =============================================================================
# FlightRadar24 Real-Time Flight Service
# =============================================================================

class RealTimeFlightService:
    """
    Real-time flight status using FlightRadar24 unofficial API.
    No API key needed. Uses the FlightRadarAPI Python package.
    """

    def __init__(self, api_key=None):
        # api_key param kept for interface compatibility but not used
        try:
            self._api = FlightRadar24API()
        except Exception as e:
            print(f"⚠️ FlightRadar24API init failed: {e}")
            self._api = None

    def is_configured(self):
        """Always True — no API key needed for FlightRadar24."""
        return self._api is not None

    # -----------------------------------------------------------------
    # Public API methods
    # -----------------------------------------------------------------

    def get_flight_status(self, flight_number):
        """Get real-time status for a specific flight number."""
        flight_num = flight_number.replace('-', '').replace(' ', '').upper()

        # Convert 3-letter ICAO to 2-letter IATA
        match = re.match(r'^([A-Z]{3})(\d+)$', flight_num)
        if match:
            icao_code = match.group(1)
            number = match.group(2)
            iata = ICAO_TO_IATA.get(icao_code)
            if iata:
                flight_num = f"{iata}{number}"

        if not self._api:
            print("⚠️ FlightRadar24 API not available — using mock data")
            result = _generate_mock_single_flight(flight_num)
            result['mock_data'] = True
            return result

        try:
            # Extract airline code
            al_match = re.match(r'^([A-Z0-9]{2})(\d+)$', flight_num)
            if not al_match:
                return {'error': f'Invalid flight number format: {flight_number}', 'mock_data': False}

            airline_iata = al_match.group(1)
            airline_icao = IATA_TO_ICAO.get(airline_iata)

            # Try to find the flight among live flights
            if airline_icao:
                try:
                    live_flights = self._api.get_flights(airline=airline_icao)
                    for f in live_flights:
                        if f.number and f.number.replace(' ', '') == flight_num:
                            self._api.get_flight_details(f)
                            return self._format_live_flight(f, flight_num)
                except Exception as e:
                    print(f"⚠️ FlightRadar24 get_flights error: {e}")

            # Flight not found live — try search
            try:
                search_results = self._api.search(flight_num)
                schedule = search_results.get('schedule', [])
                if not schedule:
                    return {'error': f'No flight found for {flight_number}', 'mock_data': False}

                sched_info = schedule[0]
                detail = sched_info.get('detail', {})

                return {
                    'flight_number': flight_num,
                    'flight_icao': detail.get('callsign'),
                    'airline': {
                        'name': self._get_airline_name(airline_iata),
                        'iata': airline_iata,
                    },
                    'status': 'scheduled',
                    'status_display': _get_status_display('scheduled'),
                    'departure': {
                        'airport': 'N/A', 'airport_code': 'N/A',
                        'terminal': None, 'gate': None,
                        'scheduled': None, 'estimated': None, 'actual': None,
                        'delay_minutes': None, 'delay_display': None,
                    },
                    'arrival': {
                        'airport': 'N/A', 'airport_code': 'N/A',
                        'terminal': None, 'gate': None, 'baggage': None,
                        'scheduled': None, 'estimated': None, 'actual': None,
                        'delay_minutes': None, 'delay_display': None,
                    },
                    'live': None,
                    'flight_date': datetime.now().strftime('%Y-%m-%d'),
                    'mock_data': False,
                    'note': 'Flight found in schedule but not currently active.',
                }
            except Exception as e:
                print(f"⚠️ FlightRadar24 search error: {e}")

            return {'error': f'No flight found for {flight_number}', 'mock_data': False}

        except Exception as e:
            print(f"⚠️ FlightRadar24 exception: {e} — using mock data")
            result = _generate_mock_single_flight(flight_num)
            result['mock_data'] = True
            return result

    def get_departures(self, airport_code, airline_code=None):
        """Get all departing flights from an airport today."""
        def _mock():
            mock_flights = _generate_mock_flights(airport_code, 'departures')
            return {
                'airport': airport_code, 'airline': airline_code,
                'type': 'departures', 'count': len(mock_flights),
                'flights': mock_flights,
                'last_updated': datetime.now().isoformat(), 'mock_data': True,
            }

        if not self._api:
            return _mock()

        try:
            details = self._api.get_airport_details(airport_code)
            schedule = details.get('airport', {}).get('pluginData', {}).get('schedule', {})
            departures = schedule.get('departures', {}).get('data', [])

            formatted = []
            for entry in departures:
                flight = entry.get('flight', {})
                airline_iata = flight.get('airline', {}).get('code', {}).get('iata', '')
                if airline_code and airline_iata != airline_code:
                    continue
                formatted.append(self._format_schedule_flight(flight, airport_code, 'departures'))

            formatted.sort(key=lambda x: x.get('scheduled_time', '') or '')
            return {
                'airport': airport_code, 'airline': airline_code,
                'type': 'departures', 'count': len(formatted),
                'flights': formatted,
                'last_updated': datetime.now().isoformat(), 'mock_data': False,
            }
        except Exception as e:
            print(f"⚠️ FlightRadar24 departures exception: {e} — using mock data")
            return _mock()

    def get_arrivals(self, airport_code, airline_code=None):
        """Get all arriving flights to an airport today."""
        def _mock():
            mock_flights = _generate_mock_flights(airport_code, 'arrivals')
            return {
                'airport': airport_code, 'airline': airline_code,
                'type': 'arrivals', 'count': len(mock_flights),
                'flights': mock_flights,
                'last_updated': datetime.now().isoformat(), 'mock_data': True,
            }

        if not self._api:
            return _mock()

        try:
            details = self._api.get_airport_details(airport_code)
            schedule = details.get('airport', {}).get('pluginData', {}).get('schedule', {})
            arrivals = schedule.get('arrivals', {}).get('data', [])

            formatted = []
            for entry in arrivals:
                flight = entry.get('flight', {})
                airline_iata = flight.get('airline', {}).get('code', {}).get('iata', '')
                if airline_code and airline_iata != airline_code:
                    continue
                formatted.append(self._format_schedule_flight(flight, airport_code, 'arrivals'))

            formatted.sort(key=lambda x: x.get('scheduled_time', '') or '')
            return {
                'airport': airport_code, 'airline': airline_code,
                'type': 'arrivals', 'count': len(formatted),
                'flights': formatted,
                'last_updated': datetime.now().isoformat(), 'mock_data': False,
            }
        except Exception as e:
            print(f"⚠️ FlightRadar24 arrivals exception: {e} — using mock data")
            return _mock()

    def get_route_flights(self, origin, destination, airline_code=None):
        """Get all flights for a specific route today."""
        def _mock():
            mock_flights = [
                _generate_mock_single_flight(
                    f"{random.choice(['F9', 'UA', 'AA', 'DL', 'WN', 'NK'])}{random.randint(100, 2999)}"
                ) for _ in range(random.randint(1, 3))
            ]
            return {
                'route': f"{origin} → {destination}", 'airline': airline_code,
                'count': len(mock_flights), 'flights': mock_flights,
                'last_updated': datetime.now().isoformat(), 'mock_data': True,
            }

        if not self._api:
            return _mock()

        try:
            details = self._api.get_airport_details(origin)
            schedule = details.get('airport', {}).get('pluginData', {}).get('schedule', {})
            departures = schedule.get('departures', {}).get('data', [])

            route_flights = []
            for entry in departures:
                flight = entry.get('flight', {})
                dest_iata = flight.get('airport', {}).get('destination', {}).get('code', {}).get('iata', '')
                airline_iata = flight.get('airline', {}).get('code', {}).get('iata', '')
                if dest_iata != destination:
                    continue
                if airline_code and airline_iata != airline_code:
                    continue
                route_flights.append(self._format_schedule_flight(flight, origin, 'departures'))

            return {
                'route': f"{origin} → {destination}", 'airline': airline_code,
                'count': len(route_flights), 'flights': route_flights,
                'last_updated': datetime.now().isoformat(), 'mock_data': False,
            }
        except Exception as e:
            print(f"⚠️ FlightRadar24 route exception: {e} — using mock data")
            return _mock()

    # -----------------------------------------------------------------
    # Response format converters
    # -----------------------------------------------------------------

    def _format_live_flight(self, flight, flight_number):
        """Format a live Flight object to app format."""
        origin_code = flight.origin_airport_iata or 'N/A'
        dest_code = flight.destination_airport_iata or 'N/A'

        if flight.on_ground:
            status = 'landed'
        elif flight.altitude and flight.altitude > 0:
            status = 'active'
        else:
            status = 'scheduled'

        return {
            'flight_number': flight_number,
            'flight_icao': flight.callsign,
            'airline': {
                'name': self._get_airline_name(flight.airline_iata or ''),
                'iata': flight.airline_iata or '',
            },
            'status': status,
            'status_display': _get_status_display(status),
            'origin': origin_code,
            'origin_city': AIRPORT_NAMES.get(origin_code, origin_code),
            'destination': dest_code,
            'destination_city': AIRPORT_NAMES.get(dest_code, dest_code),
            'departure': {
                'airport': AIRPORT_NAMES.get(origin_code, origin_code),
                'airport_code': origin_code,
                'terminal': None, 'gate': None,
                'scheduled': None, 'estimated': None, 'actual': None,
                'delay_minutes': None, 'delay_display': None,
            },
            'arrival': {
                'airport': AIRPORT_NAMES.get(dest_code, dest_code),
                'airport_code': dest_code,
                'terminal': None, 'gate': None, 'baggage': None,
                'scheduled': None, 'estimated': None, 'actual': None,
                'delay_minutes': None, 'delay_display': None,
            },
            'live': {
                'latitude': flight.latitude,
                'longitude': flight.longitude,
                'altitude': flight.altitude,
                'ground_speed': flight.ground_speed,
                'heading': flight.heading,
                'vertical_speed': flight.vertical_speed,
            } if flight.latitude else None,
            'aircraft': flight.aircraft_code or 'N/A',
            'registration': flight.registration,
            'flight_date': datetime.now().strftime('%Y-%m-%d'),
            'mock_data': False,
        }

    def _format_schedule_flight(self, flight_data, airport_code, flight_type):
        """Format a FR24 airport schedule entry to the app's board format."""
        ident = flight_data.get('identification', {})
        status_info = flight_data.get('status', {})
        aircraft_info = flight_data.get('aircraft', {})
        airline_info = flight_data.get('airline', {})
        airport_info = flight_data.get('airport', {})
        time_info = flight_data.get('time', {})

        fn = (ident.get('number', {}).get('default', '') or 'N/A').replace(' ', '')
        airline_name = airline_info.get('name', '') or airline_info.get('short', '')
        airline_iata = airline_info.get('code', {}).get('iata', '')

        generic = status_info.get('generic', {})
        status = _map_fr24_status(generic)

        origin_info = airport_info.get('origin', {})
        dest_info = airport_info.get('destination', {})

        if flight_type == 'departures':
            origin_code = airport_code
            origin_city = AIRPORT_NAMES.get(airport_code, airport_code)
            dest_code = dest_info.get('code', {}).get('iata', 'N/A')
            dest_city = dest_info.get('position', {}).get('region', {}).get('city', '') or dest_info.get('name', '') or dest_code
            terminal = origin_info.get('info', {}).get('terminal')
            gate = origin_info.get('info', {}).get('gate')
        else:
            if isinstance(origin_info, dict) and 'code' in origin_info:
                origin_code = origin_info.get('code', {}).get('iata', 'N/A')
                origin_city = origin_info.get('position', {}).get('region', {}).get('city', '') or origin_info.get('name', '') or origin_code
            else:
                origin_code = 'N/A'
                origin_city = 'N/A'
            dest_code = airport_code
            dest_city = AIRPORT_NAMES.get(airport_code, airport_code)
            terminal = dest_info.get('info', {}).get('terminal') if isinstance(dest_info, dict) else None
            gate = dest_info.get('info', {}).get('gate') if isinstance(dest_info, dict) else None

        scheduled = time_info.get('scheduled', {})
        real = time_info.get('real', {})
        estimated = time_info.get('estimated', {})

        if flight_type == 'departures':
            sched_ts = scheduled.get('departure')
            actual_ts = real.get('departure') or estimated.get('departure')
        else:
            sched_ts = scheduled.get('arrival')
            actual_ts = real.get('arrival') or estimated.get('arrival')

        scheduled_time_str = _timestamp_to_time_str(sched_ts) or ''
        scheduled_dict = _timestamp_to_time_dict(sched_ts)
        actual_dict = _timestamp_to_time_dict(actual_ts)

        delay_str = 'On time'
        if sched_ts and actual_ts and actual_ts > sched_ts:
            delay_min = (actual_ts - sched_ts) // 60
            if delay_min > 0:
                delay_str = f"+{delay_min} min"

        aircraft_model = aircraft_info.get('model', {})
        aircraft = (aircraft_model.get('code', '') or aircraft_model.get('text', 'N/A')) if isinstance(aircraft_model, dict) else 'N/A'

        return {
            'flight_number': fn,
            'airline': {'name': airline_name, 'iata': airline_iata},
            'origin': origin_code,
            'origin_city': origin_city,
            'destination': dest_code,
            'destination_city': dest_city,
            'status': status,
            'status_display': _get_status_display(status),
            'scheduled_time': scheduled_time_str,
            'scheduled': scheduled_dict,
            'actual': actual_dict,
            'delay': delay_str,
            'terminal': terminal,
            'gate': gate,
            'aircraft': aircraft,
        }

    _AIRLINE_NAMES = {
        'F9': 'Frontier Airlines', 'UA': 'United Airlines', 'AA': 'American Airlines',
        'DL': 'Delta Air Lines', 'WN': 'Southwest Airlines', 'NK': 'Spirit Airlines',
        'B6': 'JetBlue Airways', 'AS': 'Alaska Airlines', 'G4': 'Allegiant Air',
        'HA': 'Hawaiian Airlines', 'SY': 'Sun Country Airlines', 'BA': 'British Airways',
        'AF': 'Air France', 'LH': 'Lufthansa', 'AC': 'Air Canada', 'KL': 'KLM',
        'EK': 'Emirates', 'QF': 'Qantas', 'SQ': 'Singapore Airlines',
    }

    def _get_airline_name(self, iata_code):
        return self._AIRLINE_NAMES.get(iata_code, iata_code or 'Unknown Airline')
