import pandas as pd
import numpy as np
import ast
from sklearn.model_selection import train_test_split
from lightgbm import LGBMRanker
from sklearn.metrics import precision_score
import os
import joblib
from datetime import datetime

# ------------------------
# 1. Load and clean data
# ------------------------

# Load input CSVs
exec_roles = pd.read_csv("exec_roles.csv")  # Executive attributes
match = pd.read_csv("match.csv")            # Matches between execs and opportunities
opp = pd.read_csv("opp.csv")                # Opportunities

# Ensure key IDs are properly typed
match["assignment_id"] = match["assignment_id"].astype("Int64")
match["exec_entity_id"] = match["exec_entity_id"].astype("Int64")
opp["assignment_id"] = opp["assignment_id"].astype("Int64")

# Pivot exec_roles to a wide format: one row per exec with structured features
exec_roles_wide = exec_roles.pivot_table(
    index="exec_entity_id", 
    columns="type", 
    values=["json_value", "string_value"], 
    aggfunc="first"
)
exec_roles_wide.columns = [f"{a}_{b}" for a, b in exec_roles_wide.columns]
exec_roles_wide = exec_roles_wide.reset_index()
exec_roles_wide = exec_roles_wide.dropna(subset=["exec_entity_id"])
exec_roles_wide["exec_entity_id"] = exec_roles_wide["exec_entity_id"].astype("Int64")

# Merge matches with opportunities and exec features
match_opp = pd.merge(match, opp, on="assignment_id", how="left")
data = pd.merge(match_opp, exec_roles_wide, on="exec_entity_id", how="left")


# ------------------------
# 2. Feature Engineering
# ------------------------

def jaccard_sim(list1, list2):
    """
    Compute Jaccard similarity between two stringified lists.
    Used for comparing sectors, sub-sectors, and industries.
    """
    if pd.isna(list1) or pd.isna(list2):
        return 0
    try:
        set1 = set(ast.literal_eval(list1))
        set2 = set(ast.literal_eval(list2))
        return len(set1 & set2) / len(set1 | set2) if (set1 | set2) else 0
    except:
        return 0

def build_features(df):
    """
    Generate binary and similarity-based features for each exec-opportunity pair.
    """
    df["sector_match"] = (df["json_value_sectors"] == df["sectors"]).astype(int)
    df["country_match"] = (df["string_value_hq_address"] == df["country"]).astype(int)
    df["scale_match"] = (df["string_value_scale"] == df["scale"]).astype(int)
    df["sector_jaccard"] = df.apply(lambda r: jaccard_sim(r.get("json_value_sectors"), r.get("sectors")), axis=1)
    df["sub_sector_jaccard"] = df.apply(lambda r: jaccard_sim(r.get("json_value_sub_sectors"), r.get("sub_sectors")), axis=1)
    df["industry_jaccard"] = df.apply(lambda r: jaccard_sim(r.get("json_value_industry"), r.get("industry")), axis=1)
    return df

# Build feature columns
data = build_features(data)


# ------------------------
# 3. Prepare for ranking
# ------------------------

# Define features to use for ranking
features = [
    "sector_match", "country_match", "scale_match",
    "sector_jaccard", "sub_sector_jaccard", "industry_jaccard"
]

# Drop rows with missing critical fields
data = data.dropna(subset=features + ["outcome", "assignment_id"])
data["outcome"] = data["outcome"].astype(int)

# Keep only assignment_ids with at least one successful match
valid_assignments = data.groupby("assignment_id")["outcome"].sum()
valid_assignments = valid_assignments[valid_assignments > 0].index.tolist()
data = data[data["assignment_id"].isin(valid_assignments)]

# Create holdout test set from a sample of assignment_ids
assignment_ids = data["assignment_id"].unique()
test_ids = np.random.choice(assignment_ids, size=max(3, int(0.1 * len(assignment_ids))), replace=False)
train_ids = [aid for aid in assignment_ids if aid not in test_ids]

# Split the data
train_df = data[data["assignment_id"].isin(train_ids)].copy()
test_df = data[data["assignment_id"].isin(test_ids)].copy()

# Prepare data for LightGBM ranker
X_train = train_df[features]
y_train = train_df["outcome"]
group_train = train_df.groupby("assignment_id").size().values  # Number of items per group

X_test = test_df[features]
y_test = test_df["outcome"]
group_test = test_df.groupby("assignment_id").size().values


# ------------------------
# 4. Train LightGBM Ranker
# ------------------------

ranker = LGBMRanker(
    n_estimators=100,
    random_state=42,
    verbosity=-1,  # Suppresses most warnings
    force_col_wise=True  # Removes overhead message
)

ranker.fit(X_train, y_train, group=group_train)


# ------------------------
# 5. Evaluate Precision@5
# ------------------------

# Predict relevance scores for test set
test_df["score"] = ranker.predict(X_test)

# Get top 5 predictions per assignment_id
top_k = (
    test_df.groupby("assignment_id", group_keys=False)
    .apply(lambda g: g.sort_values("score", ascending=False).head(5))
    .reset_index(drop=True)
)

# Calculate average precision@5: proportion of groups where at least 1 top-5 item is a correct match
precision_at_5 = top_k.groupby("assignment_id")["outcome"].max().mean()
print(f"\nPrecision@5: {precision_at_5:.3f}")


# ------------------------
# 6. Predict top execs for new opportunity
# ------------------------

def rank_execs_for_new_opp(new_opp_row, exec_table, model, features):
    """
    Generate a ranked list of top executives for a given opportunity.

    Parameters:
        new_opp_row (Series): A single opportunity row.
        exec_table (DataFrame): Wide-format executive features.
        model: Trained ranking model.
        features (list): List of feature column names.

    Returns:
        DataFrame: Top 10 exec_entity_ids with predicted scores.
    """
    rows = []

    # For each exec, combine with new opportunity fields
    for _, exec_row in exec_table.iterrows():
        combined = new_opp_row.copy()
        for col in exec_row.index:
            combined[f"exec_{col}"] = exec_row[col]

        # Manually add needed fields
        combined["json_value_sectors"] = exec_row.get("json_value_sectors")
        combined["json_value_sub_sectors"] = exec_row.get("json_value_sub_sectors")
        combined["json_value_industry"] = exec_row.get("json_value_industry")
        combined["string_value_hq_address"] = exec_row.get("string_value_hq_address")
        combined["string_value_scale"] = exec_row.get("string_value_scale")
        combined["exec_entity_id"] = exec_row.get("exec_entity_id")
        rows.append(combined)

    # Build feature matrix and predict scores
    pred_df = pd.DataFrame(rows)
    pred_df = build_features(pred_df)
    pred_df["score"] = model.predict(pred_df[features])

    return pred_df[["exec_entity_id", "score"]].sort_values("score", ascending=False).head(10)

# Save model
os.makedirs("models", exist_ok=True)
joblib.dump(ranker, "models/lgbm_ranker.pkl")

# Log precision@5
os.makedirs("logs", exist_ok=True)
log_path = "logs/precision_log.csv"
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Append to CSV
log_entry = pd.DataFrame([[now, precision_at_5]], columns=["timestamp", "precision_at_5"])
if os.path.exists(log_path):
    log_entry.to_csv(log_path, mode="a", header=False, index=False)
else:
    log_entry.to_csv(log_path, index=False)

print(f"Model saved to models/lgbm_ranker.pkl")
print(f"Logged precision@5 to {log_path}")
