import requests
import time
from datetime import datetime
from flask import Flask
import threading
import os

# ===========================
# FLASK WEB SUNUCUSU (Render İçin Zorunlu)
# ===========================
app = Flask('')

@app.route('/')
def home():
    return "KAP Bot Aktif ve Çalışıyor!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Web sunucusunu arka planda (ayrı bir thread'de) başlatıyoruz
threading.Thread(target=run_web).start()


# ===========================
# AYARLAR
# ===========================

BOT_TOKEN = "8952631263:AAG8x4JqVmmj-7AlzbilHma9wkumBpATVsg"
CHAT_ID = "8812183487"

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
    if BOT_TOKEN == "":
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": mesaj,
                "disable_web_page_preview": True
            },
            timeout=15
        )
    except Exception as e:
        print("Telegram Hatası:", e)


# ===========================

gorulen = set()
ilk_acilis = True

print("KAP Bot Başlatıldı...")
telegram_gonder("✅ KAP Bot Başlatıldı.\n\nTelegram bağlantısı başarılı 🚀")


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
            print("API Hatası:", r.status_code)
            time.sleep(15)
            continue

        data = r.json()

        data = sorted(
            data,
            key=lambda x: x["disclosureBasic"]["disclosureIndex"]
        )

        for item in data:

            bilgi = item["disclosureBasic"]

            idx = bilgi["disclosureIndex"]

            if ilk_acilis:
                gorulen.add(idx)
                continue

            if idx in gorulen:
                continue

            gorulen.add(idx)

            baslik = bilgi.get("title", "")
            ozet = bilgi.get("summary", "")

            metin = (baslik + " " + ozet).lower()

            # Gereksiz haberleri atla
            if any(k.lower() in metin for k in IGNORE):
                continue

            # Sadece önemli haberleri göster
            if not any(k.lower() in metin for k in KEYWORDS):
                continue

            sembol = bilgi.get("relatedStocks") or bilgi.get("stockCode") or "-"

            link = f"https://www.kap.org.tr/tr/Bildirim/{bilgi['disclosureId']}"

            print("\n" + "=" * 90)
            print("🟢 YENİ ÖNEMLİ KAP HABERİ")
            print("=" * 90)
            print("Şirket :", bilgi.get("companyTitle"))
            print("Sembol :", sembol)
            print("Başlık :", baslik)
            print("Özet   :", ozet)
            print("Saat   :", bilgi.get("publishDate"))
            print("Link   :", link)
            print("=" * 90)

            mesaj = f"""🟢 KAP Bildirimi

🏢 {bilgi.get("companyTitle")}
📈 {sembol}

📄 {baslik}

📝 {ozet}

🕒 {bilgi.get("publishDate")}

🔗 {link}
"""

            telegram_gonder(mesaj)

        if ilk_acilis:
            print(f"{len(gorulen)} eski bildirim hafızaya alındı.")
            print("Artık sadece yeni önemli haberler gösterilecek.\n")
            ilk_acilis = False

    except Exception as e:
        print("HATA:", e)

    time.sleep(15)
