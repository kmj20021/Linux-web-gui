FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --user --no-cache-dir -r requirements.txt

FROM docker:cli AS docker-cli

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY . .
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
