# Fly.io Dockerfile for WildPass Backend
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
