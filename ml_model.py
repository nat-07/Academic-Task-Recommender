import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity


def recommend_tasks(conn, user_id, motivation=2.5):
    # ---------------------------
    # 1. Fetch tasks
    # ---------------------------
    query = """
    SELECT t.task_id, t.task_type, t.task_description,
           t.difficulty AS task_difficulty,
           t.estimated_time,
           m.likeness AS module_likeness,
           m.difficulty AS module_difficulty,
           m.catching_up
    FROM tasks t
    JOIN modules m ON t.module_id = m.module_id
    WHERE t.active = TRUE AND t.user_id = %s
    """
    df = pd.read_sql(query, conn, params=[user_id])

    if df.empty:
        return []

    # ---------------------------
    # 2. Feature engineering
    # ---------------------------
    current_hour = datetime.now().hour
    df["time_sin"] = np.sin(2 * np.pi * current_hour / 24)
    df["time_cos"] = np.cos(2 * np.pi * current_hour / 24)
    df["motivation"] = motivation

    task_types = pd.get_dummies(df["task_type"], prefix="type")

    X = pd.concat([
        df[[
            "task_difficulty",
            "estimated_time",
            "module_likeness",
            "module_difficulty",
            "catching_up",
            "motivation",
            "time_sin",
            "time_cos"
        ]],
        task_types
    ], axis=1)

    # ---------------------------
    # 3. ML model
    # ---------------------------
    hist_query = """
    SELECT t.task_type,
           t.difficulty AS task_difficulty,
           t.estimated_time,
           m.likeness AS module_likeness,
           m.difficulty AS module_difficulty,
           m.catching_up,
           h.accepted,
           h.motivation
    FROM task_history h
    JOIN tasks t ON h.task_id = t.task_id
    JOIN modules m ON t.module_id = m.module_id
    WHERE h.accepted IS NOT NULL AND h.user_id = %s
    """
    hist_df = pd.read_sql(hist_query, conn, params=[user_id])
    hist_df["accepted"] = hist_df["accepted"].fillna(False).astype(int)

    if not hist_df.empty and hist_df["accepted"].nunique() > 1:
        hist_task_types = pd.get_dummies(hist_df["task_type"], prefix="type")

        X_hist = pd.concat([
            hist_df[[
                "task_difficulty",
                "estimated_time",
                "module_likeness",
                "module_difficulty",
                "catching_up",
                "motivation"
            ]],
            hist_task_types
        ], axis=1)

        X_hist = X_hist.reindex(columns=X.columns, fill_value=0)
        X_hist = X_hist.fillna(0)
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
        model.fit(X_hist, hist_df["accepted"])
        X = X.fillna(0)
        df["ml_score"] = model.predict_proba(X)[:, 1]

    else:
        df["ml_score"] = (
            0.4 * df["module_likeness"] +
            0.3 * df["motivation"] -
            0.2 * df["task_difficulty"] -
            0.1 * (df["estimated_time"] / 60)
        )

    # ---------------------------
    # 4. Collaborative filtering
    # ---------------------------
    user_task_query = """
    SELECT user_id, task_id, accepted
    FROM task_history
    WHERE accepted IS NOT NULL
    """
    user_task_df = pd.read_sql(user_task_query, conn)
    

    df["cf_score"] = 0

    if not user_task_df.empty:
        user_task_matrix = user_task_df.pivot_table(
            index="user_id",
            columns="task_id",
            values="accepted",
            fill_value=0
        )

        if user_id in user_task_matrix.index:
            similarity = cosine_similarity(user_task_matrix)

            similarity_df = pd.DataFrame(
                similarity,
                index=user_task_matrix.index,
                columns=user_task_matrix.index
            )

            user_sim = similarity_df[user_id].drop(user_id)

            cf_scores = {}

            for task_id in df["task_id"]:
                score = 0
                total_sim = 0

                for other_user, sim in user_sim.items():
                    if task_id in user_task_matrix.columns:
                        rating = user_task_matrix.loc[other_user, task_id]
                        score += sim * rating
                        total_sim += abs(sim)

                cf_scores[task_id] = score / total_sim if total_sim > 0 else 0

            df["cf_score"] = df["task_id"].map(cf_scores)

    # ---------------------------
    # 5. Hybrid score
    # ---------------------------
    df["score"] = 0.7 * df["ml_score"] + 0.3 * df["cf_score"]

    # ---------------------------
    # 6. Sort + return
    # ---------------------------
    df = df.sort_values(by="score", ascending=False)

    return df[[
        "task_id",
        "task_description",
        "task_type",
        "score"
    ]].to_dict(orient="records")