#!/bin/bash

# Port defined in main.go
PORT=28964
API_URL="http://localhost:$PORT/api/v1/trade"

echo "Starting simulation of trades..."

# BTCUSDT LONG
curl -s -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT", "side": "LONG", "amount_usdt": 1000, "reason": "Simulation: Bullish trend", "type": "SQUEEZE_ARBITRAGE", "funding_rate": 0.0001}' | grep -q "success" && echo " - BTCUSDT LONG added"

# ETHUSDT LONG
curl -s -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"symbol": "ETHUSDT", "side": "LONG", "amount_usdt": 800, "reason": "Simulation: Ethereum upgrade", "type": "SQUEEZE_ARBITRAGE", "funding_rate": 0.0001}' | grep -q "success" && echo " - ETHUSDT LONG added"

# SOLUSDT SHORT
curl -s -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"symbol": "SOLUSDT", "side": "SHORT", "amount_usdt": 500, "reason": "Simulation: Local resistance", "type": "SQUEEZE_ARBITRAGE", "funding_rate": 0.0001}' | grep -q "success" && echo " - SOLUSDT SHORT added"

echo "Simulation complete. Check your dashboard."
