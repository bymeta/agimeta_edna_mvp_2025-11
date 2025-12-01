#!/bin/bash
# Setup script for creating .env files from examples

set -e

echo "Setting up Enterprise DNA configuration files..."

# Create main .env file
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo "  Please review and update POSTGRES_PASSWORD for production use!"
else
    echo "⚠ .env file already exists, skipping..."
fi

# Create cockpit .env.local file
if [ ! -f apps/cockpit/.env.local ]; then
    echo "Creating apps/cockpit/.env.local from example..."
    if [ -f apps/cockpit/.env.local.example ]; then
        cp apps/cockpit/.env.local.example apps/cockpit/.env.local
        echo "✓ Created apps/cockpit/.env.local file"
    else
        echo "NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:8000" > apps/cockpit/.env.local
        echo "✓ Created apps/cockpit/.env.local file"
    fi
else
    echo "⚠ apps/cockpit/.env.local already exists, skipping..."
fi

echo ""
echo "Setup complete! Configuration files created:"
echo "  - .env (main configuration)"
echo "  - apps/cockpit/.env.local (cockpit web UI)"
echo ""
echo "Next steps:"
echo "  1. Review .env and update POSTGRES_PASSWORD if needed"
echo "  2. Run 'make up' to start services"
echo "  3. Run 'make migrate' to initialize database"
echo "  4. Run 'make seed' to add demo data (optional)"

