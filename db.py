import psycopg2
from pathlib import Path
import os

SEARCH_INTERVAL = 900  # seconds, i.e. 15 minutes


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
        SELECT id, origin, destination, outbound_date, inbound_date, last_run_at
        FROM searches
        WHERE origin = %s
          AND destination = %s
          AND outbound_date = %s
          AND inbound_date IS NOT DISTINCT FROM %s
        """,
        (origin, destination, outbound_date, inbound_date),
    )
    pass

def create_search(origin, destination, outbound_date, inbound_date):
    # INSERT INTO searches ...
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO searches (origin, destination, outbound_date, inbound_date)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (origin, destination, outbound_date, inbound_date),
    )
    search_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return search_id

def create_subscription(user_id, search_id):
    # INSERT INTO subscriptions ...
    conn =  get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   INSERT INTO subscriptions (user_id, search_id, created_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (user_id, search_id) DO NOTHING
                   """)
    pass

def get_search_by_id(search_id):
    conn =  get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT origin, destination, outbound_date, inbound_date
                   FROM searches
                   WHERE id = %s
                   """, (search_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not row:
        return None

    return {
        "id": row[0],
        "origin": row[1],
        "destination": row[2],
        "outbound_date": row[3],
        "inbound_date": row[4],
        "last_run_at": row[5],
    }

def get_searches_due():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.exectue("""
                   SELECT id, origin, destination, outbound_date, inbound_date
                   FROM searches
                   WHERE last_checked IS NULL
                   OR last_checked <= NOW() - (%s * INTERVAL '1 second')
                   """, (SEARCH_INTERVAL,))
    
    rows = cursor.fetchall()
    
    cursor.close()
    conn.close()

    searches = []
    for row in rows:
        searches.append({
            "id": row[0],
            "origin": row[1],
            "destination": row[2],
            "outbound_date": row[3],
            "inbound_date": row[4],
            "last_run_at": row[5],
        })

    return searches

def get_subscribed_users(search_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT u.id, u.phone_number, u.is_paying
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

    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "phone_number": row[1],
            "is_paying": row[2]
        })

    return users

def get_user_by_phone_number(phone_number):
    onn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
                   SELECT id
                   FROM users
                   WHERE phone_number=%s
                   """, phone_number)
    
    row = cursor.fetchone()
    
    cursor.close()
    conn.close()
    if not row:
        return None
    
    return row

def update_last_run(search_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
                   UPDATE searches
                   SET last_checked = NOW()
                   WHERE id = %s
                   """, (search_id))
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