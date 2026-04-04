import psycopg2
from pathlib import Path

# PostgreSQL connection parameters
DB_PARAMS = {
    "host": "your-db-hostname",
    "port": 5432,
    "dbname": "your_db_name",
    "user": "your_db_user",
    "password": "your_db_password"
}

SCHEMA_FILE = "schema.sql"

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

# Example usage
if __name__ == "__main__":
    conn = init_postgres_db()
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    print("Tables in DB:", [row[0] for row in cursor.fetchall()])
    conn.close()