"""
Mock WebSocket Server - Simplified version without Kafka dependencies
Used for development/testing when full infrastructure not available
Broadcasts simulated real-time market data to connected clients
"""
import asyncio
import json
import websockets
from datetime import datetime
from typing import Set
import random

connected_clients: Set = set()

# Mock price data that will be streamed (October 22, 2025 closing prices)
symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
prices = {
    "AAPL": 232.18,      # Apple Inc.
    "GOOGL": 178.45,     # Alphabet Inc.
    "MSFT": 428.72,      # Microsoft Corporation
    "AMZN": 193.50,      # Amazon.com Inc.
    "TSLA": 287.93,      # Tesla Inc.
}


async def broadcast_prices():
    """Continuously broadcast real-time simulated price updates to all connected clients"""
    while True:
        await asyncio.sleep(1)  # Send updates every second

        for symbol in symbols:
            # Simulate realistic real-time price changes (±1-3% variation)
            fluctuation = random.uniform(-3, 3) / 100  # ±1-3% realistic movement
            prices[symbol] *= 1 + fluctuation

            tick_data = {
                "symbol": symbol,
                "price": round(prices[symbol], 2),
                "volume": random.randint(100000, 5000000),
                "timestamp": datetime.now().isoformat(),
                "tick_type": "TRADE",
            }

            # Send to all connected clients
            if connected_clients:
                await asyncio.gather(
                    *[client.send(json.dumps(tick_data)) for client in connected_clients],
                    return_exceptions=True,
                )


async def handle_client(websocket):
    """Handle new WebSocket client connection"""
    connected_clients.add(websocket)
    client_address = websocket.remote_address
    print(f"✓ Client connected: {client_address}")

    try:
        # Send connection confirmation
        await websocket.send(
            json.dumps(
                {
                    "type": "connection",
                    "status": "connected",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Connected to Market Data WebSocket (Mock)",
                }
            )
        )

        # Send current prices
        for symbol, price in prices.items():
            await websocket.send(
                json.dumps(
                    {
                        "symbol": symbol,
                        "price": round(price, 2),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

        # Handle incoming messages
        async for message in websocket:
            try:
                data = json.loads(message)

                if data.get("type") == "subscribe":
                    symbols_requested = data.get("symbols", [])
                    print(f"✓ Client {client_address} subscribed to: {symbols_requested}")
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "subscription",
                                "status": "success",
                                "symbols": symbols_requested,
                            }
                        )
                    )
            except json.JSONDecodeError:
                pass

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"✗ Client disconnected: {client_address}")


async def main():
    """Start WebSocket server and broadcast task"""
    print("=" * 60)
    print("Starting Mock WebSocket Server (Development Mode)")
    print("=" * 60)
    print("✓ WebSocket server running on ws://127.0.0.1:8002")
    print("✓ Broadcasting simulated market data (1 update/second)")
    print("✓ Available symbols: AAPL, GOOGL, MSFT, AMZN, TSLA")
    print("=" * 60)

    # Start the broadcast task
    broadcast_task = asyncio.create_task(broadcast_prices())

    # Start the WebSocket server with SO_REUSEADDR
    async with websockets.serve(handle_client, "127.0.0.1", 8002, reuse_address=True):
        await broadcast_task


if __name__ == "__main__":
    import time
    try:
        time.sleep(2)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✗ WebSocket server stopped")
