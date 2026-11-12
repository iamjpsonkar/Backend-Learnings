-- configs/postgres/init/01-init.sql
-- Run automatically on first startup by the PostgreSQL Docker image

-- Create additional databases for labs
CREATE DATABASE lab_ecommerce;
CREATE DATABASE lab_analytics;

-- Grant labuser access to everything
GRANT ALL PRIVILEGES ON DATABASE labdb TO labuser;
GRANT ALL PRIVILEGES ON DATABASE lab_ecommerce TO labuser;
GRANT ALL PRIVILEGES ON DATABASE lab_analytics TO labuser;

-- Switch to labdb and create some sample tables for labs
\c labdb

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10,2),
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    total DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed some data for database labs
INSERT INTO products (name, price, category) VALUES
    ('Widget A', 9.99, 'widgets'),
    ('Widget B', 14.99, 'widgets'),
    ('Gadget X', 49.99, 'gadgets'),
    ('Gadget Y', 79.99, 'gadgets'),
    ('Service Z', 199.99, 'services');

INSERT INTO orders (product_id, quantity, total, status) VALUES
    (1, 5, 49.95, 'completed'),
    (2, 3, 44.97, 'completed'),
    (3, 1, 49.99, 'pending'),
    (4, 2, 159.98, 'processing'),
    (1, 10, 99.90, 'completed');
