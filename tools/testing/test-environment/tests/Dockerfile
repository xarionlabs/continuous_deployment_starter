FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy test files
COPY . .

# Make scripts executable (if any exist)
RUN find . -name "*.sh" -exec chmod +x {} \; || true

# Default command
CMD ["pytest", "-v", "--tb=short"]