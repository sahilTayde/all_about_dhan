#!/bin/bash
# Stop market data recorder

set -e

if [ ! -f /tmp/recorder.pid ]; then
    echo "Recorder PID file not found. Is it running?"
    exit 1
fi

PID=$(cat /tmp/recorder.pid)

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "Recorder (PID: $PID) is not running"
    rm -f /tmp/recorder.pid
    exit 0
fi

echo "Stopping recorder (PID: $PID)..."
kill -SIGTERM "$PID"

# Wait for graceful shutdown (max 10 seconds)
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Recorder stopped"
        rm -f /tmp/recorder.pid
        exit 0
    fi
    sleep 1
done

# Force kill if still running
if ps -p "$PID" > /dev/null 2>&1; then
    echo "Recorder did not stop gracefully, forcing kill..."
    kill -SIGKILL "$PID"
    rm -f /tmp/recorder.pid
    echo "Recorder killed"
fi
