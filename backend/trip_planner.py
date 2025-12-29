"""
Trip Planner - Find optimal flight combinations based on desired trip length
"""
from datetime import datetime, timedelta

def calculate_trip_duration_hours(outbound_depart, return_arrive):
    """Calculate trip duration in hours between two datetime objects"""
    duration = return_arrive - outbound_depart
    return duration.total_seconds() / 3600

def find_optimal_trips(flights, trip_length, trip_length_unit='days', nonstop_preferred=False, max_duration=None, max_duration_unit='days'):
    """
    Find flight combinations that best match the desired trip length

    Args:
        flights: List of round-trip flight offers
        trip_length: Desired length of trip (number)
        trip_length_unit: 'hours' or 'days'
        nonstop_preferred: Boolean - prefer nonstop flights when available
        max_duration: Optional maximum trip duration (number)
        max_duration_unit: Unit for max_duration ('hours' or 'days')

    Returns:
        List of flight combinations sorted by how close they match desired duration
    """
    # Convert trip length to hours
    target_hours = float(trip_length) * (24 if trip_length_unit == 'days' else 1)

    # Convert max duration to hours if provided
    max_hours = None
    if max_duration:
        max_hours = float(max_duration) * (24 if max_duration_unit == 'days' else 1)

    # Filter for round trips only
    round_trip_flights = [f for f in flights if f.get('is_round_trip')]

    if not round_trip_flights:
        return []

    # Calculate how close each flight is to target duration
    scored_flights = []
    for flight in round_trip_flights:
        try:
            # Parse departure and return times
            depart_str = f"{flight['departure_date']} {flight['departure_time']}"
            return_str = f"{flight['return_flight']['arrival_date']} {flight['return_flight']['arrival_time']}"

            # Handle both 12-hour and 24-hour formats
            for fmt in ['%Y-%m-%d %I:%M %p', '%Y-%m-%d %H:%M']:
                try:
                    depart_dt = datetime.strptime(depart_str, fmt)
                    return_dt = datetime.strptime(return_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If no format worked, skip this flight
                continue

            # Calculate actual trip duration
            actual_hours = calculate_trip_duration_hours(depart_dt, return_dt)

            # Filter out trips exceeding max duration
            if max_hours and actual_hours > max_hours:
                continue  # Skip this flight

            # Calculate how far off from target (lower is better)
            duration_diff = abs(actual_hours - target_hours)

            # Apply nonstop preference bonus
            nonstop_bonus = 0
            if nonstop_preferred:
                outbound_nonstop = flight.get('stops', 0) == 0
                return_nonstop = flight['return_flight'].get('stops', 0) == 0

                if outbound_nonstop and return_nonstop:
                    nonstop_bonus = -10  # Both nonstop = highest priority
                elif outbound_nonstop or return_nonstop:
                    nonstop_bonus = -5   # One nonstop = medium priority
                else:
                    nonstop_bonus = 5    # No nonstop = lower priority

            # Calculate final score (lower is better)
            score = duration_diff + nonstop_bonus

            # Add metadata
            flight_with_score = {
                **flight,
                'trip_duration_hours': round(actual_hours, 2),
                'trip_duration_display': format_duration_display(actual_hours),
                'duration_match_score': score,
                'duration_diff_hours': round(duration_diff, 2)
            }

            scored_flights.append(flight_with_score)

        except (KeyError, ValueError) as e:
            # Skip flights with parsing errors
            print(f"Error processing flight: {e}")
            continue

    # Sort by score (best matches first)
    scored_flights.sort(key=lambda x: x['duration_match_score'])

    return scored_flights

def format_duration_display(hours):
    """Format duration in hours to friendly display"""
    if hours < 24:
        return f"{int(hours)}h {int((hours % 1) * 60)}m"
    else:
        days = int(hours / 24)
        remaining_hours = int(hours % 24)
        if remaining_hours > 0:
            return f"{days}d {remaining_hours}h"
        return f"{days}d"
