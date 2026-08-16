# ARZON — Native ilova (React Native + Expo)

Bu — ARZON'ning barcha platformalarда (Android, iOS, Windows, macOS, Linux)
ishlaydigan **bitta** native ilovasi. Backend (FastAPI + Neon) **o'zgармaydi** —
ilova undan REST API orqali foydalanadi.

> Telegram botlari va Mini App o'z joyida turaveradi; bu ilova ularni
> bosqichma-bosqich almashtiradi.

---

## Hozirgi holat — 1 va 2-BOSQICH tayyor

**1-bosqich (asos):**
- ✅ Expo + TypeScript, pastki tab-navigatsiya, rol-rang dizayn tizimi, API mijozi, EAS sozlamasi

**2-bosqich (kirish + rol):**
- ✅ Backend: `/api/auth/*` — Email(bcrypt)/Google/Apple + JWT + parol tiklash + rol aniqlash (`backend/app/routers/auth.py`)
- ✅ Ilova: kirish/ro'yxatdan o'tish ekrani (email), JWT xavfsiz saqlash (SecureStore), auth-gate (kirmaган -> Login), Profil + Chiqish
- ⏳ Google/Apple tugmalari — 6-bosqichда (build) client ID'lar sozlangач yoqiladi

## Keyingi bosqichlar (spec bo'yicha)

| Bosqich | Nima | Holat |
|---|---|---|
| 1 | Loyiha asosi | ✅ |
| 2 | Kirish + rol | ✅ |
| 3 | Mijoz ekranlari: katalog, mahsulot, savat/checkout, buyurtma, balans | ✅ (asosiy oqim) |
| 4 | Admin / Moliya / Menejer ekranlari | ✅ |
| 5 | Push-bildirishnoma | |
| 6 | Build fayllari (.aab/.ipa/.exe/.dmg/.AppImage) | |

**4-bosqich (rol asosidagi panellar):**
- ✅ Backend: `require_admin` / `require_manager` / `require_super` endi native JWT'ni ham qabul qiladi (rol `roles()` orqali aniqlanadi) — bir xil endpointlar bot va ilova uchun.
- ✅ Ilova: Profil ekranida rolga qarab panel tugmalari chiqadi:
  - 🛠 **Admin paneli** — do'kon tanlash, mahsulot CRUD, buyurtmalar (holat/qabul/bekor), statistika + eng ko'p sotilgan + mahfiy kod, pul yechish.
  - 💰 **Moliya paneli** — to'ldirish / pul yechish / balans qaytarish so'rovlarini tasdiqlash-rad etish + umumiy hisobot.
  - 👔 **Menejer paneli** — do'kon so'rovlari (tasdiq/rad), do'konlar + arenda (blok/blokdan chiqarish/uzaytirish), hisobot.

---

## Sizning ishingiz (hozir)

Bu ilovани sinash va keyinroq build qilish uchun **bepul Expo hisobi** kerak:

1. **expo.dev** saytiga kiring → **Sign up** (bepul).
2. Kompyuteringizда Node.js o'rnatilган bo'lsin (nodejs.org). Xcode/Android
   Studio **kerak emas** — build bulutда bo'ladi.

Hisob ochгач, menга ayting — 2-bosqichни (kirish) qilamiz.

## Ishga tushirish (Node.js bor bo'lsa, sinov uchun)

```bash
cd mobile
npm install
npx expo start
```
Telefoningizда **Expo Go** ilovасини oching va terminaldагi QR kodни skanerlang —
ilova telefoningizда ochiladi.

> Versiyalar mos kelmasa: `npx expo install --fix`

## Build (6-bosqichда, EAS orqали — bulutда)

```bash
npm install -g eas-cli
eas login                 # Expo hisobingiz bilan
eas build -p android --profile production   # .aab -> Google Play
eas build -p ios --profile production       # .ipa -> App Store
```
Build Expo bulutида quriladi; tayyor fayl havolasi terminalда beriladi.
Kompyuteringizга og'ir dastur o'rnatish shart emas.
