import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from src.utils.logger import setup_logger

logger = setup_logger("technical_indicators")


class TechnicalIndicatorCalculator:
    def __init__(self):
        self.price_history: Dict[str, pd.DataFrame] = {}

    def add_price_data(self, symbol: str, timestamp: pd.Timestamp, price: float, volume: float):
        if symbol not in self.price_history:
            self.price_history[symbol] = pd.DataFrame(columns=['timestamp', 'price', 'volume'])

        new_row = pd.DataFrame({
            'timestamp': [timestamp],
            'price': [price],
            'volume': [volume]
        })

        self.price_history[symbol] = pd.concat([self.price_history[symbol], new_row], ignore_index=True)

        if len(self.price_history[symbol]) > 1000:
            self.price_history[symbol] = self.price_history[symbol].iloc[-1000:]

    def calculate_sma(self, symbol: str, periods: List[int]) -> Dict[str, Optional[float]]:
        if symbol not in self.price_history or len(self.price_history[symbol]) < max(periods):
            return {f"sma_{p}": None for p in periods}

        df = self.price_history[symbol].copy()
        results = {}

        for period in periods:
            if len(df) >= period:
                sma_indicator = SMAIndicator(close=df['price'], window=period)
                results[f"sma_{period}"] = float(sma_indicator.sma_indicator().iloc[-1])
            else:
                results[f"sma_{period}"] = None

        return results

    def calculate_ema(self, symbol: str, periods: List[int]) -> Dict[str, Optional[float]]:
        if symbol not in self.price_history or len(self.price_history[symbol]) < max(periods):
            return {f"ema_{p}": None for p in periods}

        df = self.price_history[symbol].copy()
        results = {}

        for period in periods:
            if len(df) >= period:
                ema_indicator = EMAIndicator(close=df['price'], window=period)
                results[f"ema_{period}"] = float(ema_indicator.ema_indicator().iloc[-1])
            else:
                results[f"ema_{period}"] = None

        return results

    def calculate_rsi(self, symbol: str, period: int = 14) -> Optional[float]:
        if symbol not in self.price_history or len(self.price_history[symbol]) < period + 1:
            return None

        df = self.price_history[symbol].copy()
        rsi_indicator = RSIIndicator(close=df['price'], window=period)
        return float(rsi_indicator.rsi().iloc[-1])

    def calculate_macd(self, symbol: str, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, Optional[float]]:
        if symbol not in self.price_history or len(self.price_history[symbol]) < slow_period + signal_period:
            return {"macd": None, "macd_signal": None, "macd_histogram": None}

        df = self.price_history[symbol].copy()
        macd_indicator = MACD(
            close=df['price'],
            window_fast=fast_period,
            window_slow=slow_period,
            window_sign=signal_period
        )

        return {
            "macd": float(macd_indicator.macd().iloc[-1]),
            "macd_signal": float(macd_indicator.macd_signal().iloc[-1]),
            "macd_histogram": float(macd_indicator.macd_diff().iloc[-1])
        }

    def calculate_bollinger_bands(self, symbol: str, period: int = 20, std_dev: float = 2.0) -> Dict[str, Optional[float]]:
        if symbol not in self.price_history or len(self.price_history[symbol]) < period:
            return {"bb_upper": None, "bb_middle": None, "bb_lower": None}

        df = self.price_history[symbol].copy()
        bb_indicator = BollingerBands(close=df['price'], window=period, window_dev=std_dev)

        return {
            "bb_upper": float(bb_indicator.bollinger_hband().iloc[-1]),
            "bb_middle": float(bb_indicator.bollinger_mavg().iloc[-1]),
            "bb_lower": float(bb_indicator.bollinger_lband().iloc[-1])
        }

    def calculate_vwap(self, prices: pd.Series, volumes: pd.Series) -> float:
        if len(prices) == 0 or len(volumes) == 0:
            return 0.0

        return float((prices * volumes).sum() / volumes.sum())

    def calculate_all_indicators(self, symbol: str) -> Dict[str, Optional[float]]:
        try:
            indicators = {}

            sma_results = self.calculate_sma(symbol, [20, 50, 200])
            indicators.update(sma_results)

            ema_results = self.calculate_ema(symbol, [12, 26])
            indicators.update(ema_results)

            indicators['rsi'] = self.calculate_rsi(symbol, 14)

            macd_results = self.calculate_macd(symbol, 12, 26, 9)
            indicators.update(macd_results)

            bb_results = self.calculate_bollinger_bands(symbol, 20, 2.0)
            indicators.update(bb_results)

            return indicators

        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}", exc_info=True)
            return {}

    def detect_price_anomaly(self, symbol: str, current_price: float, threshold: float = 0.05) -> bool:
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return False

        df = self.price_history[symbol].copy()
        recent_avg = df['price'].tail(20).mean()

        price_change = abs(current_price - recent_avg) / recent_avg
        return price_change > threshold

    def detect_volume_anomaly(self, symbol: str, current_volume: float, threshold: float = 3.0) -> bool:
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return False

        df = self.price_history[symbol].copy()
        recent_avg_volume = df['volume'].tail(20).mean()

        if recent_avg_volume == 0:
            return False

        volume_ratio = current_volume / recent_avg_volume
        return volume_ratio > threshold


class WindowAggregator:
    @staticmethod
    def aggregate_window(prices: pd.Series, volumes: pd.Series, timestamps: pd.Series) -> Dict:
        if len(prices) == 0:
            return {}

        calculator = TechnicalIndicatorCalculator()
        vwap = calculator.calculate_vwap(prices, volumes)

        return {
            "open": float(prices.iloc[0]),
            "high": float(prices.max()),
            "low": float(prices.min()),
            "close": float(prices.iloc[-1]),
            "volume": float(volumes.sum()),
            "vwap": vwap,
            "trade_count": len(prices),
            "window_start": timestamps.iloc[0],
            "window_end": timestamps.iloc[-1]
        }
