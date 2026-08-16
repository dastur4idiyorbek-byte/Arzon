# 🖼 Logotipni qo'yish (terminalsiz, 5 click)

Ilova ikonkasi, ochilish ekrani va bildirishnoma ikonkasi **aynan sizning
logotipingizdan** yasalishi uchun uni bir marta yuklab qo'yasiz. Keyin har
build'da tizim uni o'zi ishlatadi.

---

## Qadamlar (hammasi brauzerda)

**1️⃣** GitHub'da `Arzon` reposini oching.

**2️⃣** Papkalarni ketma-ket bosing: **`mobile`** → **`assets`**

**3️⃣** O'ng yuqorida **`Add file`** → **`Upload files`**

**4️⃣** Logotip faylini oynaga tashlang (yoki **choose your files** bilan tanlang).

> ⚠️ Fayl nomi **aynan** `logo-source.png` bo'lishi kerak.
> Nomi boshqacha bo'lsa — yuklashdan **oldin** telefoningizda/kompyuteringizda
> faylni shu nomga o'zgartiring.

**5️⃣** Pastga suring → **`Commit changes`** ni bosing.

✅ Tayyor. Endi **ARZON Android APK** workflow'ini ishga tushirsangiz,
ikonkalar avtomatik shu logotipdan yasaladi.

---

## Logotip qanday bo'lgani ma'qul

| Talab | Tavsiya |
|---|---|
| Shakl | **Kvadrat** (masalan 1024×1024) |
| Format | PNG |
| Fon | Bir tekis (oq yoki brend rangi) |
| Chetlari | Muhim qismlar chetga juda yaqin bo'lmasin |

> **Nega kvadrat?** Android ilova ikonkasini yumaloq yoki yumaloq-burchakli
> qilib **kesadi**. Kvadrat bo'lmasa yoki chetida yozuv bo'lsa, o'sha qism
> kesilib qolishi mumkin. Shuning uchun ikonka uchun logotipning **belgi**
> qismi (sumka + "A") eng yaxshi ishlaydi; pastdagi "ONLAYN SAVDO" yozuvi
> kichik ikonkada baribir o'qilmaydi.

Agar ikkalasi ham kerak bo'lsa — ayting, ikonka uchun **belgi** qismini,
ochilish ekrani uchun esa **to'liq logotip**ni ishlataman.

---

## Nima avtomatik yasaladi

`logo-source.png` yuklangach, `scripts/make_icons.py` quyidagilarni chiqaradi:

| Fayl | Nima uchun |
|---|---|
| `icon.png` | Ilova ikonkasi (telefon ekranida) |
| `adaptive-icon.png` | Android adaptiv ikonka (chetlari kesiladi) |
| `splash.png` | Ilova ochilayotgandagi ekran |
| `notification-icon.png` | Bildirishnoma ikonkasi (oq siluet) |
| `favicon.png` | Web versiya uchun |

Buni qo'lda ishga tushirish ham mumkin: `python3 mobile/scripts/make_icons.py`
