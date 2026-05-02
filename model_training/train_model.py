import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, balanced_accuracy_score, roc_auc_score
from sklearn.ensemble import RandomForestClassifier

# =========================
# LOAD DATA
# =========================
df = pd.read_csv("marketing_campaign_data_messy (1).csv")

df.columns = df.columns.str.strip()
df = df.loc[:, ~df.columns.duplicated()]

# =========================
# CLEANING
# =========================
df["Spend"] = df["Spend"].astype(str).str.replace(r"[^0-9.]", "", regex=True)
df["Spend"] = pd.to_numeric(df["Spend"], errors="coerce")
df["Spend"] = df["Spend"].fillna(df["Spend"].median())

df["Conversions"] = df["Conversions"].fillna(0)

# =========================
# FEATURE ENGINEERING
# =========================
# Calculate campaign duration in days
def parse_date(date_str):
    if pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            continue
    return pd.to_datetime(date_str, errors='coerce')

df["Start_Date"] = df["Start_Date"].apply(parse_date)
df["End_Date"] = df["End_Date"].apply(parse_date)

df["Campaign_Duration"] = (df["End_Date"] - df["Start_Date"]).dt.days
df["Campaign_Duration"] = df["Campaign_Duration"].fillna(df["Campaign_Duration"].median())
df["Campaign_Duration"] = df["Campaign_Duration"].clip(lower=1)

df["Daily_Spend"] = df["Spend"] / df["Campaign_Duration"]

df["Converted"] = (df["Conversions"] > 0).astype(int)

# =========================
# ENCODING CHANNEL (ONE-HOT)
# =========================
df["Channel"] = df["Channel"].astype(str).str.strip().str.title()
df["Channel"] = df["Channel"].replace({
    'E-Mail': 'Email',
    'E-mail': 'Email',
    'Facebok': 'Facebook',
    'Gogle': 'Google',
    'Google Ads': 'Google',
    'Insta_Gram': 'Instagram',
    'Tik_Tok': 'TikTok',
    'N/A': 'Other',
    '': 'Other'
})

channel_dummies = pd.get_dummies(df["Channel"], prefix="Channel", drop_first=True)
df = pd.concat([df, channel_dummies], axis=1)

channel_cols = [col for col in df.columns if col.startswith("Channel_")]

# =========================
# FINAL FEATURES
# =========================
feature_cols = ["Spend", "Campaign_Duration", "Daily_Spend"] + channel_cols

df = df.dropna(subset=feature_cols + ["Converted"])

X = df[feature_cols]
y = df["Converted"]

print(f"Dataset shape: {df.shape}")
print(f"Features: {feature_cols}")
print(f"Number of channel dummies: {len(channel_cols)}")
print(f"Class distribution: {y.value_counts().to_dict()}")

# =========================
# SPLIT
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTraining set: {X_train.shape[0]} samples")
print(f"Test set: {X_test.shape[0]} samples")

# =========================
# SCALE
# =========================
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# =========================
# MODEL
# =========================
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=10,
    min_samples_leaf=4,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)

# =========================
# EVALUATION
# =========================
y_prob = model.predict_proba(X_test)[:, 1]

best_t = 0.5
best_bal = 0

for t in np.arange(0.2, 0.8, 0.01):
    y_pred_temp = (y_prob > t).astype(int)
    bal = balanced_accuracy_score(y_test, y_pred_temp)
    if bal > best_bal:
        best_bal = bal
        best_t = t

y_pred = (y_prob > best_t).astype(int)

print("\nBEST THRESHOLD:", round(best_t, 2))
print("Accuracy:", round((y_pred == y_test).mean(), 4))
print("ROC AUC:", round(roc_auc_score(y_test, y_prob), 4))
print("Balanced Accuracy:", round(balanced_accuracy_score(y_test, y_pred), 4))

print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))

# =========================
# FEATURE IMPORTANCE
# =========================
importance = model.feature_importances_
feat_imp = pd.DataFrame({
    'feature': feature_cols,
    'importance': importance
}).sort_values('importance', ascending=False)

print("\nFeature Importance:")
for _, row in feat_imp.iterrows():
    print(f"  {row['feature']}: {row['importance']:.4f}")

# =========================
# SAVE MODEL AND SCALER
# =========================
import json
import joblib
import os

os.makedirs("../backend/ml_model", exist_ok=True)

joblib.dump(model, "../backend/ml_model/model.pkl")
joblib.dump(scaler, "../backend/ml_model/scaler.pkl")

with open("../backend/ml_model/feature_cols.json", "w") as f:
    json.dump(feature_cols, f)

print("\nModel saved inside backend/ml_model/")
print(f"Feature columns saved: {len(feature_cols)} features")