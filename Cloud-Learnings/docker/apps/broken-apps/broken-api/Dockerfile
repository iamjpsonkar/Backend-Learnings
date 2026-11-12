FROM python:3.12-slim

WORKDIR /app

# NOTE: requirements has a typo — "uvicron" instead of "uvicorn"
# This is intentional for debugging practice
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8003

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
