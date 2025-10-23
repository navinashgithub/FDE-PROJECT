import json
import asyncio
import websocket
import time
from typing import Dict, List, Optional
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import requests
from src.utils.config_loader import settings, api_config
from src.utils.logger import setup_logger
from src.utils.schemas import TickData, TickType

logger = setup_logger("market_api_streamer")


class PolygonStreamer:
    def __init__(self, api_key: str, symbols: List[str], kafka_producer: KafkaProducer):
        self.api_key = api_key
        self.symbols = symbols
        self.kafka_producer = kafka_producer
        self.ws_url = f"wss://socket.polygon.io/stocks"
        self.ws = None
        self.connected = False

    def on_message(self, ws, message):
        try:
            data = json.loads(message)

            if isinstance(data, list):
                for item in data:
                    self._process_message(item)
            else:
                self._process_message(data)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def _process_message(self, item: Dict):
        try:
            if item.get("ev") == "T":
                tick_data = TickData(
                    symbol=item.get("sym"),
                    price=item.get("p"),
                    volume=item.get("s"),
                    timestamp=datetime.fromtimestamp(item.get("t") / 1000),
                    tick_type=TickType.TRADE,
                    exchange=item.get("x")
                )
                self._send_to_kafka(tick_data)

            elif item.get("ev") == "Q":
                tick_data = TickData(
                    symbol=item.get("sym"),
                    price=(item.get("bp") + item.get("ap")) / 2,
                    timestamp=datetime.fromtimestamp(item.get("t") / 1000),
                    tick_type=TickType.QUOTE,
                    bid=item.get("bp"),
                    ask=item.get("ap"),
                    bid_size=item.get("bs"),
                    ask_size=item.get("as")
                )
                self._send_to_kafka(tick_data)

        except Exception as e:
            logger.error(f"Error processing tick: {e}")

    def _send_to_kafka(self, tick_data: TickData):
        try:
            message = tick_data.model_dump_json()
            future = self.kafka_producer.send(
                settings.kafka_tick_topic,
                value=message.encode('utf-8'),
                key=tick_data.symbol.encode('utf-8')
            )
            future.add_callback(lambda _: None)
            future.add_errback(lambda e: logger.error(f"Kafka send failed: {e}"))
        except Exception as e:
            logger.error(f"Error sending to Kafka: {e}")

    def on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
        self.connected = False

    def on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.connected = False

    def on_open(self, ws):
        logger.info("WebSocket connection opened")
        self.connected = True

        auth_message = {"action": "auth", "params": self.api_key}
        ws.send(json.dumps(auth_message))

        subscribe_message = {
            "action": "subscribe",
            "params": ",".join([f"T.{symbol}" for symbol in self.symbols])
        }
        ws.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to symbols: {self.symbols}")

    def start(self):
        logger.info("Starting Polygon.io WebSocket stream")
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever()


class FinageStreamer:
    def __init__(self, api_key: str, symbols: List[str], kafka_producer: KafkaProducer):
        self.api_key = api_key
        self.symbols = symbols
        self.kafka_producer = kafka_producer
        self.ws_url = f"wss://w8s.finage.ws?token={api_key}"
        self.ws = None
        self.connected = False

    def on_message(self, ws, message):
        try:
            data = json.loads(message)

            if data.get("s") in self.symbols:
                tick_data = TickData(
                    symbol=data.get("s"),
                    price=float(data.get("p", 0)),
                    volume=float(data.get("v", 0)),
                    timestamp=datetime.fromtimestamp(data.get("t") / 1000),
                    tick_type=TickType.TRADE
                )
                self._send_to_kafka(tick_data)
        except Exception as e:
            logger.error(f"Error processing Finage message: {e}", exc_info=True)

    def _send_to_kafka(self, tick_data: TickData):
        try:
            message = tick_data.model_dump_json()
            self.kafka_producer.send(
                settings.kafka_tick_topic,
                value=message.encode('utf-8'),
                key=tick_data.symbol.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error sending to Kafka: {e}")

    def on_error(self, ws, error):
        logger.error(f"Finage WebSocket error: {error}")
        self.connected = False

    def on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"Finage WebSocket closed: {close_status_code}")
        self.connected = False

    def on_open(self, ws):
        logger.info("Finage WebSocket connection opened")
        self.connected = True

        for symbol in self.symbols:
            subscribe_msg = {"action": "subscribe", "symbols": symbol}
            ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to Finage symbols: {self.symbols}")

    def start(self):
        logger.info("Starting Finage WebSocket stream")
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever()


class AlphaVantageFallback:
    def __init__(self, api_key: str, symbols: List[str], kafka_producer: KafkaProducer):
        self.api_key = api_key
        self.symbols = symbols
        self.kafka_producer = kafka_producer
        self.base_url = "https://www.alphavantage.co/query"
        self.running = False

    async def fetch_and_stream(self):
        self.running = True
        logger.info("Starting Alpha Vantage fallback polling")

        while self.running:
            for symbol in self.symbols:
                try:
                    params = {
                        "function": "GLOBAL_QUOTE",
                        "symbol": symbol,
                        "apikey": self.api_key
                    }
                    response = requests.get(self.base_url, params=params, timeout=10)
                    data = response.json()

                    if "Global Quote" in data:
                        quote = data["Global Quote"]
                        tick_data = TickData(
                            symbol=symbol,
                            price=float(quote.get("05. price", 0)),
                            volume=float(quote.get("06. volume", 0)),
                            timestamp=datetime.now(),
                            tick_type=TickType.TRADE
                        )
                        self._send_to_kafka(tick_data)
                except Exception as e:
                    logger.error(f"Error fetching from Alpha Vantage for {symbol}: {e}")

            await asyncio.sleep(12)

    def _send_to_kafka(self, tick_data: TickData):
        try:
            message = tick_data.model_dump_json()
            self.kafka_producer.send(
                settings.kafka_tick_topic,
                value=message.encode('utf-8'),
                key=tick_data.symbol.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error sending to Kafka: {e}")

    def stop(self):
        self.running = False


def create_kafka_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: v,
        key_serializer=lambda k: k,
        acks='all',
        retries=3,
        max_in_flight_requests_per_connection=5,
        compression_type='snappy',
        batch_size=16384,
        linger_ms=10
    )


def main():
    logger.info("Starting Market Data Streamer")

    symbols = settings.symbols.split(',')
    kafka_producer = create_kafka_producer()

    try:
        if settings.polygon_api_key:
            logger.info("Using Polygon.io as primary data source")
            streamer = PolygonStreamer(settings.polygon_api_key, symbols, kafka_producer)
            streamer.start()
        elif settings.finage_api_key:
            logger.info("Using Finage as primary data source")
            streamer = FinageStreamer(settings.finage_api_key, symbols, kafka_producer)
            streamer.start()
        elif settings.alpha_vantage_api_key:
            logger.info("Using Alpha Vantage as fallback data source")
            fallback = AlphaVantageFallback(settings.alpha_vantage_api_key, symbols, kafka_producer)
            asyncio.run(fallback.fetch_and_stream())
        else:
            logger.error("No API keys configured. Please set at least one API key.")
    except KeyboardInterrupt:
        logger.info("Shutting down streamer")
    finally:
        kafka_producer.close()


if __name__ == "__main__":
    main()
