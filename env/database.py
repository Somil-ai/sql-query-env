"""
Creates an in-memory SQLite database with realistic seed data.
Three tables are used across all tasks: customers, orders, products.
A fourth table (user_events) supports the hard retention task.
"""

import sqlite3


SCHEMA_SQL = """
-- Task 1 table
CREATE TABLE customers (
    id          INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    state       TEXT NOT NULL,
    email       TEXT,
    created_at  TEXT NOT NULL
);

-- Task 2 tables
CREATE TABLE products (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price       REAL NOT NULL
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    product_id  INTEGER REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    order_date  TEXT NOT NULL
);

-- Task 3 tables
CREATE TABLE users (
    id          INTEGER PRIMARY KEY,
    signup_date TEXT NOT NULL
);

CREATE TABLE user_events (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    event_date  TEXT NOT NULL,
    event_type  TEXT NOT NULL
);
"""

SEED_SQL = """
-- Customers
INSERT INTO customers VALUES
(1,  'Alice',   'Anderson', 'California', 'alice@example.com',   '2022-01-10'),
(2,  'Bob',     'Baker',    'Texas',      'bob@example.com',     '2022-02-15'),
(3,  'Carol',   'Clark',    'California', 'carol@example.com',   '2022-03-20'),
(4,  'David',   'Davis',    'New York',   'david@example.com',   '2022-04-25'),
(5,  'Eve',     'Evans',    'California', 'eve@example.com',     '2022-05-30'),
(6,  'Frank',   'Foster',   'California', 'frank@example.com',   '2022-06-05'),
(7,  'Grace',   'Green',    'Florida',    'grace@example.com',   '2022-07-10'),
(8,  'Henry',   'Hall',     'California', 'henry@example.com',   '2022-08-15'),
(9,  'Iris',    'Hill',     'Texas',      'iris@example.com',    '2022-09-20'),
(10, 'Jack',    'Jones',    'California', 'jack@example.com',    '2022-10-25');

-- Products
INSERT INTO products VALUES
(1,  'Laptop Pro',     'Electronics', 1200.00),
(2,  'Wireless Mouse', 'Electronics',   35.00),
(3,  'Desk Chair',     'Furniture',    450.00),
(4,  'Standing Desk',  'Furniture',    800.00),
(5,  'Notebook Pack',  'Stationery',    15.00),
(6,  'Pen Set',        'Stationery',    12.00),
(7,  'Monitor 4K',     'Electronics',  650.00),
(8,  'Bookshelf',      'Furniture',    320.00),
(9,  'Sticky Notes',   'Stationery',     8.00),
(10, 'Webcam HD',      'Electronics',   95.00);

-- Orders (2023 data for task 2)
INSERT INTO orders VALUES
(1,  1,  5,  '2023-01-15'),
(2,  2,  20, '2023-01-20'),
(3,  3,  8,  '2023-02-10'),
(4,  4,  3,  '2023-02-28'),
(5,  5,  50, '2023-03-05'),
(6,  6,  40, '2023-03-12'),
(7,  7,  10, '2023-04-01'),
(8,  8,  4,  '2023-04-15'),
(9,  9,  100,'2023-05-01'),
(10, 10, 15, '2023-05-20'),
(11, 1,  2,  '2023-06-01'),
(12, 7,  6,  '2023-07-10'),
(13, 3,  5,  '2023-08-20'),
(14, 4,  2,  '2023-09-15'),
(15, 10, 8,  '2023-10-10'),
(16, 2,  30, '2023-11-01'),
(17, 5,  25, '2023-11-20'),
(18, 6,  20, '2023-12-05'),
(19, 7,  4,  '2023-12-15'),
(20, 8,  6,  '2023-12-28');

-- Users (signed up in 2024-01)
INSERT INTO users VALUES
(1, '2024-01-01'),
(2, '2024-01-01'),
(3, '2024-01-01'),
(4, '2024-01-08'),
(5, '2024-01-08'),
(6, '2024-01-08'),
(7, '2024-01-15'),
(8, '2024-01-15');

-- User events (login events in Jan-Feb 2024)
INSERT INTO user_events VALUES
(1,  1, '2024-01-01', 'login'),
(2,  2, '2024-01-01', 'login'),
(3,  3, '2024-01-01', 'login'),
(4,  1, '2024-01-05', 'login'),
(5,  2, '2024-01-06', 'login'),
(6,  1, '2024-01-08', 'login'),
(7,  3, '2024-01-09', 'login'),
(8,  4, '2024-01-08', 'login'),
(9,  5, '2024-01-08', 'login'),
(10, 6, '2024-01-08', 'login'),
(11, 4, '2024-01-12', 'login'),
(12, 5, '2024-01-13', 'login'),
(13, 1, '2024-01-15', 'login'),
(14, 2, '2024-01-15', 'login'),
(15, 7, '2024-01-15', 'login'),
(16, 8, '2024-01-15', 'login'),
(17, 7, '2024-01-20', 'login'),
(18, 8, '2024-01-22', 'login'),
(19, 1, '2024-02-01', 'login'),
(20, 4, '2024-02-02', 'login');
"""

SCHEMA_DESCRIPTION = """
Database tables available:

1. customers (id, first_name, last_name, state, email, created_at)
   - Stores customer records with their US state and signup date

2. products (id, name, category, price)
   - Product catalog with categories: Electronics, Furniture, Stationery

3. orders (id, product_id, quantity, order_date)
   - Purchase records linked to products; order_date is YYYY-MM-DD text

4. users (id, signup_date)
   - User accounts with their signup date (YYYY-MM-DD)

5. user_events (id, user_id, event_date, event_type)
   - Activity log; event_type is 'login'; event_date is YYYY-MM-DD
"""


def create_connection() -> sqlite3.Connection:
    """Create and seed a fresh in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SEED_SQL)
    conn.commit()
    return conn