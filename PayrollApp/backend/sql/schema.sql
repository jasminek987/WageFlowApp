-- backend/sql/schema.sql

CREATE TABLE IF NOT EXISTS employees (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT NOT NULL UNIQUE,
  rate        NUMERIC(10,2) NOT NULL
);

CREATE TYPE role_enum AS ENUM ('manager','employee');
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role_enum') THEN
    CREATE TYPE role_enum AS ENUM ('manager','employee');
  END IF;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS users (
  id             SERIAL PRIMARY KEY,
  username       TEXT NOT NULL UNIQUE,
  password_hash  TEXT NOT NULL,
  role           role_enum NOT NULL,
  employee_id    INTEGER NULL REFERENCES employees(id) ON DELETE SET NULL
);

CREATE TYPE status_enum AS ENUM ('pending','approved');
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_enum') THEN
    CREATE TYPE status_enum AS ENUM ('pending','approved');
  END IF;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS timesheets (
  id          SERIAL PRIMARY KEY,
  employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  week_start  DATE NOT NULL,
  hours       NUMERIC(10,2) NOT NULL,
  status      status_enum NOT NULL
);

CREATE TABLE IF NOT EXISTS payslips (
  id          SERIAL PRIMARY KEY,
  employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  period      TEXT NOT NULL,               -- 'YYYY-MM'
  gross       NUMERIC(12,2) NOT NULL,
  net         NUMERIC(12,2) NOT NULL,
  UNIQUE (employee_id, period)
);
