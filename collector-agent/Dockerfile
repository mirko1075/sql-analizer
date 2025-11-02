FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent script
COPY agent.py .

# Make the script executable
RUN chmod +x agent.py

# Set environment variables (can be overridden at runtime)
ENV DBPOWER_API_URL=http://localhost:8000/api/v1
ENV COLLECTION_INTERVAL_SECONDS=300
ENV HEARTBEAT_INTERVAL_SECONDS=60

# Run the agent
CMD ["python", "agent.py"]
