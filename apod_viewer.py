import requests
from io import BytesIO
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

API_KEY = "DEMO_KEY"  # Buraya kendi NASA API key'ini yazabilirsin

def fetch_apod(date=None):
    """NASA APOD bilgisini getirir (bugün veya seçilen tarih)."""
    url = f"https://api.nasa.gov/planetary/apod?api_key={API_KEY}"
    if date:
        url += f"&date={date}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        messagebox.showerror("Hata", f"APOD alınamadı:\n{e}")
        return None

def load_image_from_url(url, maxsize=(900, 600)):
    """URL'den görsel indirip tkinter uyumlu hale getirir."""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content))
        img.thumbnail(maxsize, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        messagebox.showerror("Hata", f"Görsel yüklenemedi:\n{e}")
        return None

def show_apod():
    """Seçilen tarihi alıp APOD'u gösterir."""
    date = date_entry.get().strip()
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")  # format kontrolü
        except ValueError:
            messagebox.showwarning("Uyarı", "Tarih formatı YYYY-MM-DD olmalı.")
            return
    else:
        date = None

    info = fetch_apod(date)
    if not info:
        return

    if info.get("media_type") != "image":
        messagebox.showinfo("Bilgi", "Bugünkü APOD bir video.\n" + info.get("url", ""))
        return

    img_tk = load_image_from_url(info["url"])
    if img_tk:
        img_label.config(image=img_tk)
        img_label.image = img_tk

    title_label.config(text=info.get("title", ""))
    desc_text.delete("1.0", tk.END)
    desc_text.insert(tk.END, info.get("explanation", ""))

# --- Arayüz ---
root = tk.Tk()
root.title("🚀 NASA APOD Viewer")
root.geometry("1000x850")

# Başlık
title_label = tk.Label(root, text="", font=("Helvetica", 18, "bold"))
title_label.pack(pady=8)

# Görsel
img_label = tk.Label(root, bg="black")
img_label.pack(pady=5)

# Açıklama (kaydırılabilir)
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

scrollbar = tk.Scrollbar(frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

desc_text = tk.Text(frame, wrap=tk.WORD, height=12, yscrollcommand=scrollbar.set)
desc_text.pack(fill=tk.BOTH, expand=True)
scrollbar.config(command=desc_text.yview)

# Tarih seçme
date_frame = tk.Frame(root)
date_frame.pack(pady=5)

tk.Label(date_frame, text="Tarih (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
date_entry = tk.Entry(date_frame, width=12)
date_entry.pack(side=tk.LEFT, padx=5)

btn = tk.Button(date_frame, text="APOD Göster", command=show_apod)
btn.pack(side=tk.LEFT, padx=5)

root.mainloop()
