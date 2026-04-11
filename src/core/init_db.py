import os
import psycopg2
from dotenv import load_dotenv

# Load .env
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# Connect as superuser (default postgres DB)
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="postgres",
    host=DB_HOST,
    port=DB_PORT
)
conn.autocommit = True
cur = conn.cursor()

# Create user if not exists
cur.execute(f"""
DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = '{DB_USER}'
   ) THEN
      CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}';
   END IF;
END
$$;
""")

# Create database if not exists
cur.execute(f"""
SELECT 1 FROM pg_database WHERE datname = %s
""", (DB_NAME,))
exists = cur.fetchone()

if not exists:
    cur.execute(f"CREATE DATABASE {DB_NAME}")

# Grant privileges
cur.execute(f"ALTER DATABASE {DB_NAME} OWNER TO {DB_USER}")
cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}")

cur.close()
conn.close()

print("Database initialized ✅")