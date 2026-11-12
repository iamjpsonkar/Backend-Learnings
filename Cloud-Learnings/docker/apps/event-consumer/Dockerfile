FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY consumer.py .

RUN useradd -m -u 1001 appuser && chown -R appuser /app
USER appuser

CMD ["python", "-u", "consumer.py"]
