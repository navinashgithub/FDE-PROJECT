# Quick Start Guide

Get the Financial Market Data Streaming System up and running in 5 minutes!

## Prerequisites Check

```bash
# Check Docker is installed
docker --version
docker-compose --version

# Check Python is installed
python --version  # Should be 3.10+
```

## Step 1: Get API Keys

You need at least ONE of these API keys (free tiers available):

1. **Polygon.io** (Recommended)
   - Sign up: https://polygon.io/
   - Get API key from dashboard
   - Free tier: 5 requests/minute

2. **Finage** (Alternative)
   - Sign up: https://finage.co.uk/
   - Get API key
   - Free tier available

3. **Alpha Vantage** (Fallback - Free)
   - Sign up: https://www.alphavantage.co/support/#api-key
   - Instant API key
   - Completely free: 5 calls/minute

4. **Financial Modeling Prep** (Optional)
   - Sign up: https://financialmodelingprep.com/developer
   - Free tier: 250 calls/day

## Step 2: Configure Environment

```bash
# Copy the environment template
cp .env.example .env

# Edit the .env file
nano .env  # or use your preferred editor

# Add your API key(s):
POLYGON_API_KEY=your_key_here
# OR
FINAGE_API_KEY=your_key_here
# OR
ALPHA_VANTAGE_API_KEY=your_key_here  # Free option!
```

**Tip**: Alpha Vantage is the easiest to get started with - completely free!

## Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Start the System

### Option A: Automated Start (Recommended)

```bash
./start_all.sh
```

This will:
- Start all Docker containers
- Launch producer, consumer, API, WebSocket, dashboard, and monitoring

### Option B: Manual Start

```bash
# 1. Start Docker services
docker-compose up -d

# Wait 30 seconds for services to initialize

# 2. Start components in separate terminals:
# Terminal 1:
python -m src.producers.market_api_streamer

# Terminal 2:
python -m src.consumers.stream_processor

# Terminal 3:
python -m src.api.rest_api

# Terminal 4:
python -m src.api.websocket_server

# Terminal 5:
python -m src.dashboard.realtime_dashboard

# Terminal 6:
python -m src.monitoring.anomaly_detector

# Terminal 7:
python -m src.monitoring.metrics_collector
```

## Step 5: Access the Dashboard

Open your browser to:

**Dashboard**: http://localhost:8050

You should see:
- Real-time price updates for AAPL, GOOGL, MSFT, AMZN, TSLA
- Candlestick charts with VWAP
- Volume bars
- RSI indicator
- Latency metrics

## Step 6: Test the API

```bash
# Get latest price
curl http://localhost:8000/api/v1/latest/AAPL

# Get available symbols
curl http://localhost:8000/api/v1/symbols

# Get aggregated data
curl http://localhost:8000/api/v1/aggregated/AAPL?window=1min

# Interactive API docs
# Open: http://localhost:8000/docs
```

## Step 7: Test WebSocket

Create a file `test_websocket.html`:

```html
<!DOCTYPE html>
<html>
<body>
  <h1>Real-Time Market Data</h1>
  <div id="output"></div>
  <script>
    const ws = new WebSocket('ws://localhost:8001');
    const output = document.getElementById('output');

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      output.innerHTML += `<p>${data.symbol}: $${data.price}</p>`;
    };
  </script>
</body>
</html>
```

Open in browser to see real-time updates!

## Troubleshooting

### "No data in dashboard"

**Check 1**: Verify API key is set correctly
```bash
grep API_KEY .env
```

**Check 2**: Check producer logs
```bash
tail -f logs/market_api_streamer.log
```

**Check 3**: Verify Kafka is receiving messages
```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tick_data --from-beginning
```

### "Connection refused" errors

**Wait longer**: Services take 30-60 seconds to fully start
```bash
# Check all containers are running
docker-compose ps

# Should show all as "Up"
```

### "Rate limit exceeded"

**Solution**: Switch to a different API or wait:
```bash
# In .env, comment out current API and use another:
# POLYGON_API_KEY=...  # Comment this
ALPHA_VANTAGE_API_KEY=your_key  # Use this instead
```

Alpha Vantage has slower updates but no rate limits for basic usage.

### Docker issues

```bash
# Restart Docker services
docker-compose down
docker-compose up -d

# View logs
docker-compose logs -f
```

## Next Steps

1. **Customize Symbols**: Edit `config/api_config.yaml`
2. **Train ML Models**: Run `make train-ml`
3. **View Grafana**: http://localhost:3000 (admin/admin)
4. **Monitor Prometheus**: http://localhost:9090
5. **Check Spark UI**: http://localhost:8080

## Stopping the System

```bash
# Automated
./stop_all.sh

# OR manually
docker-compose down
pkill -f "src.producers"
pkill -f "src.consumers"
pkill -f "src.api"
pkill -f "src.dashboard"
pkill -f "src.monitoring"
```

## Getting Help

- Check logs in `./logs/` directory
- Review Docker logs: `docker-compose logs`
- Verify environment: `cat .env`

## Free API Comparison

| Provider | Rate Limit | Real-Time | Best For |
|----------|-----------|-----------|----------|
| Alpha Vantage | 5/min | No | Getting started |
| Polygon (free) | 5/min | Yes | Development |
| Finage (free) | Limited | Yes | Testing |

**Recommendation**: Start with Alpha Vantage (free, no limits) to verify the system works, then upgrade to Polygon for real-time data.

---

**You're all set!** The system should now be streaming live market data. 🚀
