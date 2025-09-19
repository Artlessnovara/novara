#!/bin/bash
python -u app.py > app_output.log 2>&1 &
APP_PID=$!
sleep 5
python jules-scratch/verification/verify_discover_feed.py
kill $APP_PID
