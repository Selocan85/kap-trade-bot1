import requests
import time
import json
from datetime import datetime
from flask import Flask
import threading
import os

# ===========================
# FLASK WEB SUNUCUSU (Render için)
# ===========================
app = Flask('')

@app.route('/')
def home():
    return "KAP Yapay Zeka Akıllı Filtreleme Botu Aktif!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web).start()


# ===========================
# AYARLAR
# ===========================

BOT_TOKEN = "8952631263:AAG8x4JqVmmj-7AlzbilHma9wkumBpATVsg"
CHAT_ID = "8812183487"

# Groq API Anahtarınız
GROQ_API_KEY = "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"

KAP_URL = "https://www.kap.org.tr/tr/api/disclosure/list/main"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.kap.org.tr/tr",
    "Content-Type": "application/json"
}

# ===========================
# FİLTRELER ("Özel Durum" buraya eklendi, artık yapay zeka karar verecek)
# ===========================

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
    "Esas Sözleşme",
    "Özel Durum"  # Artık özel durumlar bota girecek, AI karar verecek
]

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


# ===========================
# AI TRADE ANALİZİ VE AKILLI ELEME
# ===========================

def ai_analiz(sembol, baslik, ozet):
    prompt = f"""
Sen profesyonel bir borsa, KAP ve finansal haber analiz uzmanısın. Gelen KAP bildirimini incele.

Şirket Sembolü: {sembol}
Başlık: {baslik}
Özet: {ozet}

ÖNEMLİ TALİMAT:
Eğer bu haber tamamen rutin, boş, şirketin faaliyetine veya hisse fiyatına hiçbir etkisi olmayan sıradan bir idari/genel açıklama ise; yanıtın en başına kelimesi kelimesine **ÖNEMSİZ_RUTİN** yaz ve başka hiçbir şey uzatma.
Eğer haber hissede hareket yaratabilecek (ihale, iş ilişkisi, bilanço, ortaklık, stratejik karar vb.) önemli bir gelişmeyse, alttaki formata tam olarak uyarak detaylı analiz ver:

Haberin Özü (Ne Anlama Geliyor?): (Haberin gerçekte ne olduğunu, şirket için ne ifade ettiğini net bir şekilde 1-2 cümleyle açıkla)
Etki: (Pozitif / Negatif / Nötr)
Haber Sınıfı: (Stratejik / Spekülatif / Rutin)
Temel/Teknik Skor: (0-100 arası sayı)
Günlük Trade Uygunluğu: (Uygun / Riskli / Tavsiye Edilmez)
Beklenen Günlük Marj: (Örn: %3 - %5 veya Tavan Potansiyeli / Baskılı)
Destek / Direnç Bölgesi: (Göreceli teknik bant veya yüzdesel aralık)
Trade and Risk Yorumu: (Haberin tahtadaki hacim etkisini ve dikkat edilmesi gereken riski en fazla 2 cümleyle özetle)
"""

    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        r = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=60
        )

        if r.status_code != 200:
            return f"Groq AI Hatası ({r.status_code}): {r.text}"

        veri = r.json()
        return veri["choices"][0]["message"]["content"]

    except Exception as e:
        return str(e)


print("KAP AKILLI FİLTRELEME BOTU BAŞLATILDI")
telegram_gonder("⚡ KAP Akıllı Filtreleme Trade Botu Aktif")

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
            disclosure_id = bilgi.get("disclosureId")
            link = f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"

            print("=" * 90)
            print("🟢 BİLDİRİM YAPAY ZEKAYA GÖNDERİLİYOR:", baslik)
            print("=" * 90)

            analiz = ai_analiz(sembol, baslik, ozet)

            # Yapay zeka habere "ÖNEMSİZ_RUTİN" derse Telegram'a atma
            if "ÖNEMSİZ_RUTİN" in analiz:
                print("❌ Yapay Zeka Haberi Rutin Buldu, Elendi.\n")
                continue

            print(analiz)
            
            mesaj = f"""
⚡ GÜNLÜK TRADE SİNYALİ

🏢 {sirket}
📈 {sembol}

📄 {baslik}

{analiz}

🔗 {link}
"""

            telegram_gonder(mesaj)
            print("\nTelegram'a gönderildi.\n")

        if ilk_acilis:
            print(f"{len(gorulen)} eski bildirim hafızaya alındı.")
            print("Bot akıllı filtre modunda çalışıyor.\n")
            ilk_acilis = False

    except Exception as e:
        print("BOT HATASI:", e)

    time.sleep(15)
