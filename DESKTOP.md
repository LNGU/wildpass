# WildPass Desktop App

This desktop version bundles the WildPass flight finder into a standalone application.

## Development

Run the desktop app in development mode:

```bash
npm run electron-dev
```

This will:
1. Start the React development server
2. Start the Python backend
3. Launch the Electron window

## Building

### Windows
```bash
npm run electron-build-win
```

### macOS
```bash
npm run electron-build-mac
```

### Linux
```bash
npm run electron-build-linux
```

The built application will be in the `dist/` folder.

## Requirements

Before building, ensure:
1. Python 3.7+ is installed and in PATH
2. Backend dependencies are installed: `cd backend && pip install -r requirements.txt`
3. Amadeus API credentials are configured in `backend/.env`

## Distribution

The packaged app includes:
- React frontend (bundled)
- Python backend (with dependencies)
- Electron wrapper

Users don't need to install Node.js or Python separately.
