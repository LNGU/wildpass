import React, { useState, useEffect, useCallback, useRef } from 'react';
import { getAuthHeader } from '../services/auth';
import './RealTimeFlights.css';
import RealTimeFlightDetail from './RealTimeFlightDetail';

/* global L */

function getStatusClass(status) {
  const s = typeof status === 'object' ? (status?.text || '') : (status || '');
  const statusLower = s.toLowerCase();
  if (statusLower.includes('active') || statusLower.includes('in flight')) return 'status-active';
  if (statusLower.includes('landed')) return 'status-landed';
  if (statusLower.includes('cancelled')) return 'status-cancelled';
  if (statusLower.includes('diverted')) return 'status-diverted';
  if (statusLower.includes('delayed')) return 'status-delayed';
  return 'status-scheduled';
}

function formatStatus(flight) {
  const sd = flight.status_display;
  if (!sd) return flight.status || 'Unknown';
  if (typeof sd === 'string') return sd;
  if (sd.text) return `${sd.emoji || ''} ${sd.text}`.trim();
  return flight.status || 'Unknown';
}

function getTimeDisplay(timeObj) {
  if (!timeObj) return '--:--';
  if (typeof timeObj === 'string') return timeObj;
  if (timeObj.local) return timeObj.local;
  if (timeObj.utc) return timeObj.utc;
  return '--:--';
}

function SingleFlightView({ flight, apiBaseUrl, onBack }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const [liveInfo, setLiveInfo] = useState(flight.live);
  const [lastPoll, setLastPoll] = useState(null);

  // Poll live position every 15 seconds for active flights
  useEffect(() => {
    if (flight.status !== 'active') return;

    const pollLive = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}/realtime/flight/${flight.flight_number}/live`, {
          headers: { ...getAuthHeader() },
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.live && data.latitude) {
          setLiveInfo({
            latitude: data.latitude,
            longitude: data.longitude,
            altitude: data.altitude,
            ground_speed: data.ground_speed,
            heading: data.heading,
            vertical_speed: data.vertical_speed,
          });
          setLastPoll(new Date());
        }
      } catch (e) {
        // silent
      }
    };

    pollLive();
    const interval = setInterval(pollLive, 15000);
    return () => clearInterval(interval);
  }, [flight.flight_number, flight.status, apiBaseUrl]);

  // Init map once
  useEffect(() => {
    if (!liveInfo || !liveInfo.latitude || !mapRef.current || mapInstanceRef.current) return;
    if (typeof L === 'undefined') return;

    const map = L.map(mapRef.current, {
      center: [liveInfo.latitude, liveInfo.longitude],
      zoom: 6,
      zoomControl: true,
      attributionControl: false,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
    }).addTo(map);

    const planeIcon = L.divIcon({
      html: '<div style="font-size:28px;transform:rotate(' + (liveInfo.heading || 0) + 'deg)">✈️</div>',
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      className: 'plane-marker',
    });
    markerRef.current = L.marker([liveInfo.latitude, liveInfo.longitude], { icon: planeIcon }).addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      markerRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [!!liveInfo]);

  // Update marker position on poll
  useEffect(() => {
    if (!liveInfo || !liveInfo.latitude || !mapInstanceRef.current || !markerRef.current) return;

    const newLatLng = [liveInfo.latitude, liveInfo.longitude];
    markerRef.current.setLatLng(newLatLng);
    markerRef.current.setIcon(L.divIcon({
      html: '<div style="font-size:28px;transform:rotate(' + (liveInfo.heading || 0) + 'deg)">✈️</div>',
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      className: 'plane-marker',
    }));
    mapInstanceRef.current.panTo(newLatLng);
  }, [liveInfo]);

  return (
    <div className="single-flight-card">
      <div className="single-flight-header">
        <div className="flight-id">
          <span className="big-flight-number">{flight.flight_number}</span>
          {flight.airline?.name && <span className="airline-name-large">{flight.airline.name}</span>}
        </div>
        <span className={`status-badge large ${getStatusClass(flight.status)}`}>
          {formatStatus(flight)}
        </span>
        {flight.delay && flight.delay !== 'On time' && (
          <span className="delay-badge large">{flight.delay}</span>
        )}
      </div>

      {liveInfo && liveInfo.latitude && (
        <div className="rtfd-live-section" style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ color: '#22c55e', margin: '0 0 0.75rem 0' }}>Live Position {lastPoll && <span style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 400, marginLeft: '0.5rem' }}>Updated {lastPoll.toLocaleTimeString()}</span>}</h4>
          <div ref={mapRef} style={{ width: '100%', height: '220px', borderRadius: '10px', overflow: 'hidden', marginBottom: '0.75rem' }}></div>
          <div className="rtfd-live-stats">
            <div><span>Altitude</span><strong>{liveInfo.altitude ? liveInfo.altitude.toLocaleString() : '--'} ft</strong></div>
            <div><span>Speed</span><strong>{liveInfo.ground_speed || '--'} kts</strong></div>
            <div><span>Heading</span><strong>{liveInfo.heading || '--'}</strong></div>
            {liveInfo.vertical_speed != null && (
              <div><span>V/S</span><strong>{liveInfo.vertical_speed} ft/min</strong></div>
            )}
          </div>
        </div>
      )}

      <div className="single-flight-route">
        <div className="route-point origin">
          <span className="airport-code">{flight.origin}</span>
          <span className="city">{flight.origin_city}</span>
          <div className="times">
            <div className="time-row">
              <span className="label">Scheduled:</span>
              <span className="value">{getTimeDisplay(flight.departure?.scheduled)}</span>
            </div>
            {(flight.departure?.actual || flight.departure?.estimated) && (
              <div className="time-row actual">
                <span className="label">{flight.departure?.actual ? 'Actual:' : 'Est:'}</span>
                <span className="value">{getTimeDisplay(flight.departure?.actual || flight.departure?.estimated)}</span>
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
          <span className="plane-icon"></span>
          <div className="flight-line"></div>
        </div>
        
        <div className="route-point destination">
          <span className="airport-code">{flight.destination}</span>
          <span className="city">{flight.destination_city}</span>
          <div className="times">
            <div className="time-row">
              <span className="label">Scheduled:</span>
              <span className="value">{getTimeDisplay(flight.arrival?.scheduled)}</span>
            </div>
            {(flight.arrival?.actual || flight.arrival?.estimated) && (
              <div className="time-row actual">
                <span className="label">{flight.arrival?.actual ? 'Actual:' : 'Est:'}</span>
                <span className="value">{getTimeDisplay(flight.arrival?.actual || flight.arrival?.estimated)}</span>
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
      
      <button className="back-button" onClick={onBack}>
        Back to Flight Board
      </button>
    </div>
  );
}

function RealTimeFlights({ apiBaseUrl, frontierOnly, setFrontierOnly }) {
  const [airport, setAirport] = useState(() => {
    return localStorage.getItem('wildpass_favorite_airport') || 'DEN';
  });
  const [viewMode, setViewMode] = useState('departures'); // 'departures' or 'arrivals'
  const [flights, setFlights] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [flightNumber, setFlightNumber] = useState('');
  const [singleFlight, setSingleFlight] = useState(null);
  const [favoriteAirport, setFavoriteAirport] = useState(() => {
    return localStorage.getItem('wildpass_favorite_airport') || '';
  });
  const [airportFilter, setAirportFilter] = useState('');

  const toggleFavorite = (code, e) => {
    e.stopPropagation();
    if (favoriteAirport === code) {
      setFavoriteAirport('');
      localStorage.removeItem('wildpass_favorite_airport');
    } else {
      setFavoriteAirport(code);
      localStorage.setItem('wildpass_favorite_airport', code);
    }
  };
  const [isMockData, setIsMockData] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedFlight, setSelectedFlight] = useState(null);
  const dropdownRef = useRef(null);
  const fetchIdRef = useRef(0); // track latest fetch to ignore stale responses

  // All Frontier (F9) destinations - alphabetized by city name
  const allAirports = [
    { code: 'ABQ', name: 'Albuquerque' },
    { code: 'ALB', name: 'Albany' },
    { code: 'ANC', name: 'Anchorage' },
    { code: 'ATL', name: 'Atlanta' },
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
    { code: 'DEN', name: 'Denver (Hub)' },
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
    { code: 'LAS', name: 'Las Vegas' },
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
    { code: 'MCO', name: 'Orlando' },
    { code: 'PSP', name: 'Palm Springs' },
    { code: 'PNS', name: 'Pensacola' },
    { code: 'PHL', name: 'Philadelphia' },
    { code: 'PHX', name: 'Phoenix' },
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
        ? `${apiBaseUrl}/realtime/departures/${airport}?airline=${frontierOnly ? 'F9' : 'ALL'}`
        : `${apiBaseUrl}/realtime/arrivals/${airport}?airline=${frontierOnly ? 'F9' : 'ALL'}`;
      
      const response = await fetch(endpoint, { headers: { ...getAuthHeader() } });
      
      // Ignore stale responses if airport/viewMode changed while fetching
      if (thisId !== fetchIdRef.current) return;

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      if (thisId !== fetchIdRef.current) return;

      setFlights(data.flights || []);
      setIsMockData(!!data.mock_data);
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
  }, [airport, viewMode, apiBaseUrl, frontierOnly]);

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
      // Format flight number
      let searchNumber = flightNumber.trim().toUpperCase().replace(/\s+/g, '');
      // Only prepend F9 if the input is purely numeric and in Frontier-only mode
      if (/^\d+$/.test(searchNumber) && frontierOnly) {
        searchNumber = `F9${searchNumber}`;
      }

      const response = await fetch(`${apiBaseUrl}/realtime/flight/${searchNumber}`, { headers: { ...getAuthHeader() } });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      // Backend wraps in {flight: ...}, but handle direct response too
      const flightData = data.flight || (data.flight_number ? data : null);
      setIsMockData(!!data.mock_data || !!(flightData && flightData.mock_data));
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

  const renderFlightRow = (flight, index) => {
    const isDelay = flight.delay && flight.delay !== 'On time';
    
    return (
      <div key={index} className={`realtime-flight-row ${getStatusClass(flight.status)} clickable`} onClick={() => setSelectedFlight(flight)}>
        <div className="flight-info-main">
          <div className="flight-number-cell">
            <span className="flight-number">{flight.flight_number}</span>
            <span className="airline-name">{flight.airline?.name || flight.airline_name || ''}</span>
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
              {formatStatus(flight)}
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

  return (
    <div className="realtime-flights-container">
      <div className="realtime-header">
        <h2>✈️ {frontierOnly ? "Real-Time Frontier Flights" : "Real-Time Flights"}</h2>
        <p className="realtime-subtitle">Live flight status powered by FlightRadar24</p>
        <div className="airline-toggle">
          <label className="toggle-switch">
            <input type="checkbox" checked={frontierOnly} onChange={() => setFrontierOnly(!frontierOnly)} />
            <span className="toggle-slider"></span>
          </label>
          <span className="toggle-label">{frontierOnly ? "✈️ Frontier Only" : "🌐 All Airlines"}</span>
        </div>
      </div>
      
      <div className="realtime-controls">
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
                        <span
                          className={`favorite-star ${favoriteAirport === apt.code ? 'active' : ''}`}
                          onClick={(e) => toggleFavorite(apt.code, e)}
                          title={favoriteAirport === apt.code ? 'Remove as default' : 'Set as default airport'}
                        >
                          {favoriteAirport === apt.code ? '★' : '☆'}
                        </span>
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
      
      {isMockData && (
        <div className="mock-data-banner">
          ⚠️ Showing simulated data — live API unavailable
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
      
      {!loading && singleFlight && <SingleFlightView flight={singleFlight} apiBaseUrl={apiBaseUrl} onBack={() => { setSingleFlight(null); fetchFlights(); }} />}
      
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
          <span>{frontierOnly ? `No Frontier flights found for ${airport}` : `No flights found for ${airport}`}</span>
        </div>
      )}
      
      {selectedFlight && (
        <RealTimeFlightDetail
          flight={selectedFlight}
          apiBaseUrl={apiBaseUrl}
          onClose={() => setSelectedFlight(null)}
        />
      )}

      <div className="search-flight-section" style={{ marginTop: '1.5rem' }}>
        <input
          type="text"
          placeholder={frontierOnly ? "Track a flight (e.g., 1234 or F91234)" : "Track a flight (e.g., AA1234, UA567)"}
          value={flightNumber}
          onChange={(e) => setFlightNumber(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && searchFlight()}
          className="flight-search-input"
        />
        <button onClick={searchFlight} className="search-flight-btn">
          Track
        </button>
      </div>

      <div className="realtime-footer">
        <span className="api-note">Real-time data via FlightRadar24</span>
      </div>
    </div>
  );
}

export default RealTimeFlights;
