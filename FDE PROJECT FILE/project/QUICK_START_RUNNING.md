# 🎯 Quick Access Guide

## 📱 Open the App

**👉 Go to:** http://localhost:5173

---

## 🌐 Available Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend Dashboard** | http://localhost:5173 | React app for viewing real-time market data |
| **REST API** | http://127.0.0.1:8000 | API for health checks and price queries |
| **WebSocket** | ws://127.0.0.1:8001 | Real-time price streaming |
| **API Docs** | http://127.0.0.1:8000/docs | OpenAPI/Swagger documentation |

---

## ✨ What You Can Do

### In the Dashboard (http://localhost:5173)

1. **Select a Stock Symbol**
   - AAPL (Apple)
   - GOOGL (Google)
   - MSFT (Microsoft)
   - AMZN (Amazon)
   - TSLA (Tesla)

2. **Watch Real-Time Prices**
   - Prices update every second
   - See live connection status (green = connected)

3. **Monitor Backend Health**
   - Redis status
   - TimescaleDB status
   - InfluxDB status

4. **View System Information**
   - Backend service URLs
   - Data source information

---

## 🔍 Test the API

### Get Health Status
```
GET http://127.0.0.1:8000/health
```
Returns all component statuses (Redis, TimescaleDB, InfluxDB)

### Get Latest Price
```
GET http://127.0.0.1:8000/api/v1/latest/AAPL
```
Returns: `{ symbol, price, timestamp, volume }`

### List Available Symbols
```
GET http://127.0.0.1:8000/api/v1/symbols
```
Returns: `{ symbols: ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"] }`

---

## 📊 Simulated Data

All prices are simulated with random fluctuations:
- **WebSocket**: Updates every 1 second with ±0.5% price change
- **REST API**: Generates ±2% variation when called

Perfect for testing the UI without real market connections!

---

## 🚀 Running Services

Three terminals are currently running:

```
Terminal 1: REST API Server
  $ python -m src.api.rest_api_mock
  → Running on http://127.0.0.1:8000

Terminal 2: WebSocket Server
  $ python -m src.api.websocket_server_mock
  → Running on ws://127.0.0.1:8001

Terminal 3: Vite Dev Server
  $ npm run dev
  → Running on http://localhost:5173
```

---

## ⏹️ How to Stop

Press `Ctrl+C` in each terminal to stop the services.

---

## 🔄 Restart Services

```powershell
# In project directory
npm run dev                           # Frontend
python -m src.api.rest_api_mock      # REST API
python -m src.api.websocket_server_mock  # WebSocket
```

---

## 💡 Tips

- **Browser DevTools**: Open F12 to see WebSocket messages in console
- **Live Updates**: Watch prices change in real-time as you select symbols
- **Error Messages**: Check the red alert box if services are down
- **Status Indicator**: Green dot in header = WebSocket connected

---

## 📚 Documentation

- `README.md` - Full project overview
- `ARCHITECTURE.md` - System design
- `PROJECT_SUMMARY.md` - Feature list
- `BACKEND_STATUS.md` - Service status details

---

**Everything is ready! Open http://localhost:5173 and start exploring!** 🎉
