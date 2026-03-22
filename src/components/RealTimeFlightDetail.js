import React, { useState, useEffect, useRef } from 'react';
import { getAuthHeader } from '../services/auth';
import './RealTimeFlightDetail.css';

/* global L */

function RealTimeFlightDetail({ flight, apiBaseUrl, onClose }) {
  const [liveData, setLiveData] = useState(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);

  const isActive = flight.status === 'active';

  useEffect(() => {
    if (!isActive) return;
    setLiveLoading(true);
    fetch(`${apiBaseUrl}/realtime/flight/${flight.flight_number}/live`, {
      headers: { ...getAuthHeader() },
    })
      .then(r => r.json())
      .then(data => {
        if (data.live) setLiveData(data);
        setLiveLoading(false);
      })
      .catch(() => setLiveLoading(false));
  }, [flight.flight_number, isActive, apiBaseUrl]);

  useEffect(() => {
    if (!liveData || !mapRef.current || mapInstanceRef.current) return;
    if (typeof L === 'undefined') return;

    const map = L.map(mapRef.current, {
      center: [liveData.latitude, liveData.longitude],
      zoom: 6,
      zoomControl: false,
      attributionControl: false,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
    }).addTo(map);

    const planeIcon = L.divIcon({
      html: '<div style="font-size:24px;transform:rotate(' + (liveData.heading || 0) + 'deg)">✈️</div>',
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      className: 'plane-marker',
    });
    L.marker([liveData.latitude, liveData.longitude], { icon: planeIcon }).addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [liveData]);

  const formatTs = (ts, tz) => {
    if (!ts) return '--:--';
    const d = new Date(ts * 1000);
    const opts = { hour: '2-digit', minute: '2-digit' };
    if (tz) opts.timeZone = tz;
    try {
      return d.toLocaleTimeString('en-US', opts);
    } catch {
      return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }
  };

  const calcDelay = (sched, actual) => {
    if (!sched || !actual) return null;
    return Math.round((actual - sched) / 60);
  };

  const depDelay = calcDelay(
    flight.scheduled_departure_ts,
    flight.actual_departure_ts || flight.estimated_departure_ts
  );
  const arrDelay = calcDelay(
    flight.scheduled_arrival_ts,
    flight.actual_arrival_ts || flight.estimated_arrival_ts
  );

  const durationStr = flight.duration_minutes
    ? Math.floor(flight.duration_minutes / 60) + 'h ' + (flight.duration_minutes % 60) + 'm'
    : null;

  const delayClass = (mins) => {
    if (mins === null || mins === undefined) return '';
    if (mins <= 0) return 'on-time';
    if (mins <= 15) return 'slight-delay';
    return 'delayed';
  };

  const delayText = (mins) => {
    if (mins === null || mins === undefined) return '';
    if (mins <= 0) return 'On time';
    return '+' + mins + ' min';
  };

  return (
    <div className="rtfd-overlay" onClick={onClose}>
      <div className="rtfd-modal" onClick={e => e.stopPropagation()}>
        <button className="rtfd-close" onClick={onClose}>&times;</button>

        <div className="rtfd-header">
          <div className="rtfd-flight-id">
            <span className="rtfd-fn">{flight.flight_number}</span>
            <span className="rtfd-airline">{flight.airline?.name || ''}</span>
          </div>
          <span className={'rtfd-status-badge ' + flight.status}>
            {flight.status_display || flight.status}
          </span>
          {durationStr && <span className="rtfd-duration">🕐 {durationStr}</span>}
        </div>

        <div className="rtfd-route">
          <div className="rtfd-airport origin">
            <div className="rtfd-code">{flight.origin}</div>
            <div className="rtfd-city">{flight.origin_city_name || flight.origin_city || ''}</div>
            <div className="rtfd-airport-name">{flight.origin_airport_name || ''}</div>
            <div className="rtfd-info-tags">
              {flight.origin_terminal && <span className="rtfd-tag">T{flight.origin_terminal}</span>}
              {flight.origin_gate && <span className="rtfd-tag">Gate {flight.origin_gate}</span>}
              {flight.origin_baggage && <span className="rtfd-tag">🧳 {flight.origin_baggage}</span>}
            </div>
          </div>
          <div className="rtfd-arrow">
            <div className="rtfd-line"></div>
            <span>✈️</span>
            <div className="rtfd-line"></div>
          </div>
          <div className="rtfd-airport dest">
            <div className="rtfd-code">{flight.destination}</div>
            <div className="rtfd-city">{flight.dest_city_name || flight.destination_city || ''}</div>
            <div className="rtfd-airport-name">{flight.dest_airport_name || ''}</div>
            <div className="rtfd-info-tags">
              {flight.dest_terminal && <span className="rtfd-tag">T{flight.dest_terminal}</span>}
              {flight.dest_gate && <span className="rtfd-tag">Gate {flight.dest_gate}</span>}
              {flight.dest_baggage && <span className="rtfd-tag">🧳 {flight.dest_baggage}</span>}
            </div>
          </div>
        </div>

        <div className="rtfd-times">
          <div className="rtfd-time-block">
            <h4>Departure</h4>
            <div className="rtfd-time-row">
              <span className="rtfd-label">Scheduled</span>
              <span className="rtfd-val">{formatTs(flight.scheduled_departure_ts, flight.origin_timezone)}</span>
            </div>
            {(flight.estimated_departure_ts || flight.actual_departure_ts) && (
              <div className={'rtfd-time-row ' + delayClass(depDelay)}>
                <span className="rtfd-label">{flight.actual_departure_ts ? 'Actual' : 'Estimated'}</span>
                <span className="rtfd-val">
                  {formatTs(flight.actual_departure_ts || flight.estimated_departure_ts, flight.origin_timezone)}
                </span>
                {depDelay !== null && (
                  <span className={'rtfd-delay ' + delayClass(depDelay)}>{delayText(depDelay)}</span>
                )}
              </div>
            )}
          </div>
          <div className="rtfd-time-block">
            <h4>Arrival</h4>
            <div className="rtfd-time-row">
              <span className="rtfd-label">Scheduled</span>
              <span className="rtfd-val">{formatTs(flight.scheduled_arrival_ts, flight.dest_timezone)}</span>
            </div>
            {(flight.estimated_arrival_ts || flight.actual_arrival_ts) && (
              <div className={'rtfd-time-row ' + delayClass(arrDelay)}>
                <span className="rtfd-label">{flight.actual_arrival_ts ? 'Actual' : 'Estimated'}</span>
                <span className="rtfd-val">
                  {formatTs(flight.actual_arrival_ts || flight.estimated_arrival_ts, flight.dest_timezone)}
                </span>
                {arrDelay !== null && (
                  <span className={'rtfd-delay ' + delayClass(arrDelay)}>{delayText(arrDelay)}</span>
                )}
              </div>
            )}
          </div>
        </div>

        {(flight.aircraft_model_text || flight.aircraft_registration || flight.callsign) && (
          <div className="rtfd-aircraft">
            {flight.aircraft_model_text && <span>🛩️ {flight.aircraft_model_text}</span>}
            {flight.aircraft_registration && <span>Reg: {flight.aircraft_registration}</span>}
            {flight.callsign && <span>Callsign: {flight.callsign}</span>}
          </div>
        )}

        {isActive && (
          <div className="rtfd-live-section">
            <h4>📡 Live Position</h4>
            {liveLoading && <div className="rtfd-loading">Loading live data...</div>}
            {!liveLoading && !liveData && (
              <div className="rtfd-no-live">Flight not currently trackable</div>
            )}
            {liveData && (
              <>
                <div className="rtfd-map" ref={mapRef}></div>
                <div className="rtfd-live-stats">
                  <div><span>Altitude</span><strong>{liveData.altitude ? liveData.altitude.toLocaleString() : '—'} ft</strong></div>
                  <div><span>Speed</span><strong>{liveData.ground_speed || '—'} kts</strong></div>
                  <div><span>Heading</span><strong>{liveData.heading || '—'}°</strong></div>
                  {liveData.vertical_speed != null && (
                    <div><span>V/S</span><strong>{liveData.vertical_speed} ft/min</strong></div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default RealTimeFlightDetail;
