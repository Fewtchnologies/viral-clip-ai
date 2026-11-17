FROM python:3.11-slim

# Install system dependencies including FFmpeg and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for building the React frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements & install
COPY requirements.txt ./
RUN pip install --no-cache-dir -U pip yt-dlp && pip install --no-cache-dir -r requirements.txt

# Copy frontend & build production bundle
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

COPY frontend ./frontend
RUN cd frontend && npm run build

# Copy backend source
COPY backend ./backend
COPY .env.example ./.env

# Create required media storage folders
RUN mkdir -p backend/uploads backend/temp backend/output bin

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
