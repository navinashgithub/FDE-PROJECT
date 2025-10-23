from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import uvicorn
from src.storage.timescaledb_connector import TimescaleDBConnector
from src.storage.redis_cache import RedisCache
from src.storage.influxdb_handler import InfluxDBHandler
from src.utils.config_loader import settings
from src.utils.logger import setup_logger

logger = setup_logger("rest_api")

app = FastAPI(title="Market Data API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

timescale_db = TimescaleDBConnector()
redis_cache = RedisCache()
influx_db = InfluxDBHandler()


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    components: dict


class TickDataResponse(BaseModel):
    symbol: str
    price: float
    volume: Optional[float]
    timestamp: datetime


class AggregatedDataResponse(BaseModel):
    symbol: str
    window_start: datetime
    window_end: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float]
    trade_count: int


@app.get("/")
async def root():
    return {
        "service": "Market Data API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        redis_status = "healthy" if redis_cache.client.ping() else "unhealthy"
    except:
        redis_status = "unhealthy"

    try:
        timescale_status = "healthy" if timescale_db.connection else "unhealthy"
    except:
        timescale_status = "unhealthy"

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        components={
            "redis": redis_status,
            "timescaledb": timescale_status,
            "influxdb": "healthy"
        }
    )


@app.get("/api/v1/latest/{symbol}")
async def get_latest_price(symbol: str):
    cached_data = redis_cache.get_latest_price(symbol.upper())
    if cached_data:
        return cached_data

    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=5)

    data = timescale_db.query_tick_data(symbol.upper(), start_time, end_time, limit=1)

    if not data:
        raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")

    return data[0]


@app.get("/api/v1/ticks/{symbol}", response_model=List[dict])
async def get_tick_data(
    symbol: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000)
):
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(hours=1)

    data = timescale_db.query_tick_data(symbol.upper(), start_time, end_time, limit)

    if not data:
        raise HTTPException(status_code=404, detail=f"No tick data found for symbol {symbol}")

    return data


@app.get("/api/v1/aggregated/{symbol}", response_model=List[dict])
async def get_aggregated_data(
    symbol: str,
    window: str = Query("1min", regex="^(1min|5min|15min)$"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None)
):
    cached_data = redis_cache.get_aggregated_data(symbol.upper(), window)
    if cached_data:
        return [cached_data]

    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(hours=1)

    data = timescale_db.query_aggregated_data(symbol.upper(), start_time, end_time, window)

    if not data:
        raise HTTPException(status_code=404, detail=f"No aggregated data found for symbol {symbol}")

    return data


@app.get("/api/v1/indicators/{symbol}")
async def get_technical_indicators(symbol: str):
    cached_indicators = redis_cache.get_technical_indicators(symbol.upper())
    if cached_indicators:
        return cached_indicators

    records = influx_db.query_latest_metrics(symbol.upper(), "technical_indicators", time_range="-1h")

    if not records:
        raise HTTPException(status_code=404, detail=f"No indicators found for symbol {symbol}")

    indicators = {}
    for record in records:
        indicators[record['field']] = record['value']

    return indicators


@app.get("/api/v1/symbols")
async def get_available_symbols():
    symbols = settings.symbols.split(',')
    return {
        "symbols": symbols,
        "count": len(symbols)
    }


@app.get("/api/v1/metrics/latency")
async def get_latency_metrics(time_range: str = Query("-1h")):
    try:
        records = influx_db.query_latest_metrics("", "latency_metrics", time_range)
        return {"metrics": records}
    except Exception as e:
        logger.error(f"Error fetching latency metrics: {e}")
        raise HTTPException(status_code=500, detail="Error fetching latency metrics")


@app.get("/api/v1/metrics/kafka")
async def get_kafka_metrics(time_range: str = Query("-1h")):
    try:
        query = f'''
            from(bucket: "{settings.influxdb_bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => r["_measurement"] == "kafka_metrics")
            |> sort(columns: ["_time"], desc: true)
            |> limit(n: 100)
        '''
        records = influx_db.query_api.query(query=query)
        metrics = []
        for table in records:
            for record in table.records:
                metrics.append({
                    "time": record.get_time(),
                    "topic": record.values.get("topic"),
                    "field": record.get_field(),
                    "value": record.get_value()
                })
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching Kafka metrics: {e}")
        raise HTTPException(status_code=500, detail="Error fetching Kafka metrics")


@app.on_event("startup")
async def startup_event():
    logger.info("Market Data API starting up")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Market Data API shutting down")
    timescale_db.close()
    redis_cache.close()
    influx_db.close()


def main():
    uvicorn.run(
        "src.api.rest_api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
