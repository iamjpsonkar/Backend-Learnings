-- MySQL initialization script

USE labdb;

-- Sample tables
CREATE TABLE IF NOT EXISTS products (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    sku         VARCHAR(100) UNIQUE,
    price       DECIMAL(10,2),
    category    VARCHAR(100),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255) UNIQUE NOT NULL,
    phone       VARCHAR(20),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    total       DECIMAL(10,2),
    status      ENUM('pending','processing','shipped','delivered','cancelled') DEFAULT 'pending',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Sample data
INSERT IGNORE INTO products (name, sku, price, category) VALUES
    ('Widget Pro', 'WGT-001', 19.99, 'widgets'),
    ('Gadget Plus', 'GDG-001', 39.99, 'gadgets'),
    ('Super Tool', 'TL-001', 9.99, 'tools');

INSERT IGNORE INTO customers (name, email, phone) VALUES
    ('Alice Smith', 'alice@example.local', '+1-555-0001'),
    ('Bob Jones', 'bob@example.local', '+1-555-0002');

-- Indexes for practice
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
