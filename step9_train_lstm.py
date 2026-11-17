import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import glob

all_files = glob.glob("features_region_*.csv")
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

# ארגון מחדש של הנתונים כרצף כרונולוגי
sequence_features = []
for d in DATES:
    sequence_features.extend([
        f"ndvi_{d}", 
        f"ndwi_{d}", 
        f"rain_14d_{d}", 
        f"temp_14d_{d}"
    ])
    
target = "is_maize"

X = df[sequence_features].values
y = df[target].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

class TimeSeriesCropDataset(Dataset):
    def __init__(self, features, labels):
        # המרת הוקטור השטוח למטריצה תלת ממדית: דוגמאות, צעדי זמן, מאפיינים לכל צעד
        self.X = torch.tensor(features, dtype=torch.float32).view(-1, len(DATES), 4)
        self.y = torch.tensor(labels, dtype=torch.float32).unsqueeze(1)
        
    def __len__(self):
        return len(self.y)
        
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

train_loader = DataLoader(TimeSeriesCropDataset(X_train, y_train), batch_size=32, shuffle=True)
test_loader = DataLoader(TimeSeriesCropDataset(X_test, y_test), batch_size=32, shuffle=False)

class CropLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.3)
        self.fc1 = nn.Linear(hidden_size, 16)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(16, 1)
        
    def forward(self, x):
        out, _ = self.lstm(x)
        # שליפת המצב הפנימי של הרשת רק בצעד הזמן האחרון של העונה
        out = out[:, -1, :] 
        out = self.dropout(self.relu(self.fc1(out)))
        out = self.fc2(out)
        return out

# ארבעה מאפיינים בכל תאריך שעוברים עיבוד על פני שתי שכבות
model = CropLSTM(input_size=4, hidden_size=32, num_layers=2)

num_neg = (y_train == 0).sum()
num_pos = (y_train == 1).sum()
pos_weight_val = torch.tensor([num_neg / num_pos], dtype=torch.float32)

criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight_val)
optimizer = optim.Adam(model.parameters(), lr=0.001)

epochs = 50
print(f"Training LSTM Model on temporal sequences...")
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

print("\n--- Final Model Evaluation (LSTM) ---")
cm = confusion_matrix(y_test, y_pred_np)
print("Confusion Matrix:")
print(f"Actual Other (0): {cm[0][0]:<19} | {cm[0][1]}")
print(f"Actual Maize (1): {cm[1][0]:<19} | {cm[1][1]}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred_np, target_names=["Other Crops (0)", "Maize (1)"]))