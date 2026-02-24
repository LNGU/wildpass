import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  const [airportFilter, setAirportFilter] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);
  const fetchIdRef = useRef(0); // track latest fetch to ignore stale responses

  // All Frontier (F9) destinations - alphabetized by city name
  const allAirports = [
    { code: 'ABQ', name: 'Albuquerque' },
    { code: 'ALB', name: 'Albany' },
    { code: 'ANC', name: 'Anchorage' },
    { code: 'ATL', name: 'Atlanta', hub: true },
    { code: 'AUS', name: 'Austin' },
    { code: 'BWI', name: 'Baltimore' },
    { code: 'BHM', name: 'Birmingham' },
    { code: 'BOI', name: 'Boise' },
    { code: 'BOS', name: 'Boston' },
    { code: 'BUF', name: 'Buffalo' },
    { code: 'BUR', name: 'Burbank' },
    { code: 'CUN', name: 'Cancun' },
    { code: 'CHS', name: 'Charleston' },
    { code: 'CLT', name: 'Charlotte' },
    { code: 'ORD', name: 'Chicago O\'Hare' },
    { code: 'MDW', name: 'Chicago Midway' },
    { code: 'CVG', name: 'Cincinnati' },
    { code: 'CLE', name: 'Cleveland' },
    { code: 'COS', name: 'Colorado Springs' },
    { code: 'CMH', name: 'Columbus' },
    { code: 'DFW', name: 'Dallas/Fort Worth' },
    { code: 'DAL', name: 'Dallas Love Field' },
    { code: 'DEN', name: 'Denver (Hub)', hub: true },
    { code: 'DSM', name: 'Des Moines' },
    { code: 'DTW', name: 'Detroit' },
    { code: 'ELP', name: 'El Paso' },
    { code: 'FNT', name: 'Flint' },
    { code: 'FLL', name: 'Fort Lauderdale' },
    { code: 'RSW', name: 'Fort Myers' },
    { code: 'GDL', name: 'Guadalajara' },
    { code: 'GRR', name: 'Grand Rapids' },
    { code: 'GSP', name: 'Greenville SC' },
    { code: 'BDL', name: 'Hartford' },
    { code: 'HNL', name: 'Honolulu' },
    { code: 'IAH', name: 'Houston Intercontinental' },
    { code: 'HOU', name: 'Houston Hobby' },
    { code: 'HSV', name: 'Huntsville' },
    { code: 'IND', name: 'Indianapolis' },
    { code: 'JAX', name: 'Jacksonville' },
    { code: 'MCI', name: 'Kansas City' },
    { code: 'LIH', name: 'Kauai' },
    { code: 'KOA', name: 'Kona' },
    { code: 'LAS', name: 'Las Vegas', hub: true },
    { code: 'LIT', name: 'Little Rock' },
    { code: 'LAX', name: 'Los Angeles' },
    { code: 'SJD', name: 'Los Cabos' },
    { code: 'OGG', name: 'Maui' },
    { code: 'MEM', name: 'Memphis' },
    { code: 'MIA', name: 'Miami' },
    { code: 'MKE', name: 'Milwaukee' },
    { code: 'MSP', name: 'Minneapolis' },
    { code: 'MBJ', name: 'Montego Bay' },
    { code: 'MYR', name: 'Myrtle Beach' },
    { code: 'BNA', name: 'Nashville' },
    { code: 'NAS', name: 'Nassau' },
    { code: 'EWR', name: 'Newark' },
    { code: 'MSY', name: 'New Orleans' },
    { code: 'JFK', name: 'New York JFK' },
    { code: 'LGA', name: 'New York LaGuardia' },
    { code: 'ORF', name: 'Norfolk' },
    { code: 'OAK', name: 'Oakland' },
    { code: 'OKC', name: 'Oklahoma City' },
    { code: 'OMA', name: 'Omaha' },
    { code: 'ONT', name: 'Ontario CA' },
    { code: 'SNA', name: 'Orange County' },
    { code: 'MCO', name: 'Orlando', hub: true },
    { code: 'PSP', name: 'Palm Springs' },
    { code: 'PNS', name: 'Pensacola' },
    { code: 'PHL', name: 'Philadelphia' },
    { code: 'PHX', name: 'Phoenix', hub: true },
    { code: 'PIT', name: 'Pittsburgh' },
    { code: 'PDX', name: 'Portland' },
    { code: 'PVD', name: 'Providence' },
    { code: 'PVR', name: 'Puerto Vallarta' },
    { code: 'PUJ', name: 'Punta Cana' },
    { code: 'RDU', name: 'Raleigh-Durham' },
    { code: 'RIC', name: 'Richmond' },
    { code: 'ROC', name: 'Rochester' },
    { code: 'SMF', name: 'Sacramento' },
    { code: 'SLC', name: 'Salt Lake City' },
    { code: 'SAT', name: 'San Antonio' },
    { code: 'SAN', name: 'San Diego' },
    { code: 'SFO', name: 'San Francisco' },
    { code: 'SJC', name: 'San Jose' },
    { code: 'SJU', name: 'San Juan PR' },
    { code: 'SRQ', name: 'Sarasota' },
    { code: 'SAV', name: 'Savannah' },
    { code: 'SEA', name: 'Seattle' },
    { code: 'STL', name: 'St. Louis' },
    { code: 'SYR', name: 'Syracuse' },
    { code: 'TPA', name: 'Tampa' },
    { code: 'TUS', name: 'Tucson' },
    { code: 'TUL', name: 'Tulsa' },
    { code: 'DCA', name: 'Washington Reagan' },
    { code: 'IAD', name: 'Washington Dulles' },
    { code: 'PBI', name: 'West Palm Beach' },
    { code: 'ICT', name: 'Wichita' },
  ];

  // Filter airports based on search
  const filteredAirports = airportFilter
    ? allAirports.filter(apt => 
        apt.code.toLowerCase().includes(airportFilter.toLowerCase()) ||
        apt.name.toLowerCase().includes(airportFilter.toLowerCase())
      )
    : allAirports;

  const fetchFlights = useCallback(async () => {
    const thisId = ++fetchIdRef.current; // increment to invalidate any in-flight request
    setLoading(true);
    setError(null);
    setSingleFlight(null);

    try {
      const endpoint = viewMode === 'departures' 
        ? `${apiBaseUrl}/realtime/departures/${airport}?airline=F9`
        : `${apiBaseUrl}/realtime/arrivals/${airport}?airline=F9`;
      
      const response = await fetch(endpoint);
      
      // Ignore stale responses if airport/viewMode changed while fetching
      if (thisId !== fetchIdRef.current) return;

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      if (thisId !== fetchIdRef.current) return;

      setFlights(data.flights || []);
      setLastUpdated(new Date());
    } catch (err) {
      if (thisId !== fetchIdRef.current) return;
      console.error('Error fetching real-time flights:', err);
      setError(err.message || 'Failed to fetch flight data');
      setFlights([]);
    } finally {
      if (thisId === fetchIdRef.current) {
        setLoading(false);
      }
    }
  }, [airport, viewMode, apiBaseUrl]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
      // Backend wraps in {flight: ...}, but handle direct response too
      const flightData = data.flight || (data.flight_number ? data : null);
      if (flightData) {
        setSingleFlight(flightData);
      } else if (data.error) {
        setError(data.error);
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
        <p className="realtime-subtitle">Live flight status powered by AeroDataBox</p>
      </div>
      
      <div className="realtime-controls">
        <div className="search-flight-section">
          <input
            type="text"
            placeholder="Flight # (e.g., 1234 or F91234)"
            value={flightNumber}
            onChange={(e) => setFlightNumber(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchFlight()}
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
            <div className="airport-select-wrapper" ref={dropdownRef}>
              <button
                type="button"
                className="airport-select-button"
                onClick={() => setShowDropdown(!showDropdown)}
              >
                {airport} - {allAirports.find(a => a.code === airport)?.name || airport}
                <span className="dropdown-arrow">{showDropdown ? '▲' : '▼'}</span>
              </button>
              {showDropdown && (
                <div className="airport-dropdown">
                  <input
                    type="text"
                    placeholder="Search airports..."
                    value={airportFilter}
                    onChange={(e) => setAirportFilter(e.target.value)}
                    className="airport-filter-input"
                    autoFocus
                  />
                  <ul className="airport-list">
                    {filteredAirports.map(apt => (
                      <li
                        key={apt.code}
                        className={`airport-option ${apt.code === airport ? 'selected' : ''} ${apt.hub ? 'hub' : ''}`}
                        onClick={() => {
                          setAirport(apt.code);
                          setAirportFilter('');
                          setShowDropdown(false);
                        }}
                      >
                        <span className="airport-code-label">{apt.code}</span>
                        <span className="airport-name-label">{apt.name}</span>
                        {apt.hub && <span className="hub-star">⭐</span>}
                      </li>
                    ))}
                    {filteredAirports.length === 0 && (
                      <li className="airport-option no-match">No airports match</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
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
        <span className="api-note">🎫 Free tier: 300 requests/month • Real-time data via AeroDataBox</span>
      </div>
    </div>
  );
}

export default RealTimeFlights;
