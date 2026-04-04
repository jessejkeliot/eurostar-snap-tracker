-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    is_paying BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Searches table
CREATE TABLE IF NOT EXISTS searches (
    id SERIAL PRIMARY KEY,
    origin INTEGER NOT NULL,
    destination INTEGER NOT NULL,
    outbound_date DATE NOT NULL,
    outbound_time TEXT NOT NULL,
    inbound_date DATE,
    inbound_time TEXT,
    last_checked TIMESTAMP
);

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER NOT NULL,
    search_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, search_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE
);