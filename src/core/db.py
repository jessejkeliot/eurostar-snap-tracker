import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import os
from src.core.models import User, Search, SearchPair, Subscription, Trial
from datetime import datetime
import argparse

from src.bot.myparse import get_station_id
from src.core.utility import hash_for_db

load_dotenv()

DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "../../resources/schema.sql")

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

def get_existing_search(origin, destination, outbound_date):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, origin, destination, outbound_date, created_at, last_checked, last_results
                FROM searches
                WHERE origin = %s
                  AND destination = %s
                  AND outbound_date = %s
                """,
                (origin, destination, outbound_date),
            )
            row = cursor.fetchone()
            if row:
                return Search(*row)
    finally:
        conn.close()
    return None

def create_user_from_email(email):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (email)
                VALUES (%s)
                RETURNING id
                """,
                (email,)
            )
            row = cursor.fetchone()
            cursor.execute("INSERT INTO trials (user_id) VALUES (%s)", (row[0],))
            conn.commit()
            return row[0]
    finally:
        conn.close()

def create_user_from_phone(phone_number):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (phone_number)
                VALUES (%s)
                RETURNING id
                """,
                (phone_number,)
            )
            row = cursor.fetchone()
            cursor.execute("INSERT INTO trials (user_id) VALUES (%s)", (row[0],))
            conn.commit()
            return row[0]
    finally:
        conn.close()

def create_search(origin, destination, outbound_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO searches (origin, destination, outbound_date)
        VALUES (%s, %s, %s)
        RETURNING id, origin, destination, outbound_date, created_at, last_checked, last_results
        """,
        (origin, destination, outbound_date),
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return Search(*row)

def create_subscription(user_id, search_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           INSERT INTO subscriptions (user_id, search_id, created_at)
                           VALUES (%s, %s, NOW())
                           ON CONFLICT (user_id, search_id) DO NOTHING
                           RETURNING user_id, search_id, created_at
                           """, (user_id, search_id))
            row = cursor.fetchone()
            conn.commit()
            return row is not None
    finally:
        conn.close()

def get_search_by_id(search_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT id, origin, destination, outbound_date, created_at, last_checked, last_results
                   FROM searches
                   WHERE id = %s
                   """, (search_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not row:
        return None

    return Search(*row)

def get_searches_due(search_interval: float):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           SELECT id, origin, destination, outbound_date, created_at, last_checked, last_results
                           FROM searches
                           WHERE last_checked IS NULL
                           OR last_checked <= NOW() - (%s * INTERVAL '1 second')
                           """, (search_interval,))
            rows = cursor.fetchall()
            return [Search(*row) for row in rows]
    finally:
        conn.close()

def get_subscribed_users(search_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
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
            return [User(*row) for row in rows]
    finally:
        conn.close()

def get_user_by_phone_number(phone_number):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           SELECT id, phone_number, email, is_paying, subscription_expires, created_at
                           FROM users
                           WHERE phone_number=%s
                           """, (phone_number,))
            row = cursor.fetchone()
            return User(*row) if row else None
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           SELECT id, phone_number, email, is_paying, subscription_expires, created_at
                           FROM users
                           WHERE email=%s
                           """, (email,))
            row = cursor.fetchone()
            return User(*row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           SELECT id, phone_number, email, is_paying, subscription_expires, created_at
                           FROM users
                           WHERE id=%s
                           """, (user_id,))
            row = cursor.fetchone()
            return User(*row) if row else None
    finally:
        conn.close()

def get_abuse_strikes(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT abuse_strikes FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            return row[0] if row else 0
    finally:
        conn.close()

def increment_abuse_strikes(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET abuse_strikes = abuse_strikes + 1 WHERE id = %s", (user_id,))
            conn.commit()
    finally:
        conn.close()

def reset_abuse_strikes(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET abuse_strikes = 0 WHERE id = %s", (user_id,))
            conn.commit()
    finally:
        conn.close()

def set_user_paid(user_id, expires_date=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           UPDATE users
                           SET is_paying = TRUE, subscription_expires = %s
                           WHERE id = %s
                           """, (expires_date, user_id))
            conn.commit()
    finally:
        conn.close()

def delete_all_subscriptions_for_user(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM subscriptions WHERE user_id = %s", (user_id,))
            conn.commit()
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
    finally:
        conn.close()

def delete_search(search_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM searches WHERE id = %s", (search_id,))
            conn.commit()
    finally:
        conn.close()

def delete_orphaned_searches():
    """Deletes all searches that have no associated subscriptions in ONE query."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM searches 
                WHERE id NOT IN (SELECT DISTINCT search_id FROM subscriptions)
                AND created_at < NOW() - INTERVAL '1 minute'
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    finally:
        conn.close()

def delete_expired_searches():
    """Deletes all searches that have an outbound_date in the past."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM searches WHERE outbound_date < CURRENT_DATE")
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    finally:
        conn.close()

def create_search_pair(outbound_search_id, inbound_search_id):
    """Links two one-way searches as a return trip pair."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO search_pairs (outbound_search_id, inbound_search_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id, outbound_search_id, inbound_search_id, created_at
            """, (outbound_search_id, inbound_search_id))
            row = cursor.fetchone()
            conn.commit()
            return SearchPair(*row) if row else None
    finally:
        conn.close()

def get_user_paired_search(user_id, search_id):
    """
    Given a user and a search_id, returns the OTHER leg's Search if:
    1. This search belongs to a search_pair, AND
    2. This specific user is also subscribed to the other leg.
    Returns None if not a paired search for this user.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.origin, s.destination, s.outbound_date, s.created_at, s.last_checked, s.last_results
                FROM searches s
                JOIN subscriptions sub ON sub.search_id = s.id AND sub.user_id = %s
                WHERE s.id IN (
                    SELECT CASE
                        WHEN sp.outbound_search_id = %s THEN sp.inbound_search_id
                        WHEN sp.inbound_search_id = %s THEN sp.outbound_search_id
                    END
                    FROM search_pairs sp
                    WHERE sp.outbound_search_id = %s OR sp.inbound_search_id = %s
                )
            """, (user_id, search_id, search_id, search_id, search_id))
            row = cursor.fetchone()
            return Search(*row) if row else None
    finally:
        conn.close()


def update_last_run(search_id, result_joined):
    # This updates the last_checked time for a search and the last results
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            hd = hash_for_db(result_joined)
            cursor.execute("""
                           UPDATE searches
                           SET last_checked = NOW(), last_results = %s
                           WHERE id = %s
                           """, (hd ,search_id,))
            conn.commit()
    finally:
        conn.close()

def get_user_trial(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           SELECT user_id, alerts_used, alerts_limit, started_at
                           FROM trials
                           WHERE user_id=%s
                           """, (user_id,))
            row = cursor.fetchone()
            return Trial(*row) if row else None
    finally:
        conn.close()

def increment_user_trial(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           UPDATE trials
                           SET alerts_used = alerts_used + 1
                           WHERE user_id = %s
                           RETURNING user_id, alerts_used, alerts_limit, started_at
                           """, (user_id,))
            row = cursor.fetchone()
            conn.commit()
            return Trial(*row) if row else None
    finally:
        conn.close()

def update_last_checked(search_id):
    # this only updates the last checked time
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           UPDATE searches
                           SET last_checked = NOW()
                           WHERE id = %s
                           """, (search_id,))
            conn.commit()
    finally:
        conn.close()

def elevate_user_to_paid(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            UPDATE users
            SET is_paying=TRUE
            WHERE id=%s
            """, (user_id,))
            conn.commit()
    finally:
        conn.close()


# CLI tool
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Eurostar train tracker database")
    
    # Add user arguments
    parser.add_argument("--add-user", action="store_true", help="Add a new user")
    parser.add_argument("--phone", default=None, help="Phone number for the user")
    parser.add_argument("--email", default=None, help="Email for the user")

    parser.add_argument("--elevate-user", action="store_true", help="Elevate a user to paid")
    parser.add_argument("--delete-user", action="store_true", help="Delete a user")
    
    # Add search arguments
    parser.add_argument("--add-search", action="store_true", help="Add a new search")
    parser.add_argument("--origin", type=str, default=None, help="Origin station ID")
    parser.add_argument("--destination", type=str, default=None, help="Destination station ID")
    parser.add_argument("--outbound-date", default=None, help="Outbound date (YYYY-MM-DD)")
    
    # Add subscription arguments
    parser.add_argument("--add-subscription", action="store_true", help="Add a subscription")
    parser.add_argument("--user-id", type=int, default=None, help="User ID")
    parser.add_argument("--search-id", type=int, default=None, help="Search ID")
    
    args = parser.parse_args()
    
    if args.add_user:
        if not args.phone and not args.email:
            print("Error: Must provide at least --phone or --email")
            exit(1)
        if args.phone:
            user_id = create_user_from_phone(args.phone)
        if args.email:
            user_id = create_user_from_email(args.email)
        print(f"Successfully created user {user_id} : {args.email or args.phone}")

    elif args.elevate_user:
        if not args.phone and not args.email:
            print("Error: Must provide at least --phone or --email")
            exit(1)
        if args.phone:
            user = get_user_by_phone_number(args.phone)
            if not user:
                print("Error: User not found")
                exit(1)
            elevate_user_to_paid(user.id)
        if args.email:
            user = get_user_by_email(args.email)
            if not user:
                print("Error: User not found")
                exit(1)
            elevate_user_to_paid(user.id)
        print(f"Successfully elevated user {user.id} : {user.email or user.phone} to paid status")
    elif args.delete_user:
        if not args.phone and not args.email:
            print("Error: Must provide at least --phone or --email")
            exit(1)
        if args.phone:
            user = get_user_by_phone_number(args.phone)
            if not user:
                print("Error: User not found")
                exit(1)
            delete_user(user.id)
        if args.email:
            user = get_user_by_email(args.email)
            if not user:
                print("Error: User not found")
                exit(1)
            delete_user(user.id)
        print(f"Successfully deleted user {user.id} : {user.email or user.phone}")
    elif args.add_search:
        if not args.origin or not args.destination or not args.outbound_date:
            print("Error: Must provide --origin, --destination, and --outbound-date")
            exit(1)
        
        outbound = datetime.strptime(args.outbound_date, "%Y-%m-%d").date()
        origin_id = get_station_id(args.origin)
        destination_id = get_station_id(args.destination)
        if(not origin_id or not destination_id):
            print("Error: At least one of the stations was invalid")
            exit(1)
        search = create_search(origin_id, destination_id, outbound)
        print(f"Successfully created search {search.id} : {args.origin} to {args.destination} on {args.outbound_date}")
    
    elif args.add_subscription:
        if not args.user_id or not args.search_id:
            print("Error: Must provide --user-id and --search-id")
            exit(1)
        
        sub = create_subscription(args.user_id, args.search_id)
        if sub:
            print(f"Successfully created subscription for user {args.user_id} and search {args.search_id}")
        else:
            print(f"Subscription already exists for user {args.user_id} and search {args.search_id}")
    
    else:
        # Default behavior if no command
        conn = init_postgres_db()
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        print("Tables in DB:", [row[0] for row in cursor.fetchall()])
        conn.close()