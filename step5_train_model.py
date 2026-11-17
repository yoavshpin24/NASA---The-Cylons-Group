import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import glob

all_files = glob.glob("features_region_*.csv")
df_list = [pd.read_csv(f) for f in all_files]
df = pd.concat(df_list, ignore_index=True)

train_df = df[df['split'] == 'train']
test_df = df[df['split'] == 'test']

features = ["max_ndvi", "min_ndvi", "ndvi_amplitude", "mean_ndvi", "mean_ndwi", "peak_ndvi_month"]
target = "is_maize"

X_train = train_df[features]
y_train = train_df[target]
X_test = test_df[features]
y_test = test_df[target]

rf_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
rf_model.fit(X_train, y_train)

y_pred = rf_model.predict(X_test)

print("\nConfusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(f"Actual Other (0): {cm[0][0]:<19} | {cm[0][1]}")
print(f"Actual Maize (1): {cm[1][0]:<19} | {cm[1][1]}")

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["Other Crops (0)", "Maize (1)"]))

print("\nFeature Importances:")
importances = rf_model.feature_importances_
for name, imp in sorted(zip(features, importances), key=lambda x: x[1], reverse=True):
    print(f" - {name}: {imp:.4f}")