import pymysql
import os

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'restaurant_db')

def promote_to_admin():
    email = input("Enter the email address of the user you want to make an admin: ").strip()
    
    if not email:
        print("Email cannot be empty.")
        return

    try:
        conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        with conn.cursor() as cursor:
            # First, check if user exists
            cursor.execute("SELECT * FROM Users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if not user:
                print(f"Error: User with email '{email}' does not exist in the database.")
                return
                
            # Update user role
            cursor.execute("UPDATE Users SET role = 'admin' WHERE email = %s", (email,))
            conn.commit()
            print(f"\n✅ SUCCESS: '{email}' has been promoted to Admin!")
            print("You can now log in with this account to access the Admin Dashboard.\n")

    except Exception as e:
        print(f"Database Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    promote_to_admin()
