from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sqlite3
from datetime import datetime, date
import csv
import io
import os
import hashlib  # For password hashing

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

DATABASE_FILE = os.path.join(os.getcwd(), "database.db")
STUDENT_FILE = os.path.join(os.getcwd(), "students.txt")
TEMPLATE_FILE = os.path.join(os.getcwd(), "names.txt")  # Path to template file

# Initialize the database with logs, current_status, and user accounts
def init_db():
    print(f"Initializing database at: {DATABASE_FILE}")
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )
        """)
        print("Users table created (or already exists)")


    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS current_status (
                name TEXT PRIMARY KEY,
                is_out INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )
        """)
    print("Database initialized")

# Hash a password for secure storage
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Check if the user is logged in
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hash_password(password)

        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()

            if result and result[0] == password_hash:
                # Store session details
                session['logged_in'] = True
                session['username'] = username
                session['database'] = f"{username}_database.db"
                
                # Initialize the teacher-specific database
                init_teacher_db(session['database'])
                
                return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


def init_teacher_db(teacher_db_file):
    if not os.path.exists(teacher_db_file):
        with sqlite3.connect(teacher_db_file) as conn:
            # Create all required tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS current_status (
                    name TEXT PRIMARY KEY,
                    is_out INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL
                )
            """)  # Add this to ensure users table exists
        print(f"Initialized database: {teacher_db_file}")


@app.route('/make_account', methods=['GET', 'POST'])
def make_account():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return render_template('make_account.html', error="Passwords do not match")

        password_hash = hash_password(password)

        try:
            # Use the global database for user registration
            with sqlite3.connect(DATABASE_FILE) as conn:
                conn.execute("""
                    INSERT INTO users (username, password_hash)
                    VALUES (?, ?)
                """, (username, password_hash))

            # Set up the per-teacher database
            teacher_db_file = f"{username}_database.db"
            session['database'] = teacher_db_file  # Store in session for future use
            init_teacher_db(teacher_db_file)  # Initialize the per-teacher database

            return redirect(url_for('login'))
        except sqlite3.OperationalError as e:
            print(f"OperationalError: {e}")  # Log the error for debugging
            return render_template('make_account.html', error="Database error occurred")
        except sqlite3.IntegrityError:
            return render_template('make_account.html', error="Username already exists")

    return render_template('make_account.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/home')
@login_required
def home():
    # Generate teacher-specific file name
    student_file = f"{session['username']}_students.txt"
    students = []

    # Load student names from the teacher-specific file
    if os.path.exists(student_file):
        with open(student_file, 'r') as f:
            students = [line.strip() for line in f.readlines()]

    return render_template('index.html', students=students)


@app.route('/template', methods=['GET'])
@login_required
def download_template():
    return send_file(TEMPLATE_FILE, as_attachment=True)


@app.route('/log', methods=['POST'])
@login_required
def log_button_press():
    data = request.json
    name = data.get('name')
    timestamp = datetime.now().isoformat()

    with sqlite3.connect(session['database']) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_out FROM current_status WHERE name = ?", (name,))
        result = cursor.fetchone()

        if result is None:
            cursor.execute("INSERT INTO current_status (name, is_out) VALUES (?, 1)", (name,))
            action = "out"
        else:
            is_out = result[0]
            if is_out == 0:
                cursor.execute("UPDATE current_status SET is_out = 1 WHERE name = ?", (name,))
                action = "out"
            else:
                cursor.execute("UPDATE current_status SET is_out = 0 WHERE name = ?", (name,))
                action = "in"

        conn.execute("INSERT INTO logs (name, timestamp, action) VALUES (?, ?, ?)", (name, timestamp, action))

    return jsonify({'status': 'success', 'message': f'{name} logged as {action}'})


@app.route('/status', methods=['GET'])
@login_required
def get_status():
    with sqlite3.connect(session['database']) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, is_out FROM current_status")
        status = cursor.fetchall()
    return jsonify(status)

@app.route('/mark_all_in', methods=['POST'])
@login_required
def mark_all_in():
    timestamp = datetime.now().isoformat()

    with sqlite3.connect(session['database']) as conn:
        cursor = conn.cursor()

        # Retrieve all students who are currently out
        cursor.execute("SELECT name FROM current_status WHERE is_out = 1")
        students_out = cursor.fetchall()

        # Update their status to "in" and log the action
        for student in students_out:
            name = student[0]
            cursor.execute("UPDATE current_status SET is_out = 0 WHERE name = ?", (name,))
            cursor.execute("INSERT INTO logs (name, timestamp, action) VALUES (?, ?, ?)", (name, timestamp, "in"))

    return jsonify({'status': 'success', 'message': 'All students marked as returned!'})


@app.route('/clear_logs', methods=['POST'])
@login_required
def clear_logs():
    with sqlite3.connect(session['database']) as conn:
        conn.execute("DELETE FROM logs")
        conn.execute("DELETE FROM current_status")
    return jsonify({'status': 'success', 'message': 'All logs cleared!'})


@app.route('/upload_students', methods=['POST'])
@login_required
def upload_students():
    file = request.files['file']
    if file and file.filename.endswith('.txt'):
        # Generate teacher-specific file name
        student_file = f"{session['username']}_students.txt"
        
        # Save the uploaded file to the teacher-specific file
        file.save(student_file)
        return redirect(url_for('home'))  # Redirect back to the home page
    else:
        # Handle invalid file uploads
        return render_template('index.html', error="Please upload a valid .txt file.")


@app.route('/export_all', methods=['GET'])
@login_required
def export_all():
    return export_logs()


@app.route('/export_today', methods=['GET'])
@login_required
def export_today():
    today = date.today().isoformat()
    return export_logs(filter_date=today)


def export_logs(filter_date=None):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Timestamp', 'Action'])

    with sqlite3.connect(session['database']) as conn:
        cursor = conn.cursor()
        if filter_date:
            cursor.execute("SELECT name, timestamp, action FROM logs WHERE date(timestamp) = ? ORDER BY timestamp", (filter_date,))
        else:
            cursor.execute("SELECT name, timestamp, action FROM logs ORDER BY timestamp")
        logs = cursor.fetchall()
        for log in logs:
            writer.writerow(log)

    output.seek(0)
    filename = f"bathroom_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


if __name__ == '__main__':
    init_db()  # Ensures database and tables are created
    app.run(debug=True)
