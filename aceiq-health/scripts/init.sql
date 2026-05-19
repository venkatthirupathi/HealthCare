-- Enable required PostgreSQL extensions.
-- This script runs automatically on container first start via docker-entrypoint-initdb.d.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
