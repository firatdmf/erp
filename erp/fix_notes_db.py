import psycopg2
import sys

# Database credentials
DB_NAME = "postgres"
DB_USER = "postgres.eyzefiawzpxtwzqymyph"
DB_PASSWORD = "mzH36GKgBrDgr4QF"
DB_HOST = "aws-0-eu-west-1.pooler.supabase.com"
DB_PORT = "6543"

def fix_database():
    print(f"Connecting to {DB_HOST}...")
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Connected. Checking for 'category' column in 'notes_note'...")
        
        # Check if column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='notes_note' AND column_name='category';
        """)
        
        if cur.fetchone():
            print("Column 'category' already exists. No action needed.")
        else:
            print("Column 'category' missing. Adding it...")
            # Add column
            cur.execute("""
                ALTER TABLE notes_note 
                ADD COLUMN category varchar(20) DEFAULT 'work';
            """)
            print("SUCCESS: Column 'category' added to 'notes_note' details.")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    fix_database()
