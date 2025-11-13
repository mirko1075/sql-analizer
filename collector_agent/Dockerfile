FROM python:3.11-slim

LABEL maintainer="DBPower AI Cloud"
LABEL description="Collector Agent for monitoring external databases"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy collector agent
COPY collector_agent.py .

# Create directory for config
RUN mkdir -p /app/config

# Run as non-root user
RUN useradd -m -u 1000 collector && chown -R collector:collector /app
USER collector

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Run collector agent
ENTRYPOINT ["python", "-u", "collector_agent.py"]
CMD ["--config", "/app/config/config.json"]
