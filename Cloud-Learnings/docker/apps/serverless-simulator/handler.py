"""
Serverless Function Simulator
Simulates an AWS Lambda / Cloud Run style function invocation.

POST /invoke  {"handler": "hello", "event": {...}}
GET  /health
GET  /functions  — list available handlers
"""

import json
import logging
import os
import time
import traceback
from functools import wraps

from flask import Flask, jsonify, request
from pythonjsonlogger import jsonlogger

# Setup logging
logger = logging.getLogger("serverless-sim")
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level"}
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

app = Flask(__name__)
FUNCTION_REGISTRY: dict = {}


# =============================================================================
# Function registration decorator
# =============================================================================
def register(name: str):
    def decorator(fn):
        FUNCTION_REGISTRY[name] = fn
        logger.info("Function registered", extra={"function": name})
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Sample functions
# =============================================================================
@register("hello")
def handler_hello(event: dict, context: dict) -> dict:
    name = event.get("name", "World")
    return {"message": f"Hello, {name}!", "timestamp": time.time()}


@register("echo")
def handler_echo(event: dict, context: dict) -> dict:
    return {"echo": event, "function_name": context.get("function_name")}


@register("transform")
def handler_transform(event: dict, context: dict) -> dict:
    items = event.get("items", [])
    return {
        "count": len(items),
        "transformed": [str(i).upper() for i in items],
        "sum": sum(x for x in items if isinstance(x, (int, float)))
    }


@register("fail")
def handler_fail(event: dict, _context: dict) -> dict:
    raise RuntimeError("Simulated function failure for debugging practice")


# =============================================================================
# Routes
# =============================================================================
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "serverless-simulator", "functions": list(FUNCTION_REGISTRY.keys())})


@app.route("/functions")
def list_functions():
    return jsonify({
        "functions": [
            {"name": name, "description": fn.__doc__ or ""}
            for name, fn in FUNCTION_REGISTRY.items()
        ]
    })


@app.route("/invoke", methods=["POST"])
def invoke():
    body = request.get_json(force=True) or {}
    function_name = body.get("handler") or body.get("function")
    event = body.get("event", {})

    if not function_name:
        return jsonify({"error": "Missing 'handler' field"}), 400

    if function_name not in FUNCTION_REGISTRY:
        return jsonify({"error": f"Function '{function_name}' not found", "available": list(FUNCTION_REGISTRY.keys())}), 404

    context = {"function_name": function_name, "invocation_id": os.urandom(8).hex()}
    start = time.time()

    logger.info("Invoking function", extra={"function": function_name, "invocation_id": context["invocation_id"]})

    try:
        result = FUNCTION_REGISTRY[function_name](event, context)
        duration_ms = round((time.time() - start) * 1000, 2)
        logger.info(
            "Function completed",
            extra={"function": function_name, "duration_ms": duration_ms, "invocation_id": context["invocation_id"]}
        )
        return jsonify({
            "status": "success",
            "function": function_name,
            "invocation_id": context["invocation_id"],
            "duration_ms": duration_ms,
            "result": result
        })
    except Exception as exc:
        duration_ms = round((time.time() - start) * 1000, 2)
        logger.error(
            "Function failed",
            extra={
                "function": function_name,
                "error": str(exc),
                "duration_ms": duration_ms,
                "invocation_id": context["invocation_id"]
            }
        )
        return jsonify({
            "status": "error",
            "function": function_name,
            "invocation_id": context["invocation_id"],
            "duration_ms": duration_ms,
            "error": str(exc),
            "traceback": traceback.format_exc()
        }), 500


if __name__ == "__main__":
    logger.info("Serverless simulator starting", extra={"port": 8002, "functions": list(FUNCTION_REGISTRY.keys())})
    app.run(host="0.0.0.0", port=8002, debug=False)
