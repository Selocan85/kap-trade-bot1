
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
    return "KAP Trade Bot Aktif ve Çalışıyor!", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ===========================
# AYARLAR
# ===========================

BOT_TOKEN = os.environ.get("8952631263:AAG8x4JqVmmj-7AlzbilHma9wkumBpATVsg", "").strip()
CHAT_ID = os.environ.get("8812183487", "").strip()
CHAT_ID_2 = os.environ.get("8518771668", "").strip()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()

KAP_URL = "https://www.kap.org.tr/tr/api/disclosure/list/main"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.kap.org.tr/tr",
    "Content-Type": "application/json"
}

# ÖNEMLİ HABER FİLTRELERİ
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

# GEREKSİZ / GÜRÜLTÜ YARATAN HABERLER
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
# TELEGRAM - İKİ KULLANICI
# ===========================

def telegram_gonder(mesaj):
    if not BOT_TOKEN:
        print("HATA: BOT_TOKEN tanımlanmamış.")
        return

    telegram_url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

    chat_id_listesi = list(dict.fromkeys(
        chat_id for chat_id in [CHAT_ID, CHAT_ID_2] if chat_id
    ))

    if not chat_id_listesi:
        print("HATA: CHAT_ID ve CHAT_ID_2 tanımlanmamış.")
        return

    for chat_id in chat_id_listesi:
        try:
            cevap = requests.post(
                telegram_url,
                data={
                    "chat_id": chat_id,
                    "text": mesaj,
                    "disable_web_page_preview": True
                },
                timeout=20
            )

            if cevap.status_code == 200 and cevap.json().get("ok"):
                print(f"Telegram mesajı gönderildi: {chat_id}")
            else:
                print(
                    f"Telegram gönderim hatası ({chat_id}): "
                    f"{cevap.status_code} {cevap.text}"
                )

        except Exception as e:
            print(f"Telegram bağlantı hatası ({chat_id}):", e)

# ===========================
# GEMINI AI TRADE ANALİZİ
# ===========================

def ai_analiz(sembol, baslik, ozet):
    if not GEMINI_API_KEY:
        return "AI analizi yapılamadı: GEMINI_API_KEY tanımlanmamış."

    prompt = f"""
Sen borsa ve KAP bildirimlerini değerlendiren bir analiz asistanısın.
Haberin olası etkisini değerlendir; kesin fiyat hareketi veya getiri
garantisi verme. Güncel fiyat ve grafik verisi verilmediyse destek,
direnç ve günlük marjın kesin hesaplanamayacağını belirt.

Şirket/sembol: {sembol}
KAP başlığı: {baslik}
KAP özeti: {ozet}

Şu formatta kısa yanıt ver:

Etki: (Pozitif / Negatif / Nötr)
Temel Haber Skoru: (0-100)
Günlük Trade Uygunluğu: (Uygun / Riskli / Tavsiye Edilmez)
Beklenen Günlük Marj: (Veri yoksa güvenilir şekilde tahmin edilemez yaz)
Destek / Direnç: (Güncel fiyat verisi yoksa belirlenemedi yaz)
Trade Yorumu: (En fazla 2 cümle)
Riskler: (En önemli riskleri kısaca belirt)

Haberin içeriğine dayan. Olmayan finansal veya teknik veriler uydurma.
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )

    try:
        r = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY
            },
            json={
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            },
            timeout=60
        )

        if r.status_code != 200:
            print("Gemini API Hatası:", r.status_code, r.text[:1000])
            return f"AI analizi başarısız oldu (HTTP {r.status_code})."

        veri = r.json()
        adaylar = veri.get("candidates", [])

        if not adaylar:
            print("Gemini yanıtında analiz bulunamadı:", veri)
            return "AI analizi için kullanılabilir yanıt alınamadı."

        parcalar = adaylar[0].get("content", {}).get("parts", [])
        metinler = [
            parca.get("text", "")
            for parca in parcalar
            if parca.get("text")
        ]

        if not metinler:
            return "Gemini yanıtı boş geldi."

        return "\n".join(metinler)

    except Exception as e:
        print("Gemini bağlantı hatası:", e)
        return "AI analizinde bağlantı hatası oluştu."

# ===========================
# KAP BOTU
# ===========================

print("KAP GÜNLÜK TRADE BOTU BAŞLATILDI")

telegram_gonder(
    "⚡ KAP Günlük Trade Analiz Botu Aktif\n"
    "✅ Telegram bildirim sistemi başlatıldı."
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
            KAP_URL,
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
            key=lambda x: (
                x.get("disclosureBasic") or {}
            ).get("disclosureIndex") or 0
        )

        # İlk başarılı sorguda mevcut bildirimleri hafızaya al.
        if ilk_acilis:
            for item in data:
                bilgi = item.get("disclosureBasic") or {}
                idx = bilgi.get("disclosureIndex")

                if idx is not None:
                    gorulen.add(idx)

            print(f"{len(gorulen)} eski bildirim hafızaya alındı.")
            print("Bot yeni KAP bildirimlerini dinliyor.\n")

            ilk_acilis = False
            time.sleep(15)
            continue

        for item in data:
            bilgi = item.get("disclosureBasic") or {}
            idx = bilgi.get("disclosureIndex")

            if idx is None or idx in gorulen:
                continue

            # Aynı bildirimin tekrar işlenmesini engelle.
            gorulen.add(idx)

            baslik = bilgi.get("title") or ""
            ozet = bilgi.get("summary") or ""
            metin = (baslik + " " + ozet).casefold()

            if any(k.casefold() in metin for k in IGNORE):
                continue

            if not any(k.casefold() in metin for k in KEYWORDS):
                continue

            sembol = (
                bilgi.get("relatedStocks")
                or bilgi.get("stockCode")
                or "-"
            )

            sirket = bilgi.get("companyTitle") or "-"
            saat = bilgi.get("publishDate") or "-"
            disclosure_id = bilgi.get("disclosureId")

            if disclosure_id:
                link = (
                    f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"
                )
            else:
                link = "Bildirim bağlantısı bulunamadı"

            print("=" * 90)
            print("🟢 TRADE SİNYALİ YAKALANDI")
            print("Şirket :", sirket)
            print("Sembol :", sembol)
            print("Başlık :", baslik)

            analiz = ai_analiz(sembol, baslik, ozet)
            print(analiz)

            mesaj = (
                "⚡ GÜNLÜK TRADE SİNYALİ\n\n"
                f"🏢 {sirket}\n"
                f"📈 {sembol}\n\n"
                f"📄 {baslik}\n\n"
                f"📝 {ozet}\n\n"
                f"🤖 AI ANALİZİ\n{analiz}\n\n"
                f"🕒 {saat}\n\n"
                f"🔗 {link}"
            )

            telegram_gonder(mesaj)
            print("Bildirim gönderimi tamamlandı.\n")

    except requests.exceptions.Timeout:
        print("KAP API zaman aşımı.")

    except requests.exceptions.RequestException as e:
        print("KAP bağlantı hatası:", e)

    except Exception as e:
        print("BOT HATASI:", repr(e))

    time.sleep(15)
