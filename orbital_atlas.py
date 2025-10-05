import sys
import io
import time
import math
import threading
from typing import Optional, Tuple

import requests
from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt

from PyQt6.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit, QMessageBox, QFrame
)

# Pillow resampling fallback
try:
    RESAMPLE = Image.Resampling.LANCZOS
except Exception:
    try:
        RESAMPLE = Image.LANCZOS
    except Exception:
        RESAMPLE = Image.BICUBIC

# Global HTTP session for reuse
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "Mozilla/5.0 (OrbitalAtlas)"})

# -----------------------------
# HTTP helpers with retry
# -----------------------------
def http_get_json(url: str, timeout: int = 8, retries: int = 2, delay: float = 1.0) -> dict:
    last_err = None
    for _ in range(retries):
        try:
            r = HTTP.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(delay)
    raise RuntimeError(f"HTTP JSON fetch failed: {last_err}")

def http_get_bytes(url: str, timeout: int = 10, retries: int = 2, delay: float = 1.0) -> bytes:
    last_err = None
    for _ in range(retries):
        try:
            r = HTTP.get(url, timeout=timeout, stream=True)
            r.raise_for_status()
            return r.content
        except Exception as e:
            last_err = e
            time.sleep(delay)
    raise RuntimeError(f"HTTP bytes fetch failed: {last_err}")

# -----------------------------
# APOD Tab
# -----------------------------
class ApodTab(QWidget):
    dataReady = pyqtSignal(QPixmap, str, str)
    errorSignal = pyqtSignal(str)

    NASA_APOD = "https://api.nasa.gov/planetary/apod"
    API_KEY = "DEMO_KEY"  # Kendi API anahtarını ekleyebilirsin: https://api.nasa.gov/

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.dataReady.connect(self._apply_info)
        self.errorSignal.connect(self._show_error)

    def init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("NASA APOD Viewer")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        ctrl = QHBoxLayout()
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("YYYY-MM-DD (boş: bugün)")
        self.load_btn = QPushButton("APOD Göster")
        self.load_btn.clicked.connect(self.on_load)
        ctrl.addWidget(self.date_edit)
        ctrl.addWidget(self.load_btn)
        layout.addLayout(ctrl)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.setMinimumHeight(360)
        layout.addWidget(self.image_label)

        self.title_label = QLabel("")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        layout.addWidget(self.title_label)

        self.desc = QTextEdit()
        self.desc.setReadOnly(True)
        self.desc.setMinimumHeight(160)
        layout.addWidget(self.desc)

    def on_load(self):
        params = {"api_key": self.API_KEY}
        date_str = self.date_edit.text().strip()
        if date_str:
            try:
                import datetime as dt
                dt.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                QMessageBox.warning(self, "Uyarı", "Tarih formatı YYYY-MM-DD olmalı.")
                return
            params["date"] = date_str

        url = self.NASA_APOD + "?" + "&".join([f"{k}={v}" for k, v in params.items()])

        def worker():
            try:
                info = http_get_json(url, retries=2, timeout=8)
                media_type = info.get("media_type", "")
                if media_type != "image":
                    title = info.get("title", "APOD")
                    explanation = f"Bugünkü APOD bir medya: {media_type}\n{info.get('url', '')}"
                    self.dataReady.emit(QPixmap(), title, explanation)
                    return

                img_url = info.get("hdurl") or info.get("url")
                if not img_url:
                    self.errorSignal.emit("APOD görsel URL'si bulunamadı.")
                    return

                img_bytes = http_get_bytes(img_url, retries=2, timeout=10)
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img.thumbnail((700, 450), RESAMPLE)  # daha küçük, daha akıcı
                pix = QPixmap.fromImage(ImageQt(img))
                self.dataReady.emit(pix, info.get("title", ""), info.get("explanation", ""))
            except Exception as e:
                print("APOD hata:", e)
                self.errorSignal.emit(f"APOD alınamadı:\n{e}")

        threading.Thread(target=worker, daemon=True).start()

    def _apply_info(self, pix: QPixmap, title: str, explanation: str):
        if not pix.isNull():
            self.image_label.setPixmap(pix)
        else:
            self.image_label.clear()
        self.title_label.setText(title)
        self.desc.setPlainText(explanation)

    def _show_error(self, msg: str):
        QMessageBox.critical(self, "Hata", msg)

# -----------------------------
# ISS Tab (threaded fetch)
# -----------------------------
class IssTab(QWidget):
    ISS_API = "http://api.open-notify.org/iss-now.json"
    WORLD_IMG_URL = "https://eoimages.gsfc.nasa.gov/images/imagerecords/74000/74420/world.topo.bathy.200412.3x5400x2700.jpg"

    posReady = pyqtSignal(float, float)
    statusReady = pyqtSignal(str)
    worldReady = pyqtSignal(QPixmap)

    def __init__(self):
        super().__init__()
        self.world_img_pil: Optional[Image.Image] = None
        self.last_pos: Optional[Tuple[float, float]] = None
        self.fetching = False

        self.init_ui()

        self.posReady.connect(self._on_position)
        self.statusReady.connect(self._on_status)
        self.worldReady.connect(self._on_world_pixmap)

        self.load_world_image_async()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_iss_async)
        self.timer.start(10000)  # 10 saniye

    def init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("ISS Tracker")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        self.status = QLabel("Durum: başlangıç")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        self.map_label = QLabel()
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_label.setStyleSheet("background-color: black;")
        self.map_label.setMinimumHeight(360)
        layout.addWidget(self.map_label)

        self.info = QLabel("")
        self.info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        layout.addWidget(self.info)

    def load_world_image_async(self):
        def worker():
            try:
                img_bytes = http_get_bytes(self.WORLD_IMG_URL, retries=2, timeout=10)
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img.thumbnail((800, 400), RESAMPLE)  # optimize boyut
                self.world_img_pil = img
                pix = QPixmap.fromImage(ImageQt(img))
                self.worldReady.emit(pix)
                self.statusReady.emit("Durum: Dünya görseli yüklendi")
            except Exception as e:
                print("Dünya görseli hata:", e)
                self.world_img_pil = None
                self.worldReady.emit(QPixmap())  # siyah arka plan
                self.statusReady.emit(f"Durum: Dünya görseli yüklenemedi ({e}). Siyah arka plan.")

        threading.Thread(target=worker, daemon=True).start()

    def _on_world_pixmap(self, pix: QPixmap):
        if pix and not pix.isNull():
            self.map_label.setPixmap(pix)
        else:
            base = Image.new("RGB", (800, 400), (0, 0, 0))
            self.map_label.setPixmap(QPixmap.fromImage(ImageQt(base)))

    def fetch_iss_async(self):
        if self.fetching:
            return
        self.fetching = True

        def worker():
            try:
                data = http_get_json(self.ISS_API, retries=2, timeout=6)
                pos = data.get("iss_position")
                if not pos:
                    raise ValueError("ISS konumu JSON içinde yok.")

                lat_raw = pos.get("latitude")
                lon_raw = pos.get("longitude")
                if lat_raw is None or lon_raw is None:
                    raise ValueError("ISS konumu eksik.")

                lat = float(lat_raw)
                lon = float(lon_raw)
                self.posReady.emit(lat, lon)
                self.statusReady.emit("Durum: ISS konumu güncellendi")
            except Exception as e:
                print("ISS konumu hata:", e)
                self.statusReady.emit("Durum: ISS konumu alınamadı (geçici)")
            finally:
                self.fetching = False

        threading.Thread(target=worker, daemon=True).start()

    def _on_position(self, lat: float, lon: float):
        self.last_pos = (lat, lon)
        self.redraw()

    def _on_status(self, text: str):
        self.status.setText(text)

    def latlon_to_xy(self, lat: float, lon: float, w: int, h: int) -> Tuple[int, int]:
        x = int((lon + 180.0) * (w / 360.0))
        y = int((90.0 - lat) * (h / 180.0))
        return x, y

    def redraw(self):
        if self.world_img_pil:
            base = self.world_img_pil.copy()
            w, h = base.size
        else:
            w, h = (800, 400)
            base = Image.new("RGB", (w, h), (0, 0, 0))

        draw = ImageDraw.Draw(base)

        if self.last_pos:
            lat, lon = self.last_pos
            x, y = self.latlon_to_xy(lat, lon, w, h)
            r = 10
            x = max(r, min(w - r, x))
            y = max(r, min(h - r, y))
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0), outline=(0, 0, 0), width=2)
            label = f"ISS Konumu | Lat: {lat:.2f}, Lon: {lon:.2f}"
            draw.text((20, 20), label, fill=(255, 255, 255))
            self.info.setText(f"Son konum: Lat {lat:.3f}, Lon {lon:.3f}")
        else:
            draw.text((20, 20), "ISS konumu yok (bekleniyor)", fill=(255, 255, 255))
            self.info.setText("Son konum: yok")

        self.map_label.setPixmap(QPixmap.fromImage(ImageQt(base)))

# -----------------------------
# Microgravity Tab (düşük FPS ve doğru tıklama)
# -----------------------------
class MicrogravityWidget(QWidget):
    def __init__(self, width=900, height=460, obj_count=6):
        super().__init__()
        self.setMinimumSize(width, height)
        self.objs = []
        for i in range(obj_count):
            r = 14 + int(8 * (math.sin(i + 0.7) + 1) / 2)
            self.objs.append({
                "x": float(60 + i * 120 if 60 + i * 120 < width - 60 else width // 2),
                "y": float(80 + (i % 3) * 90),
                "r": float(r),
                "vx": float(math.sin(i * 1.3) * 0.9),
                "vy": float(math.cos(i * 0.9) * 0.9),
                "color": QColor(190, 210, 255)
            })
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step)
        self.timer.start(50)  # ~20 FPS (sunum için daha güvenli)

        self.setMouseTracking(True)
        self.bg_color = QColor(10, 20, 30)
        self.pen = QPen(QColor(100, 100, 120))
        self.pen.setWidth(2)

    def step(self):
        w = float(self.width())
        h = float(self.height())
        for o in self.objs:
            o["x"] += o["vx"]
            o["y"] += o["vy"]
            if o["x"] - o["r"] < 0 or o["x"] + o["r"] > w:
                o["vx"] *= -1.0
                o["x"] = max(o["r"], min(w - o["r"], o["x"]))
            if o["y"] - o["r"] < 0 or o["y"] + o["r"] > h:
                o["vy"] *= -1.0
                o["y"] = max(o["r"], min(h - o["r"], o["y"]))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # PyQt6: position() -> QPointF; toPoint() ile integer piksele çevir
            pos = event.position().toPoint()
            mx, my = float(pos.x()), float(pos.y())
            for o in self.objs:
                dx = o["x"] - mx
                dy = o["y"] - my
                if math.hypot(dx, dy) <= o["r"]:
                    scale = 0.7 / max(o["r"], 1.0)
                    o["vx"] += dx * scale
                    o["vy"] += dy * scale

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), self.bg_color)
        p.setPen(self.pen)
        for o in self.objs:
            p.setBrush(o["color"])
            p.drawEllipse(QPointF(o["x"], o["y"]), o["r"], o["r"])
        p.setPen(QColor(220, 220, 220))
        p.setFont(QFont("Arial", 12))
        p.drawText(10, 20, "Microgravity Demo: Nesnelere tıkla, impuls uygula")

class MicrogravityTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        header = QLabel("Microgravity Simulation")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
        layout.addWidget(header)
        self.widget = MicrogravityWidget()
        layout.addWidget(self.widget)

# -----------------------------
# Main Window
# -----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orbital Atlas — NASA Data + Simulation Suite")
        self.resize(1040, 820)
        tabs = QTabWidget()
        tabs.addTab(ApodTab(), "APOD")
        tabs.addTab(IssTab(), "ISS")
        tabs.addTab(MicrogravityTab(), "Microgravity")
        self.setCentralWidget(tabs)

# -----------------------------
# Entry point with global error hook
# -----------------------------
def main():
    # Uygulama beklenmeyen hatada kapanmasın: yakalanmamış hataları logla
    def handle_exception(exc_type, exc_value, exc_traceback):
        try:
            print("Yakalanmamış hata:", exc_value)
        except Exception:
            pass
    sys.excepthook = handle_exception

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
