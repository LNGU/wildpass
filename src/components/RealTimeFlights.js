import React, { useState, useEffect, useCallback } from 'react';
import './RealTimeFlights.css';

function RealTimeFlights({ apiBaseUrl }) {
  const [airport, setAirport] = useState('DEN');
  const [viewMode, setViewMode] = useState('departures'); // 'departures' or 'arrivals'
  const [flights, setFlights] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [flightNumber, setFlightNumber] = useState('');
  const [singleFlight, setSingleFlight] = useState(null);

  // Popular Frontier hubs
  const popularAirports = ['DEN', 'LAS', 'PHX', 'MCO', 'ATL', 'ORD', 'DFW', 'MIA'];

  const fetchFlights = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSingleFlight(null);

    try {
      const endpoint = viewMode === 'departures' 
        ? `${apiBaseUrl}/realtime/departures/${airport}?airline=F9`
        : `${apiBaseUrl}/realtime/arrivals/${airport}?airline=F9`;
      
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      setFlights(data.flights || []);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error fetching real-time flights:', err);
      setError(err.message || 'Failed to fetch flight data');
      setFlights([]);
    } finally {
      setLoading(false);
    }
  }, [airport, viewMode, apiBaseUrl]);

  const searchFlight = async () => {
    if (!flightNumber.trim()) return;
    
    setLoading(true);
    setError(null);
    setFlights([]);

    try {
      // Format flight number (add F9 prefix if not present)
      let searchNumber = flightNumber.trim().toUpperCase();
      if (!searchNumber.startsWith('F9')) {
        searchNumber = `F9${searchNumber}`;
      }

      const response = await fetch(`${apiBaseUrl}/realtime/flight/${searchNumber}`);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.flight) {
        setSingleFlight(data.flight);
      } else {
        setError('Flight not found');
      }
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error searching flight:', err);
      setError(err.message || 'Failed to search flight');
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 5 minutes
  useEffect(() => {
    fetchFlights();
    const interval = setInterval(fetchFlights, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchFlights]);

  const getStatusClass = (status) => {
    const statusLower = (status || '').toLowerCase();
    if (statusLower.includes('active') || statusLower.includes('in flight')) return 'status-active';
    if (statusLower.includes('landed')) return 'status-landed';
    if (statusLower.includes('cancelled')) return 'status-cancelled';
    if (statusLower.includes('diverted')) return 'status-diverted';
    if (statusLower.includes('delayed')) return 'status-delayed';
    return 'status-scheduled';
  };

  const renderFlightRow = (flight, index) => {
    const isDelay = flight.delay && flight.delay !== 'On time';
    
    return (
      <div key={index} className={`realtime-flight-row ${getStatusClass(flight.status)}`}>
        <div className="flight-info-main">
          <div className="flight-number-cell">
            <span className="flight-number">{flight.flight_number}</span>
            <span className="aircraft">{flight.aircraft || 'A320'}</span>
          </div>
          
          <div className="route-cell">
            {viewMode === 'departures' ? (
              <>
                <span className="route-to">→ {flight.destination}</span>
                <span className="city-name">{flight.destination_city}</span>
              </>
            ) : (
              <>
                <span className="route-from">← {flight.origin}</span>
                <span className="city-name">{flight.origin_city}</span>
              </>
            )}
          </div>
          
          <div className="time-cell">
            <div className="scheduled-time">
              <span className="time-label">Scheduled</span>
              <span className="time-value">{flight.scheduled?.local || flight.scheduled_time || '--:--'}</span>
            </div>
            {flight.actual?.local && (
              <div className="actual-time">
                <span className="time-label">Actual</span>
                <span className="time-value">{flight.actual.local}</span>
              </div>
            )}
          </div>
          
          <div className="status-cell">
            <span className={`status-badge ${getStatusClass(flight.status)}`}>
              {flight.status_display || flight.status}
            </span>
            {isDelay && (
              <span className="delay-badge">{flight.delay}</span>
            )}
          </div>
          
          <div className="gate-cell">
            {flight.terminal && <span className="terminal">T{flight.terminal}</span>}
            {flight.gate && <span className="gate">Gate {flight.gate}</span>}
          </div>
        </div>
      </div>
    );
  };

  const renderSingleFlight = (flight) => (
    <div className="single-flight-card">
      <div className="single-flight-header">
        <div className="flight-id">
          <span className="big-flight-number">{flight.flight_number}</span>
          <span className={`status-badge large ${getStatusClass(flight.status)}`}>
            {flight.status_display || flight.status}
          </span>
        </div>
        {flight.delay && flight.delay !== 'On time' && (
          <span className="delay-badge large">{flight.delay}</span>
        )}
      </div>
      
      <div className="single-flight-route">
        <div className="route-point origin">
          <span className="airport-code">{flight.origin}</span>
          <span className="city">{flight.origin_city}</span>
          <div className="times">
            <div className="time-row">
              <span className="label">Scheduled:</span>
              <span className="value">{flight.departure?.scheduled?.local || '--:--'}</span>
            </div>
            {flight.departure?.actual?.local && (
              <div className="time-row actual">
                <span className="label">Actual:</span>
                <span className="value">{flight.departure.actual.local}</span>
              </div>
            )}
          </div>
          {(flight.departure?.terminal || flight.departure?.gate) && (
            <div className="gate-info">
              {flight.departure?.terminal && <span>Terminal {flight.departure.terminal}</span>}
              {flight.departure?.gate && <span>Gate {flight.departure.gate}</span>}
            </div>
          )}
        </div>
        
        <div className="route-arrow">
          <span className="plane-icon">✈️</span>
          <div className="flight-line"></div>
        </div>
        
        <div className="route-point destination">
          <span className="airport-code">{flight.destination}</span>
          <span className="city">{flight.destination_city}</span>
          <div className="times">
            <div className="time-row">
              <span className="label">Scheduled:</span>
              <span className="value">{flight.arrival?.scheduled?.local || '--:--'}</span>
            </div>
            {flight.arrival?.actual?.local && (
              <div className="time-row actual">
                <span className="label">Actual:</span>
                <span className="value">{flight.arrival.actual.local}</span>
              </div>
            )}
          </div>
          {(flight.arrival?.terminal || flight.arrival?.gate) && (
            <div className="gate-info">
              {flight.arrival?.terminal && <span>Terminal {flight.arrival.terminal}</span>}
              {flight.arrival?.gate && <span>Gate {flight.arrival.gate}</span>}
            </div>
          )}
        </div>
      </div>
      
      <button className="back-button" onClick={() => { setSingleFlight(null); fetchFlights(); }}>
        ← Back to Flight Board
      </button>
    </div>
  );

  return (
    <div className="realtime-flights-container">
      <div className="realtime-header">
        <h2>✈️ Real-Time Frontier Flights</h2>
        <p className="realtime-subtitle">Live flight status powered by AviationStack</p>
      </div>
      
      <div className="realtime-controls">
        <div className="search-flight-section">
          <input
            type="text"
            placeholder="Flight # (e.g., 1234 or F91234)"
            value={flightNumber}
            onChange={(e) => setFlightNumber(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && searchFlight()}
            className="flight-search-input"
          />
          <button onClick={searchFlight} className="search-flight-btn">
            🔍 Track Flight
          </button>
        </div>
        
        <div className="divider">or view flight board</div>
        
        <div className="board-controls">
          <div className="airport-selector">
            <label>Airport:</label>
            <select 
              value={airport} 
              onChange={(e) => setAirport(e.target.value)}
              className="airport-select"
            >
              {popularAirports.map(apt => (
                <option key={apt} value={apt}>{apt}</option>
              ))}
            </select>
          </div>
          
          <div className="view-toggle">
            <button 
              className={`toggle-btn ${viewMode === 'departures' ? 'active' : ''}`}
              onClick={() => setViewMode('departures')}
            >
              🛫 Departures
            </button>
            <button 
              className={`toggle-btn ${viewMode === 'arrivals' ? 'active' : ''}`}
              onClick={() => setViewMode('arrivals')}
            >
              🛬 Arrivals
            </button>
          </div>
          
          <button onClick={fetchFlights} className="refresh-btn" disabled={loading}>
            🔄 Refresh
          </button>
        </div>
      </div>
      
      {lastUpdated && (
        <div className="last-updated">
          Last updated: {lastUpdated.toLocaleTimeString()}
        </div>
      )}
      
      {error && (
        <div className="realtime-error">
          <span>⚠️ {error}</span>
        </div>
      )}
      
      {loading && (
        <div className="realtime-loading">
          <div className="spinner"></div>
          <span>Loading flight data...</span>
        </div>
      )}
      
      {!loading && singleFlight && renderSingleFlight(singleFlight)}
      
      {!loading && !singleFlight && flights.length > 0 && (
        <div className="flight-board">
          <div className="board-header">
            <span className="col-flight">Flight</span>
            <span className="col-route">{viewMode === 'departures' ? 'To' : 'From'}</span>
            <span className="col-time">Time</span>
            <span className="col-status">Status</span>
            <span className="col-gate">Gate</span>
          </div>
          <div className="flight-list">
            {flights.map((flight, index) => renderFlightRow(flight, index))}
          </div>
        </div>
      )}
      
      {!loading && !singleFlight && flights.length === 0 && !error && (
        <div className="no-flights">
          <span>No Frontier flights found for {airport}</span>
        </div>
      )}
      
      <div className="realtime-footer">
        <span className="api-note">🎫 Free tier: 100 requests/month • Real-time data only</span>
      </div>
    </div>
  );
}

export default RealTimeFlights;
