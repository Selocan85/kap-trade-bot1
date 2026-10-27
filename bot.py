
import requests
import time
from datetime import datetime
from flask import Flask
import threading
import os

# ===========================
# FLASK WEB SUNUCUSU (RENDER)
# ===========================

app = Flask(__name__)

@app.route("/")
def home():
    return "KAP Bot Aktif ve Çalışıyor!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ===========================
# AYARLAR
# ===========================

# Render Environment Variables bölümünden tanımla.
BOT_TOKEN = os.environ.get(""8952631263:AAG8x4JqVmmj-7AlzbilHma9wkumBpATVsg")
CHAT_ID = os.environ.get("8812183487")

URL = "https://www.kap.org.tr/tr/api/disclosure/list/main"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.kap.org.tr/tr",
    "Content-Type": "application/json"
}

# Gösterilecek haberler
KEYWORDS = [
    "Finansal Rapor",
    "Yeni İş İlişkisi",
    "Sermaye Artırımı",
    "Sermaye Azaltımı",
    "Kar Payı",
    "Temettü",
    "Payların Geri Alınmasına",
    "Pay Geri Alım",
    "Birleşme",
    "Bölünme",
    "İhale",
    "Yatırım",
    "Teşvik",
    "Kapasite Artırımı",
    "Yeni Fabrika",
    "Ortaklık",
    "Satın Alma",
    "Esas Sözleşme"
]

# Gösterilmeyecek haberler
IGNORE = [
    "Devre Kesici",
    "Varant",
    "Sertifika",
    "Borçlanma Aracı",
    "Kupon",
    "Faiz",
    "VTMK",
    "VDMK"
]

# ===========================
# TELEGRAM
# ===========================

def telegram_gonder(mesaj):
    if not BOT_TOKEN or not CHAT_ID:
        print("UYARI: BOT_TOKEN veya CHAT_ID tanımlanmamış.")
        return

    telegram_url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

    try:
        cevap = requests.post(
            telegram_url,
            data={
                "chat_id": CHAT_ID,
                "text": mesaj,
                "disable_web_page_preview": True
            },
            timeout=15
        )

        if cevap.status_code != 200:
            print("Telegram API Hatası:", cevap.text)

    except Exception as e:
        print("Telegram Hatası:", e)

# ===========================
# KAP BOTU
# ===========================

gorulen = set()
ilk_acilis = True

print("KAP Bot Başlatıldı...")
telegram_gonder(
    "✅ KAP Bot Başlatıldı.\n\nTelegram bağlantısı başarılı 🚀"
)

while True:
    bugun = datetime.now().strftime("%d.%m.%Y")

    payload = {
        "fromDate": bugun,
        "toDate": bugun,
        "memberTypes": ["IGS", "DDK"]
    }

    try:
        r = requests.post(
            URL,
            json=payload,
            headers=HEADERS,
            timeout=20
        )

        if r.status_code != 200:
            print("KAP API Hatası:", r.status_code)
            time.sleep(15)
            continue

        data = r.json()

        if not isinstance(data, list):
            print("Beklenmeyen KAP API yanıtı.")
            time.sleep(15)
            continue

        data = sorted(
            data,
            key=lambda x: x.get("disclosureBasic", {}).get(
                "disclosureIndex", 0
            )
        )

        for item in data:
            bilgi = item.get("disclosureBasic", {})

            idx = bilgi.get("disclosureIndex")

            if idx is None:
                continue

            if ilk_acilis:
                gorulen.add(idx)
                continue

            if idx in gorulen:
                continue

            gorulen.add(idx)

            baslik = bilgi.get("title", "") or ""
            ozet = bilgi.get("summary", "") or ""

            metin = (baslik + " " + ozet).casefold()

            # Gereksiz haberleri atla
            if any(k.casefold() in metin for k in IGNORE):
                continue

            # Sadece belirlenen haberleri göster
            if not any(k.casefold() in metin for k in KEYWORDS):
                continue

            sembol = (
                bilgi.get("relatedStocks")
                or bilgi.get("stockCode")
                or "-"
            )

            bildirim_id = bilgi.get("disclosureId")

            if bildirim_id:
                link = f"https://www.kap.org.tr/tr/Bildirim/{bildirim_id}"
            else:
                link = "Bağlantı bulunamadı"

            print("\n" + "=" * 70)
            print("🟢 YENİ ÖNEMLİ KAP HABERİ")
            print("=" * 70)
            print("Şirket :", bilgi.get("companyTitle"))
            print("Sembol :", sembol)
            print("Başlık :", baslik)
            print("Özet   :", ozet)
            print("Saat   :", bilgi.get("publishDate"))
            print("Link   :", link)
            print("=" * 70)

            mesaj = (
                "🟢 KAP Bildirimi\n\n"
                f"🏢 {bilgi.get('companyTitle', '-')}\n"
                f"📈 {sembol}\n\n"
                f"📄 {baslik}\n\n"
                f"📝 {ozet}\n\n"
                f"🕒 {bilgi.get('publishDate', '-')}\n\n"
                f"🔗 {link}"
            )

            telegram_gonder(mesaj)

        if ilk_acilis:
            print(f"{len(gorulen)} eski bildirim hafızaya alındı.")
            print("Artık sadece yeni önemli haberler gösterilecek.\n")
            ilk_acilis = False

    except Exception as e:
        print("HATA:", e)

    time.sleep(15)
