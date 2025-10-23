# Financial Market Data Streaming System

A production-grade real-time financial market data streaming system with comprehensive analytics, monitoring, and visualization capabilities.

## Features

- **Real-Time Data Ingestion**: WebSocket connections to Polygon.io, Finage, Alpha Vantage, and FMP APIs
- **Stream Processing**: Apache Kafka + Spark Structured Streaming with windowed aggregations (1min, 5min, 15min)
- **Technical Indicators**: SMA, EMA, RSI, MACD, Bollinger Bands calculated in real-time
- **Time-Series Storage**: TimescaleDB for historical data, InfluxDB for metrics, Redis for caching
- **REST API**: FastAPI endpoints for historical queries
- **WebSocket Server**: Real-time data broadcasting to clients
- **Live Dashboard**: Plotly Dash with candlestick charts, volume, indicators, and latency metrics
- **Anomaly Detection**: Price spikes, volume anomalies, RSI extremes with alerting
- **ML Predictions**: XGBoost model for next-price forecasting
- **Monitoring**: Prometheus metrics + Grafana dashboards
- **Performance**: <100ms end-to-end latency, 10,000+ messages/sec throughput

## Architecture

```
Market APIs (Polygon/Finage)
    ↓ WebSocket
Kafka Producer
    ↓ tick_data topic
Spark Streaming Consumer
    ↓ Windowed Aggregations
    ├→ TimescaleDB (historical data)
    ├→ InfluxDB (metrics)
    ├→ Redis (cache)
    └→ aggregated_data topic
        ↓
    ├→ REST API (FastAPI)
    ├→ WebSocket Server (broadcast)
    ├→ Dashboard (Plotly Dash)
    ├→ Anomaly Detector
    └→ ML Predictor
```

## Prerequisites

- Docker & Docker Compose
- Python 3.10+
- API Keys (at least one):
  - Polygon.io
  - Finage
  - Alpha Vantage (free tier)
  - Financial Modeling Prep

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Infrastructure

```bash
# Start all Docker services (Kafka, TimescaleDB, Redis, InfluxDB, Grafana, Spark)
make start

# Or manually:
docker-compose up -d
```

### 4. Launch Components

Open separate terminals for each component:

```bash
# Terminal 1: Market Data Producer
make producer

# Terminal 2: Spark Stream Processor
make consumer

# Terminal 3: REST API
make api

# Terminal 4: WebSocket Server
make websocket

# Terminal 5: Dashboard
make dashboard

# Terminal 6: Anomaly Detector
make anomaly

# Terminal 7: Metrics Collector
make metrics
```

### 5. Access Services

- **Dashboard**: http://localhost:8050
- **REST API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Spark UI**: http://localhost:8080

## Configuration

### Symbols

Edit `config/api_config.yaml` to add/remove symbols:

```yaml
symbols:
  - AAPL
  - GOOGL
  - MSFT
  - AMZN
  - TSLA
  - NVDA  # Add more symbols
```

### Window Configurations

Customize aggregation windows:

```yaml
window_configurations:
  - name: 1min
    duration: 60
  - name: 5min
    duration: 300
  - name: 30min
    duration: 1800
```

### Technical Indicators

Configure indicator parameters:

```yaml
technical_indicators:
  sma:
    periods: [20, 50, 200]
  ema:
    periods: [12, 26]
  rsi:
    period: 14
    overbought: 70
    oversold: 30
```

## API Endpoints

### Latest Price
```bash
curl http://localhost:8000/api/v1/latest/AAPL
```

### Historical Tick Data
```bash
curl "http://localhost:8000/api/v1/ticks/AAPL?limit=100"
```

### Aggregated Data
```bash
curl "http://localhost:8000/api/v1/aggregated/AAPL?window=1min"
```

### Technical Indicators
```bash
curl http://localhost:8000/api/v1/indicators/AAPL
```

### Available Symbols
```bash
curl http://localhost:8000/api/v1/symbols
```

## WebSocket Client Example

```javascript
const ws = new WebSocket('ws://localhost:8001');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    symbols: ['AAPL', 'GOOGL']
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Real-time data:', data);
};
```

## Machine Learning

### Train Models

```bash
# Train models for all symbols
make train-ml

# Or programmatically:
python -m src.analytics.price_predictor
```

Models are saved in `./models/` and automatically loaded on startup.

### Prediction API

```python
from src.analytics.price_predictor import PricePredictor

predictor = PricePredictor()
prediction = predictor.predict_next_price('AAPL', time_horizon_minutes=5)
print(prediction)
```

## Monitoring & Alerting

### Prometheus Metrics

- `tick_messages_received_total`: Total messages per symbol
- `processing_latency_seconds`: End-to-end latency
- `kafka_consumer_lag`: Consumer lag per topic
- `messages_per_second`: Throughput metrics

### Anomaly Detection

Automatically detects:
- **Price Spikes**: >5% deviation from 20-period average
- **Volume Spikes**: >3x average volume
- **High Latency**: >100ms processing time
- **RSI Extremes**: Overbought (>70) / Oversold (<30)

### Alerts

Configure Slack webhook in `.env`:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Alerts are sent for critical/high severity anomalies with 5-minute cooldown.

## Data Storage

### TimescaleDB

- **tick_data**: Raw tick-by-tick data
- **aggregated_data**: OHLCV + VWAP per window
- **technical_indicators**: All calculated indicators
- **anomalies**: Detected anomalies
- **predictions**: ML model predictions

Retention: 365 days with automatic partitioning

### InfluxDB

Real-time metrics for visualization:
- tick_metrics
- aggregated_metrics
- technical_indicators
- anomalies
- latency_metrics
- kafka_metrics

### Redis

Hot cache for fast lookups:
- latest_price:{symbol}
- indicators:{symbol}
- aggregated:{symbol}:{window}

TTL: 60-300 seconds

## Performance Tuning

### Kafka Producer

```python
# In market_api_streamer.py
KafkaProducer(
    batch_size=16384,      # Increase for higher throughput
    linger_ms=10,          # Batch wait time
    compression_type='snappy'
)
```

### Spark Streaming

```python
# In stream_processor.py
.config("spark.sql.shuffle.partitions", "10")
.config("spark.streaming.kafka.maxRatePerPartition", "1000")
```

### Database Connections

Use connection pooling for high-throughput scenarios.

## Troubleshooting

### Kafka Connection Issues

```bash
# Check Kafka is running
docker-compose ps kafka

# View Kafka logs
docker-compose logs -f kafka
```

### No Data in Dashboard

1. Verify producer is running and connected to API
2. Check Kafka topic has messages:
```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tick_data --from-beginning
```

### High Latency

1. Check Kafka consumer lag
2. Scale Spark workers
3. Optimize database indexes
4. Increase Redis cache TTL

## Development

### Project Structure

```
.
├── src/
│   ├── producers/          # Market data ingestion
│   ├── consumers/          # Stream processing
│   ├── analytics/          # Technical indicators & ML
│   ├── api/               # REST & WebSocket servers
│   ├── storage/           # Database connectors
│   ├── dashboard/         # Visualization
│   ├── monitoring/        # Anomaly detection & metrics
│   └── utils/             # Config, logging, schemas
├── config/                # Configuration files
├── data/                  # Data storage
├── logs/                  # Application logs
├── tests/                 # Unit tests
├── docker-compose.yml     # Infrastructure
└── requirements.txt       # Python dependencies
```

### Running Tests

```bash
make test
```

## Cleanup

```bash
# Stop services
make stop

# Remove all data and containers
make clean
```

## License

MIT License

## Support

For issues, questions, or contributions, please open a GitHub issue.

---

Built with ❤️ for real-time financial data streaming
