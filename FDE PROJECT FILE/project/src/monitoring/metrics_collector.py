import time
from datetime import datetime
from typing import Dict
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from kafka import KafkaConsumer
from kafka.admin import KafkaAdminClient, ConsumerGroupDescription
from src.utils.config_loader import settings
from src.utils.logger import setup_logger
from src.storage.influxdb_handler import InfluxDBHandler

logger = setup_logger("metrics_collector")

tick_messages_received = Counter('tick_messages_received_total', 'Total tick messages received', ['symbol'])
aggregated_messages_received = Counter('aggregated_messages_received_total', 'Total aggregated messages', ['symbol'])
processing_latency = Histogram('processing_latency_seconds', 'Processing latency', ['component'])
kafka_consumer_lag = Gauge('kafka_consumer_lag', 'Consumer lag per topic', ['topic', 'group'])
active_connections = Gauge('active_websocket_connections', 'Number of active WebSocket connections')
messages_per_second = Gauge('messages_per_second', 'Message throughput per second', ['symbol'])


class MetricsCollector:
    def __init__(self):
        self.influx_db = InfluxDBHandler()
        self.running = False

    def record_tick_message(self, symbol: str):
        tick_messages_received.labels(symbol=symbol).inc()

    def record_processing_latency(self, component: str, latency_seconds: float):
        processing_latency.labels(component=component).observe(latency_seconds)

        latency_ms = latency_seconds * 1000
        self.influx_db.write_latency_metric(component, latency_ms, datetime.now())

    def collect_kafka_metrics(self):
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=settings.kafka_bootstrap_servers
            )

            consumer_groups = admin_client.list_consumer_groups()

            for group_info in consumer_groups:
                group_id = group_info[0]

                try:
                    consumer = KafkaConsumer(
                        bootstrap_servers=settings.kafka_bootstrap_servers,
                        group_id=group_id,
                        enable_auto_commit=False
                    )

                    partitions = consumer.partitions_for_topic(settings.kafka_tick_topic)

                    if partitions:
                        total_lag = 0
                        for partition in partitions:
                            tp = (settings.kafka_tick_topic, partition)
                            committed = consumer.committed(tp)
                            end_offset = consumer.end_offsets([tp])[tp]

                            lag = end_offset - (committed or 0)
                            total_lag += lag

                        kafka_consumer_lag.labels(
                            topic=settings.kafka_tick_topic,
                            group=group_id
                        ).set(total_lag)

                        self.influx_db.write_kafka_metrics(
                            settings.kafka_tick_topic,
                            total_lag,
                            0,
                            datetime.now()
                        )

                    consumer.close()

                except Exception as e:
                    logger.debug(f"Error collecting metrics for group {group_id}: {e}")

            admin_client.close()

        except Exception as e:
            logger.error(f"Error collecting Kafka metrics: {e}", exc_info=True)

    def start_prometheus_server(self, port: int = 9100):
        try:
            start_http_server(port)
            logger.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Error starting Prometheus server: {e}", exc_info=True)

    def collect_system_metrics(self):
        self.running = True
        logger.info("Metrics collection started")

        while self.running:
            try:
                self.collect_kafka_metrics()
                time.sleep(10)

            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}", exc_info=True)

    def stop_collection(self):
        self.running = False
        logger.info("Metrics collection stopped")


def main():
    collector = MetricsCollector()

    collector.start_prometheus_server(port=9100)

    try:
        collector.collect_system_metrics()
    except KeyboardInterrupt:
        collector.stop_collection()


if __name__ == "__main__":
    main()
