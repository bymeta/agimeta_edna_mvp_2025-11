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

# Copy identity service
WORKDIR /app
COPY apps/identity /app/apps/identity
WORKDIR /app/apps/identity

# Install dependencies
RUN pip install --no-cache-dir -e .

# Run identity service
CMD ["python", "-m", "identity.main"]

