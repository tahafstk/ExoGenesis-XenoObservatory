# exoplanet_app_clean.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

# --- Streamlit sayfa ayarları ---
st.set_page_config(page_title="Ötegezegen Dedektörü", layout="centered")
st.title("🚀 Ötegezegen Dedektörü – NASA Space Apps 2025")

# --- 1. Veri setini indir ve yükle ---
@st.cache_data
def load_data():
    url = "https://exoplanetarchive.ipac.caltech.edu/cgi-bin/nstedAPI/nph-nstedAPI?table=exoplanets&format=csv"
    df = pd.read_csv(url)
    return df

df_raw = load_data()

# --- 2. Sütunları kontrol et ve eşleştir ---
raw_columns = df_raw.columns.tolist()
st.subheader("📋 Veri Seti Sütunları")
st.write(raw_columns)

# Otomatik eşleşme
column_map = {
    'orbital_period': None,
    'radius': None,
    'mass': None,
    'temperature': None,
    'discoverymethod': None
}

for col in raw_columns:
    col_lower = col.lower()
    if 'orbper' in col_lower and column_map['orbital_period'] is None:
        column_map['orbital_period'] = col
    if ('rade' in col_lower or 'radius' in col_lower) and column_map['radius'] is None:
        column_map['radius'] = col
    if 'mass' in col_lower and column_map['mass'] is None:
        column_map['mass'] = col
    if ('eqt' in col_lower or 'temp' in col_lower) and column_map['temperature'] is None:
        column_map['temperature'] = col
    if ('discmethod' in col_lower or 'method' in col_lower) and column_map['discoverymethod'] is None:
        column_map['discoverymethod'] = col

# Eksik sütun varsa durdur
if None in column_map.values():
    st.error("Veri setinde gerekli sütunlar bulunamadı. Lütfen sütun adlarını kontrol edin.")
    st.stop()

# --- 3. Veri temizleme ---
selected_columns = [col for col in column_map.values() if col in df_raw.columns]
df = df_raw[selected_columns].dropna()
df.columns = list(column_map.keys())  # Kolonları yeniden adlandır

# Discovery method için one-hot encoding
df = pd.get_dummies(df, columns=['discoverymethod'])

# Hedef: büyük kütleli gezegen = 1, küçük = 0
df['target'] = (df['mass'] > 1).astype(int)

X = df.drop('target', axis=1)
y = df['target']

# --- 4. Model eğitimi ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

# --- 5. Model performansı ---
st.subheader("📊 Model Performansı")
report = classification_report(y_test, y_pred, output_dict=True)
st.dataframe(pd.DataFrame(report).transpose())

# --- 6. Görselleştirme ---
st.subheader("📈 Yörünge Süresi Dağılımı")
fig, ax = plt.subplots(figsize=(10, 5))
sns.histplot(df['orbital_period'], bins=50, kde=True, ax=ax)
ax.set_xlabel("Yörünge Süresi (gün)")
ax.set_ylabel("Frekans")
st.pyplot(fig)

# --- 7. Tahmin arayüzü ---
st.subheader("🔮 Yeni Gezegen Tahmini")

orbper = st.number_input("Yörünge Süresi (gün)", min_value=0.0, value=365.0)
rade = st.number_input("Gezegen Yarıçapı (Dünya yarıçapı)", min_value=0.0, value=1.0)
mass = st.number_input("Kütle (Jüpiter kütlesi)", min_value=0.0, value=1.0)
temp = st.number_input("Denge Sıcaklığı (K)", min_value=0.0, value=300.0)

# Discovery method one-hot
method_cols = [col for col in X.columns if col.startswith("discoverymethod_")]
selected_method = st.selectbox("Keşif Yöntemi", method_cols)
method_vector = [1 if col == selected_method else 0 for col in method_cols]

input_data = np.array([[orbper, rade, mass, temp] + method_vector])
prediction = model.predict(input_data)[0]

st.markdown("### 🧬 Tahmin Sonucu:")
if prediction == 1:
    st.success("Bu gezegen büyük kütleli olabilir! 🚀")
else:
    st.info("Bu gezegen küçük kütleli görünüyor. 🌍")

# --- 8. Footer ---
st.markdown("---")
st.caption
