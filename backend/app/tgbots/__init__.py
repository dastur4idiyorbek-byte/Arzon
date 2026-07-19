"""Telegram botlar — webhook rejimi (bulutda, backend bilan bitta jarayonда).

Bu paket botlarni Render'да PowerShell'siz, 24/7 ishlatish uchun:
  * Telegram xabarlari webhook orqali backend'ga keladi
    (POST /webhook/telegram/savdo va /webhook/telegram/boshqaruv);
  * bot handlerlari backend API'ni localhost orqali chaqiradi.

Lokal polling skriptlari (bots/ papkasi) zaxira sifatida qoladi — lekin
webhook o'rnatilgach, polling ishlatilmaydi (Telegram 409 qaytaradi).
"""
