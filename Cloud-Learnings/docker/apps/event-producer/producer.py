"""
Event Producer
Publishes sample events to RabbitMQ and Redpanda (Kafka).
Runs a simple HTTP server for triggering events on demand.
"""

import json
import logging
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import pika
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("event-producer")
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level"}
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:adminpassword123@localhost:5672/")
EXCHANGE = "lab.events"
PORT = int(os.getenv("PORT", "8001"))


def get_rabbitmq_channel() -> tuple:
    """Create a new RabbitMQ connection and channel."""
    params = pika.URLParameters(RABBITMQ_URL)
    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True, passive=True)
    return conn, channel


def publish_event(event_type: str, payload: dict) -> str:
    """Publish an event to RabbitMQ."""
    event_id = str(uuid.uuid4())
    message = {
        "event_id": event_id,
        "type": event_type,
        "payload": payload,
        "timestamp": time.time()
    }

    logger.info("Publishing event", extra={"event_id": event_id, "type": event_type})

    try:
        conn, channel = get_rabbitmq_channel()
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=event_type,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent
                message_id=event_id,
                content_type="application/json"
            )
        )
        conn.close()
        logger.info("Event published", extra={"event_id": event_id, "routing_key": event_type})
    except Exception as exc:
        logger.error("Failed to publish event", extra={"event_id": event_id, "error": str(exc)})

    return event_id


class EventHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for triggering events."""

    def log_message(self, fmt, *args):  # Suppress default HTTP logs
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "event-producer"}).encode())

        elif self.path == "/produce":
            event_id = publish_event("order.created", {
                "orderId": f"ORD-{uuid.uuid4().hex[:8].upper()}",
                "amount": round(10 + (hash(time.time()) % 90), 2),
                "currency": "USD"
            })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"event_id": event_id}).encode())

        else:
            self.send_response(404)
            self.end_headers()


def background_producer():
    """Produces events automatically every 10 seconds."""
    logger.info("Background producer starting", extra={"interval_seconds": 10})
    while True:
        try:
            event_id = publish_event("order.created", {
                "orderId": f"ORD-{uuid.uuid4().hex[:8].upper()}",
                "amount": round(10 + (hash(time.time()) % 90), 2),
                "currency": "USD"
            })
            logger.debug("Background event sent", extra={"event_id": event_id})
        except Exception as exc:
            logger.warning("Background producer error", extra={"error": str(exc)})
        time.sleep(10)


def main():
    logger.info("Event producer starting", extra={"port": PORT, "rabbitmq": RABBITMQ_URL.split("@")[-1]})

    # Start background producer thread
    t = threading.Thread(target=background_producer, daemon=True)
    t.start()

    # Start HTTP server
    server = HTTPServer(("0.0.0.0", PORT), EventHandler)
    logger.info("HTTP server ready", extra={"port": PORT})
    logger.info("Endpoints: GET /health  GET /produce")
    server.serve_forever()


if __name__ == "__main__":
    main()
