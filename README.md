# VFS Fransa Randevu Takip Botu 🚀

7/24 çalışan otomatik VFS Fransa randevu takip botu. Tüm Türkiye şehirlerinden (Gaziantep öncelikli) randevu kontrolü yapar ve Telegram'dan bildirim gönderir.

## Özellikler ✨

- ✅ 6 şehir kontrolü (Gaziantep, İstanbul, Ankara, İzmir, Antalya, Bursa)
- 🔥 Gaziantep öncelikli bildirim (Adana'ya yakın)
- 📱 Telegram bildirimleri
- 📝 Detaylı loglama
- 🔄 Otomatik hata yönetimi
- ⏱️ Her 5 dakikada kontrol

## Kurulum

### 1. Gereksinimler
```bash
pip install -r requirements.txt
```

### 2. Telegram Bot Ayarları
1. @BotFather'dan bot oluşturun
2. Bot token'ını alın
3. Bota /start gönderin
4. `vfs_fransa_alarm.py` dosyasındaki BOT_TOKEN ve CHAT_ID'yi güncelleyin

### 3. Lokal Çalıştırma
```bash
python vfs_fransa_alarm.py
```

## Bulut Sunucuda Çalıştırma (7/24)

### Seçenek 1: PythonAnywhere (Ücretsiz)

1. [PythonAnywhere](https://www.pythonanywhere.com/) hesabı oluşturun
2. Files > Upload files > dosyaları yükleyin
3. Consoles > Bash console açın:
```bash
pip install --user -r requirements.txt
python vfs_fransa_alarm.py
```
4. Tasks > Always-on task ekleyin (ücretli hesapta)

### Seçenek 2: Replit (Ücretsiz)

1. [Replit](https://replit.com/) hesabı oluşturun
2. New Repl > Python
3. Dosyaları yükleyin
4. Run tuşuna basın
5. Always On özelliğini aktif edin

### Seçenek 3: Railway.app ($5/ay ücretsiz)

1. [Railway](https://railway.app/) hesabı oluşturun
2. New Project > Deploy from GitHub
3. Repository'yi bağlayın
4. Otomatik deploy olur

### Seçenek 4: Google Cloud (90 gün ücretsiz)

1. Google Cloud hesabı oluşturun
2. Compute Engine > VM instance oluşturun
3. SSH ile bağlanın
4. Dosyaları yükleyin ve çalıştırın

## Log Dosyası

Program `vfs_alarm.log` dosyasına tüm işlemleri kaydeder.

## Lisans

MIT
