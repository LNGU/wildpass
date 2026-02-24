import React, { useState, useEffect } from 'react';
import '../styles/BlackoutDatesModal.css';
import { getApiBaseUrl } from '../services/api';

const BlackoutDatesModal = ({ isOpen, onClose }) => {
  const [blackoutData, setBlackoutData] = useState(null);
  const [selectedYear, setSelectedYear] = useState('2026');
  const [lastUpdated, setLastUpdated] = useState(null);

  // Only load when modal opens
  useEffect(() => {
    if (isOpen) loadBlackoutDates();
  }, [isOpen]);

  // Update displayed periods when year changes - filter out past dates
  const allPeriods = blackoutData ? (blackoutData.blackout_periods[selectedYear] || []) : [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const blackoutPeriods = allPeriods.filter(period => {
    const year = new Date(period.start).getFullYear().toString();
    if (year !== selectedYear) return false;
    // Hide periods whose end date has already passed
    const [endY, endM, endD] = period.end.split('-').map(Number);
    const endDate = new Date(endY, endM - 1, endD);
    return endDate >= today;
  });

  const loadBlackoutDates = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/blackout-dates`);
      const data = await response.json();
      
      setLastUpdated(data.last_updated);
      setBlackoutData(data);
    } catch (error) {
      console.error('Failed to load blackout dates:', error);
      // Fallback to hardcoded 2026/2027 data
      const fallback = {
        '2026': [
          { start: '2026-01-01', end: '2026-01-01', description: "New Year's Day" },
          { start: '2026-01-03', end: '2026-01-04', description: 'Early January' },
          { start: '2026-01-15', end: '2026-01-16', description: 'MLK Weekend' },
          { start: '2026-01-19', end: '2026-01-19', description: 'MLK Day' },
          { start: '2026-02-12', end: '2026-02-13', description: "Valentine's/Presidents Day Weekend" },
          { start: '2026-02-16', end: '2026-02-16', description: 'Presidents Day' },
          { start: '2026-03-13', end: '2026-03-15', description: 'Spring Break Period' },
          { start: '2026-03-20', end: '2026-03-22', description: 'Spring Break Peak' },
          { start: '2026-03-27', end: '2026-03-29', description: 'Late Spring Break' },
          { start: '2026-04-03', end: '2026-04-06', description: 'Easter Weekend' },
          { start: '2026-04-10', end: '2026-04-12', description: 'Mid-April' },
          { start: '2026-05-21', end: '2026-05-22', description: 'Memorial Day Weekend' },
          { start: '2026-05-25', end: '2026-05-25', description: 'Memorial Day' },
          { start: '2026-06-25', end: '2026-06-28', description: 'Summer Start' },
          { start: '2026-07-02', end: '2026-07-06', description: 'Independence Day Weekend' },
          { start: '2026-09-03', end: '2026-09-04', description: 'Labor Day Weekend' },
          { start: '2026-09-07', end: '2026-09-07', description: 'Labor Day' },
          { start: '2026-10-08', end: '2026-10-09', description: 'Columbus Day Weekend' },
          { start: '2026-10-11', end: '2026-10-12', description: 'Mid-October' },
          { start: '2026-11-24', end: '2026-11-25', description: 'Thanksgiving' },
          { start: '2026-11-28', end: '2026-11-30', description: 'Post-Thanksgiving Weekend' },
          { start: '2026-12-19', end: '2026-12-24', description: 'Pre-Christmas' },
          { start: '2026-12-26', end: '2026-12-31', description: "Post-Christmas/New Year's" },
        ],
        '2027': [
          { start: '2027-01-01', end: '2027-01-03', description: "New Year's Holiday" },
          { start: '2027-01-14', end: '2027-01-15', description: 'MLK Weekend' },
          { start: '2027-01-18', end: '2027-01-18', description: 'MLK Day' },
          { start: '2027-02-11', end: '2027-02-12', description: "Valentine's/Presidents Day Weekend" },
          { start: '2027-02-15', end: '2027-02-15', description: 'Presidents Day' },
          { start: '2027-03-12', end: '2027-03-14', description: 'Spring Break Period' },
          { start: '2027-03-19', end: '2027-03-21', description: 'Spring Break Peak' },
          { start: '2027-03-26', end: '2027-03-29', description: 'Late Spring Break/Easter' },
          { start: '2027-04-02', end: '2027-04-04', description: 'Easter Weekend' },
        ]
      };
      setBlackoutData({ blackout_periods: fallback, last_updated: new Date().toISOString() });
    }
  };

  const formatDateRange = (start, end) => {
    // Parse as local date to avoid timezone issues
    // "2026-01-15" should display as Jan 15, not Jan 14
    const [startYear, startMonth, startDay] = start.split('-').map(Number);
    const [endYear, endMonth, endDay] = end.split('-').map(Number);
    
    const startDate = new Date(startYear, startMonth - 1, startDay);
    const endDate = new Date(endYear, endMonth - 1, endDay);
    
    const options = { month: 'short', day: 'numeric' };
    const startFormatted = startDate.toLocaleDateString('en-US', options);
    
    if (start === end) {
      return startFormatted;
    }
    
    const endFormatted = endDate.toLocaleDateString('en-US', options);
    return `${startFormatted} - ${endFormatted}`;
  };

  const groupByMonth = (periods) => {
    // Sort periods by start date first
    const sortedPeriods = [...periods].sort((a, b) => 
      new Date(a.start) - new Date(b.start)
    );
    
    const grouped = {};
    const monthOrder = [];
    
    sortedPeriods.forEach(period => {
      // Parse as local date to avoid timezone issues
      const [year, month, day] = period.start.split('-').map(Number);
      const date = new Date(year, month - 1, day);
      
      const monthName = date.toLocaleDateString('en-US', { month: 'long' });
      const yearNum = date.getFullYear();
      const monthYear = `${monthName} ${yearNum}`;
      
      if (!grouped[monthYear]) {
        grouped[monthYear] = [];
        monthOrder.push(monthYear);
      }
      grouped[monthYear].push(period);
    });
    
    // Return both grouped data and month order
    return { grouped, monthOrder };
  };

  if (!isOpen) return null;

  const { grouped: groupedPeriods, monthOrder } = groupByMonth(blackoutPeriods);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🚫 GoWild Pass Blackout Dates</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div className="year-selector">
            <button 
              className={selectedYear === '2026' ? 'year-btn active' : 'year-btn'}
              onClick={() => setSelectedYear('2026')}
            >
              2026
            </button>
            <button 
              className={selectedYear === '2027' ? 'year-btn active' : 'year-btn'}
              onClick={() => setSelectedYear('2027')}
            >
              2027
            </button>
          </div>

          <div className="blackout-info">
            <p>
              <strong>⚠️ Important:</strong> GoWild Pass cannot be used for flights on these dates. 
              Regular fares apply during blackout periods.
            </p>
          </div>

          <div className="blackout-list">
            {monthOrder.length === 0 ? (
              <p className="no-data">No blackout dates available for {selectedYear}</p>
            ) : (
              monthOrder.map((monthYear) => (
                <div key={monthYear} className="month-section">
                  <h3>{monthYear}</h3>
                  <ul>
                    {groupedPeriods[monthYear].map((period, index) => (
                      <li key={index} className="blackout-item">
                        <span className="date-range">{formatDateRange(period.start, period.end)}</span>
                        <span className="description">{period.description}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))
            )}
          </div>

          <div className="modal-footer">
            {lastUpdated && (
              <p className="last-updated">
                Last updated: {new Date(lastUpdated).toLocaleDateString()}
              </p>
            )}
            <p className="disclaimer">
              * Blackout dates are subject to change. Please verify with Frontier Airlines 
              before booking.
            </p>
            <p className="official-link">
              <a 
                href="https://www.flyfrontier.com/frontiermiles/terms-and-conditions/#GoWild!_Pass" 
                target="_blank" 
                rel="noopener noreferrer"
              >
                📄 View Official Frontier GoWild Pass Terms & Conditions
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlackoutDatesModal;
