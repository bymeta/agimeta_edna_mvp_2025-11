<<<<<<< HEAD
# Enterprise DNA

A monorepo platform for managing golden business objects, events, and identity matching rules.

## Architecture

The platform consists of:

- **api-gateway**: REST API gateway with endpoints for objects, events, and identity rules
- **scanner**: PostgreSQL schema introspection and profiling service (runs as a job)
- **identity**: Rule-based deterministic matching service that computes golden object IDs
- **semantic**: Simple glossary CRUD service
- **identity-worker**: Worker service for processing customer data and creating golden objects
- **cockpit**: Next.js web interface for managing objects and viewing scanner status
- **edna-common**: Shared package with Pydantic models and utilities

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Make (optional, for convenience commands)
- Node.js 18+ (for Cockpit web UI)

### Initial Setup

```bash
# Create configuration files from examples
make setup-env
# or manually:
# cp .env.example .env
# cp apps/cockpit/.env.local.example apps/cockpit/.env.local

# Review and update .env file if needed (especially POSTGRES_PASSWORD for production)
```

### Start Services

```bash
# Start all services
make up
# or
docker compose up -d
```

This will start:
- PostgreSQL database on port 5433
- API Gateway on port 8000
- Semantic service on port 8002
- Scanner and Identity services (as needed)

### Start Cockpit (Web UI)

The cockpit is a Next.js application that provides a web interface:

```bash
cd apps/cockpit
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Stop Services

```bash
make down
# or
docker compose down
```

### Run Migrations

Migrations are automatically run when the API Gateway starts. You can also run them manually:

```bash
make migrate
# or
python3 scripts/run_migrations.py
```

### Seed Demo Data

Seed the database with demo data (10 customers, 25 events):

```bash
make seed
# or
python3 scripts/seed_demo_data.py
```

## API Endpoints

### API Gateway (http://localhost:8000)

#### Health Check
```bash
curl http://localhost:8000/healthz
```

#### Objects

List objects with pagination, filtering, and sorting:
```bash
# Basic listing
curl "http://localhost:8000/objects?limit=10&offset=0"

# Filter by source_system and object_type
curl "http://localhost:8000/objects?source_system=crm&object_type=customer&limit=10"

# Sort by created_at (ascending)
curl "http://localhost:8000/objects?sort_by=created_at&sort_order=asc&limit=10"

# Sort by updated_at (descending)
curl "http://localhost:8000/objects?sort_by=updated_at&sort_order=desc&limit=10"

# Invalid parameters return 400
curl "http://localhost:8000/objects?limit=2000"  # Returns 400 (limit > 1000)
curl "http://localhost:8000/objects?sort_by=invalid_field"  # Returns 400
curl "http://localhost:8000/objects?sort_order=invalid"  # Returns 400
```

Get specific object:
```bash
curl http://localhost:8000/objects/{golden_id}
```

Create/update object:
```bash
curl -X POST http://localhost:8000/objects \
  -H "Content-Type: application/json" \
  -d '{
    "source_system": "crm",
    "source_id": "12345",
    "object_type": "customer",
    "attributes": {
      "name": "Acme Corp",
      "email": "contact@acme.com"
    }
  }'
```

#### Events

List events with pagination, filtering, and sorting:
```bash
# Basic listing
curl "http://localhost:8000/events?limit=10&offset=0"

# Filter by golden_id, event_type, and source_system
curl "http://localhost:8000/events?golden_id=abc123&event_type=object.created&source_system=crm&limit=10"

# Sort by occurred_at (ascending)
curl "http://localhost:8000/events?sort_by=occurred_at&sort_order=asc&limit=10"

# Sort by occurred_at (descending) - default
curl "http://localhost:8000/events?sort_by=occurred_at&sort_order=desc&limit=10"

# Invalid parameters return 400
curl "http://localhost:8000/events?limit=2000"  # Returns 400 (limit > 1000)
curl "http://localhost:8000/events?sort_by=invalid_field"  # Returns 400
curl "http://localhost:8000/events?sort_order=invalid"  # Returns 400
```

Create event:
```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "object.created",
    "golden_id": "abc123",
    "source_system": "crm",
    "payload": {
      "action": "create",
      "object_id": "12345"
    }
  }'
```

#### Identity Rules

List rules:
```bash
curl "http://localhost:8000/identity/rules?object_type=customer&active_only=true"
```

Create/update rule:
```bash
curl -X POST http://localhost:8000/identity/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "rule-001",
    "rule_name": "Customer Email Match",
    "object_type": "customer",
    "source_system": "crm",
    "key_fields": ["email", "phone"],
    "normalization_rules": {
      "email": "lowercase",
      "phone": "digits_only"
    },
    "active": true
  }'
```

### Semantic Service (http://localhost:8002)

#### Glossary (legacy)

List glossary terms:
```bash
curl http://localhost:8002/glossary
```

Create glossary term:
```bash
curl -X POST http://localhost:8002/glossary \
  -H "Content-Type: application/json" \
  -d '{
    "term": "golden_record",
    "definition": "A canonical representation of a business entity",
    "category": "data_quality",
    "metadata": {}
  }'
```

#### Terms CRUD

List terms (with optional filtering and pagination):
```bash
# List all terms
curl "http://localhost:8002/terms?limit=10&offset=0"

# Filter by object_type
curl "http://localhost:8002/terms?object_type=customer&limit=10"

# Filter by category
curl "http://localhost:8002/terms?category=business_metric&limit=10"
```

Get specific term:
```bash
curl http://localhost:8002/terms/term-customer-001
```

Create term (with optional object_type link):
```bash
curl -X POST http://localhost:8002/terms \
  -H "Content-Type: application/json" \
  -d '{
    "term_id": "term-customer-001",
    "term_name": "Customer Lifetime Value",
    "definition": "The total revenue a business can expect from a customer relationship",
    "object_type": "customer",
    "category": "business_metric",
    "metadata": {"source": "internal", "version": "1.0"}
  }'
```

Update term:
```bash
curl -X PUT http://localhost:8002/terms/term-customer-001 \
  -H "Content-Type: application/json" \
  -d '{
    "definition": "Updated definition",
    "object_type": "customer"
  }'
```

Delete term:
```bash
curl -X DELETE http://localhost:8002/terms/term-customer-001
```

#### KPIs CRUD

List KPIs (with optional filtering and pagination):
```bash
# List all KPIs
curl "http://localhost:8002/kpis?limit=10&offset=0"

# Filter by object_type
curl "http://localhost:8002/kpis?object_type=customer&limit=10"

# Filter by metric_type
curl "http://localhost:8002/kpis?metric_type=count&limit=10"
```

Get specific KPI:
```bash
curl http://localhost:8002/kpis/kpi-customer-001
```

Create KPI (with optional object_type link):
```bash
curl -X POST http://localhost:8002/kpis \
  -H "Content-Type: application/json" \
  -d '{
    "kpi_id": "kpi-customer-001",
    "kpi_name": "Active Customers",
    "definition": "Number of customers with active status",
    "metric_type": "count",
    "unit": "customers",
    "object_type": "customer",
    "calculation_formula": "COUNT(*) WHERE status = '\''active'\''",
    "metadata": {"threshold": 1000, "target": 5000}
  }'
```

Update KPI:
```bash
curl -X PUT http://localhost:8002/kpis/kpi-customer-001 \
  -H "Content-Type: application/json" \
  -d '{
    "definition": "Updated definition",
    "target": 10000
  }'
```

Delete KPI:
```bash
curl -X DELETE http://localhost:8002/kpis/kpi-customer-001
```

## Development

### Code Formatting

```bash
make fmt
# Formats code with Black and fixes issues with Ruff
```

### Linting

```bash
make lint
# Checks code style without making changes
```

### Testing

```bash
make test
# Runs pytest tests
```

### Running Scanner

The scanner service can be run as a job to profile PostgreSQL tables:

```bash
docker compose run --rm scanner
```

The scanner will:
1. Profile all tables in the database
2. Guess object types from table names
3. Write candidates to `edna_object_candidates` staging table
4. Create demo objects in `edna_objects` with `source_id` format `temp:<schema>.<table>`

### Running Identity Worker

The identity worker processes customer data from source tables and creates golden objects:

```bash
# Run in production mode
make worker
# or
docker compose run --rm identity-worker python -m identity_worker.main

# Run in dry-run mode (no database writes)
make worker-dry-run
# or
docker compose run --rm identity-worker python -m identity_worker.main --dry-run
```

The identity worker will:
1. Read identity rules from `edna_identity_rules` for `object_type='customer'`
2. Ensure `demo_customers` source table exists (creates if missing)
3. Query source data from the demo table
4. Compute golden IDs using key fields and normalization rules
5. Upsert objects into `edna_objects` with attributes and source information
6. Support dry-run mode for testing without writing to database

## Database Schema

The platform uses PostgreSQL with the following main tables:

- `edna_objects`: Golden business objects
- `edna_events`: System events
- `edna_identity_rules`: Matching rules for identity resolution
- `edna_glossary`: Semantic glossary terms (legacy)
- `edna_terms`: Terms with optional object_type links
- `edna_kpis`: KPIs with optional object_type links and calculation formulas
- `edna_object_candidates`: Staging table for scanner-discovered object candidates
- `edna_migrations`: Migration tracking table
- `demo_customers`: Demo source table for customer data (created by identity worker if missing)

See `infra/migrations/` for the full schema migrations.

## Configuration

Configuration is managed via environment variables. Run `make setup-env` to create `.env` files from examples.

### Main Configuration (`.env`)

**Database Credentials:**
- `POSTGRES_USER`: Database username (default: `edna`)
- `POSTGRES_PASSWORD`: Database password (default: `edna` - **CHANGE IN PRODUCTION!**)
- `POSTGRES_DB`: Database name (default: `edna`)
- `POSTGRES_HOST`: Database host (default: `localhost` for local, `postgres` for Docker)
- `POSTGRES_PORT`: Database port (default: `5433`)
- `DATABASE_URL`: Full connection string (optional, overrides individual vars)

**Service Ports:**
- `API_GATEWAY_PORT`: API Gateway port (default: `8000`)
- `SEMANTIC_PORT`: Semantic service port (default: `8002`)

**Logging:**
- `LOG_LEVEL`: Logging level - `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)
- `LOG_FORMAT`: Log format - `json` or `text` (default: `json`)

### Cockpit Configuration (`apps/cockpit/.env.local`)

- `NEXT_PUBLIC_API_GATEWAY_URL`: API Gateway URL for the web UI (default: `http://localhost:8000`)

**Note:** The `NEXT_PUBLIC_` prefix is required for Next.js client-side access.

## Identity Matching

The identity service computes deterministic golden object IDs by:

1. Loading active matching rules for the object type and source system
2. Extracting key fields from the source data
3. Normalizing values according to normalization rules
4. Concatenating normalized keys and computing SHA1 hash

Example normalization rules:
- `lowercase`: Convert to lowercase
- `uppercase`: Convert to uppercase
- `digits_only`: Extract only digits
- `alphanumeric_only`: Extract only alphanumeric characters
- `trim`: Remove leading/trailing whitespace

## Project Structure

```
enterprise-dna/
├── apps/
│   ├── api-gateway/     # REST API gateway
│   ├── scanner/         # Schema introspection service
│   ├── identity/        # Identity matching service
│   └── semantic/        # Glossary service
├── packages/
│   └── edna-common/     # Shared models and utilities
├── migrations/           # Database migrations
├── tests/               # Test suite
├── docker-compose.yml   # Service orchestration
├── Makefile            # Convenience commands
└── README.md           # This file
```

## License

Internal use only.
