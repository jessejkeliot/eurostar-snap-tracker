# lambda_cleanup_postgres.py
import os
import psycopg2
from datetime import date

# --- PostgreSQL connection parameters ---
# These can be set as Lambda environment variables
DB_PARAMS = {
    "host": os.environ.get("DB_HOST"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD")
}

def get_pg_connection():
    """
    Returns a psycopg2 connection to PostgreSQL
    """
    return psycopg2.connect(**DB_PARAMS)

def cleanup_old_subscriptions():
    """
    Deletes subscriptions linked to searches with outbound_date < today
    """
    conn = get_pg_connection()
    cursor = conn.cursor()
    today_str = date.today().isoformat()  # YYYY-MM-DD

    # Delete subscriptions where the search is in the past
    cursor.execute("""
        DELETE FROM subscriptions
        WHERE search_id IN (
            SELECT id FROM searches
            WHERE outbound_date < %s
        )
        RETURNING user_id, search_id;
    """, (today_str,))

    deleted_rows = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()

    return deleted_rows

# AWS Lambda handler
def lambda_handler(event, context):
    deleted = cleanup_old_subscriptions()
    print(f"Cleanup complete. Deleted {len(deleted)} subscriptions.")
    return {
        "deleted_count": len(deleted),
        "deleted_rows": deleted  # Optional, for debugging/logging
    }

# For local testing
if __name__ == "__main__":
    deleted = cleanup_old_subscriptions()
    print(f"Deleted {len(deleted)} subscriptions:", deleted)