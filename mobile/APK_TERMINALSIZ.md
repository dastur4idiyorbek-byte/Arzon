# 📱 ARZON — APK'ni TERMINALSIZ chiqarish (faqat brauzer)

Bu yo'l — **hech qanday terminal, komanda yozmasдан**, hammasi brauzerда "click"
bilan. Kompyuterга Node.js ham o'рнатиш shart emas.

Ikки usul bor. **1-usул** eng oson — undan boshlang.

---

## ✅ 1-usul — Expo saytидан to'g'ridan-to'g'ri (tavsiya)

Expo GitHub'даги kodни o'зи olib, bulutда APK yasaydi. Faqat brauzер.

### Qadamlar
1. **[expo.dev](https://expo.dev)** → **Sign up** (bepul hisоб, email + parol).
2. Kirгач: chapда **Projects** → **Create a project** (yoki **Import from GitHub**).
3. **GitHub'ни ulang** — Expo GitHub hisобингизга ruxsat so'raydi → **Authorize**.
   - So'ng **`Arzon`** reposini tanlang.
4. Loyиха sozlamаsида (Expo so'raса):
   - **Base directory / Root**: `mobile`  ← ⚠️ muhим (ilova shu papkада).
   - **Build profile**: `preview`  ← bu **.apk** beradi.
5. **Build** (yoki **Create build**) tugмасини bosing → **Android** → **preview**.
6. 15–20 daqiqа kutиng. Tayyor bo'lганда o'sha sahifада **Download** tugмаси
   (`.apk`) chiqады.
7. APK'ni yuklab olиб, **Telegram**га tashlасангиз — odamlar o'рнатади.

> Expo `projectId`ни o'зи qo'shади — **push-bildirishnoma** ham shu bilan ishlаб ketади.

---

## ✅ 2-usul — GitHub "Actions" tugмаси (zaxira)

Repoда tayyor sozlама bor (`.github/workflows/android-apk.yml`). Faqat 4 ta click:

1. **[expo.dev](https://expo.dev)** → **Sign up** (agar hali yo'q bo'lsa).
2. expo.dev → (o'ng yuqori) **Account settings** → **Access tokens** →
   **Create token** → tokenни **nusxa oling**.
3. GitHub'да: **Arzon** repo → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**:
   - **Name**: `EXPO_TOKEN`
   - **Secret**: (2-qadамдаги token)
   - **Add secret**.
4. GitHub'да: yuqоридаги **Actions** → chapдан **"ARZON Android APK"** →
   o'ngда **Run workflow** → yashил **Run workflow**.
5. 15–20 daqiqада APK tayyor: **expo.dev → loyиха → Builds → Download**.

> Agar birinchi build "owner" xatosи bersa: GitHub'да `mobile/app.json` faylини
> oching → **qalам (✏️)** belgиси → `"expo": {` дан keyin bitta qatор qo'shing:
> ```json
> "owner": "SIZNING_EXPO_LOGININGIZ",
> ```
> **Commit changes** → 4-qадамни qайta bosing. (Bu ham terminalсиз.)

---

## Qайси birини tanlаsam?
- **1-usул** — eng sodda, Expo saytида hammаси ko'rinиб turadi. **Shundан boshlang.**
- **2-usул** — GitHub yoqадиган bo'lса yoki 1-usул ishlaмаса.

## Yangилаш (kod o'zгарса)
Yangi APK kerак bo'lса — o'sha tugмани (Build / Run workflow) **qайта bosing**.
Yangi havolани odamларга tashlаysiz.

## iPhone?
Bu usullar **Android** uchun. iPhone (`.ipa`) — Apple $99/yил + TestFlight kerак,
u **keyinги ish**.
