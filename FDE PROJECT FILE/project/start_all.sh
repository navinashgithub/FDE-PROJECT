#!/bin/bash

echo "🚀 Starting Financial Market Data Streaming System"
echo "=================================================="

echo "✓ Step 1: Starting Docker infrastructure..."
docker-compose up -d

echo "⏳ Waiting for services to initialize (30 seconds)..."
sleep 30

echo "✓ Step 2: Starting Market Data Producer..."
python -m src.producers.market_api_streamer &
PRODUCER_PID=$!

echo "⏳ Waiting for producer to connect (5 seconds)..."
sleep 5

echo "✓ Step 3: Starting Spark Stream Processor..."
python -m src.consumers.stream_processor &
CONSUMER_PID=$!

echo "⏳ Waiting for stream processor (5 seconds)..."
sleep 5

echo "✓ Step 4: Starting REST API..."
python -m src.api.rest_api &
API_PID=$!

echo "✓ Step 5: Starting WebSocket Server..."
python -m src.api.websocket_server &
WS_PID=$!

echo "✓ Step 6: Starting Dashboard..."
python -m src.dashboard.realtime_dashboard &
DASHBOARD_PID=$!

echo "✓ Step 7: Starting Anomaly Detector..."
python -m src.monitoring.anomaly_detector &
ANOMALY_PID=$!

echo "✓ Step 8: Starting Metrics Collector..."
python -m src.monitoring.metrics_collector &
METRICS_PID=$!

echo ""
echo "✅ All services started successfully!"
echo ""
echo "Access Points:"
echo "  Dashboard:  http://localhost:8050"
echo "  REST API:   http://localhost:8000"
echo "  API Docs:   http://localhost:8000/docs"
echo "  Grafana:    http://localhost:3000 (admin/admin)"
echo "  Prometheus: http://localhost:9090"
echo "  Spark UI:   http://localhost:8080"
echo ""
echo "Process IDs:"
echo "  Producer: $PRODUCER_PID"
echo "  Consumer: $CONSUMER_PID"
echo "  API: $API_PID"
echo "  WebSocket: $WS_PID"
echo "  Dashboard: $DASHBOARD_PID"
echo "  Anomaly: $ANOMALY_PID"
echo "  Metrics: $METRICS_PID"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

trap "kill $PRODUCER_PID $CONSUMER_PID $API_PID $WS_PID $DASHBOARD_PID $ANOMALY_PID $METRICS_PID 2>/dev/null" EXIT

wait
