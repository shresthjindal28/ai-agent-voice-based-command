# syntax=docker/dockerfile:1
FROM python:3.11-slim

# System dependencies for audio libraries (sounddevice/soundfile)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY vani/ ./vani/
COPY agent.py ./

ENV PYTHONUNBUFFERED=1

# Expect environment variables injected at runtime (e.g., OPENAI_API_KEY)
CMD ["python", "agent.py"]