import redis
import json
from typing import Optional, Dict, Any
from datetime import timedelta
from src.utils.config_loader import settings
from src.utils.logger import setup_logger

logger = setup_logger("redis_cache")


class RedisCache:
    def __init__(self):
        self.client = None
        self.connect()

    def connect(self):
        try:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}", exc_info=True)
            raise

    def cache_latest_price(self, symbol: str, price: float, volume: float, timestamp: str, ttl_seconds: int = 60):
        try:
            key = f"latest_price:{symbol}"
            value = json.dumps({
                "price": price,
                "volume": volume,
                "timestamp": timestamp
            })
            self.client.setex(key, ttl_seconds, value)
        except Exception as e:
            logger.error(f"Error caching latest price: {e}", exc_info=True)

    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            key = f"latest_price:{symbol}"
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting latest price: {e}", exc_info=True)
            return None

    def cache_technical_indicators(self, symbol: str, indicators: Dict[str, float], ttl_seconds: int = 300):
        try:
            key = f"indicators:{symbol}"
            value = json.dumps(indicators)
            self.client.setex(key, ttl_seconds, value)
        except Exception as e:
            logger.error(f"Error caching technical indicators: {e}", exc_info=True)

    def get_technical_indicators(self, symbol: str) -> Optional[Dict[str, float]]:
        try:
            key = f"indicators:{symbol}"
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting technical indicators: {e}", exc_info=True)
            return None

    def cache_aggregated_data(self, symbol: str, window: str, data: Dict[str, Any], ttl_seconds: int = 300):
        try:
            key = f"aggregated:{symbol}:{window}"
            value = json.dumps(data)
            self.client.setex(key, ttl_seconds, value)
        except Exception as e:
            logger.error(f"Error caching aggregated data: {e}", exc_info=True)

    def get_aggregated_data(self, symbol: str, window: str) -> Optional[Dict[str, Any]]:
        try:
            key = f"aggregated:{symbol}:{window}"
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting aggregated data: {e}", exc_info=True)
            return None

    def increment_message_counter(self, symbol: str):
        try:
            key = f"message_count:{symbol}"
            self.client.incr(key)
            self.client.expire(key, 60)
        except Exception as e:
            logger.error(f"Error incrementing message counter: {e}", exc_info=True)

    def get_message_rate(self, symbol: str) -> int:
        try:
            key = f"message_count:{symbol}"
            value = self.client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Error getting message rate: {e}", exc_info=True)
            return 0

    def close(self):
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")
