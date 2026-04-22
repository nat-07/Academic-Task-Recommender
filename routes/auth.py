from flask import Blueprint, request, jsonify, session
from database.db import get_db_connection, release_db_connection

auth_bp = Blueprint("auth", __name__)

# -------------------- LOGIN --------------------
@auth_bp.route("/session", methods=["POST"])
def login():
    data = request.json

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id FROM users WHERE username=%s AND password=%s",
            (data["username"], data["password"])
        )

        user = cur.fetchone()

        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        session["user_id"] = user[0]
        return jsonify({"status": "success"}), 200

    finally:
        cur.close()
        release_db_connection(conn)


# -------------------- SIGN UP --------------------
@auth_bp.route("/auth/signup", methods=["POST"])
def sign_up():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id FROM users WHERE username = %s",
            (username,)
        )

        if cur.fetchone():
            return jsonify({"error": "Username already exists"}), 409

        cur.execute(
            """
            INSERT INTO users (username, password)
            VALUES (%s, %s)
            RETURNING user_id
            """,
            (username, password)
        )

        user_id = cur.fetchone()[0]
        conn.commit()

        session["user_id"] = user_id

        return jsonify({"status": "created"}), 201

    finally:
        cur.close()
        release_db_connection(conn)


# -------------------- LOGOUT --------------------
@auth_bp.route("/session", methods=["DELETE"])
def logout():
    session.clear()
    return "", 204


# -------------------- CHECK SESSION --------------------
@auth_bp.route("/session", methods=["GET"])
def check_session():
    return jsonify({"logged_in": "user_id" in session})