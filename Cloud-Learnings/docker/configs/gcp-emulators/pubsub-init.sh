#!/bin/bash
# GCP Pub/Sub emulator initialization script
# Run this after the emulator is started to create sample topics/subscriptions

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-local-dev-project}"
EMULATOR_HOST="${PUBSUB_EMULATOR_HOST:-localhost:8085}"

export PUBSUB_EMULATOR_HOST="$EMULATOR_HOST"

echo "[GCP PubSub Init] Initializing Pub/Sub emulator..."
echo "[GCP PubSub Init] Project: $PROJECT_ID"
echo "[GCP PubSub Init] Emulator: $EMULATOR_HOST"

# Configure gcloud to use emulator
gcloud config set project "$PROJECT_ID" 2>/dev/null || true
gcloud beta emulators pubsub env-init 2>/dev/null || true

# Create topics using the REST API directly (more reliable in scripts)
BASE_URL="http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}"

create_topic() {
  local topic_id="$1"
  echo "[GCP PubSub Init]   Creating topic: $topic_id"
  curl -sf -X PUT "${BASE_URL}/topics/${topic_id}" \
    -H "Content-Type: application/json" \
    -d '{}' > /dev/null 2>&1 && \
    echo "[GCP PubSub Init]   Created: $topic_id" || \
    echo "[GCP PubSub Init]   Already exists or failed: $topic_id"
}

create_subscription() {
  local sub_id="$1"
  local topic_id="$2"
  echo "[GCP PubSub Init]   Creating subscription: $sub_id -> $topic_id"
  curl -sf -X PUT "${BASE_URL}/subscriptions/${sub_id}" \
    -H "Content-Type: application/json" \
    -d "{\"topic\": \"projects/${PROJECT_ID}/topics/${topic_id}\", \"ackDeadlineSeconds\": 30}" \
    > /dev/null 2>&1 && \
    echo "[GCP PubSub Init]   Created: $sub_id" || \
    echo "[GCP PubSub Init]   Already exists or failed: $sub_id"
}

# Wait for emulator
until curl -sf "http://${EMULATOR_HOST}" > /dev/null 2>&1; do
  echo "[GCP PubSub Init] Waiting for emulator..."
  sleep 2
done

# Create topics
create_topic "lab-events"
create_topic "lab-orders"
create_topic "lab-notifications"

# Create subscriptions
create_subscription "lab-events-sub" "lab-events"
create_subscription "lab-orders-sub" "lab-orders"
create_subscription "lab-notifications-sub" "lab-notifications"

echo "[GCP PubSub Init] Initialization complete."
echo ""
echo "  Usage:"
echo "    export PUBSUB_EMULATOR_HOST=${EMULATOR_HOST}"
echo "    gcloud pubsub topics list --project=${PROJECT_ID}"
echo "    gcloud pubsub topics publish lab-events --message='hello' --project=${PROJECT_ID}"
