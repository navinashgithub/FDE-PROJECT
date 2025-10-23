import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from src.utils.config_loader import settings
from src.utils.logger import setup_logger

logger = setup_logger("timescaledb_connector")


class TimescaleDBConnector:
    def __init__(self):
        self.connection = None
        self.connect()
        self.initialize_schema()

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=settings.timescaledb_host,
                port=settings.timescaledb_port,
                user=settings.timescaledb_user,
                password=settings.timescaledb_password,
                database=settings.timescaledb_database
            )
            logger.info("Connected to TimescaleDB")
        except Exception as e:
            logger.error(f"Error connecting to TimescaleDB: {e}", exc_info=True)
            raise

    def initialize_schema(self):
        try:
            cursor = self.connection.cursor()

            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tick_data (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    price DOUBLE PRECISION NOT NULL,
                    volume DOUBLE PRECISION,
                    tick_type TEXT,
                    bid DOUBLE PRECISION,
                    ask DOUBLE PRECISION,
                    bid_size INTEGER,
                    ask_size INTEGER,
                    exchange TEXT,
                    metadata JSONB
                );
            """)

            cursor.execute("""
                SELECT create_hypertable('tick_data', 'time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tick_symbol_time
                ON tick_data (symbol, time DESC);
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS aggregated_data (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    window_start TIMESTAMPTZ NOT NULL,
                    window_end TIMESTAMPTZ NOT NULL,
                    window_duration TEXT NOT NULL,
                    open DOUBLE PRECISION NOT NULL,
                    high DOUBLE PRECISION NOT NULL,
                    low DOUBLE PRECISION NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    volume DOUBLE PRECISION NOT NULL,
                    vwap DOUBLE PRECISION,
                    trade_count INTEGER
                );
            """)

            cursor.execute("""
                SELECT create_hypertable('aggregated_data', 'time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agg_symbol_time
                ON aggregated_data (symbol, time DESC);
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS technical_indicators (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    sma_20 DOUBLE PRECISION,
                    sma_50 DOUBLE PRECISION,
                    sma_200 DOUBLE PRECISION,
                    ema_12 DOUBLE PRECISION,
                    ema_26 DOUBLE PRECISION,
                    rsi DOUBLE PRECISION,
                    macd DOUBLE PRECISION,
                    macd_signal DOUBLE PRECISION,
                    macd_histogram DOUBLE PRECISION,
                    bb_upper DOUBLE PRECISION,
                    bb_middle DOUBLE PRECISION,
                    bb_lower DOUBLE PRECISION
                );
            """)

            cursor.execute("""
                SELECT create_hypertable('technical_indicators', 'time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anomalies (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT,
                    current_value DOUBLE PRECISION,
                    expected_value DOUBLE PRECISION,
                    threshold DOUBLE PRECISION,
                    metadata JSONB
                );
            """)

            cursor.execute("""
                SELECT create_hypertable('anomalies', 'time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    current_price DOUBLE PRECISION NOT NULL,
                    predicted_price DOUBLE PRECISION NOT NULL,
                    confidence DOUBLE PRECISION,
                    time_horizon_minutes INTEGER,
                    model_version TEXT
                );
            """)

            cursor.execute("""
                SELECT create_hypertable('predictions', 'time',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)

            self.connection.commit()
            cursor.close()
            logger.info("TimescaleDB schema initialized")

        except Exception as e:
            logger.error(f"Error initializing schema: {e}", exc_info=True)
            self.connection.rollback()
            raise

    def insert_tick_data(self, tick_data: Dict[str, Any]):
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO tick_data (time, symbol, price, volume, tick_type, bid, ask, bid_size, ask_size, exchange)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                tick_data.get('timestamp'),
                tick_data.get('symbol'),
                tick_data.get('price'),
                tick_data.get('volume'),
                tick_data.get('tick_type'),
                tick_data.get('bid'),
                tick_data.get('ask'),
                tick_data.get('bid_size'),
                tick_data.get('ask_size'),
                tick_data.get('exchange')
            ))
            self.connection.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error inserting tick data: {e}", exc_info=True)
            self.connection.rollback()

    def insert_aggregated_data(self, agg_data: Dict[str, Any]):
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO aggregated_data (time, symbol, window_start, window_end, window_duration,
                                           open, high, low, close, volume, vwap, trade_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                agg_data.get('window_end'),
                agg_data.get('symbol'),
                agg_data.get('window_start'),
                agg_data.get('window_end'),
                agg_data.get('window_duration'),
                agg_data.get('open'),
                agg_data.get('high'),
                agg_data.get('low'),
                agg_data.get('close'),
                agg_data.get('volume'),
                agg_data.get('vwap'),
                agg_data.get('trade_count')
            ))
            self.connection.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error inserting aggregated data: {e}", exc_info=True)
            self.connection.rollback()

    def insert_technical_indicators(self, symbol: str, timestamp: datetime, indicators: Dict[str, float]):
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO technical_indicators (time, symbol, sma_20, sma_50, sma_200, ema_12, ema_26,
                                                 rsi, macd, macd_signal, macd_histogram,
                                                 bb_upper, bb_middle, bb_lower)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                timestamp, symbol,
                indicators.get('sma_20'), indicators.get('sma_50'), indicators.get('sma_200'),
                indicators.get('ema_12'), indicators.get('ema_26'),
                indicators.get('rsi'),
                indicators.get('macd'), indicators.get('macd_signal'), indicators.get('macd_histogram'),
                indicators.get('bb_upper'), indicators.get('bb_middle'), indicators.get('bb_lower')
            ))
            self.connection.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error inserting technical indicators: {e}", exc_info=True)
            self.connection.rollback()

    def query_tick_data(self, symbol: str, start_time: datetime, end_time: datetime, limit: int = 1000) -> List[Dict]:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT time, symbol, price, volume, tick_type, bid, ask, exchange
                FROM tick_data
                WHERE symbol = %s AND time BETWEEN %s AND %s
                ORDER BY time DESC
                LIMIT %s
            """, (symbol, start_time, end_time, limit))

            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Error querying tick data: {e}", exc_info=True)
            return []

    def query_aggregated_data(self, symbol: str, start_time: datetime, end_time: datetime,
                            window_duration: str = "1min") -> List[Dict]:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT time, symbol, window_start, window_end, open, high, low, close, volume, vwap, trade_count
                FROM aggregated_data
                WHERE symbol = %s AND time BETWEEN %s AND %s AND window_duration = %s
                ORDER BY time DESC
            """, (symbol, start_time, end_time, window_duration))

            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Error querying aggregated data: {e}", exc_info=True)
            return []

    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("TimescaleDB connection closed")
