import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD


def recommend_tasks(conn, user_id, motivation=2.5):

    # ============================================================
    # 1. FETCH TASK DATA
    # ============================================================
    query = """
    SELECT t.task_id, t.task_type, t.task_description,
           t.difficulty AS task_difficulty,
           t.estimated_time,
           m.name AS module_name,
           m.likeness AS module_likeness,
           m.difficulty AS module_difficulty
    FROM tasks t
    JOIN modules m ON t.module_id = m.module_id
    WHERE t.active = TRUE AND t.user_id = %s
    """
    df = pd.read_sql(query, conn, params=[user_id])

    if df.empty:
        return []

    # ============================================================
    # 2. FEATURE ENGINEERING
    # ============================================================

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
            "motivation",
            "time_sin",
            "time_cos"
        ]],
        task_types
    ], axis=1).fillna(0)

    # ============================================================
    # 3. MACHINE LEARNING
    # ============================================================

    hist_query = """
    SELECT t.task_type,
           t.difficulty AS task_difficulty,
           t.estimated_time,
           t.module_id,
           
           m.likeness AS module_likeness,
           m.difficulty AS module_difficulty,
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

    if len(hist_df) >= 5 and hist_df["accepted"].nunique() > 1:

        # -------------------------
        # TRAIN ML MODEL
        # -------------------------
        model = make_pipeline(
            StandardScaler(),
            GradientBoostingClassifier()
        )

        model.fit(
            X_hist,
            hist_df["accepted"],
            gradientboostingclassifier__sample_weight=hist_df["recency_weight"]
        )

        df["ml_score"] = model.predict_proba(X)[:, 1]

    else:

        # ============================================================
        # ✅ IMPROVED COLD START (PUT IT HERE)
        # ============================================================

        df["norm_time"] = df["estimated_time"] / df["estimated_time"].max()

        df["difficulty_match"] = 1 - abs(df["task_difficulty"] - df["motivation"]) / 5

        df["base_score"] = (
            0.35 * df["module_likeness"] +
            0.25 * df["difficulty_match"] +
            0.15 * df["motivation"] -
            0.15 * df["norm_time"]
        )

        type_weights = {
            "Lecture": 0.2,
            "Reading": 0.3,
            "Practice": 0.5,
        }

        df["type_score"] = df["task_type"].map(type_weights).fillna(0.3)

        df["exploration"] = np.random.uniform(0, 0.1, len(df))

        df["ml_score"] = (
            df["base_score"] +
            df["type_score"] +
            df["exploration"]
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
    df["mf_score"] = 0

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

            user_sim = similarity_df.loc[user_id].drop(user_id)

            weighted_sum = user_sim.values @ user_task_matrix.loc[user_sim.index].values
            sim_sum = np.abs(user_sim.values).sum()

            if sim_sum > 0:
                cf_scores = weighted_sum / sim_sum
                cf_series = pd.Series(cf_scores, index=user_task_matrix.columns)
                df["cf_score"] = df["task_id"].map(cf_series).fillna(0)

            n_users, n_tasks = user_task_matrix.shape

        # 🚨 SAFETY CHECK
        if n_users < 2 or n_tasks < 2:
            # Not enough data for SVD
            df["mf_score"] = 0
        else:
            n_components = min(10, n_users, n_tasks) - 1

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
        series = series.fillna(0)
        std = series.std()

        if std == 0 or np.isnan(std):
            return series * 0
        return (series - series.mean()) / std

    df["ml_score"] = normalize(df["ml_score"])
    df["cf_score"] = normalize(df["cf_score"])
    df["mf_score"] = normalize(df["mf_score"])

    # ============================================================
    # 6. REJECTION PRIORITISATION (NEW FEATURE)
    # ============================================================

    rejection_counts = user_task_df.groupby("task_id")["accepted"].apply(
        lambda x: (x == 0).sum()
    )

    df["rejection_count"] = df["task_id"].map(rejection_counts).fillna(0)

    # Smooth boost (recommended)
    df["rejection_boost"] = 0.2 * (1 - np.exp(-df["rejection_count"] / 5))

    # ============================================================
    # 7. HYBRID SCORING
    # ============================================================

    history_size = len(hist_df)

    if history_size < 10:
        ml_weight, cf_weight, mf_weight = 0.8, 0.1, 0.1
    else:
        ml_weight, cf_weight, mf_weight = 0.5, 0.2, 0.3

    df["score"] = (
        ml_weight * df["ml_score"] +
        cf_weight * df["cf_score"] +
        mf_weight * df["mf_score"] +
        df["rejection_boost"]
    )

    # ============================================================
    # 8. EXPLORATION
    # ============================================================
    df[["ml_score", "cf_score", "mf_score", "rejection_boost"]] = df[
        ["ml_score", "cf_score", "mf_score", "rejection_boost"]
    ].fillna(0)
    
    df["score"] = (
    ml_weight * df["ml_score"].fillna(0) +
    cf_weight * df["cf_score"].fillna(0) +
    mf_weight * df["mf_score"].fillna(0) +
    df["rejection_boost"].fillna(0)
)

    # ============================================================
    # 9. SORT AND RETURN
    # ============================================================

    df = df.sort_values(by="score", ascending=False)
    df["rank"] = np.arange(1, len(df) + 1)

    

    return df[[
        "task_id",
        "task_description",
        "module_name",
        "task_type",
        "score",
        "rank"
    ]].to_dict(orient="records")