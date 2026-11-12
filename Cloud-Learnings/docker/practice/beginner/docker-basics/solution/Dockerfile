FROM python:3.12-slim

WORKDIR /app

COPY server.py .

RUN useradd -m -u 1001 appuser && chown /app -R appuser
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["python", "server.py"]
