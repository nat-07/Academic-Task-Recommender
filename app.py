from flask import Flask, jsonify, request, redirect, url_for, render_template, session
from psycopg2 import pool
from dotenv import load_dotenv
import os
import logging
from sklearn.metrics.pairwise import cosine_similarity
from ml_model import recommend_tasks


logging.basicConfig(level=logging.DEBUG)

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change_this_to_something_secret")

# DB config
connection_pool = pool.SimpleConnectionPool(
    1, 10,
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    sslmode="require",
)

def get_db_connection():
    return connection_pool.getconn()

def release_db_connection(conn):
    connection_pool.putconn(conn)

@app.route("/recommendation")
def recommendation():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("recommendation.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("recommendation"))
    else:
        return redirect(url_for("login_page"))

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id FROM users WHERE username = %s AND password = %s",
            (username, password)
        )

        user = cursor.fetchone()

        if user:
            session["user_id"] = user[0]
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Invalid credentials"})

    finally:
        cursor.close()
        release_db_connection(conn)

@app.route("/api/sign-up", methods=["POST"])
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

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)  # Remove user_id from session if it exists
    return jsonify({"status": "success", "message": "Logged out"})

@app.route("/api/check-session", methods=["GET"])
def check_session():
    if "user_id" in session:
        return jsonify({"logged_in": True})
    else:
        return jsonify({"logged_in": False})

@app.route("/api/add-task", methods=["POST"])
def add_task():
    data = request.json
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    task_description = data.get("task_description")
    module_name = data.get("module")
    task_type = data.get("task_type")
    difficulty = data.get("difficulty", 1)  # default difficulty
    estimated_time = data.get("estimated_time", 60)  # default 60 mins

    if not task_description or not module_name or not task_type:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    conn = get_db_connection()

    try:
        cur = conn.cursor()

        # Get module_id from modules table
        cur.execute("SELECT module_id FROM modules WHERE name = %s", (module_name,))
        module_row = cur.fetchone()
        if not module_row:
            return jsonify({"status": "error", "message": "Module not found"}), 404
        module_id = module_row[0]

        # Insert new task
        cur.execute("""
    INSERT INTO tasks
    (task_description, module_id, task_type, difficulty, estimated_time, active, user_id)
    VALUES (%s, %s, %s, %s, %s, TRUE, %s)
    RETURNING task_id
""", (task_description, module_id, task_type, difficulty, estimated_time, user_id))

        new_task_id = cur.fetchone()[0]
        conn.commit()
        cur.close()

        return jsonify({"status": "success", "task_id": new_task_id})

    finally:
        release_db_connection(conn)

@app.route("/api/modules", methods=["GET"])
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
            WHERE user_id = %s
            ORDER BY name
        """, (user_id,))

        rows = cur.fetchall()

        modules = [
            {
                "module_id": r[0],
                "name": r[1],
                "likeness": float(r[2]),
                "difficulty": int(r[3])
            }
            for r in rows
        ]

        return jsonify({"status": "success", "modules": modules})

    finally:
        if cur:
            cur.close()
        release_db_connection(conn)

@app.route("/api/add-module", methods=["POST"])
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

@app.route("/api/delete-module", methods=["POST"])
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

@app.route("/recommend-task", methods=["POST"])
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

            # Check the most recent history for this task for this user
            cur.execute("""
                SELECT completed, accepted
                FROM task_history
                WHERE task_id = %s AND user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (task_id, user_id))
            row = cur.fetchone()

            if row:
                completed, accepted = row
                # If both are NULL, update to FALSE
                if completed is None and accepted is None:
                    cur.execute("""
                        UPDATE task_history
                        SET completed = FALSE, accepted = FALSE
                        WHERE task_id = %s AND user_id = %s
                        AND completed IS NULL AND accepted IS NULL
                    """, (task_id, user_id))

            # Insert new recommendation
            cur.execute("""
                INSERT INTO task_history
                (task_id, user_id, motivation, recommended, completed, accepted, created_at)
                VALUES (%s, %s, %s, TRUE, NULL, NULL, NOW())
            """, (task_id, user_id, motivation))

        conn.commit()
        cur.close()

        return jsonify({
            "status": "ranked",
            "tasks": tasks
        })

    finally:
        release_db_connection(conn)


@app.route("/api/edit-module", methods=["POST"])
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

@app.route("/api/complete-task", methods=["POST"])
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
            SET completed = TRUE, accepted = TRUE
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

if __name__ == "__main__":
    app.run(debug=True)