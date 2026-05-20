FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/

# Expose API port
EXPOSE 8000

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash jengo
USER jengo

# Run the API
CMD ["python", "-m", "jengo.api.main"]
