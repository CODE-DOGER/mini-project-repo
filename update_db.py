import pymysql
import os

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'restaurant_db')

try:
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    with conn.cursor() as cursor:
        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;")
            print("Added is_verified to Users")
        except Exception as e:
            print(f"Skipped is_verified (might exist): {e}")

        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN verification_token VARCHAR(255);")
            print("Added verification_token to Users")
        except Exception as e:
            print(f"Skipped verification_token (might exist): {e}")

        try:
            cursor.execute("ALTER TABLE Reservations ADD COLUMN pending_expires_at DATETIME;")
            print("Added pending_expires_at to Reservations")
        except Exception as e:
            print(f"Skipped pending_expires_at (might exist): {e}")
            
    conn.commit()
    print("Database altered successfully")
except Exception as e:
    print("Error connecting to database:", e)
finally:
    if 'conn' in locals():
        conn.close()
