import requests
import time
from datetime import datetime
from flask import Flask
import threading
import os
import io
from bs4 import BeautifulSoup
from pypdf import PdfReader

# ===========================
# FLASK WEB SUNUCUSU (Render için)
# ===========================
app = Flask('')

@app.route('/')
def home():
    return "KAP PDF Okumalı ve Detaylı Trade Bot Aktif!"

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
# KAP SAYFASINDAN VE PDF'TEN DETAYLI OKUMA
# ===========================

def get_pdf_metni(disclosure_id):
    """KAP sayfasındaki PDF raporlarını bulur, indirir ve içindeki metni okur."""
    url = f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Sayfadaki PDF eklerini ara
            pdf_links = []
            for a in soup.find_all('a', href=True):
                if '.pdf' in a['href'].lower():
                    link = a['href']
                    if not link.startswith('http'):
                        link = "https://www.kap.org.tr" + link
                    pdf_links.append(link)
            
            # Eğer PDF varsa ilkini indir ve oku
            if pdf_links:
                pdf_url = pdf_links[0]
                pdf_res = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
                if pdf_res.status_code == 200:
                    f = io.BytesIO(pdf_res.content)
                    reader = PdfReader(f)
                    pdf_metin = ""
                    # İlk 3 sayfayı okumak finansal veriler için yeterlidir
                    sayfa_sayisi = min(len(reader.pages), 3)
                    for i in range(sayfa_sayisi):
                        pdf_metin += reader.pages[i].extract_text() or ""
                    if len(pdf_metin.strip()) > 50:
                        return pdf_metin[:4000]

            # Eğer PDF bulunamazsa normal sayfa içeriğini çek
            content = soup.find('div', {'class': 'disclosure-page-content'}) or soup.body
            return content.get_text(separator=' ', strip=True)[:3500]

    except Exception as e:
        print("Metin/PDF Okuma Hatası:", e)
    return ""


# ===========================
# AI TRADE ANALİZİ (MATEMATİKSEL VERİ DESTEKLİ)
# ===========================

def ai_analiz(sembol, baslik, ozet, detayli_metin):
    prompt = f"""
Sen profesyonel bir borsa, KAP ve finansal veri analistisin. Sana KAP bildiriminin başlığını, özetini ve sistemin resmi sayfadan/PDF raporundan çektiği detaylı metni veriyorum. Raporun içindeki sayısal ve matematiksel verileri (kâr/zarar, ciro, ihale bedeli, büyüme oranları vb.) dikkatle incele.

Şirket Sembolü: {sembol}
Başlık: {baslik}
Özet: {ozet}
Rapor/Sayfa Detay Metni: {detayli_metin}

NOT: Hissenin anlık borsa fiyatını bilmediğin için asla net TL fiyatı verme. Destek/direnç için "Mevcut direnç bölgesi", "Zirve bandı" veya "Destek seviyesi" gibi teknik ifadeler kullan.

Aşağıdaki formata tam olarak uyarak yanıt ver:

Önemli Matematiksel Veriler: (Raporda geçen ciro, net kâr, ihale tutarı veya değişim yüzdelerini kısa maddeler halinde yaz, veri yoksa "Yok" de)
Haberin Özü (Ne Anlama Geliyor?): (Gerçekte ne olduğunu net bir şekilde 1-2 cümleyle açıkla)
Etki: (Pozitif / Negatif / Nötr)
Haber Sınıfı: (Stratejik / Spekülatif / Rutin)
Temel/Teknik Skor: (0-100 arası sayı)
Günlük Trade Uygunluğu: (Uygun / Riskli / Tavsiye Edilmez)
Beklenen Günlük Marj: (Örn: %3 - %5 veya Tavan Potansiyeli / Baskılı)
Destek / Direnç Bölgesi: (Göreceli teknik bant veya yüzdesel aralık)
Trade ve Risk Yorumu: (Verilere dayalı tahta etkisini en fazla 2 cümleyle özetle)
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


print("KAP PDF OKUMALI TRADE BOTU BAŞLATILDI")
telegram_gonder("⚡ KAP PDF Okumalı Trade Analiz Botu Aktif")

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
            print("🟢 FİLTREDEN GEÇEN BİLDİRİM - PDF VE DETAYLAR OKUNUYOR...")
            print("=" * 90)
            print("Şirket :", sirket)
            print("Sembol :", sembol)
            print("Başlık :", baslik)

            # KAP sayfasındaki PDF raporlarını veya detay metnini çek
            detayli_metin = get_pdf_metni(disclosure_id)

            # Yapay zekaya matematiksel verileri de içerecek şekilde gönder
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
            print("Bot PDF okuma modunda sinyal dinliyor.\n")
            ilk_acilis = False

    except Exception as e:
        print("BOT HATASI:", e)

    time.sleep(15)
