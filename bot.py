import requests
import time
import json
from datetime import datetime
from flask import Flask
import threading
import google.generativeai as genai

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

# Google Gemini API Anahtarınız
GEMINI_API_KEY = "AQ.Ab8RN6L8_sxJ_EyOzrU_meWJp_60LMhTCm-S4SEPBV966IY1NA"

# Resmi SDK yapılandırması
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

KAP_URL = "https://www.kap.org.tr/tr/api/disclosure/list/main"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.kap.org.tr/tr",
    "Content-Type": "application/json"
}

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
# AI TRADE ANALİZİ (Resmi SDK ile)
# ===========================

def ai_analiz(sembol, baslik, ozet):
    prompt = f"""
Sen profesyonel bir gün içi (day trading) borsa ve teknik analiz uzmanısın. Gelen KAP haberini anlık fiyat hareketi, hacim patlaması potansiyeli ve günlük trade edilebilirlik açısından süz.

Şirket: {sembol}
Başlık: {baslik}
Özet: {ozet}

Aşağıdaki formata tam olarak uyarak net, kısa ve vurucu yanıt ver:

Etki: (Pozitif / Negatif / Nötr)
Temel/Teknik Skor: (0-100 arası sayı)
Günlük Trade Uygunluğu: (Uygun / Riskli / Tavsiye Edilmez)
Beklenen Günlük Marj: (Örn: %3 - %5 veya Baskılı)
Tahmini Destek / Direnç: (Haberin yaratacağı harekete göre olası anlık seviye ipuçları veya bant aralığı)
Trade Yorumu: (Haberin gün içi tahtaya etkisini, hacim ve yön beklentisini en fazla 2 cümleyle özetle)
"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini AI Hatası: {str(e)}"


print("KAP GÜNLÜK TRADE BOTU BAŞLATILDI")
telegram_gonder("⚡ KAP Günlük Trade Analiz Botu Aktif (Render SDK Modu)")

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

            sembol = (
                bilgi.get("relatedStocks")
                or bilgi.get("stockCode")
                or "-"
            )

            sirket = bilgi.get("companyTitle", "-")
            disclosure_id = bilgi.get("disclosureId")
            link = f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"

            print("=" * 90)
            print("🟢 FİLTRESİZ BİLDİRİM YAKALANDI")
            print("=" * 90)
            print("Şirket :", sirket)
            print("Sembol :", sembol)
            print("Başlık :", baslik)

            analiz = ai_analiz(sembol, baslik, ozet)

            print(analiz)
            
            mesaj = f"""
⚡ FİLTRESİZ BİLDİRİM

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
            print("Bot render üzerinde çalışıyor.\n")
            ilk_acilis = False

    except Exception as e:
        print("BOT HATASI:", e)

    time.sleep(15)
