-- ============================================================
-- QUANT PLATFORM — POSTGRES INIT
-- Runs once on first container boot.
-- Creates extensions; schema is owned by Alembic migrations.
-- ============================================================

-- TimescaleDB: hypertables for OHLCV, features, signals, snapshots
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Trigram + btree_gin for fast ticker/symbol search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Case-insensitive text (for emails, usernames)
CREATE EXTENSION IF NOT EXISTS citext;

-- Stats + monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Schemas
CREATE SCHEMA IF NOT EXISTS market;    -- OHLCV, corporate actions, universe
CREATE SCHEMA IF NOT EXISTS feature;   -- engineered features (hypertable)
CREATE SCHEMA IF NOT EXISTS model;     -- model registry metadata
CREATE SCHEMA IF NOT EXISTS signal;    -- signals + explanations (hypertable)
CREATE SCHEMA IF NOT EXISTS portfolio; -- positions, trades, snapshots
CREATE SCHEMA IF NOT EXISTS auth;      -- users, sessions, api keys
CREATE SCHEMA IF NOT EXISTS news;      -- news + sentiment cache
CREATE SCHEMA IF NOT EXISTS macro;     -- FRED series (hypertable)

-- Sensible defaults
ALTER DATABASE quant SET timezone TO 'UTC';
ALTER DATABASE quant SET statement_timeout = '60s';
ALTER DATABASE quant SET lock_timeout = '10s';
ALTER DATABASE quant SET idle_in_transaction_session_timeout = '5min';

-- Sanity check
DO $$ BEGIN
  RAISE NOTICE 'Quant platform DB initialized: timescaledb=%, schemas created',
    (SELECT extversion FROM pg_extension WHERE extname='timescaledb');
END $$;
