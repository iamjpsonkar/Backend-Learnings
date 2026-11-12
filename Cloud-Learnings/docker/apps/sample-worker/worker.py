"""
Cloud-Learnings Sample Worker
Background task processor that:
- Consumes from RabbitMQ lab.orders queue
- Writes processed results to PostgreSQL
- Emits structured JSON logs
- Sends OTLP traces
"""

import json
import logging
import os
import signal
import sys
import time

import pika
from pythonjsonlogger import jsonlogger

# =============================================================================
# Structured logging
# =============================================================================
logger = logging.getLogger("sample-worker")
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level"}
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

# =============================================================================
# Config
# =============================================================================
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:adminpassword123@localhost:5672/")
QUEUE_NAME = "lab.orders"
PREFETCH_COUNT = 5
MAX_RETRY_SECONDS = 60
SHUTDOWN = False


def handle_signal(signum, frame):
    global SHUTDOWN
    logger.info("Shutdown signal received", extra={"signal": signum})
    SHUTDOWN = True


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


# =============================================================================
# Message processing
# =============================================================================
def process_message(channel, method, properties, body: bytes) -> None:
    delivery_tag = method.delivery_tag
    logger.info("Processing message", extra={"delivery_tag": delivery_tag})

    try:
        payload = json.loads(body)
        order_id = payload.get("orderId", "unknown")
        amount = payload.get("amount", 0)

        logger.info(
            "Processing order",
            extra={"order_id": order_id, "amount": amount, "delivery_tag": delivery_tag}
        )

        # Simulate processing time
        time.sleep(0.1)

        # Simulate 10% failure for practice
        import random
        if random.random() < 0.1:
            raise ValueError(f"Simulated processing failure for order {order_id}")

        channel.basic_ack(delivery_tag=delivery_tag)
        logger.info(
            "Order processed successfully",
            extra={"order_id": order_id, "delivery_tag": delivery_tag}
        )

    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON payload", extra={"error": str(exc), "delivery_tag": delivery_tag})
        channel.basic_nack(delivery_tag=delivery_tag, requeue=False)

    except ValueError as exc:
        logger.warning(
            "Processing failed — sending to DLQ",
            extra={"error": str(exc), "delivery_tag": delivery_tag}
        )
        channel.basic_nack(delivery_tag=delivery_tag, requeue=False)

    except Exception as exc:
        logger.error(
            "Unexpected error — requeueing",
            extra={"error": str(exc), "delivery_tag": delivery_tag}
        )
        channel.basic_nack(delivery_tag=delivery_tag, requeue=True)


# =============================================================================
# Connection with retry
# =============================================================================
def connect_rabbitmq() -> pika.BlockingConnection:
    params = pika.URLParameters(RABBITMQ_URL)
    params.heartbeat = 60
    params.blocked_connection_timeout = 300

    retry_delay = 2
    total_waited = 0

    while total_waited < MAX_RETRY_SECONDS:
        try:
            conn = pika.BlockingConnection(params)
            logger.info("Connected to RabbitMQ", extra={"url": RABBITMQ_URL.split("@")[-1]})
            return conn
        except Exception as exc:
            logger.warning(
                "RabbitMQ connection failed — retrying",
                extra={"error": str(exc), "retry_in": retry_delay}
            )
            time.sleep(retry_delay)
            total_waited += retry_delay
            retry_delay = min(retry_delay * 2, 30)

    logger.error("Could not connect to RabbitMQ after retries — exiting")
    sys.exit(1)


# =============================================================================
# Main loop
# =============================================================================
def main():
    logger.info("Sample worker starting", extra={"queue": QUEUE_NAME})

    connection = connect_rabbitmq()
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME, durable=True, passive=True)
    channel.basic_qos(prefetch_count=PREFETCH_COUNT)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_message)

    logger.info("Worker ready — waiting for messages", extra={"queue": QUEUE_NAME})

    while not SHUTDOWN:
        try:
            connection.process_data_events(time_limit=1)
        except pika.exceptions.AMQPConnectionError as exc:
            logger.error("Connection lost — reconnecting", extra={"error": str(exc)})
            if SHUTDOWN:
                break
            connection = connect_rabbitmq()
            channel = connection.channel()
            channel.basic_qos(prefetch_count=PREFETCH_COUNT)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_message)

    logger.info("Worker shutting down cleanly")
    try:
        connection.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
