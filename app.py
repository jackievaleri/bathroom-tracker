from flask import Flask, render_template, request, jsonify, send_file
import redis
import csv
import io
from datetime import datetime

app = Flask(__name__)
db = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/log', methods=['POST'])
def log_button_press():
    data = request.json
    name = data.get('name')
    timestamp = datetime.now().isoformat()
    db.rpush(name, timestamp)
    return jsonify({'status': 'success', 'message': f'Logged timestamp for {name}'})

@app.route('/export', methods=['GET'])
def export_data():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Entry Time', 'Exit Time', 'Duration'])

    for name in db.keys():
        timestamps = db.lrange(name, 0, -1)
        for i in range(0, len(timestamps), 2):
            entry = timestamps[i]
            exit = timestamps[i + 1] if i + 1 < len(timestamps) else 'Still in bathroom'
            duration = (
                datetime.fromisoformat(exit) - datetime.fromisoformat(entry)
            ).seconds if exit != 'Still in bathroom' else 'N/A'
            writer.writerow([name, entry, exit, duration])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='bathroom_log.csv',
    )

if __name__ == '__main__':
    app.run(debug=True)
