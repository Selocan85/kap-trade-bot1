import requests
import time
import json
from datetime import datetime
from flask import Flask
import threading

# ===========================
# FLASK WEB SUNUCUSU (Render için gerekli)
# ===========================
app = Flask('')

@app.route('/')
def home():
    return "KAP Trade Bot Aktif ve Çalışıyor!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# Web sunucusunu arka planda ayrı bir iş parçacığında başlatıyoruz
threading.Thread(target=run_web).start()


# ===========================
# AYARLAR
# ===========================

BOT_TOKEN = "8952631263:AAG8x4JqVmmj-7AlzbilHma9wkumBpATVsg"
CHAT_ID = "8812183487"

KAP_URL = "https://www.kap.org.tr/tr/api/disclosure/list/main"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.kap.org.tr/tr",
    "Content-Type": "application/json"
}

# Sadece yakalanmasını istediğimiz önemli anahtar kelimeler
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

# Kesinlikle bildirim gelmesini istemediğimiz (eleceğimiz) kelimeler
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

gorulen = set()
ilk_acilis = True

# ===========================
# TELEGRAM
# ===========================

def telegram_gonder(mesaj):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": mesaj,
                "disable_web_page_preview": True
            },
            timeout=20
        )
    except Exception as e:
        print("Telegram:", e)


print("KAP TRADE BOTU BAŞLATILDI (Filtreli Mod)")
telegram_gonder("⚡ KAP Trade Bot Aktif (Filtreli Mod)")

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

            # IGNORE listesindekileri atla
            if any(k.lower() in metin for k in IGNORE):
                continue

            # KEYWORDS listesinden en az biri geçmiyorsa atla
            if not any(k.lower() in metin for k in KEYWORDS):
                continue

            sembol = (
                bilgi.get("relatedStocks")
                or bilgi.get("stockCode")
                or "-"
            )

            sirket = bilgi.get("companyTitle", "-")
            disclosure_id = bilgi.get("disclosureId")
            link = f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"

            print("=" * 90)
            print("🟢 FİLTREYE UYGUN BİLDİRİM YAKALANDI")
            print("=" * 90)
            print("Şirket :", sirket)
            print("Sembol :", sembol)
            print("Başlık :", baslik)
            
            mesaj = f"""
⚡️ YENİ KAPA BİLDİRİMİ (Filtrelendi)

🏢 {sirket}
📈 {sembol}

📄 {baslik}

Özet: {ozet[:300]}...

🔗 {link}
"""

            telegram_gonder(mesaj)
            print("\nTelegram'a gönderildi.\n")

        if ilk_acilis:
            print(f"{len(gorulen)} eski bildirim hafızaya alındı.")
            print("Bot yeni filtrelenmiş bildirimleri dinliyor.\n")
            ilk_acilis = False

    except Exception as e:
        print("BOT HATASI:", e)

    time.sleep(15)
