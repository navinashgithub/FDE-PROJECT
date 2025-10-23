import os
import yaml
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    polygon_api_key: str = Field(default="", alias="POLYGON_API_KEY")
    finage_api_key: str = Field(default="", alias="FINAGE_API_KEY")
    alpha_vantage_api_key: str = Field(default="", alias="ALPHA_VANTAGE_API_KEY")
    fmp_api_key: str = Field(default="", alias="FMP_API_KEY")

    kafka_bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_tick_topic: str = Field(default="tick_data", alias="KAFKA_TICK_TOPIC")
    kafka_aggregated_topic: str = Field(default="aggregated_data", alias="KAFKA_AGGREGATED_TOPIC")

    timescaledb_host: str = Field(default="localhost", alias="TIMESCALEDB_HOST")
    timescaledb_port: int = Field(default=5432, alias="TIMESCALEDB_PORT")
    timescaledb_user: str = Field(default="postgres", alias="TIMESCALEDB_USER")
    timescaledb_password: str = Field(default="postgres", alias="TIMESCALEDB_PASSWORD")
    timescaledb_database: str = Field(default="market_data", alias="TIMESCALEDB_DATABASE")

    influxdb_url: str = Field(default="http://localhost:8086", alias="INFLUXDB_URL")
    influxdb_token: str = Field(default="", alias="INFLUXDB_TOKEN")
    influxdb_org: str = Field(default="market_org", alias="INFLUXDB_ORG")
    influxdb_bucket: str = Field(default="market_metrics", alias="INFLUXDB_BUCKET")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    supabase_url: str = Field(default="", alias="VITE_SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="VITE_SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    websocket_port: int = Field(default=8001, alias="WEBSOCKET_PORT")

    symbols: str = Field(default="AAPL,GOOGL,MSFT,AMZN,TSLA", alias="SYMBOLS")
    processing_latency_threshold_ms: int = Field(default=100, alias="PROCESSING_LATENCY_THRESHOLD_MS")
    max_messages_per_second: int = Field(default=10000, alias="MAX_MESSAGES_PER_SECOND")

    alert_email: str = Field(default="", alias="ALERT_EMAIL")
    slack_webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")

    ml_model_path: str = Field(default="./models/price_predictor.pkl", alias="ML_MODEL_PATH")
    ml_retrain_interval_hours: int = Field(default=24, alias="ML_RETRAIN_INTERVAL_HOURS")

    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True


def load_api_config() -> Dict[str, Any]:
    config_path = Path(__file__).parent.parent.parent / "config" / "api_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


settings = Settings()
api_config = load_api_config()
