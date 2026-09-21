import os
import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)

ENVIRONMENT = os.getenv("ENVIRONMENT", "DEV")
APP_VERSION = os.getenv("APP_VERSION", "5.0")
DB_HOST = os.getenv("DB_HOST", "customer-db-dev")
DB_NAME = os.getenv("DB_NAME", "customer_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres123")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        connect_timeout=4
    )

@app.route("/")
def index():
    return jsonify({
        "application": "customer-app",
        "environment": ENVIRONMENT,
        "version": APP_VERSION,
        "db_host": DB_HOST
    }), 200

@app.route("/health")
def health():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.close()
        conn.close()
        return jsonify({
            "status": "healthy",
            "environment": ENVIRONMENT,
            "version": APP_VERSION,
            "database": "connected"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "environment": ENVIRONMENT,
            "version": APP_VERSION,
            "database_error": str(e)
        }), 500

@app.route("/customers", methods=["GET"])
def customer_search():
    search_term = request.args.get("query", "")
    return jsonify({
        "status": "success",
        "query": search_term,
        "environment": ENVIRONMENT,
        "records": [
            {"customer_id": 101, "name": "Global Logistics Inc", "tier": "Enterprise"},
            {"customer_id": 102, "name": "Apex Retail Systems", "tier": "Standard"}
        ]
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)