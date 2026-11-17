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

# 1. טעינת נתוני הראייה (תמונות הלוויין)
all_files = glob.glob("patches_region_*.npz")
if not all_files:
    print("Error: No .npz files found in the current directory.")
    exit()

X_img_list = []
y_list = []

for f in all_files:
    data = np.load(f)
    X_img_list.append(data['X'])
    y_list.append(data['y'])

X_img = np.concatenate(X_img_list, axis=0)
y = np.concatenate(y_list, axis=0)

# נרמול עוצמות ההחזר ושינוי ממדים למבנה קונבולוציה
X_img = X_img.astype(np.float32) / 10000.0
X_img = np.transpose(X_img, (0, 2, 1, 3, 4))

for c in range(X_img.shape[1]):
    mean_val = np.mean(X_img[:, c, :, :, :])
    std_val = np.std(X_img[:, c, :, :, :])
    X_img[:, c, :, :, :] = (X_img[:, c, :, :, :] - mean_val) / (std_val + 1e-8)

# 2. חילוץ וטעינת נתוני האקלים
DATES = [
    "20190606", "20190701", "20190706", "20190711", "20190721",
    "20190805", "20190815", "20190825", "20190909", "20190919",
    "20190924", "20191004", "20191103"
]

nasa_df = pd.read_csv("nasa_climate_kenya_2019.csv")
nasa_df['datetime'] = pd.to_datetime(nasa_df['date'], format='%Y%m%d')
nasa_df.set_index('datetime', inplace=True)

climate_features = []
for d in DATES:
    dt = pd.to_datetime(d, format='%Y%m%d')
    start_dt = dt - pd.Timedelta(days=14)
    window = nasa_df.loc[start_dt:dt]
    climate_features.append(window['precipitation_mm'].sum())
    climate_features.append(window['temperature_c'].mean())

clim_vector = np.array(climate_features, dtype=np.float32)
# שכפול וקטור האקלים לכל הדוגמאות (כיוון שמייצג את התקופה המרחבית המשותפת)
X_clim = np.tile(clim_vector, (len(y), 1))

# נרמול נתוני האקלים
scaler = StandardScaler()
X_clim = scaler.fit_transform(X_clim)

# 3. חלוקה לסט אימון ובדיקה (פיצול מסונכרן של תמונות ואקלים)
X_img_train, X_img_test, X_clim_train, X_clim_test, y_train, y_test = train_test_split(
    X_img, X_clim, y, test_size=0.2, random_state=42, stratify=y
)

# הגדרת דוגם ממושקל לאיזון האצוות
class_counts = np.bincount(y_train.astype(int))
class_weights = 1.0 / class_counts
sample_weights = np.array([class_weights[int(label)] for label in y_train])
sampler = WeightedRandomSampler(weights=torch.from_numpy(sample_weights).double(), num_samples=len(sample_weights), replacement=True)

# 4. מחלקת נתונים משולבת
class MultiModalDataset(Dataset):
    def __init__(self, img_features, clim_features, labels):
        self.X_img = torch.tensor(img_features)
        self.X_clim = torch.tensor(clim_features, dtype=torch.float32)
        self.y = torch.tensor(labels, dtype=torch.float32).unsqueeze(1)
        
    def __len__(self):
        return len(self.y)
        
    def __getitem__(self, idx):
        return self.X_img[idx], self.X_clim[idx], self.y[idx]

train_loader = DataLoader(MultiModalDataset(X_img_train, X_clim_train, y_train), batch_size=32, sampler=sampler)
test_loader = DataLoader(MultiModalDataset(X_img_test, X_clim_test, y_test), batch_size=32, shuffle=False)

# 5. הארכיטקטורה המשולבת
class CropMultiModalNet(nn.Module):
    def __init__(self, clim_dim):
        super().__init__()
        
        # זרוע א' - קונבולוציה לראייה מרחבית
        self.conv1 = nn.Conv3d(in_channels=3, out_channels=16, kernel_size=(3, 3, 3), padding=1)
        self.bn1 = nn.BatchNorm3d(16)
        self.relu = nn.LeakyReLU(0.1)
        self.pool = nn.MaxPool3d(kernel_size=(2, 2, 2))
        
        self.flatten = nn.Flatten()
        self.img_fc = nn.Linear(16 * 6 * 2 * 2, 64)
        self.img_bn = nn.BatchNorm1d(64)
        
        # זרוע ב' - רשת ליניארית לנתוני אקלים
        self.clim_fc = nn.Linear(clim_dim, 16)
        self.clim_bn = nn.BatchNorm1d(16)
        
        # צוואר בקבוק משולב
        self.dropout = nn.Dropout(0.4)
        self.final_fc = nn.Linear(64 + 16, 1)
        
    def forward(self, x_img, x_clim):
        # מסלול הראייה
        v = self.conv1(x_img)
        v = self.bn1(v)
        v = self.relu(v)
        v = self.pool(v)
        v = self.flatten(v)
        v = self.img_fc(v)
        v = self.img_bn(v)
        v = self.relu(v)
        
        # מסלול האקלים
        c = self.clim_fc(x_clim)
        c = self.clim_bn(c)
        c = self.relu(c)
        
        # שרשור הווקטורים מהזרועות
        merged = torch.cat((v, c), dim=1)
        merged = self.dropout(merged)
        
        return self.final_fc(merged)

model = CropMultiModalNet(clim_dim=X_clim.shape[1])
criterion = nn.BCEWithLogitsLoss()
optimizer = optim.Adam(model.parameters(), lr=0.0001)

# 6. לולאת אימון שמתמודדת עם שני ערוצי נתונים
epochs = 40
print(f"Training Multi-Modal Architecture (3D-CNN + Climate)...")
for epoch in range(epochs):
    model.train()
    total_loss = 0
    for batch_X_img, batch_X_clim, batch_y in train_loader:
        optimizer.zero_grad()
        outputs = model(batch_X_img, batch_X_clim)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        
    if (epoch + 1) % 10 == 0:
        print(f"Epoch {epoch + 1}/{epochs}, Loss: {total_loss / len(train_loader):.4f}")

model.eval()
y_pred_list = []
with torch.no_grad():
    for batch_X_img, batch_X_clim, _ in test_loader:
        logits = model(batch_X_img, batch_X_clim)
        probs = torch.sigmoid(logits)
        preds = (probs > 0.5).int()
        y_pred_list.extend(preds.numpy())

y_pred_np = np.array(y_pred_list).flatten()

print("\n--- Final Multi-Modal Evaluation ---")
cm = confusion_matrix(y_test, y_pred_np)
print("Confusion Matrix:")
print(f"Actual Other (0): {cm[0][0]:<19} | {cm[0][1]}")
print(f"Actual Maize (1): {cm[1][0]:<19} | {cm[1][1]}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred_np, target_names=["Other Crops (0)", "Maize (1)"]))