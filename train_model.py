import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pickle
import os


csv_file = "data/dane2.csv"  
if not os.path.exists(csv_file):
    print(f"Nie znaleziono pliku: {csv_file}")
    exit()

print("Wczytywanie danych")
df = pd.read_csv(csv_file, sep=",", skiprows=53, on_bad_lines="skip", engine="python")





df = df[['koi_period', 'koi_duration', 'koi_depth', 'koi_prad', 'koi_disposition']].dropna()
df.columns = df.columns.str.strip().str.lower()  


print("Kolumny dostępne w danych:")
print(df.columns.tolist())


features = ['koi_period', 'koi_duration', 'koi_depth', 'koi_prad']
missing = [col for col in features if col not in df.columns]
if missing:
    print(f"Brakuje kolumn: {missing}")
    exit()

X = df[features]
y = df['koi_disposition'].apply(lambda x: 1 if x == 'CONFIRMED' else 0)


X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


print("rening modelu AI")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)


y_pred = model.predict(X_test)
print("📋 Raport klasyfikacji:")
print(classification_report(y_test, y_pred))

# 💾 Zapis modelu
model_file = "exoplanet_model.pkl"
with open(model_file, "wb") as f:
    pickle.dump(model, f)

print(f"Model zapisany jako: {model_file}")
