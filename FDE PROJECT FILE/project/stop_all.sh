#!/bin/bash

echo "🛑 Stopping Financial Market Data Streaming System"
echo "=================================================="

echo "Stopping Python processes..."
pkill -f "src.producers.market_api_streamer"
pkill -f "src.consumers.stream_processor"
pkill -f "src.api.rest_api"
pkill -f "src.api.websocket_server"
pkill -f "src.dashboard.realtime_dashboard"
pkill -f "src.monitoring.anomaly_detector"
pkill -f "src.monitoring.metrics_collector"

echo "Stopping Docker containers..."
docker-compose down

echo "✅ All services stopped successfully!"
