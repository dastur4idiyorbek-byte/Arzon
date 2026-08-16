# 📱 ARZON — Android APK chiqarish yo'llanmasi (Telegram bilan tarqatish)

Bu yo'llanma — ilovани **`.apk`** fayl qilib chiqarib, **Telegram orqali** odamlarга
tarqatиш uchun. Play Store **kerak emas**, Google hisobi **kerak emas**, pul **kerak emas**.

> APK — Android ilova fayli. Odam uni Telegram'дан yuklab, bosиб o'rnatади.
> iPhone uchun bu usul ishlamaydi (Apple ruxsat bermaydi) — u keyinги ish.

---

## Nima kerak (bir marta tayyorlash)

1. **Kompyuter** (Windows / Mac / Linux — farqi yo'q).
2. **Node.js** — bepul dastur. [nodejs.org](https://nodejs.org) → "LTS" tugmasини yuklab o'rnating.
3. **Bepul Expo hisobi** — [expo.dev](https://expo.dev) → **Sign up**.

> ⚠️ Xcode, Android Studio — **kerak emas**. Build Expo bulutида bo'ladi.

---

## 1-qadam — Expo hisobi ochish
1. [expo.dev](https://expo.dev) → **Sign up** → email + parol.
2. Emailни tasdiqlang.

## 2-qadam — Kompyuterда loyihani ochish
Terminal (Windows'да "Command Prompt" yoki "PowerShell") oching va yozing:

```bash
# loyihani yuklab olish (agar hali yo'q bo'lsa)
git clone https://github.com/dastur4idiyorbek-byte/Arzon.git
cd Arzon/mobile

# kutubxonalarni o'rnatish (bir marta, biroz vaqt oladi)
npm install

# EAS vositasini o'rnatish (bir marta)
npm install -g eas-cli
```

## 3-qadam — Expo hisobiga kirish
```bash
eas login
```
Email va parolني kiriting (2-qadamда ochганingiz).

## 4-qadam — Loyihani Expo bilan bog'lash (bir marta)
```bash
eas build:configure
```
- "Which platforms?" deganда **Android**ни tanlang (yoki "All").
- Bu `app.json`га `projectId` qo'shади — **push-bildirishnoma** ham shu bilan ishlaydi.

## 5-qadam — APK chiqarish 🎉
```bash
eas build -p android --profile preview
```
- Build **Expo bulutида** quriladi (10–20 daqiqa).
- Tugagач terminalда **havola** beriladi, masalan:
  `https://expo.dev/artifacts/.../arzon.apk`
- Yoki [expo.dev](https://expo.dev) → loyihангiz → **Builds** → so'nggi build → **Download**.

## 6-qadam — Telegram bilan tarqatish
1. APK faylни yuklab oling (havoladан).
2. Telegram'да o'zingizга yoki guruhга **fayl sifatида** tashlang.
3. Odam faylни bosиб yuklab oladi → bosиб **o'rnатади**.
   - Birinchi marta "Noma'lum manbалардан o'rnатишга ruxsat" chiqса — **Ruxsat** bering (bir marta).
4. Tayyor — ilova telefonда ochилаверади (internet bo'lса).

---

## Yangилаш (kod o'zгарса)
Kod o'zгаргач yangi APK kerak bo'lsa — **5-qadамни qайta bajaring**:
```bash
git pull
eas build -p android --profile preview
```
Yangi havolани odamларга qايtа tashlaysiz. (Ilova ichидаги avtoма-yangилаш keyinги bosqич.)

---

## Tez-tez so'raladиган savollар

**S: Har build pul turаdими?**
Yo'q. Expo bepul rejasида Android APK build **bepul** (oyга cheklов bor, lekin sizга yetadi).

**S: Backend qayerда?**
Ilova `app.json` → `extra.apiUrl` (`https://arzon-backend.onrender.com`) manzилига ulanadi.
Backend Render'да turган ekan, APK **istаган telefonда** ishlaydi.

**S: iPhone'га-chi?**
Bu usul iPhone'да ishlamaydi. iPhone uchun TestFlight (Apple $99/yil) yoki App Store kerak — keyinги ish.

**S: Play Store'га qачон qo'yamiz?**
Xohlаган paytингизда. O'sha payt `--profile production` bilan `.aab` chiqараmиз
(`eas build -p android --profile production`) va Play Console'ga yuklаймиз ($25 bir marta).
Kod o'zgармaydи.
