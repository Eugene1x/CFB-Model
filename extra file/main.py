import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb

# === Step 1: Load your CSV ===
df = pd.read_csv("base_games_with_underdogs.csv")
print(f"✅ Loaded {len(df)} rows")

# === Step 2: Basic preprocessing ===
# Convert neutral_site to int (True/False to 1/0)
df['neutral_site'] = df['neutral_site'].astype(int)

# Drop non-numeric identifiers (optional)
df = df.drop(columns=['home_team', 'away_team', 'favorite', 'underdog', 'winner', 'venue'])

# === Step 3: Define features and label ===
X = df.drop(columns=['underdog_win'])
y = df['underdog_win']

# === Step 4: Train/test split ===
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# === Step 5: Train XGBoost ===
model = xgb.XGBClassifier(
    use_label_encoder=False,
    eval_metric='logloss',
    random_state=42
)
model.fit(X_train, y_train)

# === Step 6: Evaluation ===
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]  # Probability of underdog win

print("=== Classification Report ===")
print(classification_report(y_test, y_pred))
print("ROC AUC Score:", roc_auc_score(y_test, y_proba))

# === Step 7: Save predictions (optional) ===
predictions_df = X_test.copy()
predictions_df['underdog_win_actual'] = y_test.values
predictions_df['underdog_win_proba'] = y_proba
predictions_df.to_csv("underdog_predictions.csv", index=False)
print("📄 Saved predictions to underdog_predictions.csv")

# === Step 8: Feature importance (optional) ===
import matplotlib.pyplot as plt

xgb.plot_importance(model, importance_type='gain')
plt.title("XGBoost Feature Importance")
plt.tight_layout()
plt.show()
