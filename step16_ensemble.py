import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import glob

# 1. טעינת נתוני הראייה (תמונות הלוויין) כולל מספרי הזיהוי של השדות
npz_files = glob.glob("patches_region_*.npz")
X_img_list, y_list, fid_list = [], [], []

for f in npz_files:
    data = np.load(f)
    X_img_list.append(data['X'])
    y_list.append(data['y'])
    fid_list.append(data['field_ids'])

X_img = np.concatenate(X_img_list, axis=0)
y = np.concatenate(y_list, axis=0)
fids_img = np.concatenate(fid_list, axis=0)

X_img = X_img.astype(np.float32) / 10000.0
X_img = np.transpose(X_img, (0, 2, 1, 3, 4))

for c in range(X_img.shape[1]):
    mean_val = np.mean(X_img[:, c, :, :, :])
    std_val = np.std(X_img[:, c, :, :, :])
    X_img[:, c, :, :, :] = (X_img[:, c, :, :, :] - mean_val) / (std_val + 1e-8)

# 2. טעינת הנתונים הטבלאיים וסינכרון מוחלט מול התמונות
csv_files = glob.glob("features_region_*.csv")
if not csv_files:
    # גיבוי למקרה שהשתמשנו בקבצי המדד המתוקן
    csv_files = glob.glob("features_savi_region_*.csv")
    
df = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)

DATES = ["20190606", "20190701", "20190706", "20190711", "20190721",
         "20190805", "20190815", "20190825", "20190909", "20190919",
         "20190924", "20191004", "20191103"]

nasa_df = pd.read_csv("nasa_climate_kenya_2019.csv")
nasa_df['datetime'] = pd.to_datetime(nasa_df['date'], format='%Y%m%d')
nasa_df.set_index('datetime', inplace=True)

climate_features = {}
for d in DATES:
    dt = pd.to_datetime(d, format='%Y%m%d')
    window = nasa_df.loc[dt - pd.Timedelta(days=14):dt]
    climate_features[f"rain_{d}"] = window['precipitation_mm'].sum()
    climate_features[f"temp_{d}"] = window['temperature_c'].mean()

for col, val in climate_features.items():
    df[col] = val

# חילוץ העמודות הרלוונטיות בהתאם לסוג הקובץ שנמצא
sat_cols = [c for c in df.columns if "ndvi" in c or "ndwi" in c or "savi" in c]
clim_cols = list(climate_features.keys())
tab_features = sat_cols + clim_cols

# סידור הטבלה בדיוק לפי סדר השדות שהגיעו מקבצי התמונות
df_indexed = df.set_index("field_id")
X_tab = df_indexed.loc[fids_img][tab_features].values

scaler = StandardScaler()
X_tab = scaler.fit_transform(X_tab)

# 3. פיצול אחיד לשני המודלים כדי להבטיח הערכה הוגנת
X_img_train, X_img_test, X_tab_train, X_tab_test, y_train, y_test = train_test_split(
    X_img, X_tab, y, test_size=0.2, random_state=42, stratify=y
)

# דוגם ממושקל למניעת קריסת מצב
class_counts = np.bincount(y_train.astype(int))
class_weights = 1.0 / class_counts
sample_weights = np.array([class_weights[int(label)] for label in y_train])
sampler = WeightedRandomSampler(weights=torch.from_numpy(sample_weights).double(), num_samples=len(sample_weights), replacement=True)

class EnsembleDataset(Dataset):
    def __init__(self, img_feat, tab_feat, labels):
        self.img = torch.tensor(img_feat)
        self.tab = torch.tensor(tab_feat, dtype=torch.float32)
        self.y = torch.tensor(labels, dtype=torch.float32).unsqueeze(1)
        
    def __len__(self):
        return len(self.y)
        
    def __getitem__(self, idx):
        return self.img[idx], self.tab[idx], self.y[idx]

train_loader = DataLoader(EnsembleDataset(X_img_train, X_tab_train, y_train), batch_size=32, sampler=sampler)
test_loader = DataLoader(EnsembleDataset(X_img_test, X_tab_test, y_test), batch_size=32, shuffle=False)

# 4. הגדרת הארכיטקטורות הנפרדות
class TabularNet(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.3),
            nn.Linear(32, 1)
        )
    def forward(self, x): return self.net(x)

class CNN3DNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv3d(3, 16, kernel_size=(3, 3, 3), padding=1)
        self.bn1 = nn.BatchNorm3d(16)
        self.relu = nn.LeakyReLU(0.1)
        self.pool = nn.MaxPool3d((2, 2, 2))
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(16 * 6 * 2 * 2, 64)
        self.bn2 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(0.4)
        self.fc2 = nn.Linear(64, 1)
    def forward(self, x):
        x = self.pool(self.relu(self.bn1(self.conv1(x))))
        x = self.relu(self.bn2(self.fc1(self.flatten(x))))
        return self.fc2(self.dropout(x))

model_tab = TabularNet(X_tab.shape[1])
model_cnn = CNN3DNet()

criterion = nn.BCEWithLogitsLoss()
opt_tab = optim.Adam(model_tab.parameters(), lr=0.001)
opt_cnn = optim.Adam(model_cnn.parameters(), lr=0.0001)

# 5. אימון מקביל של שתי הרשתות
epochs = 35
print("Training Tabular and CNN Models for Ensemble...")
for epoch in range(epochs):
    model_tab.train()
    model_cnn.train()
    for b_img, b_tab, b_y in train_loader:
        # אימון מודל טבלאי
        opt_tab.zero_grad()
        out_tab = model_tab(b_tab)
        loss_tab = criterion(out_tab, b_y)
        loss_tab.backward()
        opt_tab.step()
        
        # אימון מודל קונבולוציה
        opt_cnn.zero_grad()
        out_cnn = model_cnn(b_img)
        loss_cnn = criterion(out_cnn, b_y)
        loss_cnn.backward()
        opt_cnn.step()

# 6. הצבעה רכה (Soft Voting) ושקלול התוצאות
model_tab.eval()
model_cnn.eval()

y_pred_list = []
with torch.no_grad():
    for b_img, b_tab, _ in test_loader:
        # חילוץ הסתברויות מכל מודל בנפרד
        probs_tab = torch.sigmoid(model_tab(b_tab))
        probs_cnn = torch.sigmoid(model_cnn(b_img))
        
        # מתן משקל של 60% למודל הטבלאי (עבור רגישות) ו-40% לקונבולוציה (עבור דיוק)
        ensemble_probs = (0.6 * probs_tab) + (0.4 * probs_cnn)
        
        preds = (ensemble_probs > 0.5).int()
        y_pred_list.extend(preds.numpy())

y_pred_np = np.array(y_pred_list).flatten()

print("\n--- Final Ensemble Model Evaluation ---")
cm = confusion_matrix(y_test, y_pred_np)
print("Confusion Matrix:")
print(f"Actual Other (0): {cm[0][0]:<19} | {cm[0][1]}")
print(f"Actual Maize (1): {cm[1][0]:<19} | {cm[1][1]}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred_np, target_names=["Other Crops (0)", "Maize (1)"]))