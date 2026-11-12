FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask python-json-logger

COPY handler.py .

RUN useradd -m -u 1001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8002

CMD ["python", "-u", "handler.py"]
