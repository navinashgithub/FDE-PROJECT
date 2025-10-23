from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from typing import Dict, List, Any
from datetime import datetime
from src.utils.config_loader import settings
from src.utils.logger import setup_logger

logger = setup_logger("influxdb_handler")


class InfluxDBHandler:
    def __init__(self):
        self.client = None
        self.write_api = None
        self.query_api = None
        self.connect()

    def connect(self):
        try:
            self.client = InfluxDBClient(
                url=settings.influxdb_url,
                token=settings.influxdb_token,
                org=settings.influxdb_org
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            logger.info("Connected to InfluxDB")
        except Exception as e:
            logger.error(f"Error connecting to InfluxDB: {e}", exc_info=True)
            raise

    def write_tick_metrics(self, symbol: str, price: float, volume: float, timestamp: datetime):
        try:
            point = Point("tick_metrics") \
                .tag("symbol", symbol) \
                .field("price", price) \
                .field("volume", volume) \
                .time(timestamp, WritePrecision.MS)

            self.write_api.write(bucket=settings.influxdb_bucket, record=point)
        except Exception as e:
            logger.error(f"Error writing tick metrics to InfluxDB: {e}", exc_info=True)

    def write_aggregated_metrics(self, symbol: str, window_duration: str, metrics: Dict[str, float], timestamp: datetime):
        try:
            point = Point("aggregated_metrics") \
                .tag("symbol", symbol) \
                .tag("window", window_duration) \
                .field("open", metrics.get("open", 0.0)) \
                .field("high", metrics.get("high", 0.0)) \
                .field("low", metrics.get("low", 0.0)) \
                .field("close", metrics.get("close", 0.0)) \
                .field("volume", metrics.get("volume", 0.0)) \
                .field("vwap", metrics.get("vwap", 0.0)) \
                .field("trade_count", metrics.get("trade_count", 0)) \
                .time(timestamp, WritePrecision.MS)

            self.write_api.write(bucket=settings.influxdb_bucket, record=point)
        except Exception as e:
            logger.error(f"Error writing aggregated metrics to InfluxDB: {e}", exc_info=True)

    def write_technical_indicators(self, symbol: str, indicators: Dict[str, float], timestamp: datetime):
        try:
            point = Point("technical_indicators") \
                .tag("symbol", symbol)

            for key, value in indicators.items():
                if value is not None:
                    point = point.field(key, value)

            point = point.time(timestamp, WritePrecision.MS)

            self.write_api.write(bucket=settings.influxdb_bucket, record=point)
        except Exception as e:
            logger.error(f"Error writing technical indicators to InfluxDB: {e}", exc_info=True)

    def write_anomaly(self, symbol: str, anomaly_type: str, severity: str, current_value: float, timestamp: datetime):
        try:
            point = Point("anomalies") \
                .tag("symbol", symbol) \
                .tag("type", anomaly_type) \
                .tag("severity", severity) \
                .field("value", current_value) \
                .time(timestamp, WritePrecision.MS)

            self.write_api.write(bucket=settings.influxdb_bucket, record=point)
        except Exception as e:
            logger.error(f"Error writing anomaly to InfluxDB: {e}", exc_info=True)

    def write_latency_metric(self, component: str, latency_ms: float, timestamp: datetime):
        try:
            point = Point("latency_metrics") \
                .tag("component", component) \
                .field("latency_ms", latency_ms) \
                .time(timestamp, WritePrecision.MS)

            self.write_api.write(bucket=settings.influxdb_bucket, record=point)
        except Exception as e:
            logger.error(f"Error writing latency metric to InfluxDB: {e}", exc_info=True)

    def write_kafka_metrics(self, topic: str, lag: int, messages_per_sec: float, timestamp: datetime):
        try:
            point = Point("kafka_metrics") \
                .tag("topic", topic) \
                .field("lag", lag) \
                .field("messages_per_sec", messages_per_sec) \
                .time(timestamp, WritePrecision.MS)

            self.write_api.write(bucket=settings.influxdb_bucket, record=point)
        except Exception as e:
            logger.error(f"Error writing Kafka metrics to InfluxDB: {e}", exc_info=True)

    def query_latest_metrics(self, symbol: str, measurement: str, time_range: str = "-1h") -> List[Dict]:
        try:
            query = f'''
                from(bucket: "{settings.influxdb_bucket}")
                |> range(start: {time_range})
                |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                |> filter(fn: (r) => r["symbol"] == "{symbol}")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 100)
            '''

            result = self.query_api.query(query=query)
            records = []

            for table in result:
                for record in table.records:
                    records.append({
                        "time": record.get_time(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        "symbol": record.values.get("symbol")
                    })

            return records
        except Exception as e:
            logger.error(f"Error querying metrics from InfluxDB: {e}", exc_info=True)
            return []

    def query_aggregated_metrics(self, symbol: str, window: str, time_range: str = "-1h") -> List[Dict]:
        try:
            query = f'''
                from(bucket: "{settings.influxdb_bucket}")
                |> range(start: {time_range})
                |> filter(fn: (r) => r["_measurement"] == "aggregated_metrics")
                |> filter(fn: (r) => r["symbol"] == "{symbol}")
                |> filter(fn: (r) => r["window"] == "{window}")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"], desc: true)
            '''

            result = self.query_api.query(query=query)
            records = []

            for table in result:
                for record in table.records:
                    records.append(record.values)

            return records
        except Exception as e:
            logger.error(f"Error querying aggregated metrics from InfluxDB: {e}", exc_info=True)
            return []

    def close(self):
        if self.client:
            self.client.close()
            logger.info("InfluxDB connection closed")
