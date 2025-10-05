import requests
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# API URL'leri
ISS_API = "http://api.open-notify.org/iss-now.json"
ASTRONAUTS_API = "http://api.open-notify.org/astros.json"

# Alternatif Dünya görseli (NASA Earth Observatory)
WORLD_IMG_URL = "https://eoimages.gsfc.nasa.gov/images/imagerecords/74000/74420/world.topo.bathy.200412.3x5400x2700.jpg"

def fetch_iss_position(retries=3, delay=2):
    """ISS konumunu API'den alır, hata olursa tekrar dener."""
    for i in range(retries):
        try:
            r = requests.get(ISS_API, timeout=5)
            r.raise_for_status()
            data = r.json()
            pos = data["iss_position"]
            return float(pos["latitude"]), float(pos["longitude"])
        except Exception:
            if i < retries - 1:
                time.sleep(delay)
            else:
                return None

def fetch_astronauts():
    """ISS'teki astronotları listeler."""
    try:
        r = requests.get(ASTRONAUTS_API, timeout=5)
        r.raise_for_status()
        data = r.json()
        people = [p["name"] for p in data["people"] if p["craft"] == "ISS"]
        return people
    except Exception:
        return []

# Harita ayarları
fig = plt.figure(figsize=(12, 6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.stock_img()
ax.add_feature(cfeature.BORDERS, linestyle=':')
ax.add_feature(cfeature.COASTLINE)

# Başlangıç noktası
scat = ax.scatter([], [], color='red', s=100, edgecolors='black', zorder=5)
text = ax.text(-170, -80, "", fontsize=10, color="yellow",
               bbox=dict(facecolor="black", alpha=0.5))

def update(frame):
    pos = fetch_iss_position()
    if pos:
        lat, lon = pos
        scat.set_offsets([[lon, lat]])
        astronauts = fetch_astronauts()
        info = f"ISS Konumu\nLat: {lat:.2f}, Lon: {lon:.2f}\nAstronotlar: {', '.join(astronauts) if astronauts else 'Bilinmiyor'}"
        text.set_text(info)
    else:
        text.set_text("ISS konumu alınamadı.")
    return scat, text

ani = FuncAnimation(fig, update, interval=5000)  # 5 saniyede bir güncelle
plt.title("🌍 Uluslararası Uzay İstasyonu (ISS) Gerçek Zamanlı Takip")
plt.show()
