# Dockerfile
# MedFabric/Dockerfile
FROM python:3.13.7-slim-trixie

WORKDIR /app

# Copy the app code
COPY medfabric/ /app/medfabric/
COPY requirements.txt /app/
COPY poetry.lock pyproject.toml /app/
COPY .streamlit/ /app/.streamlit/


RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
#    software-properties-common \
#    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENV PYTHONPATH=/app
ENTRYPOINT ["streamlit", "run", "medfabric/main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]