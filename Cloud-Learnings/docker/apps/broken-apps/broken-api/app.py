"""
Broken API — for debugging practice
This application has 3 deliberate bugs. Find and fix them.

Bug hints (read after you've tried):
1. Check the imports at the top
2. Check how DATABASE_URL is constructed
3. Check the /health endpoint
"""

import os

from fastapi import FastAPI

# BUG 1: Wrong import name — this module doesn't exist
# from fastapi.responses import JsonResponse  # Typo: should be JSONResponse
from fastapi.responses import JSONResponse

# BUG 2: Using a non-existent environment variable name
# The env var is DATABASE_URL but we're reading DB_CONNECTION_STR
DATABASE_URL = os.getenv("DB_CONNECTION_STR")  # Bug: should be "DATABASE_URL"
if not DATABASE_URL:
    # This will cause a startup failure
    raise RuntimeError("Missing required environment variable: DB_CONNECTION_STR")

app = FastAPI(title="Broken API (for debugging)")


@app.get("/health")
def health():
    # BUG 3: Division by zero — will crash on every /health call
    uptime = 100 / 0  # Bug: division by zero
    return JSONResponse({"status": "ok", "uptime": uptime})


@app.get("/")
def root():
    return {"message": "I am a broken API. Fix my bugs!"}
