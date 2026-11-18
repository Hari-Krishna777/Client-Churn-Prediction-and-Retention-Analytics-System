# ── Stage 1: install Python dependencies ─────────────────────────────────────
FROM python:3.13-slim AS deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /deps

# Build context is the project root; requirements.txt lives under backend/
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

# psycopg2-binary bundles libpq; no extra system packages needed.

WORKDIR /app/backend

# Copy installed site-packages from the build stage
COPY --from=deps /usr/local/lib/python3.13/site-packages \
                 /usr/local/lib/python3.13/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Backend application source (alembic/, app/, requirements.txt, alembic.ini …)
# The build context is the project root (see docker-compose.yml), so we copy
# the backend/ subdirectory into WORKDIR and the models/ directory to /app/models.
COPY backend/ .
COPY models/ /app/models/

# Create the batch-jobs storage directory (also mounted as a named volume)
RUN mkdir -p storage/batch_jobs

EXPOSE 8000

# Apply reviewed Alembic migrations, then start Uvicorn.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
