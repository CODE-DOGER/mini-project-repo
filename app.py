from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pymysql
import pymysql.cursors
import bcrypt
import os
import uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_reservation_key')

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'restaurant_db')

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ====================
# Routes - Frontend Views
# ====================
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin', methods=['GET'])
@admin_required
def admin_dashboard():
    return render_template('admin.html')

@app.route('/history', methods=['GET'])
@login_required
def history():
    return render_template('history.html')

@app.route('/transaction', methods=['GET'])
@login_required
def transaction():
    return render_template('transaction.html')

@app.route('/verify/<token>', methods=['GET'])
def verify_email(token):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM Users WHERE verification_token = %s", (token,))
            user = cursor.fetchone()
            if not user:
                return "Invalid or expired verification token.", 400
                
            cursor.execute("UPDATE Users SET is_verified = TRUE, verification_token = NULL WHERE verification_token = %s", (token,))
        conn.commit()
        return redirect(url_for('login', verified='true'))
    except Exception as e:
        return str(e), 500
    finally:
        conn.close()

# ====================
# API Endpoints
# ====================
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    
    if not all([name, email, phone, password]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if email exists
            cursor.execute("SELECT user_id FROM Users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Email already registered'}), 409
                
            token = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO Users (name, email, phone, password_hash, is_verified, verification_token) VALUES (%s, %s, %s, %s, FALSE, %s)",
                (name, email, phone, hashed_pw, token)
            )
            
            # Simulate sending email
            print(f"\n*** [EMAIL SIMULATION] To: {email}")
            print(f"*** Subject: Verify your Restaurant System account")
            print(f"*** Body: Please click the following link to verify your account:")
            print(f"*** http://localhost:5000/verify/{token}\n")
            
        conn.commit()
        return jsonify({'message': 'Registration successful. Please check your email to verify your account.'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, name, email, password_hash, role, is_verified FROM Users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                if not user['is_verified']:
                    return jsonify({'error': 'Please check your email to verify your account.'}), 403
                    
                session['user_id'] = user['user_id']
                session['name'] = user['name']
                session['role'] = user['role']
                return jsonify({'message': 'Login successful', 'role': user['role']}), 200
            else:
                return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/logout', methods=['POST', 'GET'])
def api_logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/available-tables', methods=['GET'])
def api_available_tables():
    date = request.args.get('date')
    time = request.args.get('time')
    guests = request.args.get('guests')
    location = request.args.get('location') # indoor or outdoor
    
    if not all([date, time, guests]):
        return jsonify({'error': 'Missing date, time, or guests'}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Find tables that can fit the guests and match location, 
            # and are NOT booked on that date and time (status confirmed or pending)
            query = """
                SELECT * FROM Tables t
                WHERE t.capacity >= %s
            """
            params = [int(guests)]
            if location:
                query += " AND t.location = %s"
                params.append(location)
                
            query += """
                AND t.table_id NOT IN (
                    SELECT table_id FROM Reservations 
                    WHERE reservation_date = %s 
                    AND reservation_time = %s 
                    AND (status = 'confirmed' OR (status = 'pending' AND pending_expires_at > NOW()))
                )
            """
            params.extend([date, time])
            
            cursor.execute(query, tuple(params))
            tables = cursor.fetchall()
            return jsonify({'available_tables': tables}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/reserve-table', methods=['POST'])
def api_reserve_table():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    table_id = data.get('table_id')
    date = data.get('date')
    time = data.get('time')
    guests = data.get('guests')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check availability again to prevent double booking
            cursor.execute("""
                SELECT reservation_id FROM Reservations 
                WHERE table_id = %s AND reservation_date = %s 
                AND reservation_time = %s AND (status = 'confirmed' OR (status = 'pending' AND pending_expires_at > NOW()))
            """, (table_id, date, time))
            
            if cursor.fetchone():
                return jsonify({'error': 'Table is already booked for this time'}), 409
                
            cursor.execute("""
                INSERT INTO Reservations (user_id, table_id, reservation_date, reservation_time, guests, status, pending_expires_at)
                VALUES (%s, %s, %s, %s, %s, 'pending', DATE_ADD(NOW(), INTERVAL 2 MINUTE))
            """, (session['user_id'], table_id, date, time, guests))
            
            reservation_id = cursor.lastrowid
        conn.commit()
        return jsonify({'message': 'Reservation created', 'reservation_id': reservation_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/transactions', methods=['POST'])
def api_transactions():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    reservation_id = data.get('reservation_id')
    payment_method = data.get('payment_method')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Confirm reservation exists and belongs to user
            cursor.execute("SELECT * FROM Reservations WHERE reservation_id = %s AND user_id = %s", 
                         (reservation_id, session['user_id']))
            reservation = cursor.fetchone()
            if not reservation:
                return jsonify({'error': 'Reservation not found'}), 404
                
            if reservation['status'] == 'pending':
                cursor.execute("SELECT IF(pending_expires_at > NOW(), 1, 0) as is_valid FROM Reservations WHERE reservation_id = %s", (reservation_id,))
                res_check = cursor.fetchone()
                if not res_check or res_check['is_valid'] == 0:
                    cursor.execute("UPDATE Reservations SET status = 'cancelled' WHERE reservation_id = %s", (reservation_id,))
                    conn.commit()
                    return jsonify({'error': 'Reservation time expired (2 minutes). Please try booking again.'}), 400
                
            # Create transaction
            cursor.execute("""
                INSERT INTO Transactions (reservation_id, payment_method, transaction_status)
                VALUES (%s, %s, 'success')
            """, (reservation_id, payment_method))
            
            # Update reservation status to confirmed
            cursor.execute("UPDATE Reservations SET status = 'confirmed' WHERE reservation_id = %s", (reservation_id,))
            
        conn.commit()
        
        # Simulate Email Reminder
        print(f"\n*** [EMAIL SIMULATION] Booking Confirmed!")
        print(f"*** User ID: {session['user_id']}")
        print(f"*** Reservation ID: {reservation_id}")
        print(f"*** We have set a reminder for your upcoming reservation.\n")

        return jsonify({'message': 'Payment successful and reservation confirmed. Email reminder sent!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/history', methods=['GET'])
def api_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT r.reservation_id, r.reservation_date, r.reservation_time, r.guests, r.status,
                       t.table_number, t.location, tr.payment_method, tr.transaction_status
                FROM Reservations r
                JOIN Tables t ON r.table_id = t.table_id
                LEFT JOIN Transactions tr ON r.reservation_id = tr.reservation_id
                WHERE r.user_id = %s
                ORDER BY r.reservation_date DESC, r.reservation_time DESC
            """, (session['user_id'],))
            history = cursor.fetchall()
            for row in history:
                if 'reservation_time' in row and row['reservation_time']:
                    row['reservation_time'] = str(row['reservation_time'])
                if 'reservation_date' in row and row['reservation_date']:
                    row['reservation_date'] = str(row['reservation_date'])
            return jsonify({'history': history}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/reservations', methods=['GET', 'DELETE'])
def api_admin_reservations():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute("""
                    SELECT r.reservation_id, u.name as user_name, u.email, u.phone,
                           t.table_number, r.reservation_date, r.reservation_time, r.guests, r.status
                    FROM Reservations r
                    JOIN Users u ON r.user_id = u.user_id
                    JOIN Tables t ON r.table_id = t.table_id
                    ORDER BY r.reservation_date DESC, r.reservation_time DESC
                """)
                reservations = cursor.fetchall()
                for row in reservations:
                    if 'reservation_time' in row and row['reservation_time']:
                        row['reservation_time'] = str(row['reservation_time'])
                    if 'reservation_date' in row and row['reservation_date']:
                        row['reservation_date'] = str(row['reservation_date'])
                return jsonify({'reservations': reservations}), 200
            elif request.method == 'DELETE':
                reservation_id = request.json.get('reservation_id')
                cursor.execute("DELETE FROM Reservations WHERE reservation_id = %s", (reservation_id,))
                conn.commit()
                return jsonify({'message': 'Reservation deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/users', methods=['GET', 'DELETE'])
def api_admin_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT user_id, name, email, phone, role, is_verified, created_at FROM Users")
                users = cursor.fetchall()
                for row in users:
                    row['created_at'] = str(row['created_at'])
                return jsonify({'users': users}), 200
            elif request.method == 'DELETE':
                user_id = request.json.get('user_id')
                cursor.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
                conn.commit()
                return jsonify({'message': 'User deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/tables', methods=['GET', 'POST', 'DELETE'])
def api_admin_tables():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT * FROM Tables")
                tables = cursor.fetchall()
                return jsonify({'tables': tables}), 200
            elif request.method == 'POST':
                data = request.json
                table_number = data.get('table_number')
                capacity = data.get('capacity')
                location = data.get('location')
                cursor.execute("INSERT INTO Tables (table_number, capacity, location) VALUES (%s, %s, %s)", 
                               (table_number, capacity, location))
                conn.commit()
                return jsonify({'message': 'Table added'}), 201
            elif request.method == 'DELETE':
                table_id = request.json.get('table_id')
                cursor.execute("DELETE FROM Tables WHERE table_id = %s", (table_id,))
                conn.commit()
                return jsonify({'message': 'Table deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/stats', methods=['GET'])
def api_admin_stats():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM Tables")
            total_tables = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM Reservations WHERE DATE(reservation_date) = CURDATE() AND status != 'cancelled'")
            today_res = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT DATE(reservation_date) as date, COUNT(*) as count 
                FROM Reservations 
                WHERE reservation_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) AND status != 'cancelled'
                GROUP BY DATE(reservation_date)
                ORDER BY DATE(reservation_date)
            """)
            daily_bookings = cursor.fetchall()
            for row in daily_bookings:
                if 'date' in row and row['date']:
                    row['date'] = str(row['date'])
                    
            return jsonify({
                'total_tables': total_tables,
                'today_reservations': today_res,
                'daily_bookings': daily_bookings
            }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/user/credentials', methods=['PUT'])
def update_credentials():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    new_phone = data.get('phone')
    new_password = data.get('password')
    
    if not new_phone and not new_password:
        return jsonify({'error': 'No data provided'}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if new_phone:
                cursor.execute("UPDATE Users SET phone = %s WHERE user_id = %s", (new_phone, session['user_id']))
            if new_password:
                hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("UPDATE Users SET password_hash = %s WHERE user_id = %s", (hashed_pw, session['user_id']))
        conn.commit()
        return jsonify({'message': 'Credentials updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    # Create required template directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    app.run(debug=True, port=5000)
