FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy shared package
COPY packages/edna-common /app/packages/edna-common
WORKDIR /app/packages/edna-common
RUN pip install -e .

# Copy scanner service
WORKDIR /app
COPY apps/scanner /app/apps/scanner
WORKDIR /app/apps/scanner

# Install dependencies
RUN pip install --no-cache-dir -e .

# Run scanner
CMD ["python", "-m", "scanner.main"]

