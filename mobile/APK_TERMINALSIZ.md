# 📱 ARZON — APK'ni TERMINALSIZ chiqarish (faqat brauzer)

Bu yo'l — **hech qanday terminal, komanda yozmasdan**, hammasi brauzerda "click"
bilan. Kompyuterga Node.js ham o'rnatish shart emas.

Ikki usul bor. **1-usul** eng oson — undan boshlang.

---

## ✅ 1-usul — Expo saytidan to'g'ridan-to'g'ri (tavsiya)

Expo GitHub'dagi kodni o'zi olib, bulutda APK yasaydi. Faqat brauzer.

### Qadamlar
1. **[expo.dev](https://expo.dev)** → **Sign up** (bepul hisob, email + parol).
2. Kirgach: chapda **Projects** → **Create a project** (yoki **Import from GitHub**).
3. **GitHub'ni ulang** — Expo GitHub hisobingizga ruxsat so'raydi → **Authorize**.
   - So'ng **`Arzon`** reposini tanlang.
4. Loyiha sozlamasida (Expo so'rasa):
   - **Base directory / Root**: `mobile`  ← ⚠️ muhim (ilova shu papkada).
   - **Build profile**: `preview`  ← bu **.apk** beradi.
5. **Build** (yoki **Create build**) tugmasini bosing → **Android** → **preview**.
6. 15–20 daqiqa kuting. Tayyor bo'lganda o'sha sahifada **Download** tugmasi
   (`.apk`) chiqadi.
7. APK'ni yuklab olib, **Telegram**ga tashlasangiz — odamlar o'rnatadi.

> Expo `projectId`ni o'zi qo'shadi — **push-bildirishnoma** ham shu bilan ishlab ketadi.

---

## ✅ 2-usul — GitHub "Actions" tugmasi (juda sodda)

Bu usul **2 qismdan** iborat:
**A)** bir marta tayyorgarlik (5 daqiqa), **B)** tugmani bosish.
Bir marta tayyorlab qo'ysangiz, keyin har safar faqat **bitta tugma**.

---

### A qismi — bir marta tayyorgarlik

**1️⃣ Expo hisobi**
[expo.dev](https://expo.dev) oching → **Sign up** → email va parol → tayyor.

**2️⃣ Maxfiy kalit (token) olish**
Expo saytida o'ng yuqoridagi rasmingizni bosing →
**Account settings** → chapdan **Access tokens** → **Create token** →
chiqqan uzun yozuvni **nusxa oling** (Copy).
⚠️ Bu yozuvni hech kimga bermang.

**3️⃣ Kalitni GitHub'ga qo'yish**
GitHub'da `Arzon` reposini oching va ketma-ket bosing:
> **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Ochilgan oynada:
- **Name** katakcha: `EXPO_TOKEN`  (aynan shunday yozing)
- **Secret** katakcha: 2️⃣ da nusxa olgan kalitni joylashtiring (Paste)
- **Add secret** ni bosing.

✅ Tayyorgarlik tugadi. Buni **bir marta** qilasiz, xolos.

---

### B qismi — APK yasash (har safar shu)

**4️⃣** GitHub'da `Arzon` reposida yuqoridagi **Actions** yozuvini bosing.
**5️⃣** Chapdagi ro'yxatdan **"ARZON Android APK"** ni bosing.
**6️⃣** O'ng tomonda **"Run workflow"** → chiqqan oynada yana yashil
**"Run workflow"** tugmasini bosing.

Tamom! 15–20 daqiqa kuting. So'ng APK'ni oling:
> [expo.dev](https://expo.dev) → **Projects** → loyiha → **Builds** →
> so'nggi qator → **Download** → `.apk` fayl.

O'sha faylni **Telegram**ga tashlasangiz — odamlar o'rnatadi. 🎉

Keyin yangi APK kerak bo'lsa — faqat **4️⃣–6️⃣ ni** qayta bosing
(A qismi endi shart emas).

> 🛠 Agar 6️⃣ dan keyin qizil ✗ chiqib, "owner" haqida xato bo'lsa:
> GitHub'da `mobile/app.json` faylini oching → **qalam (✏️)** belgisi →
> `"expo": {` yozuvidan keyin yangi qator qo'shing:
> ```json
>     "owner": "EXPO_LOGININGIZ",
> ```
> (EXPO_LOGININGIZ — expo.dev'dagi foydalanuvchi nomingiz) → pastdan
> **Commit changes** → so'ng 4️⃣–6️⃣ ni qayta bosing. Bu ham terminalsiz.

---

## Qaysi birini tanlasam?
- **1-usul** — eng sodda, Expo saytida hammasi ko'rinib turadi. **Shundan boshlang.**
- **2-usul** — GitHub yoqadigan bo'lsa yoki 1-usul ishlamasa.

## Yangilash (kod o'zgarsa)
Yangi APK kerak bo'lsa — o'sha tugmani (Build / Run workflow) **qayta bosing**.
Yangi havolani odamlarga tashlaysiz.

## iPhone?
Bu usullar **Android** uchun. iPhone (`.ipa`) — Apple $99/yil + TestFlight kerak,
u **keyingi ish**.
