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

# Copy identity service (needed by api-gateway)
COPY apps/identity /app/apps/identity
WORKDIR /app/apps/identity
RUN pip install -e .

# Copy api-gateway service
WORKDIR /app
COPY apps/api-gateway /app/apps/api-gateway

# Copy scripts for migrations
COPY scripts /app/scripts

# Install dependencies
WORKDIR /app/apps/api-gateway
RUN pip install --no-cache-dir -e .

# Run api-gateway
CMD ["python", "-m", "api_gateway.main"]

