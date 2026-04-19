import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD


def recommend_tasks(conn, user_id, motivation=2.5):
    """
    Advanced hybrid recommendation system for ranking student tasks.

    Combines:
    - Supervised ML (Gradient Boosting)
    - Memory-based CF (cosine similarity)
    - Model-based CF (matrix factorisation via SVD)
    - Context-aware features (time, motivation)
    - Recency-aware learning
    """

    # ============================================================
    # 1. FETCH TASK DATA
    # ============================================================
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

    # ============================================================
    # 2. FEATURE ENGINEERING (CONTEXT-AWARE)
    # ============================================================

    # Encode time cyclically
    current_hour = datetime.now().hour
    df["time_sin"] = np.sin(2 * np.pi * current_hour / 24)
    df["time_cos"] = np.cos(2 * np.pi * current_hour / 24)

    # Add user motivation context
    df["motivation"] = motivation

    # One-hot encode task type
    task_types = pd.get_dummies(df["task_type"], prefix="type")

    # Build feature matrix
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
    ], axis=1).fillna(0)

    # ============================================================
    # 3. MACHINE LEARNING (PERSONAL MODEL)
    # ============================================================

    hist_query = """
    SELECT t.task_type,
           t.difficulty AS task_difficulty,
           t.estimated_time,
           m.likeness AS module_likeness,
           m.difficulty AS module_difficulty,
           m.catching_up,
           h.accepted,
           h.motivation,
           h.created_at
    FROM task_history h
    JOIN tasks t ON h.task_id = t.task_id
    JOIN modules m ON t.module_id = m.module_id
    WHERE h.accepted IS NOT NULL AND h.user_id = %s
    """
    hist_df = pd.read_sql(hist_query, conn, params=[user_id])
    hist_df["accepted"] = hist_df["accepted"].fillna(False).astype(int)

    if not hist_df.empty and hist_df["accepted"].nunique() > 1:

        # Recency weighting (recent actions matter more)
        hist_df["created_at"] = pd.to_datetime(hist_df["created_at"]).dt.tz_localize(None)
        now = datetime.now()
        days_diff = (now - hist_df["created_at"]).dt.days
        hist_df["recency_weight"] = np.exp(-days_diff / 7)

        # Encode task types
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

        # Align columns
        X_hist = X_hist.reindex(columns=X.columns, fill_value=0).fillna(0)

        # Train model
        model = make_pipeline(
            StandardScaler(),
            GradientBoostingClassifier()
        )

        model.fit(
            X_hist,
            hist_df["accepted"],
            gradientboostingclassifier__sample_weight=hist_df["recency_weight"]
        )

        # Predict acceptance probability
        df["ml_score"] = model.predict_proba(X)[:, 1]

    else:
        # Cold-start heuristic
        df["ml_score"] = (
            0.4 * df["module_likeness"] +
            0.3 * df["motivation"] -
            0.2 * df["task_difficulty"] -
            0.1 * (df["estimated_time"] / 60)
        )

    # ============================================================
    # 4. COLLABORATIVE FILTERING
    # ============================================================

    user_task_query = """
    SELECT user_id, task_id, accepted
    FROM task_history
    WHERE accepted IS NOT NULL
    """
    user_task_df = pd.read_sql(user_task_query, conn)

    df["cf_score"] = 0
    df["mf_score"] = 0  # Matrix factorisation score

    if not user_task_df.empty:

        user_task_matrix = user_task_df.pivot_table(
            index="user_id",
            columns="task_id",
            values="accepted",
            fill_value=0
        )

        if user_id in user_task_matrix.index:

            # ---------------------------
            # A. USER-BASED CF
            # ---------------------------
            similarity = cosine_similarity(user_task_matrix)

            similarity_df = pd.DataFrame(
                similarity,
                index=user_task_matrix.index,
                columns=user_task_matrix.index
            )

            user_sim = similarity_df.loc[user_id].drop(user_id)

            weighted_sum = user_sim.values @ user_task_matrix.loc[user_sim.index].values
            sim_sum = np.abs(user_sim.values).sum()

            if sim_sum > 0:
                cf_scores = weighted_sum / sim_sum
                cf_series = pd.Series(cf_scores, index=user_task_matrix.columns)
                df["cf_score"] = df["task_id"].map(cf_series).fillna(0)

            # ---------------------------
            # B. MATRIX FACTORISATION (SVD)
            # ---------------------------
            n_users, n_tasks = user_task_matrix.shape
            n_components = max(2, min(10, n_users, n_tasks) - 1)

            svd = TruncatedSVD(n_components=n_components, random_state=42)
            latent_matrix = svd.fit_transform(user_task_matrix)

            reconstructed = np.dot(latent_matrix, svd.components_)

            reconstructed_df = pd.DataFrame(
                reconstructed,
                index=user_task_matrix.index,
                columns=user_task_matrix.columns
            )

            user_predictions = reconstructed_df.loc[user_id]

            df["mf_score"] = df["task_id"].map(user_predictions).fillna(0)

    # ============================================================
    # 5. NORMALISATION
    # ============================================================
    def normalize(series):
        if series.std() == 0:
            return series
        return (series - series.mean()) / series.std()

    df["ml_score"] = normalize(df["ml_score"])
    df["cf_score"] = normalize(df["cf_score"])
    df["mf_score"] = normalize(df["mf_score"])

    # ============================================================
    # 6. HYBRID SCORING (ADAPTIVE)
    # ============================================================
    history_size = len(hist_df)

    if history_size < 10:
        ml_weight, cf_weight, mf_weight = 0.8, 0.1, 0.1
    else:
        ml_weight, cf_weight, mf_weight = 0.5, 0.2, 0.3

    df["score"] = (
        ml_weight * df["ml_score"] +
        cf_weight * df["cf_score"] +
        mf_weight * df["mf_score"]
    )

    # ============================================================
    # 7. EXPLORATION
    # ============================================================
    df["score"] += np.random.normal(0, 0.02, len(df))

    # ============================================================
    # 8. SORT AND RETURN
    # ============================================================
    df = df.sort_values(by="score", ascending=False)

    return df[[
        "task_id",
        "task_description",
        "task_type",
        "score"
    ]].to_dict(orient="records")