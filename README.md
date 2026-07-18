# ARZON — Multi-vendor Telegram/Instagram savdo platformasi

ARZON — Telegram va Instagram orqali ishlaydigan ko'p sotuvchili (multi-vendor)
onlayn do'kon. Mijoz uchun bu bitta yagona do'kon kabi ko'rinadi, lekin ortida
bir nechta admin (do'kon) bo'lishi mumkin. AI chat-yordamchi (Claude) va
semantik qidiruv (ChromaDB) bilan jihozlangan.

## Loyiha tuzilmasi

```
Arzon/
├── backend/                 # FastAPI backend (API, xavfsizlik, biznes-mantiq)
│   ├── app/
│   │   ├── main.py          # FastAPI kirish nuqtasi
│   │   ├── config.py        # .env sozlamalari
│   │   ├── database.py      # SQLAlchemy ulanishi
│   │   ├── models.py        # ORM modellar (database_schema)
│   │   ├── schemas.py       # Pydantic sxemalari
│   │   ├── security.py      # initData HMAC, check_store_access, rate-limit
│   │   ├── ai.py            # Claude integratsiyasi + system prompt
│   │   ├── vector_store.py  # ChromaDB (semantik qidiruv)
│   │   ├── routers/         # products, orders, chat, loyalty, bot, admin, instagram
│   │   └── services/        # catalog (mahfiy kod), orders (kod), loyalty
│   ├── tests/               # E2E testlar — 11 arxitektura qoidasini tekshiradi
│   ├── seed.py              # Demo ma'lumotlar
│   └── requirements.txt
├── bots/
│   ├── common.py            # Umumiy backend API mijozi
│   ├── savdo_bot/           # Mijozlar uchun bot (AI chat, Mini App, /holat)
│   ├── boshqaruv_bot/       # Adminlar uchun bot (mahsulot, buyurtma, mahfiy kod)
│   └── requirements.txt
├── miniapp/                 # Telegram Mini App (bitta umumiy katalog)
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── config.js            # Backend URL sozlamasi
├── .env.example
└── README.md
```

## Kritik arxitektura qoidalari (qanday amalga oshirilgan)

Bu 11 qoida loyihaning asosidir. Har biri kodда qayerда bajarilgani:

| # | Qoida | Amalga oshirish |
|---|-------|-----------------|
| 1 | Bitta umumiy katalog (do'kon tanlash yo'q) | `services/catalog.py:get_catalog` — barcha do'kon mahsulotlari bitta ro'yxatда; `miniapp/app.js:loadCatalog` |
| 2 | Do'konni yashirish yo'q | `models.py:Store` — faqat `mahfiy_kirish_kodi`, boshqa ko'rinish/havola maydoni yo'q |
| 3 | Do'kon uchun bitta mahfiy kod | `Store.mahfiy_kirish_kodi` + `Product.korinish='mahfiy'`; kod mahsulotга emas, do'konга |
| 4 | Kod faqat Boshqaruv Botiда | `routers/admin.py:refresh_secret_code`; Mini App/Savdo Bot faqat KIRITADI (`/api/unlock`) |
| 5 | Kod doimiy ochiq | `models.py:UnlockedStore` — bir marta kiritilса saqlanadi |
| 6 | Kod yangilansა qayta yopiladi | `services/catalog.py:get_unlocked_store_ids` — o'qish paytiда `ishlatilgan_kod == joriy kod` solishtiriladi; alohida "tozalash" yo'q |
| 7 | Admin izolyatsiyasi | `security.py:check_store_access` — har admin-endpointда chaqiriladi, ruxsat yo'q bo'lsా 403 |
| 8 | Ikki bosqichli tasdiqlash | `security.py:verify_init_data` (HMAC-SHA256) + `routers/orders.py:confirm_phone` (kontakt) |
| 9 | Sodiqlik umumiy (user_id) | `services/loyalty.py:count_purchases` — barcha do'konlar bo'yicha jamlanadi |
| 10 | Savat do'kon bo'yicha ajratiladi | `services/orders.py:create_orders_from_cart` — har store_id uchun alohida buyurtma+kod |
| 11 | Yangi admin faqat super-admin | `routers/admin.py:create_store` — `is_super_admin` tekshiruvi; `admin_ids` bazада (real vaqtда) |

## Ishga tushirish

### 1. Sozlamalar

```bash
cp .env.example .env
# .env'ni to'ldiring: bot tokenlar, Claude API kaliti, SUPER_ADMIN_IDS,
# INTERNAL_API_TOKEN (tasodifiy uzun qator).
python -c "import secrets; print(secrets.token_urlsafe(32))"  # INTERNAL_API_TOKEN uchun
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py            # (ixtiyoriy) demo ma'lumotlar
uvicorn app.main:app --reload
# API hujjatlari: http://localhost:8000/docs
```

> `.env` faylini backend ildizида (yoki `backend/` ичида) joylashtiring. `chromadb`
> va `anthropic` o'rnatilmasა ham backend ishlaydi (qidiruv/AI zaxira rejimда).

### 3. Botlar

```bash
cd bots
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python savdo_bot/bot.py       # alohida terminalда
python boshqaruv_bot/bot.py   # alohida terminalда
```

### 4. Mini App

`miniapp/config.js` ичидаги `ARZON_API_URL`'ni backend manzilингизга o'zgartiring,
so'ng `miniapp/` papkasини Vercel yoki Netlify'ga joylashtiring. BotFather'да
Savdo Botiга Mini App URL'ini ulang (`/setmenubutton` yoki WebApp tugmasi).

## Xavfsizlik modeli

- **Mini App → backend**: har so'rovда `X-Telegram-Init-Data` sarlavhasi;
  backend HMAC-SHA256 imzoni tekshiradi (rule 8, 1-bosqich).
- **Botlar → backend**: `X-Internal-Token` (ishonchli server-server). Admin
  darajасидaги ruxsat esa `check_store_access` orqali (rule 7).
- **Rate-limit**: kod kiritish urinishлари cheklangan (brute-force himoyа).
- **Telefon tasdiqlash**: birinchi buyurtмада Telegram kontakti (SMS-OTP kerak emas).

## Testlar

11 arxitektura qoidасини uchdan-uchiga tekshiruvchi testlar:

```bash
cd backend && source .venv/bin/activate
pip install pytest
python -m pytest tests/ -v
```

Testlar quyidagиларни tasdiqlaydi: bitta umumiy katalog (rule 1), admin
izolyatsiyаси/403 (rule 7), soxta initData rad etilиши (rule 8), mahfiy kod
ochilиши va yangilanganда qayta yopilиши (rule 3, 6), savat do'kon bo'yicha
ajratilиши (rule 10), sodiqlik jamlanиши (rule 9), rate-limit (phase 3.6),
faqat super-admin do'kon qo'shиши (rule 11).

## Holat (build_plan bo'yicha)

Amalga oshirilgan: Faza 2 (backend, multi-vendor, `check_store_access`),
Faza 3 (buyurtma kodi, initData, rate-limit, kontakt), Faza 4 (sodiqlik,
referal, promo), Faza 5 (Savdo Boti), Faza 6 (Instagram webhook skeleti),
Faza 7 (Mini App — bitta katalog), Faza 8 (Boshqaruv Boti, super-admin).

Tashqi hisob/kalit talab qiladigan qadamlar (BotFather tokenlar, Meta Developer
akkaunt, Anthropic kaliti, hosting) `.env` va joylashtириш bo'limларида
hujjatlashtirilgan — ular sizнинг hisoblaringiz bilan to'ldirилади.
