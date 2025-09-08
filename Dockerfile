FROM python:3.13.7-slim

# RUN apt-get update && apt-get install -y --no-install-recommends \
#    build-essential libpq-dev \
#    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

WORKDIR /MedFabric

COPY pyproject.toml poetry.lock* ./
COPY medfabric/ ./medfabric/
COPY .streamlit/ ./.streamlit/
 

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --with dev

VOLUME /MedFabric/public_data    
EXPOSE 8501
ENV PYTHONPATH=/MedFabric
CMD ["streamlit", "run", "medfabric/main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--server.showEmailPrompt=false"]
