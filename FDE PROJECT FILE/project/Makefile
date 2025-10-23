.PHONY: help install start stop restart logs clean test

help:
	@echo "Market Data Streaming System - Commands:"
	@echo "  make install       - Install Python dependencies"
	@echo "  make start         - Start all Docker services"
	@echo "  make stop          - Stop all Docker services"
	@echo "  make restart       - Restart all services"
	@echo "  make logs          - Show Docker logs"
	@echo "  make clean         - Clean up containers and volumes"
	@echo "  make producer      - Start market data producer"
	@echo "  make consumer      - Start Spark stream processor"
	@echo "  make api           - Start REST API server"
	@echo "  make websocket     - Start WebSocket server"
	@echo "  make dashboard     - Start Dash dashboard"
	@echo "  make anomaly       - Start anomaly detector"
	@echo "  make metrics       - Start metrics collector"
	@echo "  make train-ml      - Train ML prediction models"
	@echo "  make test          - Run tests"

install:
	pip install -r requirements.txt

start:
	docker-compose up -d
	@echo "Waiting for services to start..."
	@sleep 10
	@echo "Services started successfully!"

stop:
	docker-compose down

restart: stop start

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	rm -rf data/processed/*
	rm -rf data/parquet/*
	rm -rf logs/*
	rm -rf models/*

producer:
	python -m src.producers.market_api_streamer

consumer:
	python -m src.consumers.stream_processor

api:
	python -m src.api.rest_api

websocket:
	python -m src.api.websocket_server

dashboard:
	python -m src.dashboard.realtime_dashboard

anomaly:
	python -m src.monitoring.anomaly_detector

metrics:
	python -m src.monitoring.metrics_collector

train-ml:
	python -m src.analytics.price_predictor

test:
	pytest tests/ -v
