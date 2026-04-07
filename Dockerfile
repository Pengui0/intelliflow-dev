# IntelliFlow Urban Traffic Control
# Hugging Face Docker Space compatible image
# Port: 7860 (HF default)

FROM python:3.11-slim

# Metadata
LABEL maintainer="IntelliFlow Research"
LABEL description="OpenEnv-compliant Urban Traffic RL Environment"
LABEL version="1.0.0"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user (HF requirement)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
# Create persistent data directory for DQN weight storage
RUN mkdir -p /data && chown -R appuser:appuser /data
USER appuser

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:7860/health || exit 1

# Launch
CMD ["uvicorn", "app.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "7860", \
     "--workers", "1", \
     "--log-level", "info"]