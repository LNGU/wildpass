import React, { useState, useEffect } from 'react';
import { getAuthHeader } from '../services/auth';
import './PriceTracker.css';

function PriceTracker({ apiBaseUrl }) {
  const [priceData, setPriceData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [error, setError] = useState(null);

  const fetchPrices = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/prices/icn-sea`, {
        headers: { ...getAuthHeader() },
      });
      if (!res.ok) throw new Error('Failed to fetch prices');
      const data = await res.json();
      setPriceData(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const triggerScrape = async () => {
    setScraping(true);
    try {
      const res = await fetch(`${apiBaseUrl}/prices/icn-sea/scrape`, {
        method: 'POST',
        headers: { ...getAuthHeader() },
      });
      if (!res.ok) throw new Error('Scrape failed');
      await fetchPrices();
    } catch (e) {
      setError(e.message);
    } finally {
      setScraping(false);
    }
  };

  useEffect(() => {
    fetchPrices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getLatestSnapshot = () => {
    if (!priceData?.snapshots?.length) return null;
    return priceData.snapshots[priceData.snapshots.length - 1];
  };

  const getPriceHistory = () => {
    if (!priceData?.snapshots?.length) return [];
    const history = [];
    for (const snap of priceData.snapshots) {
      const date = new Date(snap.scraped_at).toLocaleDateString();
      for (const d of snap.dates || []) {
        history.push({
          scraped: date,
          travelDate: d.travel_date,
          lowest: d.lowest_price,
        });
      }
    }
    return history;
  };

  const latest = getLatestSnapshot();
  const history = getPriceHistory();

  // Find overall lowest
  const allPrices = history.filter(h => h.lowest).map(h => h.lowest);
  const overallLowest = allPrices.length ? Math.min(...allPrices) : null;
  const overallHighest = allPrices.length ? Math.max(...allPrices) : null;

  return (
    <div className="price-tracker-container">
      <div className="price-tracker-header">
        <h2>ICN to SEA Price Tracker</h2>
        <p className="price-subtitle">Nonstop flights from Seoul Incheon to Seattle</p>
      </div>

      {loading && <div className="price-loading">Loading price data...</div>}
      {error && <div className="price-error">{error}</div>}

      {!loading && latest && (
        <>
          <div className="price-summary">
            {overallLowest && (
              <div className="price-stat">
                <span className="stat-label">Lowest Seen</span>
                <span className="stat-value low">${overallLowest}</span>
              </div>
            )}
            {overallHighest && overallHighest !== overallLowest && (
              <div className="price-stat">
                <span className="stat-label">Highest Seen</span>
                <span className="stat-value high">${overallHighest}</span>
              </div>
            )}
            <div className="price-stat">
              <span className="stat-label">Last Checked</span>
              <span className="stat-value">{new Date(latest.scraped_at).toLocaleString()}</span>
            </div>
          </div>

          <div className="price-dates">
            <h3>Current Prices</h3>
            <div className="date-cards">
              {latest.dates?.map((d, i) => (
                <div key={i} className={`date-card ${d.lowest_price === overallLowest ? 'best-price' : ''}`}>
                  <div className="date-card-header">
                    <span className="travel-date">{new Date(d.travel_date + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</span>
                    <span className="lowest-price">${d.lowest_price}</span>
                  </div>
                  <div className="flight-options">
                    {d.flights?.map((f, j) => (
                      <div key={j} className="flight-option">
                        <span className="fo-airline">{f.airline}</span>
                        <span className="fo-time">{f.departure?.split(' on ')[0]} - {f.arrival?.split(' on ')[0]}</span>
                        <span className="fo-duration">{f.duration}</span>
                        <span className="fo-price">{f.price}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {history.length > 3 && (
            <div className="price-history">
              <h3>Price History</h3>
              <div className="history-table">
                <div className="history-header">
                  <span>Checked</span>
                  <span>Travel Date</span>
                  <span>Lowest</span>
                </div>
                {history.slice().reverse().map((h, i) => (
                  <div key={i} className={`history-row ${h.lowest === overallLowest ? 'best' : ''}`}>
                    <span>{h.scraped}</span>
                    <span>{h.travelDate}</span>
                    <span>${h.lowest}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {!loading && !latest && (
        <div className="no-prices">
          <p>No price data yet. Click refresh to scrape current prices.</p>
        </div>
      )}

      <button className="scrape-button" onClick={triggerScrape} disabled={scraping}>
        {scraping ? 'Checking prices...' : 'Refresh Prices'}
      </button>
    </div>
  );
}

export default PriceTracker;
