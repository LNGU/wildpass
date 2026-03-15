"""
FlightRadar24 API Integration for Real-Time Flight Status

Replaces AeroDataBox API. Uses the unofficial FlightRadar24 Python SDK.
No API key required. Provides real-time flight tracking data.
No mock data fallback -- errors are returned directly.

Package: FlightRadarAPI (pip install FlightRadarAPI)
"""
import re
from datetime import datetime
from FlightRadar24 import FlightRadar24API


# =============================================================================
# Constants
# =============================================================================

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
            return {'error': 'FlightRadar24 API failed to initialize', 'mock_data': False}

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
            print(f"⚠️ FlightRadar24 exception: {e}")
            return {'error': f'FlightRadar24 API error: {str(e)}', 'mock_data': False}

    def get_departures(self, airport_code, airline_code=None):
        """Get all departing flights from an airport today."""
        if not self._api:
            return {'error': 'FlightRadar24 API not available', 'flights': [], 'mock_data': False}

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
            print(f"⚠️ FlightRadar24 departures exception: {e}")
            return {'error': f'FlightRadar24 API error: {str(e)}', 'flights': [], 'mock_data': False}

    def get_arrivals(self, airport_code, airline_code=None):
        """Get all arriving flights to an airport today."""
        if not self._api:
            return {'error': 'FlightRadar24 API not available', 'flights': [], 'mock_data': False}

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
            print(f"⚠️ FlightRadar24 arrivals exception: {e}")
            return {'error': f'FlightRadar24 API error: {str(e)}', 'flights': [], 'mock_data': False}

    def get_route_flights(self, origin, destination, airline_code=None):
        """Get all flights for a specific route today."""
        if not self._api:
            return {'error': 'FlightRadar24 API not available', 'flights': [], 'mock_data': False}

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
            print(f"⚠️ FlightRadar24 route exception: {e}")
            return {'error': f'FlightRadar24 API error: {str(e)}', 'flights': [], 'mock_data': False}

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

        # Detail fields for flight detail view
        origin_terminal = origin_info.get('info', {}).get('terminal') if isinstance(origin_info, dict) else None
        origin_gate = origin_info.get('info', {}).get('gate') if isinstance(origin_info, dict) else None
        origin_baggage = origin_info.get('info', {}).get('baggage') if isinstance(origin_info, dict) else None
        dest_terminal_d = dest_info.get('info', {}).get('terminal') if isinstance(dest_info, dict) else None
        dest_gate_d = dest_info.get('info', {}).get('gate') if isinstance(dest_info, dict) else None
        dest_baggage = dest_info.get('info', {}).get('baggage') if isinstance(dest_info, dict) else None

        origin_airport_name = origin_info.get('name', '') if isinstance(origin_info, dict) else ''
        origin_city_full = (origin_info.get('position', {}).get('region', {}).get('city', '') if isinstance(origin_info, dict) else '') or origin_city
        dest_airport_name = dest_info.get('name', '') if isinstance(dest_info, dict) else ''
        dest_city_full = (dest_info.get('position', {}).get('region', {}).get('city', '') if isinstance(dest_info, dict) else '') or dest_city

        sched_dep_ts = scheduled.get('departure')
        sched_arr_ts = scheduled.get('arrival')
        est_dep_ts = estimated.get('departure')
        est_arr_ts = estimated.get('arrival')
        actual_dep_ts = real.get('departure')
        actual_arr_ts = real.get('arrival')

        duration_minutes = None
        if sched_dep_ts and sched_arr_ts and sched_arr_ts > sched_dep_ts:
            duration_minutes = (sched_arr_ts - sched_dep_ts) // 60

        callsign = ident.get('callsign', '')
        aircraft_reg = aircraft_info.get('registration', '')
        aircraft_model_code = aircraft_model.get('code', '') if isinstance(aircraft_model, dict) else ''
        aircraft_model_text_v = aircraft_model.get('text', '') if isinstance(aircraft_model, dict) else ''

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
            'origin_terminal': origin_terminal,
            'origin_gate': origin_gate,
            'origin_baggage': origin_baggage,
            'dest_terminal': dest_terminal_d,
            'dest_gate': dest_gate_d,
            'dest_baggage': dest_baggage,
            'origin_airport_name': origin_airport_name,
            'origin_city_name': origin_city_full,
            'dest_airport_name': dest_airport_name,
            'dest_city_name': dest_city_full,
            'scheduled_departure_ts': sched_dep_ts,
            'scheduled_arrival_ts': sched_arr_ts,
            'estimated_departure_ts': est_dep_ts,
            'estimated_arrival_ts': est_arr_ts,
            'actual_departure_ts': actual_dep_ts,
            'actual_arrival_ts': actual_arr_ts,
            'duration_minutes': duration_minutes,
            'callsign': callsign,
            'aircraft_registration': aircraft_reg,
            'aircraft_model': aircraft_model_code,
            'aircraft_model_text': aircraft_model_text_v,
        }


    def get_live_flight(self, flight_number):
        """Get live position data for a specific flight."""
        flight_num = flight_number.replace('-', '').replace(' ', '').upper()

        match = re.match(r'^([A-Z]{3})(\d+)$', flight_num)
        if match:
            icao_code = match.group(1)
            number = match.group(2)
            iata = ICAO_TO_IATA.get(icao_code)
            if iata:
                flight_num = f"{iata}{number}"

        if not self._api:
            return {'error': 'FlightRadar24 API not available', 'live': False}

        try:
            al_match = re.match(r'^([A-Z0-9]{2})(\d+)$', flight_num)
            if not al_match:
                return {'error': f'Invalid flight number: {flight_number}', 'live': False}

            airline_iata = al_match.group(1)
            airline_icao = IATA_TO_ICAO.get(airline_iata)

            if airline_icao:
                try:
                    live_flights = self._api.get_flights(airline=airline_icao)
                    for f in live_flights:
                        if f.number and f.number.replace(' ', '') == flight_num:
                            return {
                                'flight_number': flight_num,
                                'latitude': f.latitude,
                                'longitude': f.longitude,
                                'altitude': f.altitude,
                                'ground_speed': f.ground_speed,
                                'heading': f.heading,
                                'vertical_speed': f.vertical_speed,
                                'on_ground': f.on_ground if hasattr(f, 'on_ground') else (f.altitude == 0),
                                'live': True,
                                'mock_data': False,
                            }
                except Exception as e:
                    print(f"\u26a0\ufe0f FlightRadar24 live lookup error: {e}")

            return {'error': 'Flight not currently trackable', 'live': False}
        except Exception as e:
            return {'error': f'FlightRadar24 API error: {str(e)}', 'live': False}

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
