import json
from typing import Dict, List, Optional
from datetime import datetime
from kafka import KafkaConsumer
from src.analytics.technical_indicators import TechnicalIndicatorCalculator
from src.storage.timescaledb_connector import TimescaleDBConnector
from src.storage.influxdb_handler import InfluxDBHandler
from src.utils.config_loader import settings, api_config
from src.utils.logger import setup_logger
from src.monitoring.alerting import AlertManager

logger = setup_logger("anomaly_detector")


class AnomalyDetector:
    def __init__(self):
        self.indicator_calculator = TechnicalIndicatorCalculator()
        self.timescale_db = TimescaleDBConnector()
        self.influx_db = InfluxDBHandler()
        self.alert_manager = AlertManager()
        self.anomaly_config = api_config.get("anomaly_detection", {})

    def detect_price_spike(self, symbol: str, current_price: float) -> Optional[Dict]:
        threshold = self.anomaly_config.get("price_spike_threshold", 0.05)

        is_anomaly = self.indicator_calculator.detect_price_anomaly(
            symbol, current_price, threshold
        )

        if is_anomaly:
            anomaly = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "anomaly_type": "price_spike",
                "severity": "high",
                "description": f"Price spike detected for {symbol}",
                "current_value": current_price,
                "threshold": threshold
            }

            self._log_anomaly(anomaly)
            return anomaly

        return None

    def detect_volume_spike(self, symbol: str, current_volume: float) -> Optional[Dict]:
        threshold = self.anomaly_config.get("volume_spike_threshold", 3.0)

        is_anomaly = self.indicator_calculator.detect_volume_anomaly(
            symbol, current_volume, threshold
        )

        if is_anomaly:
            anomaly = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "anomaly_type": "volume_spike",
                "severity": "medium",
                "description": f"Volume spike detected for {symbol}",
                "current_value": current_volume,
                "threshold": threshold
            }

            self._log_anomaly(anomaly)
            return anomaly

        return None

    def detect_latency_anomaly(self, component: str, latency_ms: float) -> Optional[Dict]:
        threshold = settings.processing_latency_threshold_ms

        if latency_ms > threshold:
            anomaly = {
                "symbol": component,
                "timestamp": datetime.now(),
                "anomaly_type": "high_latency",
                "severity": "critical",
                "description": f"High latency detected in {component}",
                "current_value": latency_ms,
                "threshold": threshold
            }

            self._log_anomaly(anomaly)
            return anomaly

        return None

    def detect_rsi_extremes(self, symbol: str, rsi: float) -> Optional[Dict]:
        config = api_config.get("technical_indicators", {}).get("rsi", {})
        overbought = config.get("overbought", 70)
        oversold = config.get("oversold", 30)

        if rsi >= overbought:
            anomaly = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "anomaly_type": "rsi_overbought",
                "severity": "low",
                "description": f"RSI indicates overbought conditions for {symbol}",
                "current_value": rsi,
                "threshold": overbought
            }
            self._log_anomaly(anomaly)
            return anomaly

        elif rsi <= oversold:
            anomaly = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "anomaly_type": "rsi_oversold",
                "severity": "low",
                "description": f"RSI indicates oversold conditions for {symbol}",
                "current_value": rsi,
                "threshold": oversold
            }
            self._log_anomaly(anomaly)
            return anomaly

        return None

    def _log_anomaly(self, anomaly: Dict):
        try:
            self.influx_db.write_anomaly(
                symbol=anomaly["symbol"],
                anomaly_type=anomaly["anomaly_type"],
                severity=anomaly["severity"],
                current_value=anomaly["current_value"],
                timestamp=anomaly["timestamp"]
            )

            logger.warning(f"Anomaly detected: {anomaly}")

            self.alert_manager.send_alert(anomaly)

        except Exception as e:
            logger.error(f"Error logging anomaly: {e}", exc_info=True)


class AnomalyMonitor:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.kafka_consumer = None
        self.running = False

    def start_monitoring(self):
        self.kafka_consumer = KafkaConsumer(
            settings.kafka_tick_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id='anomaly-detector',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )

        self.running = True
        logger.info("Anomaly monitoring started")

        for message in self.kafka_consumer:
            if not self.running:
                break

            try:
                data = message.value
                symbol = data.get('symbol')
                price = data.get('price')
                volume = data.get('volume', 0)

                self.detector.indicator_calculator.add_price_data(
                    symbol,
                    datetime.fromisoformat(data.get('timestamp')),
                    price,
                    volume
                )

                self.detector.detect_price_spike(symbol, price)
                if volume > 0:
                    self.detector.detect_volume_spike(symbol, volume)

                indicators = self.detector.indicator_calculator.calculate_all_indicators(symbol)
                if indicators.get('rsi'):
                    self.detector.detect_rsi_extremes(symbol, indicators['rsi'])

            except Exception as e:
                logger.error(f"Error processing message in anomaly detector: {e}", exc_info=True)

    def stop_monitoring(self):
        self.running = False
        if self.kafka_consumer:
            self.kafka_consumer.close()
        logger.info("Anomaly monitoring stopped")


def main():
    monitor = AnomalyMonitor()
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.stop_monitoring()


if __name__ == "__main__":
    main()
