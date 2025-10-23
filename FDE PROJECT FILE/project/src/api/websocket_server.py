import asyncio
import json
import websockets
from typing import Set
from datetime import datetime
from kafka import KafkaConsumer
from threading import Thread
from src.utils.config_loader import settings
from src.utils.logger import setup_logger

logger = setup_logger("websocket_server")

connected_clients: Set[websockets.WebSocketServerProtocol] = set()
latest_data = {}


class WebSocketBroadcaster:
    def __init__(self):
        self.kafka_consumer = None
        self.running = False

    def start_kafka_consumer(self):
        self.kafka_consumer = KafkaConsumer(
            settings.kafka_tick_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id='websocket-broadcaster',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )

        self.running = True
        logger.info("Kafka consumer started for WebSocket broadcasting")

        for message in self.kafka_consumer:
            if not self.running:
                break

            try:
                data = message.value
                symbol = data.get('symbol')

                latest_data[symbol] = {
                    'symbol': symbol,
                    'price': data.get('price'),
                    'volume': data.get('volume'),
                    'timestamp': data.get('timestamp'),
                    'tick_type': data.get('tick_type')
                }

                asyncio.run(self.broadcast_to_clients(latest_data[symbol]))

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)

    async def broadcast_to_clients(self, data: dict):
        if connected_clients:
            message = json.dumps(data)
            await asyncio.gather(
                *[client.send(message) for client in connected_clients],
                return_exceptions=True
            )

    def stop(self):
        self.running = False
        if self.kafka_consumer:
            self.kafka_consumer.close()


broadcaster = WebSocketBroadcaster()


async def handle_client(websocket, path):
    connected_clients.add(websocket)
    client_address = websocket.remote_address
    logger.info(f"Client connected: {client_address}")

    try:
        await websocket.send(json.dumps({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to Market Data WebSocket"
        }))

        if latest_data:
            for symbol_data in latest_data.values():
                await websocket.send(json.dumps(symbol_data))

        async for message in websocket:
            try:
                data = json.loads(message)

                if data.get('type') == 'subscribe':
                    symbols = data.get('symbols', [])
                    logger.info(f"Client {client_address} subscribed to: {symbols}")
                    await websocket.send(json.dumps({
                        "type": "subscription",
                        "status": "success",
                        "symbols": symbols
                    }))

                elif data.get('type') == 'ping':
                    await websocket.send(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from client {client_address}")
            except Exception as e:
                logger.error(f"Error handling message from {client_address}: {e}")

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {client_address}")
    except Exception as e:
        logger.error(f"Error with client {client_address}: {e}", exc_info=True)
    finally:
        connected_clients.remove(websocket)


async def start_websocket_server():
    logger.info(f"Starting WebSocket server on port {settings.websocket_port}")

    consumer_thread = Thread(target=broadcaster.start_kafka_consumer, daemon=True)
    consumer_thread.start()

    async with websockets.serve(handle_client, "0.0.0.0", settings.websocket_port):
        await asyncio.Future()


def main():
    try:
        asyncio.run(start_websocket_server())
    except KeyboardInterrupt:
        logger.info("WebSocket server shutting down")
        broadcaster.stop()


if __name__ == "__main__":
    main()
