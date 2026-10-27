```python
import requests
import time
from datetime import datetime
from flask import Flask
import threading
import os

app = Flask('')

@app.route('/')
def home():
    return "KAP Trade Bot Aktif ve Çalışıyor!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

BOT_TOKEN = "AQ.Ab8RN6Jnvj1PxZ0b20tTEiDHPZL0aNSoTdVJDZq6iLOfCbctjQ"
CHAT_ID = "8812183487"

KAP_URL = "https://www.kap.org.tr/tr/api/disclosure/list/main"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.kap.org.tr/tr",
    "Content-Type": "application/json"
}

KEYWORDS = [
    "Finansal Rapor",
    "Bilanço",
    "Yeni İş İlişkisi",
    "Sözleşme",
    "Sermaye Artırımı",
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
    "Stratejik İş Birliği",
    "Esas Sözleşme"
]

IGNORE = [
    "Devre Kesici",
    "Varant",
    "Sertifika",
    "Borçlanma Aracı",
    "Kupon",
    "Faiz",
    "VTMK",
    "VDMK",
    "Özel Durum Açıklaması (Genel)"
]

gorulen = set()
ilk_acilis = True

def telegram_gonder(mesaj):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": mesaj,
                "disable_web_page_preview": True
            },
            timeout=20
        )
        if r.status_code != 200:
            print("Telegram Hatası:", r.text)
    except Exception as e:
        print("Telegram:", e)

print("KAP HABER BOTU BAŞLATILDI")
telegram_gonder("✅ KAP Haber Botu Aktif. Yeni KAP bildirimleri takip ediliyor.")

while True:
    bugun = datetime.now().strftime("%d.%m.%Y")

    payload = {
        "fromDate": bugun,
        "toDate": bugun,
        "memberTypes": ["IGS", "DDK"]
    }

    try:
        r = requests.post(
            KAP_URL,
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

            if any(k.lower() in metin for k in IGNORE):
                continue

            if not any(k.lower() in metin for k in KEYWORDS):
                continue

            sembol = (
                bilgi.get("relatedStocks")
                or bilgi.get("stockCode")
                or "-"
            )

            sirket = bilgi.get("companyTitle", "-")
            saat = bilgi.get("publishDate", "-")
            disclosure_id = bilgi.get("disclosureId")
            link = f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"

            print("=" * 90)
            print("YENİ KAP HABERİ")
            print("=" * 90)
            print("Şirket :", sirket)
            print("Sembol :", sembol)
            print("Başlık :", baslik)
            print("Özet :", ozet)
            print("Saat :", saat)
            print("Link :", link)

            mesaj = f"""🔔 YENİ KAP BİLDİRİMİ

🏢 {sirket}
📈 {sembol}

📄 {baslik}

📝 {ozet}

🕒 {saat}

🔗 {link}
"""

            telegram_gonder(mesaj)
            print("Telegram'a gönderildi.\n")

        if ilk_acilis:
            print(f"{len(gorulen)} eski bildirim hafızaya alındı.")
            print("Bot yeni KAP haberlerini takip ediyor.\n")
            ilk_acilis = False

    except Exception as e:
        print("BOT HATASI:", e)

    time.sleep(15)
```
