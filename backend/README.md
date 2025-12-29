# WildPass Backend - Frontier Airlines Scraper

Flask-based API that scrapes flight data from Frontier Airlines and serves it to the React frontend.

## Features

- Scrapes flight availability and pricing from Frontier Airlines
- Supports multiple origin and destination airports
- In-memory caching (1-hour expiration)
- GoWild Pass fare filtering
- Rate limiting to avoid blocking

## Setup

### Prerequisites

- Python 3.7+
- pip

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Server

```bash
python app.py
```

The API will run on `http://localhost:5001` (using 5001 to avoid conflicts with macOS AirPlay on port 5000)

## API Endpoints

### POST /api/search

Search for flights based on parameters.

**Request Body:**
```json
{
  "origins": ["DEN", "LAX"],
  "destinations": ["MCO", "MIA"],
  "tripType": "round-trip",
  "departureDate": "2025-06-15",
  "returnDate": "2025-06-20"
}
```

**Response:**
```json
{
  "flights": [...],
  "cached": false,
  "searchParams": {...},
  "count": 10
}
```

### GET /api/destinations

Get list of all Frontier destinations.

**Response:**
```json
{
  "destinations": ["ATL", "DEN", "LAS", ...],
  "count": 48
}
```

### GET /api/health

Health check endpoint.

### POST /api/cache/clear

Clear the flight cache.

### GET /api/cache/stats

Get cache statistics.

## Scraper Implementation Notes

The current scraper implementation (`scraper.py`) provides the structure for scraping Frontier Airlines. However, the actual HTML parsing logic needs to be customized based on Frontier's current website structure.

### To Complete the Implementation:

1. Visit Frontier's booking page and inspect the HTML/JavaScript
2. Update the `parse_flight_data()` method to extract the flight data correctly
3. The data is typically embedded in `<script>` tags as JSON
4. Look for objects containing `journeys`, `flights`, and `isGoWildFareEnabled` fields

### Rate Limiting

The scraper includes random delays (2-5 seconds) between requests to avoid overwhelming Frontier's servers. Adjust as needed.

## Caching

Results are cached in memory for 1 hour. This reduces load on Frontier's servers and improves response time for repeat searches.

To clear the cache:
```bash
curl -X POST http://localhost:5001/api/cache/clear
```

## Development

To run in debug mode (auto-reload on changes):
```bash
python app.py
```

Debug mode is enabled by default in `app.py`.
