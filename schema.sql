-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE,
    email TEXT UNIQUE,
    is_paying BOOLEAN DEFAULT FALSE,
    subscription_expires DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    CHECK (email IS NOT NULL OR phone_number IS NOT NULL)
);

-- Searches table
CREATE TABLE IF NOT EXISTS searches (
    id SERIAL PRIMARY KEY,
    UNIQUE(origin, destination, outbound_date, inbound_date),
    origin INTEGER NOT NULL,
    destination INTEGER NOT NULL,
    outbound_date DATE NOT NULL,
    inbound_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP DEFAULT NULL,
    last_results CHAR(64) DEFAULT NULL
);

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER NOT NULL,
    search_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, search_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE,
    UNIQUE(user_id, search_id)
);