import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import glob

# 1. טעינת הקבצים הדחוסים
all_files = glob.glob("patches_region_*.npz")
if not all_files:
    print("Error: No .npz files found in the current directory.")
    exit()

X_list = []
y_list = []

for f in all_files:
    data = np.load(f)
    X_list.append(data['X'])
    y_list.append(data['y'])

X = np.concatenate(X_list, axis=0)
y = np.concatenate(y_list, axis=0)

# נרמול עוצמות ההחזר
X = X.astype(np.float32) / 10000.0

# סידור הממדים: (דוגמאות, ערוצים, זמן, גובה, רוחב)
X = np.transpose(X, (0, 2, 1, 3, 4))

# התיקון הקריטי מס' 1: נרמול מתקדם לפי ערוצים (Z-Score)
for c in range(X.shape[1]):
    mean_val = np.mean(X[:, c, :, :, :])
    std_val = np.std(X[:, c, :, :, :])
    X[:, c, :, :, :] = (X[:, c, :, :, :] - mean_val) / (std_val + 1e-8)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# חישוב משקלי דגימה
class_counts = np.bincount(y_train.astype(int))
class_weights = 1.0 / class_counts
sample_weights = np.array([class_weights[int(label)] for label in y_train])
sampler = WeightedRandomSampler(weights=torch.from_numpy(sample_weights).double(), num_samples=len(sample_weights), replacement=True)

class SpatialCropDataset(Dataset):
    def __init__(self, features, labels):
        self.X = torch.tensor(features)
        self.y = torch.tensor(labels, dtype=torch.float32).unsqueeze(1)
        
    def __len__(self):
        return len(self.y)
        
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

train_loader = DataLoader(SpatialCropDataset(X_train, y_train), batch_size=32, sampler=sampler)
test_loader = DataLoader(SpatialCropDataset(X_test, y_test), batch_size=32, shuffle=False)

# 2. הארכיטקטורה המעודכנת
class Crop3DCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv3d(in_channels=3, out_channels=16, kernel_size=(3, 3, 3), padding=1)
        self.bn1 = nn.BatchNorm3d(16)
        # התיקון הקריטי מס' 2: החלפה לפונקציה שמונעת תמותת נוירונים
        self.relu = nn.LeakyReLU(0.1)
        self.pool = nn.MaxPool3d(kernel_size=(2, 2, 2))
        
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(16 * 6 * 2 * 2, 64)
        self.bn2 = nn.BatchNorm1d(64)
        self.dropout = nn.Dropout(0.4)
        self.fc2 = nn.Linear(64, 1)
        
    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.pool(x)
        x = self.flatten(x)
        x = self.fc1(x)
        x = self.bn2(x)
        x = self.relu(x)
        x = self.dropout(x)
        return self.fc2(x)

model = Crop3DCNN()
criterion = nn.BCEWithLogitsLoss()

# התיקון הקריטי מס' 3: חיתוך קצב הלמידה
optimizer = optim.Adam(model.parameters(), lr=0.0001)

epochs = 40
print(f"Training 3D-CNN Model with LeakyReLU and Z-Score Normalization...")
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

model.eval()
y_pred_list = []
with torch.no_grad():
    for batch_X, _ in test_loader:
        logits = model(batch_X)
        probs = torch.sigmoid(logits)
        preds = (probs > 0.5).int()
        y_pred_list.extend(preds.numpy())

y_pred_np = np.array(y_pred_list).flatten()

print("\n--- Final Model Evaluation ---")
cm = confusion_matrix(y_test, y_pred_np)
print("Confusion Matrix:")
print(f"Actual Other (0): {cm[0][0]:<19} | {cm[0][1]}")
print(f"Actual Maize (1): {cm[1][0]:<19} | {cm[1][1]}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred_np, target_names=["Other Crops (0)", "Maize (1)"]))