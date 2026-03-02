#!/bin/bash
export PATH=$PATH:~/go_dist/go/bin
cd /root/.openclaw/workspace/crypto_dashboard

# Stop existing processes
pkill -9 -f crypto_pro_daemon || true
pkill -9 -f agent_squeeze_hunter.py || true
pkill -9 -f agent_trend_catcher.py || true

# Start Go Engine
nohup ./crypto_pro_daemon > quant_engine.log 2>&1 &

# Wait for Go engine to warm up
sleep 3

# Start Python Agents
nohup python3 agent_squeeze_hunter.py > squeeze_hunter.log 2>&1 &
nohup python3 agent_trend_catcher.py > trend_catcher.log 2>&1 &

echo "All services started."
