from flask import Flask, request, jsonify
import mysql.connector
import os
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)


# =========================
# DB CONNECTION (MYSQL_URL)
# =========================
def get_connection():
    try:
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

    except Exception as e:
        print("❌ DB CONNECTION ERROR:", e)
        raise


# =========================
# SAFE HELPERS
# =========================
def extract_name(value, default="Unknown"):
    if isinstance(value, dict):
        return value.get("name", default)
    return str(value or default)


def convert_time(value):
    try:
        if isinstance(value, dict):
            value = value.get("value")

        if not value:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        value = int(value)

        # Convert milliseconds → seconds
        if value > 10**12:
            value = value / 1000

        return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

    except:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# =========================
# CREATE TABLE IF NOT EXISTS
# =========================
def create_table():
    try:
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

    except Exception as e:
        print("❌ Table creation error:", e)


# =========================
# WEBHOOK ENDPOINT
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json

        print("🔥 WEBHOOK RECEIVED:", data)

        if not data:
            return jsonify({"error": "No data received"}), 400

        # SDP sometimes sends nested payload
        ticket = data.get("data", {}).get("request", data)

        ticket_id = ticket.get("id")
        subject = ticket.get("subject", "")

        status = extract_name(ticket.get("status"))
        priority = extract_name(ticket.get("priority"))

        created_time = convert_time(ticket.get("created_time"))

        print(f"DEBUG → {ticket_id} | {status} | {priority}")

        # =========================
        # INSERT INTO DB
        # =========================
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
        print("❌ WEBHOOK ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# =========================
# ROOT (OPTIONAL)
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Webhook server is running 🚀", 200


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    create_table()  # Ensure table exists

    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Server running on port {port}")

    app.run(host="0.0.0.0", port=port)
