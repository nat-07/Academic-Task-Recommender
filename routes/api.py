from flask import Blueprint, request, jsonify, session
from database.db import get_db_connection, release_db_connection
from ml_model import recommend_tasks

api_bp = Blueprint("api", __name__)

@api_bp.route("/api/modules", methods=["GET"])
def get_modules():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]

    conn = get_db_connection()
    cur = None

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT module_id, name, likeness, difficulty
            FROM modules
            WHERE user_id = %s AND active = TRUE
            ORDER BY name
        """, (user_id,))

        rows = cur.fetchall()

        modules = [
            {
                "module_id": r[0],
                "name": r[1],
                "likeness": float(r[2]),
                "difficulty": float(r[3])
            }
            for r in rows
        ]

        return jsonify({"status": "success", "modules": modules})

    finally:
        if cur:
            cur.close()
        release_db_connection(conn)

@api_bp.route("/api/delete-module", methods=["POST"])
def delete_module():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user_id = session["user_id"]
    data = request.get_json()
    module_id = data.get("module_id")

    if not module_id:
        return jsonify({"status": "error", "message": "No module_id provided"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Start transaction
        conn.autocommit = False

        # 1️⃣ Deactivate module
        cur.execute("""
            UPDATE modules
            SET active = FALSE
            WHERE module_id = %s AND user_id = %s
        """, (module_id, user_id))

        # 2️⃣ Deactivate tasks + collect affected task_ids
        cur.execute("""
            UPDATE tasks
            SET active = FALSE
            WHERE module_id = %s AND user_id = %s AND active = TRUE
            RETURNING task_id
        """, (module_id, user_id))

        task_ids = [row[0] for row in cur.fetchall()]

        # 3️⃣ Update task_history (accepted NULL → FALSE)
        if task_ids:
            cur.execute("""
                UPDATE task_history
                SET accepted = FALSE
                WHERE task_id = ANY(%s)
                AND accepted IS NULL
            """, (task_ids,))

        # Commit everything
        conn.commit()

        return jsonify({"status": "success"})

    except Exception as e:
        conn.rollback()
        print("Error deleting module:", e)
        return jsonify({"status": "error", "message": "Failed to delete module"}), 500

    finally:
        cur.close()
        release_db_connection(conn)

@api_bp.route("/api/add-module", methods=["POST"])
def add_module():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user_id = session["user_id"]
    data = request.json
    name = data.get("name")
    likeness = data.get("likeness")
    difficulty = data.get("difficulty")

    if not all([name, likeness is not None, difficulty is not None]):
        return jsonify({"status": "error", "message": "Missing data"}), 400

    conn = get_db_connection()
    cur = None

    try:
        cur = conn.cursor()

        # Check if module exists for this user
        cur.execute("""
            SELECT module_id, active
            FROM modules
            WHERE user_id = %s AND name = %s
        """, (user_id, name))

        row = cur.fetchone()

        if row:
            module_id, active = row
            if not active:
                # Reactivate and update likeness/difficulty
                cur.execute("""
                    UPDATE modules
                    SET active = TRUE, likeness = %s, difficulty = %s
                    WHERE module_id = %s
                """, (likeness, difficulty, module_id))
                conn.commit()
                return jsonify({"status": "success", "message": "Module reactivated"}), 200
            else:
                return jsonify({"status": "error", "message": "Module already exists"}), 400
        else:
            # Insert new module
            cur.execute("""
                INSERT INTO modules (user_id, name, likeness, difficulty, active)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (user_id, name, likeness, difficulty))
            conn.commit()
            return jsonify({"status": "success", "message": "Module added"}), 201

    finally:
        if cur:
            cur.close()
        release_db_connection(conn)

@api_bp.route("/api/add-task", methods=["POST"])
def add_task():
    data = request.json

    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]

    task_description = data.get("task_description")
    module_name = data.get("module")
    task_type = data.get("task_type")
    difficulty = data.get("difficulty", 1)
    estimated_time = data.get("estimated_time", 60)

    if not task_description or not module_name or not task_type:
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        # Get module_id from module name
        cur.execute(
            "SELECT module_id FROM modules WHERE name = %s",
            (module_name,)
        )
        module_row = cur.fetchone()

        if not module_row:
            return jsonify({
                "status": "error",
                "message": "Module not found"
            }), 404

        module_id = module_row[0]

        # ✅ Check for duplicate task
        cur.execute("""
            SELECT task_id
            FROM tasks
            WHERE task_description = %s
              AND module_id = %s
              AND user_id = %s
              AND active = TRUE
        """, (task_description, module_id, user_id))

        if cur.fetchone():
            return jsonify({
                "status": "error",
                "message": "This task already exist."
            }), 409

        # Insert new task
        cur.execute("""
            INSERT INTO tasks (
                task_description,
                module_id,
                task_type,
                difficulty,
                estimated_time,
                active,
                user_id
            )
            VALUES (%s, %s, %s, %s, %s, TRUE, %s)
            RETURNING task_id
        """, (
            task_description,
            module_id,
            task_type,
            difficulty,
            estimated_time,
            user_id
        ))

        new_task_id = cur.fetchone()[0]
        conn.commit()
        cur.close()

        return jsonify({
            "status": "success",
            "task_id": new_task_id
        })

    finally:
        release_db_connection(conn)

@api_bp.route("/api/recommend-task", methods=["POST"])
def recommend_task():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    motivation = float(request.json.get("motivation", 2.5))

    conn = get_db_connection()
    try:
        tasks = recommend_tasks(conn, user_id, motivation)

        if not tasks:
            return jsonify({"status": "no_task", "tasks": []})

        cur = conn.cursor()

        for t in tasks:
            task_id = t["task_id"]
            rank = t["rank"]

            # Check latest record
            cur.execute("""
                SELECT accepted
                FROM task_history
                WHERE task_id = %s AND user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (task_id, user_id))

            row = cur.fetchone()

            if row:
                accepted = row[0]   # ✅ FIXED

                if accepted is None:
                    cur.execute("""
                        UPDATE task_history
                        SET accepted = FALSE   -- ✅ FIXED
                        WHERE task_id = %s AND user_id = %s
                        AND accepted IS NULL
                    """, (task_id, user_id))

            # Insert new recommendation
            cur.execute("""
                INSERT INTO task_history
                (task_id, user_id, motivation, rank, accepted, created_at)
                VALUES (%s, %s, %s, %s, NULL, NOW())
            """, (task_id, user_id, motivation, rank))
        conn.commit()
        cur.close()

        return jsonify({
            "status": "ranked",
            "tasks": tasks
        })

    finally:
        release_db_connection(conn)


@api_bp.route("/api/edit-module", methods=["POST"])
def edit_module():
    data = request.json
    name = data.get("name")
    likeness = float(data.get("likeness", 0.5))
    difficulty = float(data.get("difficulty", 0.5))
    module_id = data.get("module_id")  # None if new module

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if module_id:
            # Update existing module
            cur.execute("""
                UPDATE modules
                SET name = %s, likeness = %s, difficulty = %s
                WHERE module_id = %s
            """, (name, likeness, difficulty, module_id))
        else:
            # Insert new module
            cur.execute("""
                INSERT INTO modules (name, likeness, difficulty, user_id)
                VALUES (%s, %s, %s, %s)     
            """, (name, likeness, difficulty))
        conn.commit()
        cur.close()
        return jsonify({"status": "success"})
    finally:
        release_db_connection(conn)

@api_bp.route("/api/complete-task", methods=["POST"])
def complete_task():
    data = request.json
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    task_id = data["task_id"]
    motivation = data.get("motivation", 2.5)

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        # Mark task_history entry as completed and accepted
        cur.execute("""
            UPDATE task_history
            SET accepted = True
            WHERE task_id = %s AND user_id = %s
        """, (task_id, user_id))

        # Mark the task as inactive
        cur.execute("""
            UPDATE tasks
            SET active = FALSE
            WHERE task_id = %s
        """, (task_id,))

        conn.commit()
        cur.close()

        return jsonify({"status": "success"})

    finally:
        release_db_connection(conn)

@api_bp.route("/api/check-session", methods=["GET"])
def check_session():
    if "user_id" in session:
        return jsonify({"logged_in": True})
    else:
        return jsonify({"logged_in": False})
    
@api_bp.route("/api/sign-up", methods=["POST"])
def sign_up():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING user_id",
            (username, password)
        )

        user_id = cur.fetchone()[0]
        conn.commit()

        # auto login
        session["user_id"] = user_id

        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"status": "error", "message": "Username may already exist"})

    finally:
        cur.close()
        release_db_connection(conn)