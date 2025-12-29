// Mock flight data structure
// This represents what we'll get from scraping Frontier Airlines later

export const mockFlights = [
  {
    origin: 'DEN',
    destination: 'MCO',
    price: 89,
    departureDate: '2025-06-15',
    departureTime: '08:30 AM',
    arrivalDate: '2025-06-15',
    arrivalTime: '02:45 PM',
    duration: '3h 15m',
    stops: 0,
    airline: 'Frontier Airlines',
    flightNumber: 'F9-1234',
  },
  {
    origin: 'LAX',
    destination: 'LAS',
    price: 45,
    departureDate: '2025-06-16',
    departureTime: '10:00 AM',
    arrivalDate: '2025-06-16',
    arrivalTime: '11:15 AM',
    duration: '1h 15m',
    stops: 0,
    airline: 'Frontier Airlines',
    flightNumber: 'F9-5678',
  },
  {
    origin: 'SFO',
    destination: 'MIA',
    price: 129,
    departureDate: '2025-06-17',
    departureTime: '06:45 AM',
    arrivalDate: '2025-06-17',
    arrivalTime: '03:20 PM',
    duration: '5h 35m',
    stops: 0,
    airline: 'Frontier Airlines',
    flightNumber: 'F9-9012',
  },
];

// Structure for what we'll scrape from Frontier
export const flightDataStructure = {
  origin: 'string',          // Origin airport code
  destination: 'string',      // Destination airport code
  price: 'number',            // Price in USD
  departureDate: 'string',    // Format: YYYY-MM-DD
  departureTime: 'string',    // Format: HH:MM AM/PM
  arrivalDate: 'string',      // Format: YYYY-MM-DD
  arrivalTime: 'string',      // Format: HH:MM AM/PM
  duration: 'string',         // Format: Xh Ym
  stops: 'number',            // Number of stops
  airline: 'string',          // Airline name
  flightNumber: 'string',     // Flight number
};
