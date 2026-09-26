#!/bin/bash
# Start market data recorder
# Usage: ./scripts/start_recorder.sh [--dry-run]

set -e

cd "$(dirname "$0")/.."

# Check if recorder is already running
if [ -f /tmp/recorder.pid ]; then
    OLD_PID=$(cat /tmp/recorder.pid)
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Recorder already running (PID: $OLD_PID)"
        exit 1
    fi
fi

# Parse arguments
DRY_RUN=""
if [ "$1" = "--dry-run" ]; then
    DRY_RUN="--dry-run"
    echo "Starting recorder in DRY-RUN mode"
else
    echo "Starting recorder in PRODUCTION mode"
    
    # Check credentials
    if [ -z "$DHAN_CLIENT_ID" ] || [ -z "$DHAN_ACCESS_TOKEN" ]; then
        echo "ERROR: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set for production mode"
        echo "Set them in .env or export them:"
        echo "  export DHAN_CLIENT_ID='your_client_id'"
        echo "  export DHAN_ACCESS_TOKEN='your_access_token'"
        exit 1
    fi
fi

# Start recorder in background
nohup python3 -m data_recorder.runner $DRY_RUN > /tmp/recorder.log 2>&1 &
PID=$!

echo $PID > /tmp/recorder.pid
echo "Recorder started (PID: $PID)"
echo "Logs: /tmp/recorder.log"
echo "Heartbeat: data/recon/recorder_heartbeat.jsonl"
echo ""
echo "To stop: ./scripts/stop_recorder.sh"
echo "To check status: tail -f /tmp/recorder.log"
