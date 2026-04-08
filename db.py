import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import os
from models import User, Search, Subscription
from hashlib import sha256
SEARCH_INTERVAL = 900  # seconds, i.e. 15 minutes

load_dotenv()

DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

SCHEMA_FILE = "schema.sql"

def get_connection():
    return psycopg2.connect(**DB_PARAMS)

def init_postgres_db(db_params=DB_PARAMS, schema_file=SCHEMA_FILE):
    """
    Connects to PostgreSQL, executes the schema SQL file to create tables.
    Returns a psycopg2 connection object.
    """
    # Connect to PostgreSQL
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()

    # Read schema.sql
    schema_path = Path(schema_file)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    # Split the SQL into statements and execute
    statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
    for stmt in statements:
        cursor.execute(stmt)

    conn.commit()
    print(f"Database initialized with schema from {schema_file}")
    return conn

def get_existing_search(origin, destination, outbound_date, inbound_date):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT id, origin, destination, outbound_date, inbound_date, created_at, last_checked, last_results
        FROM searches
        WHERE origin = %s
          AND destination = %s
          AND outbound_date = %s
          AND inbound_date IS NOT DISTINCT FROM %s
        """,
        (origin, destination, outbound_date, inbound_date),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return Search(*row)
    return None

def create_user_from_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (email)
        VALUES (%s)
        RETURNING id
        """,
        (email,)
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return row[0]

def create_user_from_phone(phone_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (phone_number)
        VALUES (%s)
        RETURNING id
        """,
        (phone_number,)
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return row[0]

def create_search(origin, destination, outbound_date, inbound_date):
    # INSERT INTO searches ...
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO searches (origin, destination, outbound_date, inbound_date)
        VALUES (%s, %s, %s, %s)
        RETURNING id, origin, destination, outbound_date, inbound_date, created_at, last_checked, last_results
        """,
        (origin, destination, outbound_date, inbound_date),
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return Search(*row)

def create_subscription(user_id, search_id):
    # INSERT INTO subscriptions ...
    conn =  get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   INSERT INTO subscriptions (user_id, search_id, created_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (user_id, search_id) DO NOTHING
                   RETURNING user_id, search_id, created_at
                   """, (user_id, search_id))
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    if row:
        return Subscription(*row)
    return None

def get_search_by_id(search_id):
    conn =  get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT id, origin, destination, outbound_date, inbound_date, created_at, last_checked, last_results
                   FROM searches
                   WHERE id = %s
                   """, (search_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not row:
        return None

    return Search(*row)

def get_searches_due():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT id, origin, destination, outbound_date, inbound_date, created_at, last_checked, last_results
                   FROM searches
                   WHERE last_checked IS NULL
                   OR last_checked <= NOW() - (%s * INTERVAL '1 second')
                   """, (SEARCH_INTERVAL,))
    
    rows = cursor.fetchall()
    
    cursor.close()
    conn.close()

    searches = [Search(*row) for row in rows]

    return searches

def get_subscribed_users(search_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT u.id, u.phone_number, u.email, u.is_paying, u.subscription_expires, u.created_at
                   FROM users as u
                   WHERE EXISTS (
                    SELECT 1
                    FROM subscriptions AS s
                    WHERE s.user_id = u.id
                    AND s.search_id = %s)
                   """, (search_id,))
    
    rows = cursor.fetchall()
    
    cursor.close()
    conn.close()

    users = [User(*row) for row in rows]

    return users

def get_user_by_phone_number(phone_number):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
                   SELECT id, phone_number, email, is_paying, subscription_expires, created_at
                   FROM users
                   WHERE phone_number=%s
                   """, (phone_number,))
    
    row = cursor.fetchone()
    
    cursor.close()
    conn.close()
    if not row:
        return None
    
    return User(*row)

def update_last_run(search_id, result_joined):
    conn = get_connection()
    cursor = conn.cursor()
    
    sha256_hash = sha256()
    sha256_hash.update(str(result_joined).encode())
    hd = sha256_hash.hexdigest()
    
    cursor.execute("""
                   UPDATE searches
                   SET last_checked = NOW(), last_result = %s
                   WHERE id = %s
                   """, (hd ,search_id,))
    conn.commit()
    cursor.close()
    conn.close()
    

    



# Example usage
if __name__ == "__main__":
    conn = init_postgres_db()
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    print("Tables in DB:", [row[0] for row in cursor.fetchall()])
    conn.close()
