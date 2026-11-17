import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import glob

all_files = glob.glob("features_region_*.csv")
if not all_files:
    print("Error: No feature CSV files found in the current directory.")
    exit()

df_list = [pd.read_csv(f) for f in all_files]
df = pd.concat(df_list, ignore_index=True)

DATES = [
    "20190606", "20190701", "20190706", "20190711", "20190721",
    "20190805", "20190815", "20190825", "20190909", "20190919",
    "20190924", "20191004", "20191103"
]

features = [f"ndvi_{d}" for d in DATES] + [f"ndwi_{d}" for d in DATES]
target = "is_maize"

X = df[features]
y = df[target]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print(f"--- Dataset Summary (Random Split with Time-Series) ---")
print(f"Total parcels: {len(df)}")
print(f"Training on {len(X_train)} parcels using {len(features)} temporal features")

rf_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
print("\nTraining Random Forest model...")
rf_model.fit(X_train, y_train)

# Extract the probability of the positive class (Maize)
y_probs = rf_model.predict_proba(X_test)[:, 1]

# Lower the decision threshold from 0.50 to 0.30
y_pred = (y_probs > 0.30).astype(int)

print("\nConfusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(f"Actual Other (0): {cm[0][0]:<19} | {cm[0][1]}")
print(f"Actual Maize (1): {cm[1][0]:<19} | {cm[1][1]}")

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["Other Crops (0)", "Maize (1)"]))