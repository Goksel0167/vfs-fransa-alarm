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

# 🎯 Tüm Türkiye şehirleri için VFS Fransa URL'leri
# Gaziantep ÖNCELİKLİ (Adana'ya en yakın)
VFS_BASE_URL = "https://visa.vfsglobal.com/tur/tr/fra"
SEHIRLER = {
    "Gaziantep": f"{VFS_BASE_URL}/book-an-appointment",  # ÖNCELİKLİ
    "İstanbul": f"{VFS_BASE_URL}/book-an-appointment",
    "Ankara": f"{VFS_BASE_URL}/book-an-appointment",
    "İzmir": f"{VFS_BASE_URL}/book-an-appointment",
    "Antalya": f"{VFS_BASE_URL}/book-an-appointment",
    "Bursa": f"{VFS_BASE_URL}/book-an-appointment"
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
    """Bir şehir için randevu kontrolü yap"""
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
        logger.warning(f"⏱️ {sehir_adi} - Zaman aşımı")
        return False
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.warning(f"🔒 {sehir_adi} - Site bot koruması aktif (403)")
        else:
            logger.error(f"🌐 {sehir_adi} - HTTP hatası: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 {sehir_adi} - Bağlantı hatası: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ {sehir_adi} - Beklenmeyen hata: {e}")
        return False

def tum_sehirleri_kontrol():
    """Tüm şehirleri kontrol et"""
    randevu_bulunan_sehirler = []
    
    for sehir, url in SEHIRLER.items():
        logger.info(f"🔍 {sehir} kontrol ediliyor...")
        
        randevu_var = randevu_kontrol_sehir(sehir, url)
        
        if randevu_var:
            randevu_bulunan_sehirler.append(sehir)
            logger.info(f"✅ {sehir}'da RANDEVU VAR!")
        else:
            logger.info(f"⏳ {sehir}'da randevu yok")
        
        time.sleep(3)  # Şehirler arası bekleme - sunucuya yük vermemek için
    
    return randevu_bulunan_sehirler

def main():
    """Ana program döngüsü"""
    logger.info("="*70)
    logger.info("🚀 VFS Fransa TÜRKİYE çapında randevu takip başladı!")
    logger.info(f"📍 Kontrol edilen şehirler: {', '.join(SEHIRLER.keys())}")
    logger.info(f"⏱️ Kontrol sıklığı: 5 dakika")
    logger.info("="*70)
    
    # Başlangıç bildirimi
    telegram_mesaj_gonder("✅ Bot başlatıldı! VFS Fransa randevu takibi aktif.")
    
    hata_sayaci = 0
    max_hata = 5
    
    while True:
        try:
            logger.info(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Yeni kontrol başlıyor...")
            
            randevu_bulunan = tum_sehirleri_kontrol()
            
            if randevu_bulunan:
                # Gaziantep öncelikli bildirim
                if "Gaziantep" in randevu_bulunan:
                    mesaj = "🔥 <b>ACİL! GAZİANTEP'TE RANDEVU VAR!</b> 🔥\n\n"
                    mesaj += "📍 <b>Adana'ya en yakın şehir!</b>\n"
                    mesaj += "✅ Gaziantep\n\n"
                    
                    if len(randevu_bulunan) > 1:
                        mesaj += "<b>Diğer şehirler:</b>\n"
                        for sehir in randevu_bulunan:
                            if sehir != "Gaziantep":
                                mesaj += f"✅ {sehir}\n"
                    
                    mesaj += "\n🔗 HEMEN BAŞVUR: https://visa.vfsglobal.com/tur/tr/fra/"
                else:
                    mesaj = "🚨 <b>FRANSA VFS RANDEVU AÇILDI!</b> 🚨\n\n"
                    mesaj += "📍 <b>Randevu Bulunan Şehirler:</b>\n"
                    for sehir in randevu_bulunan:
                        mesaj += f"✅ {sehir}\n"
                    mesaj += "\n🔗 Hemen başvur: https://visa.vfsglobal.com/tur/tr/fra/"
                
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
