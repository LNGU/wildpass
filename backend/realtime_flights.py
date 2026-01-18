"""
Real-Time Flight Status Service using AviationStack API

Provides live flight information including:
- Current flight status (scheduled, active, landed, cancelled, etc.)
- Actual vs scheduled departure/arrival times
- Delays
- Gate and terminal information
- Live tracking data

Note: AviationStack free tier provides 100 requests/month for real-time data.
"""
import os
import requests
from datetime import datetime


class RealTimeFlightService:
    """Real-time flight status using AviationStack API"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('AVIATIONSTACK_API_KEY')
        self.base_url = "http://api.aviationstack.com/v1"
    
    def is_configured(self):
        return bool(self.api_key)
    
    def get_flight_status(self, flight_number):
        """
        Get real-time status for a specific flight number
        
        Args:
            flight_number: Flight number (e.g., 'F9777', 'F91993')
        
        Returns:
            Flight status dictionary or None
        """
        if not self.api_key:
            return {'error': 'AviationStack API key not configured'}
        
        try:
            # Normalize flight number (remove dash if present)
            flight_num = flight_number.replace('-', '').upper()
            
            params = {
                'access_key': self.api_key,
                'flight_iata': flight_num
            }
            
            response = requests.get(f"{self.base_url}/flights", params=params, timeout=30)
            data = response.json()
            
            if 'error' in data:
                return {'error': data['error'].get('message', 'Unknown error')}
            
            flights = data.get('data', [])
            if not flights:
                return {'error': f'No flight found for {flight_number}'}
            
            # Return the most recent/relevant flight
            return self._format_flight_status(flights[0])
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_route_flights(self, origin, destination, airline_code='F9'):
        """
        Get all real-time flights for a specific route
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            airline_code: Airline IATA code (default: F9 for Frontier)
        
        Returns:
            List of flight status dictionaries
        """
        if not self.api_key:
            return {'error': 'AviationStack API key not configured', 'flights': []}
        
        try:
            params = {
                'access_key': self.api_key,
                'dep_iata': origin,
                'arr_iata': destination,
                'airline_iata': airline_code
            }
            
            response = requests.get(f"{self.base_url}/flights", params=params, timeout=30)
            data = response.json()
            
            if 'error' in data:
                return {'error': data['error'].get('message', 'Unknown error'), 'flights': []}
            
            flights = data.get('data', [])
            formatted_flights = [self._format_flight_status(f) for f in flights]
            
            return {
                'route': f"{origin} → {destination}",
                'airline': airline_code,
                'count': len(formatted_flights),
                'flights': formatted_flights,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e), 'flights': []}
    
    def get_departures(self, airport_code, airline_code='F9'):
        """
        Get all departing flights from an airport
        
        Args:
            airport_code: Airport IATA code
            airline_code: Airline IATA code (default: F9 for Frontier)
        
        Returns:
            List of departing flights
        """
        if not self.api_key:
            return {'error': 'AviationStack API key not configured', 'flights': []}
        
        try:
            params = {
                'access_key': self.api_key,
                'dep_iata': airport_code,
                'airline_iata': airline_code
            }
            
            response = requests.get(f"{self.base_url}/flights", params=params, timeout=30)
            data = response.json()
            
            if 'error' in data:
                return {'error': data['error'].get('message', 'Unknown error'), 'flights': []}
            
            flights = data.get('data', [])
            formatted_flights = [self._format_flight_status(f) for f in flights]
            
            # Sort by departure time
            formatted_flights.sort(key=lambda x: x.get('departure', {}).get('scheduled', {}).get('iso', '') or '')
            
            return {
                'airport': airport_code,
                'airline': airline_code,
                'type': 'departures',
                'count': len(formatted_flights),
                'flights': formatted_flights,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e), 'flights': []}
    
    def get_arrivals(self, airport_code, airline_code='F9'):
        """
        Get all arriving flights to an airport
        
        Args:
            airport_code: Airport IATA code
            airline_code: Airline IATA code (default: F9 for Frontier)
        
        Returns:
            List of arriving flights
        """
        if not self.api_key:
            return {'error': 'AviationStack API key not configured', 'flights': []}
        
        try:
            params = {
                'access_key': self.api_key,
                'arr_iata': airport_code,
                'airline_iata': airline_code
            }
            
            response = requests.get(f"{self.base_url}/flights", params=params, timeout=30)
            data = response.json()
            
            if 'error' in data:
                return {'error': data['error'].get('message', 'Unknown error'), 'flights': []}
            
            flights = data.get('data', [])
            formatted_flights = [self._format_flight_status(f) for f in flights]
            
            # Sort by arrival time
            formatted_flights.sort(key=lambda x: x.get('arrival', {}).get('scheduled', {}).get('iso', '') or '')
            
            return {
                'airport': airport_code,
                'airline': airline_code,
                'type': 'arrivals',
                'count': len(formatted_flights),
                'flights': formatted_flights,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e), 'flights': []}
    
    def _format_flight_status(self, flight_data):
        """Format raw AviationStack data into a clean status object"""
        departure = flight_data.get('departure', {})
        arrival = flight_data.get('arrival', {})
        airline = flight_data.get('airline', {})
        flight_info = flight_data.get('flight', {})
        live = flight_data.get('live')
        
        # Calculate delay
        dep_delay = departure.get('delay')
        arr_delay = arrival.get('delay')
        
        # Determine status with emoji
        status = flight_data.get('flight_status', 'unknown')
        status_display = self._get_status_display(status)
        
        return {
            'flight_number': flight_info.get('iata', 'N/A'),
            'flight_icao': flight_info.get('icao'),
            'airline': {
                'name': airline.get('name', 'Frontier Airlines'),
                'iata': airline.get('iata', 'F9'),
                'icao': airline.get('icao')
            },
            'status': status,
            'status_display': status_display,
            'departure': {
                'airport': departure.get('airport'),
                'airport_code': departure.get('iata'),
                'terminal': departure.get('terminal'),
                'gate': departure.get('gate'),
                'scheduled': self._format_time(departure.get('scheduled')),
                'estimated': self._format_time(departure.get('estimated')),
                'actual': self._format_time(departure.get('actual')),
                'delay_minutes': dep_delay,
                'delay_display': f"+{dep_delay} min" if dep_delay and dep_delay > 0 else None
            },
            'arrival': {
                'airport': arrival.get('airport'),
                'airport_code': arrival.get('iata'),
                'terminal': arrival.get('terminal'),
                'gate': arrival.get('gate'),
                'baggage': arrival.get('baggage'),
                'scheduled': self._format_time(arrival.get('scheduled')),
                'estimated': self._format_time(arrival.get('estimated')),
                'actual': self._format_time(arrival.get('actual')),
                'delay_minutes': arr_delay,
                'delay_display': f"+{arr_delay} min" if arr_delay and arr_delay > 0 else None
            },
            'live': {
                'is_live': live is not None,
                'latitude': live.get('latitude') if live else None,
                'longitude': live.get('longitude') if live else None,
                'altitude': live.get('altitude') if live else None,
                'speed': live.get('speed_horizontal') if live else None,
                'direction': live.get('direction') if live else None,
                'updated': live.get('updated') if live else None
            } if live else None,
            'flight_date': flight_data.get('flight_date')
        }
    
    def _format_time(self, time_str):
        """Format ISO time string to readable format"""
        if not time_str:
            return None
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return {
                'iso': time_str,
                'time': dt.strftime('%I:%M %p'),
                'date': dt.strftime('%Y-%m-%d'),
                'full': dt.strftime('%b %d, %I:%M %p')
            }
        except:
            return {'iso': time_str, 'time': time_str, 'date': None, 'full': time_str}
    
    def _get_status_display(self, status):
        """Get display-friendly status with emoji"""
        status_map = {
            'scheduled': {'emoji': '🕐', 'text': 'Scheduled', 'color': 'gray'},
            'active': {'emoji': '✈️', 'text': 'In Flight', 'color': 'blue'},
            'landed': {'emoji': '✅', 'text': 'Landed', 'color': 'green'},
            'cancelled': {'emoji': '❌', 'text': 'Cancelled', 'color': 'red'},
            'incident': {'emoji': '⚠️', 'text': 'Incident', 'color': 'orange'},
            'diverted': {'emoji': '↪️', 'text': 'Diverted', 'color': 'orange'},
            'delayed': {'emoji': '⏰', 'text': 'Delayed', 'color': 'yellow'},
            'unknown': {'emoji': '❓', 'text': 'Unknown', 'color': 'gray'}
        }
        return status_map.get(status, status_map['unknown'])
