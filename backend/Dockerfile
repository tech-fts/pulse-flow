FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy dependencies first so unchanged dependencies use a cached layer.
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy only source required at runtime.
COPY app ./app

# Compose supplies either the Uvicorn or worker command.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
