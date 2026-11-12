"""
Event Consumer
Consumes events from RabbitMQ lab.orders queue.
Logs all received events with structured JSON.
"""

import json
import logging
import os
import signal
import sys
import time

import pika
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("event-consumer")
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level"}
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:adminpassword123@localhost:5672/")
QUEUE_NAME = "lab.orders"
SHUTDOWN = False


def handle_signal(signum, _frame):
    global SHUTDOWN
    logger.info("Shutdown signal received", extra={"signal": signum})
    SHUTDOWN = True


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def on_message(channel, method, _properties, body: bytes) -> None:
    try:
        payload = json.loads(body)
        event_id = payload.get("event_id", "unknown")
        event_type = payload.get("type", "unknown")

        logger.info(
            "Event received",
            extra={
                "event_id": event_id,
                "type": event_type,
                "order_id": payload.get("payload", {}).get("orderId", "unknown"),
                "delivery_tag": method.delivery_tag
            }
        )

        # Simulate processing
        time.sleep(0.05)

        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Event acknowledged", extra={"event_id": event_id, "delivery_tag": method.delivery_tag})

    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON", extra={"error": str(exc)})
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as exc:
        logger.error("Consumer error", extra={"error": str(exc)})
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def connect() -> pika.BlockingConnection:
    params = pika.URLParameters(RABBITMQ_URL)
    retry = 2
    waited = 0
    while waited < 60:
        try:
            conn = pika.BlockingConnection(params)
            logger.info("Connected to RabbitMQ", extra={"host": RABBITMQ_URL.split("@")[-1]})
            return conn
        except Exception as exc:
            logger.warning("Waiting for RabbitMQ", extra={"error": str(exc), "retry_in": retry})
            time.sleep(retry)
            waited += retry
            retry = min(retry * 2, 15)
    logger.error("Could not connect to RabbitMQ")
    sys.exit(1)


def main():
    logger.info("Event consumer starting", extra={"queue": QUEUE_NAME})
    connection = connect()
    channel = connection.channel()
    channel.basic_qos(prefetch_count=5)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
    logger.info("Consumer ready", extra={"queue": QUEUE_NAME})
    while not SHUTDOWN:
        try:
            connection.process_data_events(time_limit=1)
        except Exception as exc:
            logger.error("Connection error — reconnecting", extra={"error": str(exc)})
            if SHUTDOWN:
                break
            connection = connect()
            channel = connection.channel()
            channel.basic_qos(prefetch_count=5)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
    logger.info("Consumer shutdown")
    try:
        connection.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
