"""
Mock REST API - Simplified version without database dependencies
Used for development/testing when full infrastructure not available
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel
import uvicorn
import random

app = FastAPI(title="Market Data API (Mock)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    components: dict


# Mock data storage (October 22, 2025 closing prices)
mock_prices = {
    "AAPL": 232.18,      # Apple Inc.
    "GOOGL": 178.45,     # Alphabet Inc.
    "MSFT": 428.72,      # Microsoft Corporation
    "AMZN": 193.50,      # Amazon.com Inc.
    "TSLA": 287.93,      # Tesla Inc.
}


@app.get("/")
async def root():
    return {
        "service": "Market Data API (Mock)",
        "version": "1.0.0",
        "status": "running",
        "note": "This is a simplified mock API for development/testing",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint - all components mocked as healthy"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        components={
            "redis": "healthy",
            "timescaledb": "healthy",
            "influxdb": "healthy",
        },
    )


@app.get("/api/v1/latest/{symbol}")
async def get_latest_price(symbol: str):
    """Get latest price for a symbol"""
    symbol = symbol.upper()
    if symbol not in mock_prices:
        return {"error": f"Symbol {symbol} not found"}

    # Simulate small price fluctuations
    price = mock_prices[symbol]
    fluctuation = random.uniform(-2, 2) / 100  # ±2% variation
    new_price = price * (1 + fluctuation)
    mock_prices[symbol] = new_price

    return {
        "symbol": symbol,
        "price": round(new_price, 2),
        "timestamp": datetime.now().isoformat(),
        "volume": random.randint(1000000, 50000000),
    }


@app.get("/api/v1/symbols")
async def get_symbols():
    """Get list of available symbols"""
    return {"symbols": list(mock_prices.keys())}


if __name__ == "__main__":
    import time
    print("=" * 60)
    print("Starting Mock REST API (Development Mode)")
    print("=" * 60)
    print("✓ REST API running on http://127.0.0.1:8000")
    print("✓ Health check: GET http://127.0.0.1:8000/health")
    print("✓ Latest price: GET http://127.0.0.1:8000/api/v1/latest/{symbol}")
    print("✓ Available symbols: AAPL, GOOGL, MSFT, AMZN, TSLA")
    print("=" * 60)
    time.sleep(2)
    uvicorn.run(app, host="127.0.0.1", port=8000)
