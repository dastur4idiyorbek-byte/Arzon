# ARZON — Native ilova (React Native + Expo)

Bu — ARZON'ning barcha platformalarда (Android, iOS, Windows, macOS, Linux)
ishlaydigan **bitta** native ilovasi. Backend (FastAPI + Neon) **o'zgармaydi** —
ilova undan REST API orqali foydalanadi.

> Telegram botlari va Mini App o'z joyida turaveradi; bu ilova ularni
> bosqichma-bosqich almashtiradi.

---

## Hozirgi holat — 1-BOSQICH tayyor (loyiha asosi)

- ✅ Expo + TypeScript loyiha asosi
- ✅ Pastki tab-navigatsiya (React Navigation)
- ✅ Rol-rang dizayn tizimi (`src/theme.ts`) — 🟠 xarid / 🟢 do'kon / 🟡 balans
- ✅ Backend API mijozi (`src/api.ts`)
- ✅ EAS Build sozlamasi (`eas.json`)

## Keyingi bosqichlar (spec bo'yicha)

| Bosqich | Nima |
|---|---|
| 2 | Kirish: Google / Apple / Email (bcrypt + JWT) + rol aniqlash |
| 3 | Mijoz ekranlari: katalog, mahsulot, savat/checkout, buyurtma, balans, sodiqlik |
| 4 | Admin / Moliya / Menejer ekranlari |
| 5 | Push-bildirishnoma (buyurtma holati, balans, arenda) |
| 6 | Build fayllari (.aab/.ipa/.exe/.dmg/.AppImage) — EAS + Electron |

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
