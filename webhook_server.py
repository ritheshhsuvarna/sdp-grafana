from flask import Flask, request, jsonify
import mysql.connector
import os
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)

# =========================
# DB CONNECTION (FIXED)
# =========================
def get_connection():
    url = os.environ.get("MYSQL_URL")

    if not url:
        raise Exception("MYSQL_URL not set")

    parsed = urlparse(url)

    return mysql.connector.connect(
        host=parsed.hostname,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:],
        port=parsed.port
    )


# =========================
# SAFE VALUE EXTRACTORS
# =========================
def safe(val, default="Unknown"):
    if val is None or val == "":
        return default
    return val


def safe_nested(obj, key, default="Unknown"):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return safe(obj, default)


# =========================
# TIME CONVERTER
# =========================
def convert_time(value):
    try:
        if not value:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        value = int(value)

        # Handle milliseconds
        if value > 10**12:
            value = value / 1000

        return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

    except:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# =========================
# CREATE TABLE
# =========================
def create_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id BIGINT PRIMARY KEY,
        subject TEXT,
        status VARCHAR(50),
        priority VARCHAR(50),
        created_time DATETIME
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ Table ready")


# =========================
# WEBHOOK ENDPOINT
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("🔥 RECEIVED:", data)

        if not data:
            return jsonify({"error": "No data"}), 400

        # Extract fields safely
        ticket_id = safe(data.get("id"))
        subject = safe(data.get("subject"))
        status = safe(data.get("status"))
        priority = safe(data.get("priority"))
        created_time = convert_time(data.get("created_time"))

        print(f"DEBUG → {ticket_id} | {status} | {priority}")

        # Skip if ID missing
        if ticket_id == "Unknown":
            return jsonify({"error": "Invalid ticket id"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO tickets (id, subject, status, priority, created_time)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            subject=%s,
            status=%s,
            priority=%s
        """

        cursor.execute(query, (
            ticket_id,
            subject,
            status,
            priority,
            created_time,
            subject,
            status,
            priority
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({"error": str(e)}), 500


# =========================
# ROOT (OPTIONAL)
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Webhook server is running 🚀", 200


# =========================
# RUN
# =========================
if __name__ == "__main__":
    create_table()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
