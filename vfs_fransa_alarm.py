import requests
import time
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import sys
import os

# 📝 Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vfs_alarm.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 🔐 Telegram bilgileri - Environment Variables'dan al (GÜVENLİ)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# Token kontrolü
if not BOT_TOKEN or not CHAT_ID:
    logger.error("❌ HATA: BOT_TOKEN veya CHAT_ID environment variable olarak ayarlanmamış!")
    logger.error("Railway.app'te Variables bölümünden bu değerleri ekleyin.")
    sys.exit(1)

# 🎯 VFS Fransa Başvuru Detayları
VFS_BASE_URL = "https://visa.vfsglobal.com/tur/tr/fra"

# ✅ Sadece Ankara ve Gaziantep (Gaziantep ÖNCELİKLİ)
# 📋 Başvuru Kategorisi: Kısa dönem - Short term
# 🎯 Alt Kategori: Tourism - Premiere demande, Standard
SEHIRLER = {
    "Gaziantep": {
        "url": f"{VFS_BASE_URL}/book-an-appointment",
        "kategori": "Kısa dönem - Short term",
        "alt_kategori": "Tourism - Premiere demande / Standard",
        "oncelik": 1  # En yüksek öncelik
    },
    "Ankara": {
        "url": f"{VFS_BASE_URL}/book-an-appointment",
        "kategori": "Kısa dönem - Short term", 
        "alt_kategori": "Tourism - Premiere demande / Standard",
        "oncelik": 2
    }
}

# Daha gerçekçi tarayıcı başlıkları
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0"
}

def telegram_mesaj_gonder(mesaj):
    """Telegram'a mesaj gönder - yeniden deneme mekanizmalı"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mesaj,
        "parse_mode": "HTML"
    }
    
    for deneme in range(3):  # 3 kez dene
        try:
            response = requests.post(url, data=payload, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Telegram mesajı başarıyla gönderildi")
                return True
            else:
                logger.warning(f"⚠️ Telegram hata kodu: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Telegram gönderim hatası (deneme {deneme+1}/3): {e}")
            time.sleep(5)
    
    return False

def randevu_kontrol_sehir(sehir_adi, url):
    """Bir şehir için randevu kontrolü yap - None döner ise kontrol yapılamadı"""
    try:
        # Session kullan - daha gerçekçi tarayıcı davranışı
        session = requests.Session()
        
        # İlk olarak ana sayfaya git (normal kullanıcı gibi)
        session.get(VFS_BASE_URL, headers=BROWSER_HEADERS, timeout=15)
        time.sleep(1)  # İnsan gibi davran
        
        # Randevu sayfasını kontrol et
        response = session.get(url, headers=BROWSER_HEADERS, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        sayfa_metni = soup.get_text().lower()
        
        # Randevu kontrolü - daha kapsamlı kelime kontrolü
        randevu_yok_kelimeleri = [
            "no appointment",
            "randevu yok",
            "no slots available",
            "uygun slot yok",
            "no available",
            "müsait değil"
        ]
        
        # Hiçbir "randevu yok" kelimesi yoksa randevu var demektir
        randevu_var = not any(kelime in sayfa_metni for kelime in randevu_yok_kelimeleri)
        
        return randevu_var
        
    except requests.exceptions.Timeout:
        logger.warning(f"⏱️ {sehir_adi} - Zaman aşımı (kontrol yapılamadı)")
        return None  # Kontrol yapılamadı
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.warning(f"🔒 {sehir_adi} - Bot koruması aktif (kontrol yapılamadı)")
        else:
            logger.error(f"🌐 {sehir_adi} - HTTP hatası: {e}")
        return None  # Kontrol yapılamadı
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 {sehir_adi} - Bağlantı hatası: {e}")
        return None  # Kontrol yapılamadı
    except Exception as e:
        logger.error(f"❌ {sehir_adi} - Beklenmeyen hata: {e}")
        return None  # Kontrol yapılamadı

def tum_sehirleri_kontrol():
    """Tüm şehirleri kontrol et - Sadece başarılı kontrolleri bildir"""
    randevu_bulunan_sehirler = []
    basarisiz_kontrol_sayisi = 0
    
    # Şehirleri öncelik sırasına göre sırala
    sirali_sehirler = sorted(SEHIRLER.items(), key=lambda x: x[1]["oncelik"])
    
    for sehir, bilgi in sirali_sehirler:
        logger.info(f"🔍 {sehir} kontrol ediliyor...")
        logger.info(f"   📋 Kategori: {bilgi['kategori']}")
        logger.info(f"   🎯 Alt Kategori: {bilgi['alt_kategori']}")
        
        sonuc = randevu_kontrol_sehir(sehir, bilgi["url"])
        
        if sonuc is None:
            # Kontrol yapılamadı
            basarisiz_kontrol_sayisi += 1
            logger.warning(f"⚠️ {sehir} kontrol yapılamadı (bot koruması veya hata)")
        elif sonuc is True:
            # GERÇEKTEN randevu var!
            randevu_bulunan_sehirler.append({
                "sehir": sehir,
                "kategori": bilgi["kategori"],
                "alt_kategori": bilgi["alt_kategori"],
                "oncelik": bilgi["oncelik"]
            })
            logger.info(f"✅ {sehir}'da RANDEVU VAR!")
        else:
            # Randevu yok
            logger.info(f"⏳ {sehir}'da randevu yok")
        
        time.sleep(3)  # Şehirler arası bekleme
    
    # Eğer tüm şehirler kontrol yapılamadıysa, boş liste döndür
    if basarisiz_kontrol_sayisi == len(SEHIRLER):
        logger.warning("⚠️ Hiçbir şehir kontrol edilemedi - VFS sitesi bot koruması kullanıyor olabilir")
        return []
    
    return randevu_bulunan_sehirler

def main():
    """Ana program döngüsü"""
    logger.info("="*70)
    logger.info("🚀 VFS Fransa randevu takip başladı!")
    logger.info(f"📍 Kontrol edilen merkezler: Gaziantep (ÖNCELİKLİ), Ankara")
    logger.info(f"📋 Başvuru kategorisi: Kısa dönem - Short term")
    logger.info(f"🎯 Alt kategori: Tourism - Premiere demande / Standard")
    logger.info(f"⏱️ Kontrol sıklığı: 5 dakika")
    logger.info("="*70)
    
    # Başlangıç bildirimi
    baslangic_mesaj = "✅ <b>Bot başlatıldı!</b>\n\n"
    baslangic_mesaj += "📋 <b>KONTROL DETAYLARI:</b>\n"
    baslangic_mesaj += "└ Merkezler: Gaziantep (ÖNCELİKLİ), Ankara\n"
    baslangic_mesaj += "└ Kategori: Kısa dönem - Short term\n"
    baslangic_mesaj += "└ Alt Kategori: Tourism - Premiere demande / Standard\n"
    baslangic_mesaj += "└ Kontrol: Her 5 dakikada\n\n"
    baslangic_mesaj += "🔔 Randevu açıldığında hemen bildirim alacaksınız!"
    telegram_mesaj_gonder(baslangic_mesaj)
    
    hata_sayaci = 0
    max_hata = 5
    
    while True:
        try:
            logger.info(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Yeni kontrol başlıyor...")
            
            randevu_bulunan = tum_sehirleri_kontrol()
            
            if randevu_bulunan:
                # Öncelik sırasına göre mesaj oluştur
                randevu_bulunan_sirali = sorted(randevu_bulunan, key=lambda x: x["oncelik"])
                
                # En öncelikli şehir
                en_oncelikli = randevu_bulunan_sirali[0]
                
                if en_oncelikli["sehir"] == "Gaziantep":
                    mesaj = "🔥 <b>ACİL! GAZİANTEP'TE RANDEVU VAR!</b> 🔥\n\n"
                    mesaj += "📍 <b>Adana'ya en yakın şehir!</b>\n\n"
                else:
                    mesaj = "🚨 <b>FRANSA VFS RANDEVU AÇILDI!</b> 🚨\n\n"
                
                # Randevu detaylarını ekle
                mesaj += "📋 <b>BAŞVURU DETAYLARI:</b>\n"
                mesaj += f"└ Kategori: {en_oncelikli['kategori']}\n"
                mesaj += f"└ Alt Kategori: {en_oncelikli['alt_kategori']}\n\n"
                
                mesaj += "📍 <b>RANDEVU BULUNAN MERKEZLER:</b>\n"
                for randevu in randevu_bulunan_sirali:
                    if randevu["oncelik"] == 1:
                        mesaj += f"✅ <b>{randevu['sehir']}</b> (ÖNCELİKLİ)\n"
                    else:
                        mesaj += f"✅ {randevu['sehir']}\n"
                
                mesaj += "\n🔗 <b>HEMEN BAŞVUR:</b>\n"
                mesaj += "https://visa.vfsglobal.com/tur/tr/fra/"
                
                telegram_mesaj_gonder(mesaj)
                logger.info("📱 Randevu bildirimi gönderildi!")
                logger.info("⏸️ 1 saat bekleniyor...")
                time.sleep(3600)  # 1 saat bekle
            else:
                logger.info("❌ Hiçbir şehirde randevu bulunamadı")
                logger.info("⏸️ 5 dakika bekleniyor...")
                time.sleep(300)  # 5 dakika bekle
            
            hata_sayaci = 0  # Başarılı kontrol, hata sayacını sıfırla
            
        except KeyboardInterrupt:
            logger.info("\n⛔ Program kullanıcı tarafından durduruldu")
            telegram_mesaj_gonder("⛔ Bot durduruldu.")
            break
            
        except Exception as e:
            hata_sayaci += 1
            logger.error(f"❌ Genel hata ({hata_sayaci}/{max_hata}): {e}")
            
            if hata_sayaci >= max_hata:
                mesaj_hata = f"⚠️ Bot {max_hata} kez hata aldı. Lütfen kontrol edin!"
                telegram_mesaj_gonder(mesaj_hata)
                logger.critical("🛑 Maksimum hata sayısına ulaşıldı, bot duruyor")
                break
            
            logger.info("⏸️ 10 dakika sonra tekrar denenecek...")
            time.sleep(600)  # Hata durumunda 10 dakika bekle

if __name__ == "__main__":
    main()
