import requests
import time
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
    return "KAP API Detay Okumalı Trade Bot Aktif!"

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
# FİLTRELER
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
# KAP DETAY SERVİSİNDEN DOĞRUDAN VERİ ÇEKME
# ===========================

def get_pdf_metni(disclosure_id):
    """KAP'ın resmi detay servisinden bildirimin tüm ham içeriğini çeker."""
    detay_url = f"https://www.kap.org.tr/tr/api/disclosure/{disclosure_id}"
    try:
        r = requests.get(detay_url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            veri = r.json()
            rapor_metni = ""
            if "disclosure" in veri:
                d = veri["disclosure"]
                rapor_metni += d.get("summary", "") + " "
                rapor_metni += d.get("disclosureContent", "") + " "
            return rapor_metni[:4000]
    except Exception as e:
        print("API Detay Çekme Hatası:", e)
    return ""


# ===========================
# AI TRADE ANALİZİ (MATEMATİKSEL VERİ DESTEKLİ)
# ===========================

def ai_analiz(sembol, baslik, ozet, detayli_metin):
    prompt = f"""
Sen profesyonel bir borsa, KAP ve finansal veri analistisin. Sana KAP bildiriminin başlığını, özetini ve sistemin KAP detay servisinden çektiği ham metni veriyorum. Raporun içindeki sayısal ve matematiksel verileri (kâr/zarar, ciro, ihale bedeli, büyüme oranları vb.) dikkatle incele.

Şirket Sembolü: {sembol}
Başlık: {baslik}
Özet: {ozet}
Ham Rapor Metni: {detayli_metin}

NOT: Hissenin anlık borsa fiyatını ve tahtasını bilmediğin için asla kesin TL fiyatı (örn: 50 TL) içeren destek/direnç verme. Bunun yerine "Mevcut direnç bölgesi", "Zirve bandı" veya "Teknik destek seviyesi" gibi göreceli ifadeler kullan.

Aşağıdaki formata tam olarak uyarak yanıt ver:

Önemli Matematiksel Veriler: (Raporda geçen ciro, net kâr, ihale tutarı veya değişim yüzdelerini kısa maddeler halinde yaz, veri yoksa "Yok" de)
Haberin Özü (Ne Anlama Geliyor?): (Gerçekte ne olduğunu net bir şekilde 1-2 cümleyle açıkla)
Etki: (Pozitif / Negatif / Nötr)
Haber Sınıfı: (Stratejik / Spekülatif / Rutin)
Temel/Teknik Skor: (0-100 arası sayı)
Günlük Trade Uygunluğu: (Uygun / Riskli / Tavsiye Edilmez)
Beklenen Günlük Marj: (Örn: %3 - %5 veya Tavan Potansiyeli / Baskılı)
Destek / Direnç Bölgesi: (Göreceli teknik bant veya yüzdesel aralık)
Trade and Risk Yorumu: (Verilere dayalı tahta etkisini en fazla 2 cümleyle özetle)
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


print("KAP API DETAYLI TRADE BOTU BAŞLATILDI")
telegram_gonder("⚡ KAP API Detaylı Trade Analiz Botu Aktif")

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
            print("🟢 FİLTREDEN GEÇEN BİLDİRİM - KAP API DETAYLARI ÇEKİLİYOR...")
            print("=" * 90)
            print("Şirket :", sirket)
            print("Sembol :", sembol)
            print("Başlık :", baslik)

            # KAP resmi API detay servisinden ham rapor metnini çek
            detayli_metin = get_pdf_metni(disclosure_id)

            # Yapay zekaya matematiksel verilerle birlikte gönder
            analiz = ai_analiz(sembol, baslik, ozet, detayli_metin)

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
            print("Bot API detay modunda sinyal dinliyor.\n")
            ilk_acilis = False

    except Exception as e:
        print("BOT HATASI:", e)

    time.sleep(15)
