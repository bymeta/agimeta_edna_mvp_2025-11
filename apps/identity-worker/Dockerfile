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

# Copy identity-worker service
WORKDIR /app
COPY apps/identity-worker /app/apps/identity-worker
WORKDIR /app/apps/identity-worker

# Install dependencies
RUN pip install --no-cache-dir -e .

# Run identity-worker
CMD ["python", "-m", "identity_worker.main"]

