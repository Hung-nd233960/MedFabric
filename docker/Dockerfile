FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies first to maximize layer cache hit rate.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy application source after dependencies.
COPY medfabric /app/medfabric
COPY scripts /app/scripts
COPY config.toml /app/config.toml
COPY pyproject.toml /app/pyproject.toml

EXPOSE 8501

CMD ["sh", "-c", "bash /app/scripts/initialize.sh && streamlit run medfabric/main.py --server.address=0.0.0.0 --server.port=8501"]
