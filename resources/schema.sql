-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE,
    email TEXT UNIQUE,
    is_paying BOOLEAN DEFAULT FALSE,
    abuse_strikes INTEGER DEFAULT 0,
    subscription_expires DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    CHECK (email IS NOT NULL OR phone_number IS NOT NULL)
);

-- Searches table (all searches are one-way)
CREATE TABLE IF NOT EXISTS searches (
    id SERIAL PRIMARY KEY,
    UNIQUE(origin, destination, outbound_date),
    origin INTEGER NOT NULL,
    destination INTEGER NOT NULL,
    outbound_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP DEFAULT NULL,
    last_results CHAR(64) DEFAULT NULL
);

-- Search pairs table (links two one-way searches that form a return trip)
CREATE TABLE IF NOT EXISTS search_pairs (
    id SERIAL PRIMARY KEY,
    outbound_search_id INTEGER NOT NULL,
    inbound_search_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (outbound_search_id) REFERENCES searches(id) ON DELETE CASCADE,
    FOREIGN KEY (inbound_search_id) REFERENCES searches(id) ON DELETE CASCADE
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

-- Trials table
CREATE TABLE IF NOT EXISTS trials (
    user_id INTEGER PRIMARY KEY,
    alerts_used INTEGER DEFAULT 0,
    alerts_limit INTEGER DEFAULT 3,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);