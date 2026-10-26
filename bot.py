
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

@app.route('/')
def home():
    return "KAP Bot Aktif ve Çalışıyor!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()


# ===========================
# AYARLAR
# ===========================

# Render Environment Variables bölümüne ekle:
# TELEGRAM_BOT_TOKEN = BotFather'dan aldığın YENİ token

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Birinci ve ikinci kişinin Telegram Chat ID'si
CHAT_IDS = [
    "8812183487",
    "8518771668"
]

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
# TELEGRAM BİLDİRİMİ
# ===========================

def telegram_gonder(mesaj):
    if not BOT_TOKEN:
        print("HATA: TELEGRAM_BOT_TOKEN ayarlanmamış!")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for chat_id in CHAT_IDS:
        try:
            response = requests.post(
                url,
                data={
                    "chat_id": chat_id,
                    "text": mesaj,
                    "disable_web_page_preview": True
                },
                timeout=15
            )

            sonuc = response.json()

            if response.ok and sonuc.get("ok"):
                print(f"Bildirim gönderildi: {chat_id}")
            else:
                print(
                    f"Telegram gönderim hatası ({chat_id}): "
                    f"{sonuc.get('description', response.text)}"
                )

        except Exception as e:
            print(f"Telegram hatası ({chat_id}): {e}")


# ===========================
# KAP TAKİP SİSTEMİ
# ===========================

gorulen = set()
ilk_acilis = True

print("KAP Bot Başlatıldı...")

telegram_gonder(
    "✅ KAP Bot Başlatıldı.\n\n"
    "Telegram bağlantısı başarılı 🚀"
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

            # Yalnızca seçilen önemli haberler
            if not any(k.lower() in metin for k in KEYWORDS):
                continue

            sembol = (
                bilgi.get("relatedStocks")
                or bilgi.get("stockCode")
                or "-"
            )

            link = (
                "https://www.kap.org.tr/tr/Bildirim/"
                + str(bilgi["disclosureId"])
            )

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

            # Aynı bildirimi iki kişiye de gönder
            telegram_gonder(mesaj)

        if ilk_acilis:
            print(f"{len(gorulen)} eski bildirim hafızaya alındı.")
            print(
                "Artık sadece yeni önemli haberler gösterilecek.\n"
            )
            ilk_acilis = False

    except Exception as e:
        print("HATA:", e)

    time.sleep(15)
