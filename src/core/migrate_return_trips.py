import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

def migrate():
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()

    try:
        print("🚀 Starting migration: Linked One-Way Searches...")

        # 1. Create search_pairs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_pairs (
                id SERIAL PRIMARY KEY,
                outbound_search_id INTEGER NOT NULL,
                inbound_search_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (outbound_search_id) REFERENCES searches(id) ON DELETE CASCADE,
                FOREIGN KEY (inbound_search_id) REFERENCES searches(id) ON DELETE CASCADE
            );
        """)

        # 2. Find return searches that need splitting
        cursor.execute("SELECT id, origin, destination, outbound_date, inbound_date FROM searches WHERE inbound_date IS NOT NULL")
        return_searches = cursor.fetchall()
        print(f"📊 Found {len(return_searches)} return searches to migrate.")

        for old_id, origin, dest, out_date, in_date in return_searches:
            # Create (or find) the inbound leg: destination -> origin on inbound_date
            # Check if a one-way search already exists for this leg
            cursor.execute("""
                SELECT id FROM searches 
                WHERE origin = %s AND destination = %s AND outbound_date = %s AND inbound_date IS NULL
            """, (dest, origin, in_date))
            existing_inbound = cursor.fetchone()

            if existing_inbound:
                inbound_id = existing_inbound[0]
            else:
                # Create the new inbound leg
                cursor.execute("""
                    INSERT INTO searches (origin, destination, outbound_date)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (dest, origin, in_date))
                inbound_id = cursor.fetchone()[0]

            # Link them in search_pairs
            cursor.execute("""
                INSERT INTO search_pairs (outbound_search_id, inbound_search_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (old_id, inbound_id))

            # Migrate subscriptions: Anyone subscribed to the old return search 
            # must now be subscribed to the new inbound leg as well.
            cursor.execute("""
                INSERT INTO subscriptions (user_id, search_id)
                SELECT user_id, %s FROM subscriptions WHERE search_id = %s
                ON CONFLICT DO NOTHING
            """, (inbound_id, old_id))

        print("✅ Data migration complete. Cleaning up table structure...")

        # 3. Drop the old unique constraint and and add the new one
        # Note: Constraint names can vary, so we'll look for the unique index
        cursor.execute("ALTER TABLE searches DROP CONSTRAINT IF EXISTS searches_origin_destination_outbound_date_inbound_date_key")
        
        # 4. Remove the inbound_date column
        cursor.execute("ALTER TABLE searches DROP COLUMN IF EXISTS inbound_date")

        # 5. Add the new one-way unique constraint
        cursor.execute("ALTER TABLE searches ADD CONSTRAINT searches_one_way_unique UNIQUE (origin, destination, outbound_date)")

        conn.commit()
        print("🎊 Migration successful!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()