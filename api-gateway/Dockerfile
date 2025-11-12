# DBPower API Gateway - Dockerfile

FROM python:3.11-slim

LABEL maintainer="DBPower AI <support@dbpower.ai>"
LABEL description="API Gateway for DBPower services - routing, auth, rate limiting"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r dbpower && \
    useradd -r -g dbpower -u 1000 dbpower && \
    chown -R dbpower:dbpower /app

# Copy requirements first (for better caching)
COPY --chown=dbpower:dbpower requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=dbpower:dbpower . .

# Switch to non-root user
USER dbpower

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "gateway.py"]
