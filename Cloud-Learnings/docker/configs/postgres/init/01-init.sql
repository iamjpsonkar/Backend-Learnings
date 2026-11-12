-- PostgreSQL initialization script
-- Runs automatically on first container start

-- Create additional schemas
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS audit;

-- Sample tables for practice
CREATE TABLE IF NOT EXISTS app.users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(100) UNIQUE NOT NULL,
    email       VARCHAR(255) UNIQUE NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.orders (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES app.users(id),
    amount      NUMERIC(10,2) NOT NULL,
    status      VARCHAR(50) DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.items (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    price       NUMERIC(10,2),
    stock       INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit.log (
    id          SERIAL PRIMARY KEY,
    table_name  VARCHAR(100),
    action      VARCHAR(10),
    record_id   INTEGER,
    changed_at  TIMESTAMP DEFAULT NOW()
);

-- Sample data
INSERT INTO app.users (username, email) VALUES
    ('alice', 'alice@example.local'),
    ('bob',   'bob@example.local'),
    ('carol', 'carol@example.local')
ON CONFLICT DO NOTHING;

INSERT INTO app.items (name, description, price, stock) VALUES
    ('Widget A', 'A sample widget', 9.99, 100),
    ('Widget B', 'Another widget', 14.99, 50),
    ('Gadget X', 'A useful gadget', 29.99, 25)
ON CONFLICT DO NOTHING;

-- Create a read-only user for practice
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'readonly') THEN
        CREATE USER readonly WITH PASSWORD 'readonly123';
        GRANT CONNECT ON DATABASE labdb TO readonly;
        GRANT USAGE ON SCHEMA app TO readonly;
        GRANT SELECT ON ALL TABLES IN SCHEMA app TO readonly;
    END IF;
END$$;

-- Index examples
CREATE INDEX IF NOT EXISTS idx_users_email ON app.users(email);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON app.orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON app.orders(status);

COMMENT ON TABLE app.users IS 'User accounts for lab practice';
COMMENT ON TABLE app.orders IS 'Sample orders table for SQL practice';
COMMENT ON TABLE app.items IS 'Catalog items for practice';
