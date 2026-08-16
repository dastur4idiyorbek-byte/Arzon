"""ARZON ilova ikonkalarini yaratadi (logotip uslubida).

Chiqadigan fayllar (mobile/assets/):
  icon.png            1024x1024  — ilova ikonkasi (iOS + umumiy)
  adaptive-icon.png   1024x1024  — Android adaptiv ikonka (old qatlam)
  splash.png          1284x2778  — ochilish ekrani
  notification-icon.png 96x96    — bildirishnoma ikonkasi (oq siluet)
  favicon.png         48x48      — web

Logotip uslubi: to'q sariq gradient xarid sumkasi, ichida "A" harfi va
tezlik chizig'i bilan savat. Ranglar theme.ts bilan bir xil.

Ishga tushirish:  python3 scripts/make_icons.py
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

BU_YER = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BU_YER, "..", "assets")

BRAND = (232, 89, 12)       # #E8590C
BRAND_LIGHT = (247, 148, 30)  # yuqori gradient
CARD_TOP = (255, 248, 242)  # #FFF8F2
OQ = (255, 255, 255)


def gradient(size: int, yuqori, past) -> Image.Image:
    """Vertikal gradient kvadrat."""
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / max(size - 1, 1)
        d.line(
            [(0, y), (size, y)],
            fill=tuple(int(yuqori[i] + (past[i] - yuqori[i]) * t) for i in range(3)),
        )
    return img


def _font(px: int):
    """Qalin shrift topadi; topilmasa standart."""
    nomzodlar = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for p in nomzodlar:
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def sumka_va_a(size: int, fon=None) -> Image.Image:
    """Xarid sumkasi + 'A' + savat — logotipning soddalashtirilgan shakli."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if fon is not None:
        img.paste(fon, (0, 0))
    d = ImageDraw.Draw(img)
    s = size / 1024.0  # masshtab

    # --- Sumka dastasi (yarim doira) — uchlari sumka ustiga aniq tegadi ---
    BAG_TOP = 330
    d.arc(
        [355 * s, 215 * s, 669 * s, (2 * BAG_TOP - 215) * s],
        start=180, end=360, fill=OQ, width=int(34 * s),
    )

    # --- Sumka tanasi (dastadan keyin — uchlarini toza yopadi) ---
    x0, y0, x1, y1 = 250 * s, BAG_TOP * s, 774 * s, 800 * s
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(48 * s), fill=OQ)

    # --- "A" harfi (sumka ichida, brend rangida) ---
    f = _font(int(360 * s))
    matn = "A"
    quti = d.textbbox((0, 0), matn, font=f)
    tw, th = quti[2] - quti[0], quti[3] - quti[1]
    d.text(
        ((size - tw) / 2 - quti[0], (y0 + y1) / 2 - th / 2 - quti[1]),
        matn, font=f, fill=BRAND,
    )

    # --- Tezlik chiziqlari (chapda) — sumka o'rtasiga qarata, uzunligi turlicha ---
    orta = (y0 + y1) / 2 / s
    for ofset, uz in ((-72, 118), (0, 160), (72, 96)):
        yy = orta + ofset
        d.rounded_rectangle(
            [(238 - uz) * s, (yy - 13) * s, 238 * s, (yy + 13) * s],
            radius=int(13 * s), fill=OQ,
        )
    return img


def ikonka(size: int = 1024) -> Image.Image:
    fon = gradient(size, BRAND_LIGHT, BRAND).convert("RGBA")
    return sumka_va_a(size, fon)


def adaptiv(size: int = 1024) -> Image.Image:
    """Android adaptiv ikonka: fon alohida (app.json), bu yerda faqat shakl.

    Android chetlarini kesadi — shuning uchun shaklni kichraytiramiz (safe zone).
    """
    ichki = int(size * 0.62)
    shakl = sumka_va_a(ichki)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ofset = (size - ichki) // 2
    img.paste(shakl, (ofset, ofset), shakl)
    return img


def splash(w: int = 1284, h: int = 2778) -> Image.Image:
    img = Image.new("RGB", (w, h), CARD_TOP)
    logo_o = int(w * 0.46)
    logo = ikonka(logo_o)
    # Yumaloq burchak niqobi
    niqob = Image.new("L", (logo_o, logo_o), 0)
    ImageDraw.Draw(niqob).rounded_rectangle(
        [0, 0, logo_o, logo_o], radius=int(logo_o * 0.22), fill=255
    )
    img.paste(logo, ((w - logo_o) // 2, int(h * 0.36)), niqob)

    d = ImageDraw.Draw(img)
    f = _font(int(w * 0.105))
    matn = "ARZON"
    q = d.textbbox((0, 0), matn, font=f)
    d.text(
        ((w - (q[2] - q[0])) / 2 - q[0], int(h * 0.36) + logo_o + int(h * 0.035)),
        matn, font=f, fill=BRAND,
    )
    f2 = _font(int(w * 0.036))
    m2 = "ONLAYN SAVDO"
    q2 = d.textbbox((0, 0), m2, font=f2)
    d.text(
        ((w - (q2[2] - q2[0])) / 2 - q2[0],
         int(h * 0.36) + logo_o + int(h * 0.035) + int(w * 0.13)),
        m2, font=f2, fill=(107, 107, 107),
    )
    return img


def bildirishnoma(size: int = 96) -> Image.Image:
    """Android bildirishnoma ikonkasi — faqat OQ siluet (tizim talabi)."""
    katta = sumka_va_a(512)
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    px = katta.load()
    yangi = img.load()
    for y in range(512):
        for x in range(512):
            r, g, b, a = px[x, y]
            # Oq qismlarni saqlaymiz, qolganini shaffof qilamiz.
            if a > 0 and r > 200 and g > 200 and b > 200:
                yangi[x, y] = (255, 255, 255, 255)
    return img.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------
# HAQIQIY LOGOTIPDAN yasash (agar yuklangan bo'lsa)
# ---------------------------------------------------------------------------
MANBA = os.path.join(ASSETS, "logo-source.png")


def _kvadrat(img: Image.Image, fon=OQ, chekka: float = 0.0) -> Image.Image:
    """Rasmni kvadratga keltiradi (kesmasdan, fon bilan to'ldirib).

    `chekka` — atrofda qoldiriladigan bo'sh joy (tomonning ulushi).
    """
    w, h = img.size
    tomon = int(max(w, h) * (1 + chekka * 2))
    yangi = Image.new("RGB", (tomon, tomon), fon)
    yangi.paste(img, ((tomon - w) // 2, (tomon - h) // 2),
                img if img.mode == "RGBA" else None)
    return yangi


def _kes(img: Image.Image) -> Image.Image:
    """Atrofdagi bo'sh (shaffof) joyni kesib tashlaydi."""
    quti = img.getbbox()
    return img.crop(quti) if quti else img


def belgini_ajrat(src: Image.Image) -> Image.Image:
    """Logotipdan FAQAT belgi (yuqoridagi rasm) qismini ajratadi.

    Logotip odatda ikki qavat: yuqorida belgi, pastida nom yozuvi. Ular orasida
    bo'sh gorizontal yo'lak bo'ladi. Shu yo'lakni topib, yuqori qismni qaytaramiz.

    Nega kerak: telefondagi ikonka juda kichik — undagi yozuv o'qilmaydi va
    faqat rasmni ifloslantiradi. Belgi esa aniq ko'rinadi.

    Yo'lak topilmasa — butun logotip qaytariladi (xavfsiz zaxira).
    """
    img = _kes(src.convert("RGBA"))
    w, h = img.size
    alpha = img.getchannel("A")
    px = alpha.load()

    # Har bir qatorda nechta ko'rinadigan piksel bor?
    qatorlar = []
    for y in range(h):
        soni = 0
        for x in range(0, w, 4):  # har 4-piksel — tezlik uchun yetarli
            if px[x, y] > 40:
                soni += 1
        qatorlar.append(soni)

    eng_kop = max(qatorlar) or 1
    bosh = [q < eng_kop * 0.02 for q in qatorlar]  # deyarli bo'sh qator

    # Rasmning o'rta qismidan (35%..75%) eng uzun bo'sh yo'lakni qidiramiz —
    # belgi bilan yozuv orasidagi ajratgich shu yerda bo'ladi.
    eng_uzun, eng_boshi = 0, None
    i = int(h * 0.35)
    chek = int(h * 0.78)
    while i < chek:
        if bosh[i]:
            j = i
            while j < chek and bosh[j]:
                j += 1
            if j - i > eng_uzun:
                eng_uzun, eng_boshi = j - i, i
            i = j
        else:
            i += 1

    # Yo'lak juda ingichka bo'lsa — ishonchsiz, butun logotipni qaytaramiz.
    if eng_boshi is None or eng_uzun < h * 0.015:
        print("   ⚠️  belgi/yozuv ajratgichi topilmadi — butun logotip ishlatiladi.")
        return img
    print(f"   ✂️  belgi ajratildi (0..{eng_boshi}px, {eng_boshi * 100 // h}%)")
    return _kes(img.crop((0, 0, w, eng_boshi)))


def logodan() -> bool:
    """`assets/logo-source.png` bo'lsa — barcha ikonkalarni O'SHANDAN yasaydi.

    Foydalanuvchi o'z logotipini GitHub orqali shu nom bilan yuklaydi; shunda
    ilova ikonkasi aynan o'sha rasm bo'ladi.
    """
    if not os.path.exists(MANBA):
        return False
    print(f"✅ Logotip topildi: {os.path.relpath(MANBA)}")
    src = Image.open(MANBA).convert("RGBA")

    # IKONKA uchun — faqat BELGI qismi (yozuvsiz). Kichik ekranda yozuv
    # o'qilmaydi, belgi esa aniq ko'rinadi.
    belgi = belgini_ajrat(src)
    belgi_kv = _kvadrat(belgi, chekka=0.08)

    # 1) Ilova ikonkasi — 1024x1024.
    belgi_kv.resize((1024, 1024), Image.LANCZOS).save(
        os.path.join(ASSETS, "icon.png")
    )

    # 2) Android adaptiv — tizim chetlarini kesadi (yumaloq/kvadrat niqob),
    #    shuning uchun belgi xavfsiz zonaga (~66%) kichraytiriladi.
    ichki = int(1024 * 0.66)
    kichik = _kvadrat(belgi, fon=OQ).resize((ichki, ichki), Image.LANCZOS)
    adap = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    adap.paste(kichik, ((1024 - ichki) // 2, (1024 - ichki) // 2))
    adap.save(os.path.join(ASSETS, "adaptive-icon.png"))

    # 3) Ochilish ekrani — TO'LIQ logotip (yozuvi bilan), joyi keng.
    w, h = 1284, 2778
    sp = Image.new("RGB", (w, h), OQ)
    toliq = _kes(src)
    lo_w = int(w * 0.74)
    lo_h = int(toliq.size[1] * lo_w / toliq.size[0])
    sp.paste(
        toliq.resize((lo_w, lo_h), Image.LANCZOS),
        ((w - lo_w) // 2, (h - lo_h) // 2),
        toliq.resize((lo_w, lo_h), Image.LANCZOS),
    )
    sp.save(os.path.join(ASSETS, "splash.png"))

    # 4) Bildirishnoma ikonkasi — Android uni faqat OQ SILUET qilib ko'rsatadi
    #    (ranglarni tashlaydi). Shuning uchun belgi shaklidan siluet yasaymiz.
    sil = belgi.resize((96, 96), Image.LANCZOS)
    oq = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    sp_a, sp_b = sil.getchannel("A"), oq.load()
    a_px = sp_a.load()
    for y in range(96):
        for x in range(96):
            if a_px[x, y] > 60:
                sp_b[x, y] = (255, 255, 255, 255)
    oq.save(os.path.join(ASSETS, "notification-icon.png"))

    # 5) Web favicon.
    belgi_kv.resize((48, 48), Image.LANCZOS).convert("RGB").save(
        os.path.join(ASSETS, "favicon.png")
    )
    return True


def main() -> None:
    os.makedirs(ASSETS, exist_ok=True)
    if not logodan():
        print("ℹ️  logo-source.png yo'q — vaqtinchalik ikonka chizilyapti.")
        print("   O'z logotipingizni qo'yish uchun uni GitHub'da")
        print("   mobile/assets/logo-source.png nomi bilan yuklang.")
        ikonka(1024).convert("RGB").save(os.path.join(ASSETS, "icon.png"))
        adaptiv(1024).save(os.path.join(ASSETS, "adaptive-icon.png"))
        splash().save(os.path.join(ASSETS, "splash.png"))
        bildirishnoma(96).save(os.path.join(ASSETS, "notification-icon.png"))
        ikonka(48).convert("RGB").save(os.path.join(ASSETS, "favicon.png"))
    print("\nTayyor fayllar:")
    for f in sorted(os.listdir(ASSETS)):
        yol = os.path.join(ASSETS, f)
        print(f"  {f:24} {os.path.getsize(yol) // 1024} KB")


if __name__ == "__main__":
    main()
