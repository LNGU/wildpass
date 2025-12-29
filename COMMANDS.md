# Common Commands

Quick reference for common tasks when working with WildPass.

## Starting the Application

### Start Both Servers (Recommended)

Open two terminal windows:

**Terminal 1 - Frontend:**
```bash
npm start
```

**Terminal 2 - Backend:**
```bash
cd backend
python app.py
```

### Alternative: One-Line Background Start

```bash
# Start backend in background
cd backend && python app.py &

# Start frontend (will open browser)
npm start
```

To stop the background backend:
```bash
# Find the process
lsof -i :5001

# Kill it (replace PID with actual process ID)
kill <PID>
```

## Development

### Install/Update Dependencies

**Frontend:**
```bash
npm install
```

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

### Environment Configuration

**Create environment files:**
```bash
# Frontend
cp .env.example .env

# Backend
cd backend
cp .env.example .env
```

**Edit backend credentials:**
```bash
# Mac/Linux
nano backend/.env

# Or use your preferred editor
code backend/.env  # VS Code
vim backend/.env   # Vim
```

## Testing

### Test Backend API

**Health check:**
```bash
curl http://localhost:5001/api/health
```

**Test with mock data (no API calls):**
```bash
# In backend/.env, set:
DEV_MODE=true

# Then restart backend
cd backend
python app.py
```

### Test Amadeus Connection

```bash
cd backend
python test_amadeus.py
```

### Test Streaming Endpoint

```bash
cd backend
python test_streaming.py
```

## Caching

### Clear Server Cache

**Via API:**
```bash
curl -X POST http://localhost:5001/api/cache/clear
```

**Via UI:**
- Click "Clear Cache" button in the footer

### Check Cache Stats

```bash
curl http://localhost:5001/api/cache/stats
```

### Clear Browser Cache

- Click "Clear Cache" in the app footer
- Or manually clear localStorage in browser DevTools

## Building for Production

### Build Frontend

```bash
npm run build
```

This creates an optimized production build in the `build/` directory.

### Production Backend

For production, use a WSGI server instead of Flask's development server:

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
cd backend
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

## Troubleshooting

### Check What's Running on Ports

```bash
# Check port 3000 (frontend)
lsof -i :3000

# Check port 5001 (backend)
lsof -i :5001
```

### Kill Process on Port

```bash
# Kill process on port 5001
lsof -ti :5001 | xargs kill -9

# Kill process on port 3000
lsof -ti :3000 | xargs kill -9
```

### View Backend Logs

Backend logs appear in the terminal where you ran `python app.py`. For more detailed logging:

```bash
# Run with Python's verbose flag
python -v app.py

# Or redirect output to file
python app.py > backend.log 2>&1
```

### Reset Everything

```bash
# Stop all processes
lsof -ti :3000 | xargs kill -9
lsof -ti :5001 | xargs kill -9

# Clear caches
rm -rf node_modules/.cache
curl -X POST http://localhost:5001/api/cache/clear

# Reinstall dependencies
npm install
cd backend && pip install -r requirements.txt
```

## Git Commands

### Check Status
```bash
git status
```

### Add Files
```bash
# Add specific files
git add README.md SETUP.md

# Add all changes (be careful!)
git add .
```

### Commit
```bash
git commit -m "Your commit message"
```

### Push to GitHub
```bash
git push origin main
```

### Check What's Ignored
```bash
git check-ignore backend/.env
git status --ignored
```

## Environment Variables Quick Reference

### Frontend (.env)
```env
REACT_APP_API_URL=http://localhost:5001/api
```

### Backend (backend/.env)
```env
AMADEUS_API_KEY=your_key_here
AMADEUS_API_SECRET=your_secret_here
DEV_MODE=false  # Set to true for mock data
```

## Common Issues

### "Module not found" errors
```bash
npm install  # Frontend
cd backend && pip install -r requirements.txt  # Backend
```

### Port already in use
```bash
# Kill the process using the port
lsof -ti :5001 | xargs kill -9
```

### API rate limit exceeded
```bash
# Wait 60 seconds, or use dev mode
# In backend/.env: DEV_MODE=true
```

### Changes not reflecting
```bash
# Restart both servers
# Frontend: Ctrl+C, then npm start
# Backend: Ctrl+C, then python app.py
```

---

For more help, see [SETUP.md](SETUP.md) or [README.md](README.md).
