import React from 'react';
import './FlightDetailsModal.css';

const FlightDetailsModal = ({ flight, onClose }) => {
  if (!flight) return null;

  const formatTime = (time) => {
    if (!time) return 'N/A';
    return time;
  };

  const formatDate = (date) => {
    if (!date) return 'N/A';
    // Parse as local date to avoid timezone issues
    const [year, month, day] = date.split('-').map(Number);
    const d = new Date(year, month - 1, day);
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="flight-details-modal-overlay" onClick={onClose}>
      <div className="flight-details-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="flight-details-modal-header">
          <h2>✈️ Flight Details</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="flight-details-modal-body">
          {/* Route Header */}
          <div className="route-header">
            <div className="route-info">
              <div className="route-airports">
                <span className="airport-code">{flight.origin}</span>
                <span className="route-arrow">{flight.is_round_trip ? '⇄' : '→'}</span>
                <span className="airport-code">{flight.destination}</span>
              </div>
              <div className="route-type">
                {flight.is_round_trip ? 'Round Trip' : 'One Way'}
              </div>
            </div>
            <div className="price-info">
              <div className="price-amount">${flight.price}</div>
              {flight.gowild_eligible && !flight.blackout_dates?.has_blackout && (
                <div className="gowild-badge-large">🎫 GoWild Eligible</div>
              )}
            </div>
          </div>

          {/* Outbound Flight */}
          <div className="flight-segment-details">
            <h3>{flight.is_round_trip ? '✈️ Outbound Flight' : '✈️ Flight Details'}</h3>
            <div className="details-grid">
              <div className="detail-item">
                <label>Airline</label>
                <value>{flight.airline}</value>
              </div>
              <div className="detail-item">
                <label>Flight Number</label>
                <value>{flight.flightNumber || flight.flight_number}</value>
              </div>
              <div className="detail-item">
                <label>Departure Date</label>
                <value>{formatDate(flight.departureDate || flight.departure_date)}</value>
              </div>
              <div className="detail-item">
                <label>Departure Time</label>
                <value>{formatTime(flight.departureTime || flight.departure_time)}</value>
              </div>
              <div className="detail-item">
                <label>Arrival Date</label>
                <value>{formatDate(flight.arrivalDate || flight.arrival_date)}</value>
              </div>
              <div className="detail-item">
                <label>Arrival Time</label>
                <value>{formatTime(flight.arrivalTime || flight.arrival_time)}</value>
              </div>
              <div className="detail-item">
                <label>Duration</label>
                <value>{flight.duration}</value>
              </div>
              <div className="detail-item">
                <label>Stops</label>
                <value>{flight.stops === 0 ? 'Nonstop' : `${flight.stops} stop(s)`}</value>
              </div>
              {flight.seatsRemaining && (
                <div className="detail-item">
                  <label>Seats Available</label>
                  <value className={flight.seatsRemaining <= 3 ? 'low-seats' : ''}>
                    {flight.seatsRemaining}
                  </value>
                </div>
              )}
            </div>
          </div>

          {/* Return Flight (if round trip) */}
          {flight.is_round_trip && flight.return_flight && (
            <div className="flight-segment-details">
              <h3>✈️ Return Flight</h3>
              <div className="details-grid">
                <div className="detail-item">
                  <label>Airline</label>
                  <value>{flight.return_flight.airline || flight.airline}</value>
                </div>
                <div className="detail-item">
                  <label>Flight Number</label>
                  <value>{flight.return_flight.flight_number || flight.return_flight.flightNumber}</value>
                </div>
                <div className="detail-item">
                  <label>Departure Date</label>
                  <value>{formatDate(flight.return_flight.departure_date || flight.return_flight.departureDate)}</value>
                </div>
                <div className="detail-item">
                  <label>Departure Time</label>
                  <value>{formatTime(flight.return_flight.departure_time || flight.return_flight.departureTime)}</value>
                </div>
                <div className="detail-item">
                  <label>Arrival Date</label>
                  <value>{formatDate(flight.return_flight.arrival_date || flight.return_flight.arrivalDate)}</value>
                </div>
                <div className="detail-item">
                  <label>Arrival Time</label>
                  <value>{formatTime(flight.return_flight.arrival_time || flight.return_flight.arrivalTime)}</value>
                </div>
                <div className="detail-item">
                  <label>Duration</label>
                  <value>{flight.return_flight.duration}</value>
                </div>
                <div className="detail-item">
                  <label>Stops</label>
                  <value>{flight.return_flight.stops === 0 ? 'Nonstop' : `${flight.return_flight.stops} stop(s)`}</value>
                </div>
              </div>
            </div>
          )}

          {/* GoWild & Blackout Information */}
          {flight.gowild_eligible && (
            <div className={`gowild-info ${flight.blackout_dates?.has_blackout ? 'has-blackout' : ''}`}>
              <h4>🎫 GoWild Pass Information</h4>
              {flight.blackout_dates?.has_blackout ? (
                <div className="blackout-warning-detailed">
                  <p><strong>⚠️ Blackout Period Active</strong></p>
                  <p>{flight.blackout_dates.message}</p>
                  <p className="blackout-note">This flight cannot be booked with a GoWild pass during this period. Regular fares apply.</p>
                </div>
              ) : (
                <div className="gowild-eligible-info">
                  <p><strong>✓ Eligible for GoWild Pass</strong></p>
                  <p>Book this flight using your GoWild Pass and only pay taxes and fees (typically $5-15).</p>
                  <p className="regular-price-info">Regular price: ${flight.price}</p>
                </div>
              )}
            </div>
          )}

          {/* Booking Info */}
          <div className="booking-info">
            <p className="info-note">
              💡 <strong>Note:</strong> This is a flight search tool. To book this flight, visit Frontier Airlines' website or contact them directly.
            </p>
          </div>
        </div>

        <div className="flight-details-modal-footer">
          <button className="close-modal-button" onClick={onClose}>Close</button>
          <a 
            href="https://www.flyfrontier.com" 
            target="_blank" 
            rel="noopener noreferrer"
            className="book-on-frontier-button"
          >
            Book on Frontier →
          </a>
        </div>
      </div>
    </div>
  );
};

export default FlightDetailsModal;
