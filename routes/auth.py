from flask import Blueprint, request, jsonify, session
from database.db import get_db_connection, release_db_connection

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/login", methods=["POST"])
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

        if user:
            session["user_id"] = user[0]
            return jsonify({"status": "success"})
        return jsonify({"status": "error"})

    finally:
        cur.close()
        release_db_connection(conn)


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success"})