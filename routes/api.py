from flask import Blueprint, request, jsonify, session
from database.db import get_db_connection, release_db_connection
from ml_model import recommend_tasks

api_bp = Blueprint("api", __name__)


# -------------------- MODULES --------------------

@api_bp.route("/modules", methods=["GET"])
def get_modules():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT module_id, name, likeness, difficulty
            FROM modules
            WHERE user_id = %s AND active = TRUE
            ORDER BY name
        """, (user_id,))

        modules = [
            {
                "module_id": r[0],
                "name": r[1],
                "likeness": float(r[2]),
                "difficulty": float(r[3])
            }
            for r in cur.fetchall()
        ]

        return jsonify({"status": "success", "modules": modules})

    finally:
        cur.close()
        release_db_connection(conn)


@api_bp.route("/modules", methods=["POST"])
def create_module():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    data = request.json

    name = data.get("name")
    likeness = data.get("likeness")
    difficulty = data.get("difficulty")

    if not all([name, likeness is not None, difficulty is not None]):
        return jsonify({"error": "Missing data"}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT module_id, active
            FROM modules
            WHERE user_id = %s AND name = %s
        """, (user_id, name))

        row = cur.fetchone()

        if row:
            module_id, active = row
            if active:
                return jsonify({"error": "Module already exists"}), 409

            cur.execute("""
                UPDATE modules
                SET active = TRUE, likeness = %s, difficulty = %s
                WHERE module_id = %s AND user_id = %s
            """, (likeness, difficulty, module_id, user_id))

            conn.commit()
            return jsonify({"status": "reactivated"}), 200

        cur.execute("""
            INSERT INTO modules (user_id, name, likeness, difficulty, active)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (user_id, name, likeness, difficulty))

        conn.commit()
        return jsonify({"status": "created"}), 201

    finally:
        cur.close()
        release_db_connection(conn)


@api_bp.route("/modules/<int:module_id>", methods=["DELETE"])
def delete_module(module_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]

    conn = get_db_connection()
    try:
        conn.autocommit = False
        cur = conn.cursor()

        cur.execute("""
            UPDATE modules
            SET active = FALSE
            WHERE module_id = %s AND user_id = %s
        """, (module_id, user_id))

        cur.execute("""
            UPDATE tasks
            SET active = FALSE
            WHERE module_id = %s AND user_id = %s
            RETURNING task_id
        """, (module_id, user_id))

        task_ids = [r[0] for r in cur.fetchall()]

        if task_ids:
            cur.execute("""
                UPDATE task_history
                SET accepted = FALSE
                WHERE task_id = ANY(%s) AND user_id = %s
                AND accepted IS NULL
            """, (task_ids, user_id))

        conn.commit()
        return jsonify({"status": "deleted"})

    except Exception:
        conn.rollback()
        return jsonify({"error": "Failed"}), 500

    finally:
        cur.close()
        release_db_connection(conn)


@api_bp.route("/modules/<int:module_id>", methods=["PATCH"])
def update_module(module_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    name = data.get("name")
    likeness = data.get("likeness")
    difficulty = data.get("difficulty")
    user_id = session["user_id"]

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            UPDATE modules
            SET name = %s, likeness = %s, difficulty = %s
            WHERE module_id = %s AND user_id = %s
        """, (name, likeness, difficulty, module_id, user_id))

        conn.commit()
        return jsonify({"status": "updated"})

    finally:
        cur.close()
        release_db_connection(conn)


# -------------------- TASKS --------------------

@api_bp.route("/tasks", methods=["POST"])
def create_task():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    data = request.json

    module_name = data.get("module")
    description = data.get("task_description")
    task_type = data.get("task_type")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
    "SELECT module_id FROM modules WHERE name = %s AND user_id = %s",
    (module_name, user_id)
)
        row = cur.fetchone()

        if not row:
            return jsonify({"error": "Module not found"}), 404

        module_id = row[0]

        cur.execute("""
            INSERT INTO tasks (
                task_description, module_id, task_type,
                difficulty, estimated_time, active, user_id
            )
            VALUES (%s, %s, %s, %s, %s, TRUE, %s)
            RETURNING task_id
        """, (
            description,
            module_id,
            task_type,
            data.get("difficulty", 1),
            data.get("estimated_time", 60),
            user_id
        ))

        task_id = cur.fetchone()[0]
        conn.commit()

        return jsonify({"task_id": task_id, "status" : "created"}), 201

    finally:
        cur.close()
        release_db_connection(conn)


@api_bp.route("/tasks/<int:task_id>/complete", methods=["PATCH"])
def complete_task(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            UPDATE task_history
            SET accepted = TRUE
            WHERE task_id = %s AND user_id = %s
        """, (task_id, user_id))

        cur.execute("""
            UPDATE tasks
            SET active = FALSE
            WHERE task_id = %s AND user_id = %s
        """, (task_id, user_id))

        conn.commit()
        return jsonify({"status": "completed"})

    finally:
        cur.close()
        release_db_connection(conn)


# -------------------- RECOMMENDATIONS --------------------

@api_bp.route("/tasks/recommendations", methods=["GET"])
def recommend_task():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    motivation = float(request.args.get("motivation", 2.5))

    conn = get_db_connection()
    try:
        tasks = recommend_tasks(conn, user_id, motivation)
        return jsonify({"tasks": tasks, "status": "success"})

    finally:
        release_db_connection(conn)

