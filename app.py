from flask import Flask, request, jsonify
import psycopg2
import redis
import json
import time

app = Flask(__name__)

def get_db_connection():
    attempt = 0
    while attempt < 5:
        try:
            return psycopg2.connect(
                host="db",
                database="mydb",
                user="postgres",
                password="password"
            )
        except:
            attempt += 1
            time.sleep(2)

redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

@app.route("/")
def home():
    return "Flask + PostgreSQL + Redis Working!"

@app.route("/add_user", methods=["POST"])
def add_user():
    data = request.json
    name = data["name"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name VARCHAR(100));")
    cur.execute("INSERT INTO users (name) VALUES (%s) RETURNING id;", (name,))
    user_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    redis_client.delete("users")

    return jsonify({"message": "User added", "id": user_id})

@app.route("/users", methods=["GET"])
def get_users():
    cached = redis_client.get("users")
    if cached:
        return jsonify({"source": "cache", "data": json.loads(cached)})

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name VARCHAR(100));")
    cur.execute("SELECT * FROM users;")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    redis_client.set("users", json.dumps(rows))
    return jsonify({"source": "database", "data": rows})

@app.route("/update_user/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.json
    new_name = data["name"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET name=%s WHERE id=%s;", (new_name, user_id))
    conn.commit()
    cur.close()
    conn.close()

    redis_client.delete("users")

    return jsonify({"message": "User updated", "id": user_id})

@app.route("/delete_user/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s;", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    redis_client.delete("users")

    return jsonify({"message": "User deleted", "id": user_id})

@app.route("/clear_cache", methods=["POST"])
def clear_cache():
    redis_client.delete("users")
    return jsonify({"message": "Cache cleared"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
