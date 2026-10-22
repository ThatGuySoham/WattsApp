-- WattsApp schema (PostgreSQL). Idempotent: safe to run repeatedly.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS households (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    state       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS appliances (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id        UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    appliance_name      TEXT NOT NULL,
    category            TEXT NOT NULL,
    power_rating_watts  INTEGER NOT NULL CHECK (power_rating_watts > 0),
    age_years           INTEGER NOT NULL DEFAULT 0 CHECK (age_years >= 0),
    is_smart            BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_appliances_household ON appliances(household_id);

CREATE TABLE IF NOT EXISTS daily_usage_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appliance_id        UUID NOT NULL REFERENCES appliances(id) ON DELETE CASCADE,
    date                DATE NOT NULL,
    hours_used          DOUBLE PRECISION NOT NULL CHECK (hours_used >= 0 AND hours_used <= 24),
    energy_consumed_wh  DOUBLE PRECISION NOT NULL CHECK (energy_consumed_wh >= 0)
);
CREATE INDEX IF NOT EXISTS idx_usage_appliance_date ON daily_usage_logs(appliance_id, date);

CREATE TABLE IF NOT EXISTS regression_models (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id        UUID NOT NULL UNIQUE REFERENCES households(id) ON DELETE CASCADE,
    coefficient_hours   DOUBLE PRECISION NOT NULL,
    coefficient_age     DOUBLE PRECISION NOT NULL,
    coefficient_watts   DOUBLE PRECISION NOT NULL,
    intercept           DOUBLE PRECISION NOT NULL,
    r_squared           DOUBLE PRECISION NOT NULL,
    last_trained        TIMESTAMPTZ NOT NULL DEFAULT now()
);
