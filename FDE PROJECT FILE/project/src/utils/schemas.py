from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TickType(str, Enum):
    TRADE = "trade"
    QUOTE = "quote"
    AGGREGATE = "aggregate"


class TickData(BaseModel):
    symbol: str
    price: float
    volume: Optional[float] = None
    timestamp: datetime
    tick_type: TickType = TickType.TRADE
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    exchange: Optional[str] = None
    conditions: Optional[list] = None

    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

    @validator('volume')
    def volume_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError('Volume cannot be negative')
        return v


class AggregatedData(BaseModel):
    symbol: str
    window_start: datetime
    window_end: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float
    trade_count: int
    window_duration: str


class TechnicalIndicators(BaseModel):
    symbol: str
    timestamp: datetime
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None


class Anomaly(BaseModel):
    symbol: str
    timestamp: datetime
    anomaly_type: str
    severity: str
    description: str
    current_value: float
    expected_value: Optional[float] = None
    threshold: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class PricePrediction(BaseModel):
    symbol: str
    timestamp: datetime
    current_price: float
    predicted_price: float
    confidence: float
    time_horizon_minutes: int
    model_version: str
