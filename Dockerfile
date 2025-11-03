# syntax=docker/dockerfile:1
FROM python:3.11-slim

# System dependencies for audio libraries (sounddevice/soundfile)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libportaudio2 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY vani/ ./vani/
COPY agent.py ./

ENV PYTHONUNBUFFERED=1

# Expose FastAPI via Uvicorn
EXPOSE 8000

# Default CMD - run API server (note: audio features require host access)
CMD ["uvicorn", "vani.api:app", "--host", "0.0.0.0", "--port", "8000"]