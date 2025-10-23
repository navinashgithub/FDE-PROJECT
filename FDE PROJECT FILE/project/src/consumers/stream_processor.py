from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, avg, sum as spark_sum, max as spark_max,
    min as spark_min, count, first, last, current_timestamp, to_timestamp
)
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
import json
from src.utils.config_loader import settings, api_config
from src.utils.logger import setup_logger

logger = setup_logger("stream_processor")


class SparkStreamProcessor:
    def __init__(self):
        self.spark = self._create_spark_session()
        self.tick_schema = self._define_tick_schema()

    def _create_spark_session(self) -> SparkSession:
        return SparkSession.builder \
            .appName("MarketDataStreamProcessor") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
            .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoint") \
            .config("spark.sql.shuffle.partitions", "10") \
            .config("spark.streaming.kafka.maxRatePerPartition", "1000") \
            .getOrCreate()

    def _define_tick_schema(self) -> StructType:
        return StructType([
            StructField("symbol", StringType(), False),
            StructField("price", DoubleType(), False),
            StructField("volume", DoubleType(), True),
            StructField("timestamp", StringType(), False),
            StructField("tick_type", StringType(), True),
            StructField("bid", DoubleType(), True),
            StructField("ask", DoubleType(), True),
            StructField("bid_size", StringType(), True),
            StructField("ask_size", StringType(), True),
            StructField("exchange", StringType(), True),
        ])

    def process_tick_stream(self):
        logger.info("Starting Spark Structured Streaming for tick data")

        df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", settings.kafka_bootstrap_servers) \
            .option("subscribe", settings.kafka_tick_topic) \
            .option("startingOffsets", "latest") \
            .option("maxOffsetsPerTrigger", "10000") \
            .load()

        parsed_df = df.select(
            from_json(col("value").cast("string"), self.tick_schema).alias("data")
        ).select("data.*")

        parsed_df = parsed_df.withColumn(
            "timestamp",
            to_timestamp(col("timestamp"))
        )

        return parsed_df

    def create_windowed_aggregations(self, stream_df):
        window_configs = api_config.get("window_configurations", [])

        for window_config in window_configs:
            window_name = window_config["name"]
            duration_seconds = window_config["duration"]
            slide_seconds = window_config.get("slide", duration_seconds)

            logger.info(f"Creating {window_name} window aggregation")

            windowed_df = stream_df \
                .withWatermark("timestamp", "30 seconds") \
                .groupBy(
                    window(col("timestamp"), f"{duration_seconds} seconds", f"{slide_seconds} seconds"),
                    col("symbol")
                ) \
                .agg(
                    first("price").alias("open"),
                    spark_max("price").alias("high"),
                    spark_min("price").alias("low"),
                    last("price").alias("close"),
                    spark_sum("volume").alias("volume"),
                    avg(col("price") * col("volume")).alias("price_volume"),
                    spark_sum("volume").alias("total_volume"),
                    count("*").alias("trade_count")
                ) \
                .withColumn("vwap", col("price_volume") / col("total_volume")) \
                .withColumn("window_duration", col("window.end").cast("long") - col("window.start").cast("long")) \
                .select(
                    col("symbol"),
                    col("window.start").alias("window_start"),
                    col("window.end").alias("window_end"),
                    col("open"),
                    col("high"),
                    col("low"),
                    col("close"),
                    col("volume"),
                    col("vwap"),
                    col("trade_count"),
                    col("window_duration")
                )

            query = windowed_df \
                .writeStream \
                .outputMode("append") \
                .format("kafka") \
                .option("kafka.bootstrap.servers", settings.kafka_bootstrap_servers) \
                .option("topic", f"{settings.kafka_aggregated_topic}_{window_name}") \
                .option("checkpointLocation", f"/tmp/spark-checkpoint/{window_name}") \
                .start()

            logger.info(f"Started streaming query for {window_name} window")

        return query

    def process_and_write_to_console(self, stream_df):
        query = stream_df \
            .writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", "false") \
            .start()

        return query

    def start_processing(self):
        try:
            tick_stream = self.process_tick_stream()

            self.create_windowed_aggregations(tick_stream)

            self.spark.streams.awaitAnyTermination()

        except Exception as e:
            logger.error(f"Error in stream processing: {e}", exc_info=True)
        finally:
            self.spark.stop()


def main():
    processor = SparkStreamProcessor()
    processor.start_processing()


if __name__ == "__main__":
    main()
