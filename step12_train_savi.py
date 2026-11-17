import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import glob

all_files = glob.glob("features_savi_region_*.csv")
if not all_files:
    print("Error: SAVI CSV files not found.")
    exit()

df = pd.concat([pd.read_csv(f) for f in all_files], ignore_index=True)

DATES = [
    "20190606", "20190701", "20190706", "20190711", "20190721",
    "20190805", "20190815", "20190825", "20190909", "20190919",
    "20190924", "20191004", "20191103"
]

nasa_df = pd.read_csv("nasa_climate_kenya_2019.csv")
nasa_df['datetime'] = pd.to_datetime(nasa_df['date'], format='%Y%m%d')
nasa_df.set_index('datetime', inplace=True)

climate_features = {}
for d in DATES:
    dt = pd.to_datetime(d, format='%Y%m%d')
    start_dt = dt - pd.Timedelta(days=14)
    window = nasa_df.loc[start_dt:dt]
    climate_features[f"rain_14d_{d}"] = window['precipitation_mm'].sum()
    climate_features[f"temp_14d_{d}"] = window['temperature_c'].mean()

for col, val in climate_features.items():
    df[col] = val

sat_features = [f"savi_{d}" for d in DATES] + [f"ndwi_{d}" for d in DATES]
clim_features = list(climate_features.keys())
features = sat_features + clim_features
target = "is_maize"

X = df[features].values
y = df[target].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

class CropDataset(Dataset):
    def __init__(self, features, labels):
        self.X = torch.tensor(features, dtype=torch.float32)
        self.y = torch.tensor(labels, dtype=torch.float32).unsqueeze(1)
        
    def __len__(self):
        return len(self.y)
        
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

train_loader = DataLoader(CropDataset(X_train, y_train), batch_size=32, shuffle=True)
test_loader = DataLoader(CropDataset(X_test, y_test), batch_size=32, shuffle=False)

class CropNet(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 1)
        )
        
    def forward(self, x):
        return self.network(x)

class BinaryFocalLoss(nn.Module):
    def __init__(self, alpha=0.5, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        
    def forward(self, inputs, targets):
        bce_loss = F.binary_cross_entropy_with_logits(inputs, targets, reduction='none')
        probs = torch.sigmoid(inputs)
        pt = torch.where(targets == 1, probs, 1 - probs)
        alpha_weight = torch.where(targets == 1, self.alpha, 1 - self.alpha)
        focal_loss = alpha_weight * (1 - pt) ** self.gamma * bce_loss
        return focal_loss.mean()

model = CropNet(input_dim=len(features))

num_neg = (y_train == 0).sum()
num_pos = (y_train == 1).sum()
dynamic_alpha = num_neg / (num_pos + num_neg)

criterion = BinaryFocalLoss(alpha=dynamic_alpha, gamma=2.0)
optimizer = optim.Adam(model.parameters(), lr=0.001)

epochs = 60
print("Training PyTorch Model with SAVI & Focal Loss...")
for epoch in range(epochs):
    model.train()
    for batch_X, batch_y in train_loader:
        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()

model.eval()
y_pred_list = []
with torch.no_grad():
    for batch_X, _ in test_loader:
        logits = model(batch_X)
        probs = torch.sigmoid(logits)
        preds = (probs > 0.5).int()
        y_pred_list.extend(preds.numpy())

y_pred_np = np.array(y_pred_list).flatten()

print("\n--- Final Model Evaluation (SAVI + Focal Loss) ---")
cm = confusion_matrix(y_test, y_pred_np)
print("Confusion Matrix:")
print(f"Actual Other (0): {cm[0][0]:<19} | {cm[0][1]}")
print(f"Actual Maize (1): {cm[1][0]:<19} | {cm[1][1]}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred_np, target_names=["Other Crops (0)", "Maize (1)"]))