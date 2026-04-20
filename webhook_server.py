from flask import Flask, request, jsonify
import mysql.connector
import os

app = Flask(__name__)


def get_connection():
    return mysql.connector.connect(
        host=os.environ["MYSQLHOST"],
        user=os.environ["MYSQLUSER"],
        password=os.environ["MYSQLPASSWORD"],
        database=os.environ["MYSQLDATABASE"],
        port=int(os.environ["MYSQLPORT"])
    )


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("🔥 RECEIVED:", data)

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO tickets (id, subject, status, priority, created_time)
    VALUES (%s, %s, %s, %s, NOW())
    ON DUPLICATE KEY UPDATE 
        subject=%s,
        status=%s,
        priority=%s
    """

    cursor.execute(query, (
        data.get("id"),
        data.get("subject"),
        data.get("status"),
        data.get("priority"),
        data.get("subject"),
        data.get("status"),
        data.get("priority")
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)