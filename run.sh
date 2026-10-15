
#!/usr/bin/env bash

set -e

# Always run from the project root
cd "$(dirname "$0")"

echo "===================================="
echo " Starting Property Finder Django"
echo "===================================="

# Step 1: Check required files
if [ ! -f "manage.py" ]; then
    echo "ERROR: manage.py not found."
    exit 1
fi

if [ ! -f "pyproject.toml" ]; then
    echo "ERROR: pyproject.toml not found."
    exit 1
fi

if [ ! -f "compose.yaml" ] && \
   [ ! -f "docker-compose.yml" ] && \
   [ ! -f "docker-compose.yaml" ]; then
    echo "ERROR: Docker Compose file not found."
    exit 1
fi

# Step 2: Check uv
if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is not installed."
    echo "Install uv first: https://docs.astral.sh/uv/"
    exit 1
fi

# Step 3: Create/sync the Python environment
echo "Installing project dependencies with uv..."
uv sync --locked

# Step 4: Start PostgreSQL/PostGIS
echo "Starting database container..."
docker compose up -d

# Step 5: Wait for database readiness
# Assumes the Compose service is named 'db'
echo "Waiting for PostgreSQL..."

DB_READY=false

for attempt in $(seq 1 30); do
    if docker compose exec -T db pg_isready >/dev/null 2>&1; then
        DB_READY=true
        break
    fi

    echo "Database not ready yet ($attempt/30)..."
    sleep 2
done

if [ "$DB_READY" != true ]; then
    echo "ERROR: Database did not become ready."
    echo "Check the database service name in compose.yaml."
    docker compose ps
    docker compose logs
    exit 1
fi

# Step 6: Check Django configuration
echo "Checking Django configuration..."
uv run --locked python manage.py check

# Step 7: Apply migrations
echo "Applying database migrations..."
uv run --locked python manage.py migrate --noinput

# Step 8: Start Django server
echo "Starting Django server..."
echo "Website: http://127.0.0.1:8000/"
echo "Admin:   http://127.0.0.1:8000/admin/"
echo "Press Ctrl+C to stop the server."

exec uv run --locked python manage.py runserver 0.0.0.0:8000