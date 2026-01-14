# Blackout Dates Auto-Update System

## Overview
The WildPass app automatically checks Frontier Airlines' website for updated GoWild Pass blackout dates every 30 days and on each app startup.

## How It Works

### 1. Automatic Updates
- **On Startup**: Backend checks if blackout dates need updating when the app starts
- **Monthly Check**: Updates are fetched if the last update was more than 30 days ago
- **Cache System**: Data is cached locally in `backend/blackout_cache.json`

### 2. Data Source
- **URL**: https://www.flyfrontier.com/frontiermiles/terms-and-conditions/#GoWild!_Pass
- **Scraper**: `backend/blackout_updater.py` uses BeautifulSoup to extract dates
- **Fallback**: If scraping fails, uses hardcoded data from `gowild_blackout.py`

### 3. API Endpoints

#### Get Blackout Dates
```
GET http://localhost:5001/api/blackout-dates
```
Returns all blackout periods with last updated timestamp.

#### Manual Refresh
```
POST http://localhost:5001/api/blackout-dates/refresh
```
Forces an immediate update from Frontier's website.

## File Structure

```
backend/
├── blackout_updater.py       # Web scraper and update logic
├── blackout_cache.json        # Cached blackout data (auto-generated)
├── gowild_blackout.py         # Fallback data and blackout checking logic
└── app.py                     # Flask server with API endpoints

src/
└── components/
    └── BlackoutDatesModal.js  # Frontend modal displaying dates
```

## Configuration

### Update Frequency
Edit `backend/blackout_updater.py`:
```python
UPDATE_INTERVAL_DAYS = 30  # Change to desired interval
```

### Blackout Cache Location
```python
CACHE_FILE = "blackout_cache.json"  # Relative to backend/
```

## Manual Operations

### Force Update
```powershell
cd backend
python blackout_updater.py
```

### Clear Cache
Delete the cache file to force a fresh update:
```powershell
rm backend/blackout_cache.json
```

### View Cache
```powershell
cat backend/blackout_cache.json
```

## Data Format

```json
{
  "last_updated": "2026-01-13T21:10:37.336594",
  "blackout_periods": {
    "2026": [
      {
        "start": "2026-01-01",
        "end": "2026-01-01",
        "description": "New Year's Day"
      }
    ],
    "2027": [...],
    "2028": [...]
  },
  "source": "https://www.flyfrontier.com/..."
}
```

## Frontend Display

The blackout dates modal:
- **Default Year**: 2026 (2025 data removed)
- **Year Selector**: 2026, 2027 buttons
- **Last Updated**: Shows timestamp from backend
- **Fallback**: Displays hardcoded data if API fails

## Troubleshooting

### Updates Not Working
1. Check internet connection
2. Verify Frontier's website structure hasn't changed
3. Check backend console for error messages
4. Try manual refresh via API

### Missing Dates
- Scraper may need adjustment if Frontier changes their HTML structure
- Edit `blackout_updater.py` to improve date parsing

### Stale Data
- Delete `blackout_cache.json` and restart backend
- Or call POST `/api/blackout-dates/refresh`

## Future Enhancements

- [ ] Better HTML parsing for more accurate date extraction
- [ ] Description extraction from surrounding context
- [ ] Email notifications when new blackout periods are detected
- [ ] Admin panel to manually edit blackout dates
- [ ] Support for multiple sources/validation

## Dependencies

```
beautifulsoup4==4.12.0
requests==2.31.0
flask==3.1.2
```

All dependencies are in `backend/requirements.txt`.
