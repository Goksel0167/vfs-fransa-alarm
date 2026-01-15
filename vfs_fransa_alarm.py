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

# 🔍 Arama Kelimeleri - Fransa turist vizesi randevu
ARAMA_KELIMELERI = [
    "vfs fransa randevu",
    "fransa vizesi randevu",
    "gaziantep fransa randevu",
    "ankara fransa randevu",
    "vfs randevu açıldı",
    "fransa turist vizesi randevu",
    "schengen randevu",
    "france visa appointment"
]

# 📱 Kontrol edilecek sosyal platformlar
PLATFORMLAR = {
    "eksisozluk": {
        "url": "https://eksisozluk.com/vfs-fransa--7234567",
        "aktif": True
    },
    "twitter": {
        "url": "https://twitter.com/search?q=vfs+fransa+randevu&f=live",
        "aktif": False  # Twitter API key gerekir
    }
}

# 🕒 Görülen paylaşımları sakla (tekrar bildirim göndermeyi engelle)
gorulmus_paylasimllar = set()

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

def eksisozluk_kontrol():
    """Ekşi Sözlük VFS Fransa başlığını kontrol et"""
    try:
        logger.info("🔍 Ekşi Sözlük kontrol ediliyor...")
        
        url = "https://eksisozluk.com/vfs-fransa--7234567"
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=20, verify=False)
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Ekşi Sözlük erişim hatası: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Son entry'leri al
        entries = soup.find_all("div", {"class": "content"}, limit=5)
        
        bulunan_bilgiler = []
        
        for entry in entries:
            entry_text = entry.get_text().lower()
            entry_id = entry.get("data-id", str(hash(entry_text[:50])))
            
            # Eğer daha önce görüldüyse atla
            if entry_id in gorulmus_paylasimllar:
                continue
            
            # Randevu açıldı mı kontrol et
            randevu_kelimeleri = ["randevu açıldı", "randevu var", "randevu buldum", "slot açıldı"]
            gaziantep_mi = "gaziantep" in entry_text
            ankara_mi = "ankara" in entry_text
            turist_mi = "turist" in entry_text or "tourism" in entry_text
            
            if any(kelime in entry_text for kelime in randevu_kelimeleri):
                gorulmus_paylasimllar.add(entry_id)
                
                sehir = "Bilinmiyor"
                if gaziantep_mi:
                    sehir = "Gaziantep"
                elif ankara_mi:
                    sehir = "Ankara"
                
                bulunan_bilgiler.append({
                    "platform": "Ekşi Sözlük",
                    "sehir": sehir,
                    "turist": turist_mi,
                    "metin": entry_text[:200]
                })
                logger.info(f"✅ Ekşi'de yeni paylaşım bulundu: {sehir}")
        
        return bulunan_bilgiler
        
    except Exception as e:
        logger.error(f"❌ Ekşi Sözlük kontrol hatası: {e}")
        return []

def reddit_kontrol():
    """Reddit r/Turkey'de VFS randevu paylaşımlarını kontrol et"""
    try:
        logger.info("🔍 Reddit kontrol ediliyor...")
        
        # Reddit arama URL'i
        url = "https://www.reddit.com/r/Turkey/search.json?q=vfs+fransa+randevu&sort=new&restrict_sr=1&limit=10"
        
        headers = BROWSER_HEADERS.copy()
        headers["User-Agent"] = "Mozilla/5.0 (compatible; VFSBot/1.0)"
        
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Reddit erişim hatası: {response.status_code}")
            return []
        
        data = response.json()
        posts = data.get("data", {}).get("children", [])
        
        bulunan_bilgiler = []
        
        for post in posts[:5]:
            post_data = post.get("data", {})
            title = post_data.get("title", "").lower()
            selftext = post_data.get("selftext", "").lower()
            post_id = post_data.get("id", "")
            
            if post_id in gorulmus_paylasimllar:
                continue
            
            combined_text = title + " " + selftext
            
            randevu_kelimeleri = ["randevu açıldı", "randevu var", "randevu buldum", "appointment available"]
            gaziantep_mi = "gaziantep" in combined_text
            ankara_mi = "ankara" in combined_text
            turist_mi = "turist" in combined_text or "tourism" in combined_text
            
            if any(kelime in combined_text for kelime in randevu_kelimeleri):
                gorulmus_paylasimllar.add(post_id)
                
                sehir = "Bilinmiyor"
                if gaziantep_mi:
                    sehir = "Gaziantep"
                elif ankara_mi:
                    sehir = "Ankara"
                
                bulunan_bilgiler.append({
                    "platform": "Reddit",
                    "sehir": sehir,
                    "turist": turist_mi,
                    "metin": title[:200]
                })
                logger.info(f"✅ Reddit'te yeni paylaşım bulundu: {sehir}")
        
        return bulunan_bilgiler
        
    except Exception as e:
        logger.error(f"❌ Reddit kontrol hatası: {e}")
        return []

def twitter_kontrol():
    """Twitter'da VFS Fransa randevu paylaşımlarını kontrol et"""
    try:
        logger.info("🔍 Twitter kontrol ediliyor...")
        
        # Nitter (Twitter alternatif frontend) kullan
        url = "https://nitter.net/search?f=tweets&q=vfs+fransa+randevu&since=&until=&near="
        
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=20, verify=False)
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Twitter erişim hatası: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        tweets = soup.find_all("div", {"class": "timeline-item"}, limit=5)
        
        bulunan_bilgiler = []
        
        for tweet in tweets:
            try:
                tweet_text = tweet.get_text().lower()
                tweet_link = tweet.find("a", {"class": "tweet-link"})
                tweet_id = str(hash(tweet_text[:50])) if tweet_link else str(hash(tweet_text[:30]))
                
                if tweet_id in gorulmus_paylasimllar:
                    continue
                
                randevu_kelimeleri = ["randevu açıldı", "randevu var", "randevu buldum", "slot açıldı", "müsait"]
                gaziantep_mi = "gaziantep" in tweet_text
                ankara_mi = "ankara" in tweet_text
                turist_mi = "turist" in tweet_text or "tourism" in tweet_text
                vfs_fransa = "vfs" in tweet_text and "fransa" in tweet_text
                
                if vfs_fransa and any(kelime in tweet_text for kelime in randevu_kelimeleri):
                    gorulmus_paylasimllar.add(tweet_id)
                    
                    sehir = "Bilinmiyor"
                    if gaziantep_mi:
                        sehir = "Gaziantep"
                    elif ankara_mi:
                        sehir = "Ankara"
                    
                    bulunan_bilgiler.append({
                        "platform": "Twitter (X)",
                        "sehir": sehir,
                        "turist": turist_mi,
                        "metin": tweet_text[:200]
                    })
                    logger.info(f"✅ Twitter'da yeni paylaşım bulundu: {sehir}")
            except:
                continue
        
        return bulunan_bilgiler
        
    except Exception as e:
        logger.error(f"❌ Twitter kontrol hatası: {e}")
        return []

def instagram_kontrol():
    """Instagram'da VFS Fransa hashtag'lerini kontrol et"""
    try:
        logger.info("🔍 Instagram kontrol ediliyor...")
        
        # Instagram public hashtag sayfası
        hashtags = ["vfsfransa", "fransavizesi", "vfsglobal"]
        bulunan_bilgiler = []
        
        for hashtag in hashtags:
            try:
                url = f"https://www.instagram.com/explore/tags/{hashtag}/"
                response = requests.get(url, headers=BROWSER_HEADERS, timeout=20)
                
                if response.status_code != 200:
                    continue
                
                # Instagram JSON verisi sayfada gömülü olabilir
                if "randevu" in response.text.lower() or "appointment" in response.text.lower():
                    logger.info(f"💡 Instagram #{hashtag} - Potansiyel randevu paylaşımı algılandı")
                    # Not: Instagram API olmadan detaylı bilgi almak zor
            except:
                continue
        
        return bulunan_bilgiler
        
    except Exception as e:
        logger.error(f"❌ Instagram kontrol hatası: {e}")
        return []

def facebook_kontrol():
    """Facebook gruplarında VFS Fransa randevu paylaşımlarını kontrol et"""
    try:
        logger.info("🔍 Facebook kontrol ediliyor...")
        
        # Facebook public search
        search_query = "vfs fransa randevu"
        url = f"https://www.facebook.com/public?query={search_query.replace(' ', '%20')}"
        
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=20)
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Facebook erişim hatası: {response.status_code}")
            return []
        
        # Facebook login olmadan detaylı erişim sınırlı
        if "randevu açıldı" in response.text.lower() or "randevu var" in response.text.lower():
            logger.info("💡 Facebook - Potansiyel randevu paylaşımı algılandı")
        
        return []
        
    except Exception as e:
        logger.error(f"❌ Facebook kontrol hatası: {e}")
        return []

def tum_platformlari_kontrol():
    """Tüm sosyal medya platformlarını kontrol et ve randevu paylaşımlarını topla"""
    tum_bulgular = []
    
    # Ekşi Sözlük kontrolü
    try:
        eksisozluk_bulgular = eksisozluk_kontrol()
        tum_bulgular.extend(eksisozluk_bulgular)
    except Exception as e:
        logger.error(f"❌ Ekşi Sözlük genel hatası: {e}")
    
    time.sleep(2)  # Platformlar arası bekleme
    
    # Reddit kontrolü
    try:
        reddit_bulgular = reddit_kontrol()
        tum_bulgular.extend(reddit_bulgular)
    except Exception as e:
        logger.error(f"❌ Reddit genel hatası: {e}")
    
    time.sleep(2)  # Platformlar arası bekleme
    
    # Twitter kontrolü
    try:
        twitter_bulgular = twitter_kontrol()
        tum_bulgular.extend(twitter_bulgular)
    except Exception as e:
        logger.error(f"❌ Twitter genel hatası: {e}")
    
    time.sleep(2)  # Platformlar arası bekleme
    
    # Instagram kontrolü
    try:
        instagram_bulgular = instagram_kontrol()
        tum_bulgular.extend(instagram_bulgular)
    except Exception as e:
        logger.error(f"❌ Instagram genel hatası: {e}")
    
    time.sleep(2)  # Platformlar arası bekleme
    
    # Facebook kontrolü
    try:
        facebook_bulgular = facebook_kontrol()
        tum_bulgular.extend(facebook_bulgular)
    except Exception as e:
        logger.error(f"❌ Facebook genel hatası: {e}")
    
    return tum_bulgular

def randevu_kontrol_sehir(sehir_adi, url):
    """Bir şehir için randevu kontrolü yap - SADECE kesin randevu varsa True döner"""
    try:
        # Session kullan - daha gerçekçi tarayıcı davranışı
        session = requests.Session()
        
        # İlk olarak ana sayfaya git (normal kullanıcı gibi)
        session.get(VFS_BASE_URL, headers=BROWSER_HEADERS, timeout=15)
        time.sleep(1)  # İnsan gibi davran
        
        # Randevu sayfasını kontrol et
        response = session.get(url, headers=BROWSER_HEADERS, timeout=20)
        response.raise_for_status()
        
        # Sayfa içeriğini kontrol et
        if len(response.text) < 100:
            logger.warning(f"⚠️ {sehir_adi} - Sayfa içeriği çok kısa, gerçek veri değil")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        sayfa_metni = soup.get_text().lower()
        
        # ÖNCE: Sayfanın gerçekten VFS sayfası olduğunu doğrula
        vfs_dogrulama = ["vfs", "visa", "appointment", "randevu"]
        vfs_sayfa_mi = any(kelime in sayfa_metni for kelime in vfs_dogrulama)
        
        if not vfs_sayfa_mi:
            logger.warning(f"⚠️ {sehir_adi} - VFS sayfası değil, bot koruması olabilir")
            return None
        
        # "RANDEVU YOK" kelimeleri - AÇIKÇA belirtmeli
        randevu_yok_kelimeleri = [
            "no appointment",
            "randevu yok",
            "no slots available",
            "uygun slot yok",
            "no available",
            "müsait değil",
            "currently no slots",
            "şu anda randevu yok"
        ]
        
        # "RANDEVU VAR" kelimeleri - AÇIKÇA belirtmeli
        randevu_var_kelimeleri = [
            "book appointment",
            "randevu al",
            "available slots",
            "uygun randevu",
            "select date",
            "tarih seç"
        ]
        
        # AÇIKÇA "randevu yok" yazıyorsa - kesin olarak yok
        randevu_yok_bulundu = any(kelime in sayfa_metni for kelime in randevu_yok_kelimeleri)
        
        # AÇIKÇA "randevu var" yazıyorsa - kesin olarak var
        randevu_var_bulundu = any(kelime in sayfa_metni for kelime in randevu_var_kelimeleri)
        
        if randevu_yok_bulundu:
            # AÇIKÇA randevu yok deniyor
            logger.info(f"✓ {sehir_adi} - Kesin: RANDEVU YOK")
            return False
        elif randevu_var_bulundu and not randevu_yok_bulundu:
            # AÇIKÇA randevu var deniyor VE randevu yok yazmıyor
            logger.info(f"🎯 {sehir_adi} - Kesin: RANDEVU VAR!")
            return True
        else:
            # BELİRSİZ - bildirim GÖNDERME
            logger.warning(f"❓ {sehir_adi} - Belirsiz durum, gerçek veri okunamadı")
            return None
        
    except requests.exceptions.Timeout:
        logger.warning(f"⏱️ {sehir_adi} - Zaman aşımı (gerçek veri alınamadı)")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.warning(f"🔒 {sehir_adi} - Bot koruması aktif (gerçek veri alınamadı)")
        else:
            logger.error(f"🌐 {sehir_adi} - HTTP hatası: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 {sehir_adi} - Bağlantı hatası: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ {sehir_adi} - Beklenmeyen hata: {e}")
        return None

def tum_sehirleri_kontrol():
    """Tüm şehirleri kontrol et - SADECE kesin randevu varsa bildir"""
    randevu_bulunan_sehirler = []
    basarili_kontrol_sayisi = 0
    randevu_yok_sayisi = 0
    belirsiz_sayisi = 0
    
    # Şehirleri öncelik sırasına göre sırala
    sirali_sehirler = sorted(SEHIRLER.items(), key=lambda x: x[1]["oncelik"])
    
    for sehir, bilgi in sirali_sehirler:
        logger.info(f"🔍 {sehir} kontrol ediliyor...")
        logger.info(f"   📋 Kategori: {bilgi['kategori']}")
        logger.info(f"   🎯 Alt Kategori: {bilgi['alt_kategori']}")
        
        sonuc = randevu_kontrol_sehir(sehir, bilgi["url"])
        
        if sonuc is None:
            # Kontrol yapılamadı - BELİRSİZ
            belirsiz_sayisi += 1
            logger.warning(f"❓ {sehir} - Gerçek veri alınamadı (bot koruması veya hata)")
        elif sonuc is True:
            # KESİN OLARAK randevu var!
            basarili_kontrol_sayisi += 1
            randevu_bulunan_sehirler.append({
                "sehir": sehir,
                "kategori": bilgi["kategori"],
                "alt_kategori": bilgi["alt_kategori"],
                "oncelik": bilgi["oncelik"]
            })
            logger.info(f"🎯 {sehir} - KESİN: RANDEVU VAR!")
        else:  # sonuc is False
            # KESİN OLARAK randevu yok
            basarili_kontrol_sayisi += 1
            randevu_yok_sayisi += 1
            logger.info(f"✓ {sehir} - Kesin: Randevu yok")
        
        time.sleep(3)  # Şehirler arası bekleme
    
    # İstatistik
    logger.info(f"\n📊 KONTROL SONUCU:")
    logger.info(f"   ✅ Başarılı kontrol: {basarili_kontrol_sayisi}/{len(SEHIRLER)}")
    logger.info(f"   🎯 Randevu bulunan: {len(randevu_bulunan_sehirler)}")
    logger.info(f"   ❌ Randevu yok: {randevu_yok_sayisi}")
    logger.info(f"   ❓ Belirsiz: {belirsiz_sayisi}")
    
    # SADECE gerçek veri varsa ve randevu bulunduysa bildir
    if belirsiz_sayisi == len(SEHIRLER):
        logger.warning("⚠️ HİÇBİR ŞEHİR KONTROL EDİLEMEDİ - VFS bot koruması aktif")
        logger.warning("⚠️ Gerçek veri alınamadığı için BİLDİRİM GÖNDERİLMİYOR")
        return []
    
    # Eğer en az 1 başarılı kontrol varsa VE randevu bulunduysa bildir
    if basarili_kontrol_sayisi > 0 and len(randevu_bulunan_sehirler) > 0:
        logger.info("✅ Gerçek veri alındı ve RANDEVU BULUNDU - Bildirim gönderiliyor!")
        return randevu_bulunan_sehirler
    
    return []

def main():
    """Ana program döngüsü"""
    logger.info("="*70)
    logger.info("🚀 VFS Fransa SOSYAL MEDYA TAKİP başladı!")
    logger.info(f"📱 Kontrol edilen platformlar: Ekşi Sözlük, Reddit, Twitter, Instagram, Facebook")
    logger.info(f"🔍 Aranan: Fransa kısa dönem turist standard vize randevu")
    logger.info(f"📍 Şehirler: Gaziantep (ÖNCELİKLİ), Ankara")
    logger.info(f"⏱️ Kontrol sıklığı: Her 3 dakikada")
    logger.info("="*70)
    
    # Başlangıç bildirimi
    baslangic_mesaj = "✅ <b>Sosyal Medya Takip Botu Başladı!</b>\n\n"
    baslangic_mesaj += "🔍 <b>TAKİP EDİLEN PLATFORMLAR:</b>\n"
    baslangic_mesaj += "└ Ekşi Sözlük (VFS Fransa başlığı)\n"
    baslangic_mesaj += "└ Reddit r/Turkey\n"
    baslangic_mesaj += "└ Twitter / X (arama)\n"
    baslangic_mesaj += "└ Instagram (#vfsfransa)\n"
    baslangic_mesaj += "└ Facebook (gruplar)\n\n"
    baslangic_mesaj += "📋 <b>ARANAN BİLGİLER:</b>\n"
    baslangic_mesaj += "└ Fransa turist vizesi randevu\n"
    baslangic_mesaj += "└ Gaziantep & Ankara\n"
    baslangic_mesaj += "└ Kısa dönem - Standard\n\n"
    baslangic_mesaj += "🔔 Birisi randevu paylaştığında hemen bilgi alacaksınız!"
    telegram_mesaj_gonder(baslangic_mesaj)
    
    hata_sayaci = 0
    max_hata = 5
    
    while True:
        try:
            logger.info(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Yeni tarama başlıyor...")
            
            randevu_paylasimlari = tum_platformlari_kontrol()
            
            if randevu_paylasimlari:
                # Bulguları bildir
                for bulgu in randevu_paylasimlari:
                    if bulgu["sehir"] == "Gaziantep":
                        mesaj = "🔥 <b>ACİL! SOSYAL MEDYADA RANDEVUİLGİSİ!</b> 🔥\n\n"
                        mesaj += f"📱 <b>Platform:</b> {bulgu['platform']}\n"
                        mesaj += f"📍 <b>Şehir:</b> {bulgu['sehir']} (ÖNCELİKLİ)\n"
                    else:
                        mesaj = "🚨 <b>SOSYAL MEDYADA RANDEVU BİLGİSİ!</b> 🚨\n\n"
                        mesaj += f"📱 <b>Platform:</b> {bulgu['platform']}\n"
                        mesaj += f"📍 <b>Şehir:</b> {bulgu['sehir']}\n"
                    
                    if bulgu["turist"]:
                        mesaj += "✅ Turist vizesi onaylandı\n"
                    
                    mesaj += f"\n📝 <b>Paylaşım:</b>\n{bulgu['metin'][:150]}...\n"
                    mesaj += "\n🔗 <b>HEMEN KONTROL ET:</b>\n"
                    mesaj += "https://visa.vfsglobal.com/tur/tr/fra/"
                    
                    telegram_mesaj_gonder(mesaj)
                    logger.info("📱 Randevu bildirimi gönderildi!")
                    time.sleep(5)  # Mesajlar arası bekleme
                
                logger.info("⏸️ 10 dakika bekleniyor...")
                time.sleep(600)  # Bulgu sonrası 10 dakika bekle
            else:
                logger.info("❌ Henüz randevu paylaşımı bulunamadı")
                logger.info("⏸️ 3 dakika bekleniyor...")
                time.sleep(180)  # 3 dakika bekle
            
            hata_sayaci = 0  # Başarılı kontrol
            
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
            
            logger.info("⏸️ 5 dakika sonra tekrar denenecek...")
            time.sleep(300)

if __name__ == "__main__":
    main()
