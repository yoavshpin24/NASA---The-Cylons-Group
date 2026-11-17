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

# 1. Load data
all_files = glob.glob("features_region_*.csv")
if not all_files:
    print("Error: No feature CSV files found in the current directory.")
    exit()

df = pd.concat([pd.read_csv(f) for f in all_files], ignore_index=True)

DATES = [
    "20190606", "20190701", "20190706", "20190711", "20190721",
    "20190805", "20190815", "20190825", "20190909", "20190919",
    "20190924", "20191004", "20191103"
]

features = [f"ndvi_{d}" for d in DATES] + [f"ndwi_{d}" for d in DATES]
target = "is_maize"

X = df[features].values
y = df[target].values

# 2. Split and Scale
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# 3. PyTorch Dataset Configuration
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

# 4. Neural Network Architecture
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

model = CropNet(input_dim=len(features))

# 5. Handle Imbalance with Weighted Loss
num_neg = (y_train == 0).sum()
num_pos = (y_train == 1).sum()
pos_weight_val = torch.tensor([num_neg / num_pos], dtype=torch.float32)

criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight_val)
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 6. Training Loop
epochs = 50
print(f"Training Deep Learning Model for {epochs} epochs...")
for epoch in range(epochs):
    model.train()
    total_loss = 0
    for batch_X, batch_y in train_loader:
        optimizer.zero_grad()
        outputs = model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        
    if (epoch + 1) % 10 == 0:
        print(f"Epoch {epoch + 1}/{epochs}, Loss: {total_loss / len(train_loader):.4f}")

# 7. Evaluation
model.eval()
y_pred_list = []
with torch.no_grad():
    for batch_X, _ in test_loader:
        logits = model(batch_X)
        probs = torch.sigmoid(logits)
        # Using 0.5 threshold because the weighted loss already shifted the decision boundary naturally
        preds = (probs > 0.5).int()
        y_pred_list.extend(preds.numpy())

y_pred_np = np.array(y_pred_list).flatten()

print("\n--- Model Evaluation (PyTorch Neural Network) ---")
cm = confusion_matrix(y_test, y_pred_np)
print("Confusion Matrix:")
print(f"Actual Other (0): {cm[0][0]:<19} | {cm[0][1]}")
print(f"Actual Maize (1): {cm[1][0]:<19} | {cm[1][1]}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred_np, target_names=["Other Crops (0)", "Maize (1)"]))