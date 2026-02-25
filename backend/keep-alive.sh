#!/bin/bash
# keep-alive.sh — Ping WildPass backend every 5 minutes to prevent Render cold starts
# 
# Usage:
#   1. Make executable:  chmod +x keep-alive.sh
#   2. Add to crontab:   crontab -e
#      Then add:          */5 * * * * /path/to/keep-alive.sh >> /tmp/wildpass-keepalive.log 2>&1
#
# Or use a free service like https://cron-job.org to hit the URL every 5 minutes.

BACKEND_URL="${WILDPASS_BACKEND_URL:-https://your-wildpass-backend.onrender.com}"

curl -sf "${BACKEND_URL}/health" -o /dev/null && echo "$(date): OK" || echo "$(date): FAIL"
