from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
from datetime import datetime, date
import csv
import io
import os

app = Flask(__name__)

DATABASE_FILE = os.path.join(os.getcwd(), "database.db")
STUDENT_FILE = os.path.join(os.getcwd(), "students.txt")
TEMPLATE_FILE = os.path.join(os.getcwd(), "names.txt")  # Path to template file

# Initialize the database
def init_db():
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
    print("Database initialized")

@app.route('/')
def home():
    # Load student names from file
    students = []
    if os.path.exists(STUDENT_FILE):
        with open(STUDENT_FILE, 'r') as f:
            students = [line.strip() for line in f.readlines()]
    return render_template('index.html', students=students)

@app.route('/template', methods=['GET'])
def download_template():
    # Serve the names.txt template for download
    return send_file(TEMPLATE_FILE, as_attachment=True)

@app.route('/log', methods=['POST'])
def log_button_press():
    data = request.json
    name = data.get('name')
    timestamp = datetime.now().isoformat()

    with sqlite3.connect(DATABASE_FILE) as conn:
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
def get_status():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, is_out FROM current_status")
        status = cursor.fetchall()
    return jsonify(status)

@app.route('/mark_all_in', methods=['POST'])
def mark_all_in():
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("UPDATE current_status SET is_out = 0")
    return jsonify({'status': 'success', 'message': 'All students marked as returned!'})

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("DELETE FROM logs")
        conn.execute("DELETE FROM current_status")
    return jsonify({'status': 'success', 'message': 'All logs cleared!'})

@app.route('/upload_students', methods=['POST'])
def upload_students():
    file = request.files['file']
    if file and file.filename.endswith('.txt'):
        file.save(STUDENT_FILE)
        return jsonify({'status': 'success', 'message': 'Student list uploaded successfully!'})
    else:
        return jsonify({'status': 'error', 'message': 'Please upload a valid .txt file.'}), 400


@app.route('/export_all', methods=['GET'])
def export_all():
    return export_logs()

@app.route('/export_today', methods=['GET'])
def export_today():
    today = date.today().isoformat()
    return export_logs(filter_date=today)

def export_logs(filter_date=None):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Timestamp', 'Action'])

    with sqlite3.connect(DATABASE_FILE) as conn:
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
    init_db()
    app.run(debug=True)
