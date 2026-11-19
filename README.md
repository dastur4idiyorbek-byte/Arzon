# ARZON 2.0

Ko‘p sotuvchili onlayn savdo platformasi uchun FastAPI backend va React Native (Expo) ilova.

## Asosiy tuzilmalar

- `backend/app/main.py` — FastAPI kirish nuqtasi
- `backend/app/models.py` — SQLAlchemy modellari
- `backend/app/routers/` — autentifikatsiya, katalog, buyurtmalar, admin, kuryer va media API’lari
- `backend/app/services/` — autentifikatsiya, push-bildirishnoma va kunlik vazifalar
- `mobile/` — React Native ilova
- `bots/` — Telegram botlari

## Ishga tushirish

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Testlar:

```bash
python -m pytest backend/tests -v
```

## Muhim holatlar

- Super-admin ro‘li `SUPER_ADMIN_EMAILS` env parametri orqali belgilanadi.
- Kuryer ro‘li `is_kuryer=True` yoki `KURYER_EMAILS` orqali beriladi.
- `demo_tozalash.py` ARZON 2.0 da bekor qilingan eski demo-tozalash skriptidir.
