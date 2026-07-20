"""ARZON — kritik arxitektura qoidalarining uchdan-uchiga (E2E) testlari.

Bu testlar spec'dagi verification bandlarini avtomatlashtiradi:
  * phase 2: /products, izolyatsiya (403)
  * phase 3: buyurtma kodi, soxta initData rad etilishi, rate-limit
  * phase 4: sodiqlik do'konlar bo'yicha jamlanishi (rule 9)
  * phase 7: bitta umumiy katalog (rule 1), mahfiy kod (rule 3)
  * phase 8: mahfiy kod yangilansa qayta yopilishi (rule 6), rule 11
"""
import hashlib
import hmac
import json
import urllib.parse

from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Store

client = TestClient(app)

BOT_TOKEN = "TEST:BOT-TOKEN-123"
INTERNAL = {"X-Internal-Token": "internal-secret-xyz"}


# ---------------------------------------------------------------------------
# Yordamchi: haqiqiy imzolangan initData yaratish (rule 8, 1-bosqich)
# ---------------------------------------------------------------------------
def make_init_data(telegram_id: int, first_name: str = "Test") -> str:
    user = json.dumps(
        {"id": telegram_id, "first_name": first_name}, separators=(",", ":")
    )
    pairs = {"user": user, "auth_date": "1700000000"}
    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    pairs["hash"] = h
    return urllib.parse.urlencode(pairs)


def customer_headers(telegram_id: int) -> dict:
    return {"X-Telegram-Init-Data": make_init_data(telegram_id)}


def admin_headers(admin_id: int) -> dict:
    return {**INTERNAL, "X-Admin-Id": str(admin_id)}


# ---------------------------------------------------------------------------
# Fixtures uchun sodda o'rnatuvchi: ikkita do'kon + adminlar + mahsulotlar
# ---------------------------------------------------------------------------
SUPER = 999999
ADMIN_A = 1001
ADMIN_B = 2002


def setup_two_stores():
    """Super-admin ikkita do'kon yaratadi (rule 11)."""
    r1 = client.post(
        "/api/admin/stores",
        headers=admin_headers(SUPER),
        json={"nomi": "Do'kon A", "admin_telegram_id": ADMIN_A},
    )
    assert r1.status_code == 200, r1.text
    store_a = r1.json()

    r2 = client.post(
        "/api/admin/stores",
        headers=admin_headers(SUPER),
        json={"nomi": "Do'kon B", "admin_telegram_id": ADMIN_B},
    )
    assert r2.status_code == 200, r2.text
    store_b = r2.json()
    return store_a, store_b


# ===========================================================================
# rule 11: yangi do'kon faqat super-admin tomonidan
# ===========================================================================
def test_rule11_only_super_admin_creates_store():
    # Oddiy admin do'kon yarata olmaydi.
    r = client.post(
        "/api/admin/stores",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Ruxsatsiz", "admin_telegram_id": ADMIN_A},
    )
    assert r.status_code == 403, r.text


def test_rule11_internal_token_required():
    # Ichki tokensiz admin endpointlarga kirib bo'lmaydi.
    r = client.get("/api/admin/my-stores", headers={"X-Admin-Id": str(SUPER)})
    assert r.status_code == 401, r.text


# ===========================================================================
# rule 1 + rule 7: bitta umumiy katalog va admin izolyatsiyasi
# ===========================================================================
def test_rule1_single_catalog_and_rule7_isolation():
    store_a, store_b = setup_two_stores()

    # Admin A o'z do'koniga ommaviy mahsulot qo'shadi.
    ra = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Ko'ylak A", "narxi": 100000, "korinish": "ommaviy"},
    )
    assert ra.status_code == 200, ra.text

    # Admin B o'z do'koniga ommaviy mahsulot qo'shadi.
    rb = client.post(
        f"/api/admin/stores/{store_b['store_id']}/products",
        headers=admin_headers(ADMIN_B),
        json={"nomi": "Shim B", "narxi": 150000, "korinish": "ommaviy"},
    )
    assert rb.status_code == 200, rb.text

    # rule 7: Admin A boshqa do'kon (B)ga mahsulot qo'sha olmaydi -> 403.
    forbidden = client.post(
        f"/api/admin/stores/{store_b['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Ruxsatsiz", "narxi": 1, "korinish": "ommaviy"},
    )
    assert forbidden.status_code == 403, forbidden.text

    # rule 1: mijoz bitta katalogda IKKALA do'kon mahsulotini ko'radi.
    cat = client.get("/api/products", headers=customer_headers(555))
    assert cat.status_code == 200, cat.text
    names = {p["nomi"] for p in cat.json()}
    assert {"Ko'ylak A", "Shim B"} <= names


# ===========================================================================
# rule 8: soxta initData rad etiladi (phase 3 verification)
# ===========================================================================
def test_rule8_fake_initdata_rejected():
    r = client.get(
        "/api/products",
        headers={"X-Telegram-Init-Data": "user=%7B%22id%22%3A1%7D&hash=deadbeef"},
    )
    assert r.status_code == 401, r.text


# ===========================================================================
# rule 3 + rule 6: mahfiy kod ochilishi va kod yangilansa qayta yopilishi
# ===========================================================================
def test_rule3_and_rule6_secret_code_flow():
    store_a, _ = setup_two_stores()
    sid = store_a["store_id"]
    secret = store_a["mahfiy_kirish_kodi"]

    # Admin A mahfiy mahsulot qo'shadi.
    client.post(
        f"/api/admin/stores/{sid}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Maxfiy tovar", "narxi": 500000, "korinish": "mahfiy"},
    )

    cust = customer_headers(777)

    # Kod kiritilmasdan mahfiy tovar ko'rinmaydi.
    before = client.get("/api/products", headers=cust).json()
    assert "Maxfiy tovar" not in {p["nomi"] for p in before}

    # To'g'ri kod kiritiladi (rule 3).
    unlock = client.post("/api/unlock", headers=cust, json={"kod": secret})
    assert unlock.status_code == 200, unlock.text
    assert unlock.json()["ochildi"] is True

    after = client.get("/api/products", headers=cust).json()
    assert "Maxfiy tovar" in {p["nomi"] for p in after}

    # rule 5: keyingi safar qayta so'ralmaydi — tovar hali ko'rinadi.
    again = client.get("/api/products", headers=cust).json()
    assert "Maxfiy tovar" in {p["nomi"] for p in again}

    # rule 6: admin kodni yangilaydi -> mijoz uchun avtomatik qayta yopiladi.
    refresh = client.post(
        f"/api/admin/stores/{sid}/secret-code/refresh",
        headers=admin_headers(ADMIN_A),
    )
    assert refresh.status_code == 200, refresh.text
    assert refresh.json()["mahfiy_kirish_kodi"] != secret

    closed = client.get("/api/products", headers=cust).json()
    assert "Maxfiy tovar" not in {p["nomi"] for p in closed}


def test_rule7_secret_code_not_visible_to_other_admin():
    store_a, _ = setup_two_stores()
    sid = store_a["store_id"]
    # Admin B, A'ning kodini ko'ra olmaydi -> 403.
    r = client.get(
        f"/api/admin/stores/{sid}/secret-code",
        headers=admin_headers(ADMIN_B),
    )
    assert r.status_code == 403, r.text


# ===========================================================================
# rule 8 (2-bosqich) + rule 10: checkout telefon talab qiladi, do'kon bo'yicha
# ===========================================================================
def test_rule8_phone_required_and_rule10_split_orders():
    store_a, store_b = setup_two_stores()

    pa = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Tovar A", "narxi": 10000, "korinish": "ommaviy"},
    ).json()
    pb = client.post(
        f"/api/admin/stores/{store_b['store_id']}/products",
        headers=admin_headers(ADMIN_B),
        json={"nomi": "Tovar B", "narxi": 20000, "korinish": "ommaviy"},
    ).json()

    cust = customer_headers(888)
    cart = {
        "items": [
            {"product_id": pa["id"], "soni": 1},
            {"product_id": pb["id"], "soni": 2},
        ],
        "manzil": "Toshkent, Chilonzor 1",
    }

    # Telefon tasdiqlanmagan -> checkout rad etiladi (rule 8, 2-bosqich).
    denied = client.post("/api/checkout", headers=cust, json=cart)
    assert denied.status_code == 428, denied.text

    # Kontaktni ulashish.
    conf = client.post(
        "/api/confirm-phone", headers=cust, json={"tel": "+998901234567"}
    )
    assert conf.status_code == 200

    # Endi checkout ikkita alohida buyurtma yaratadi (rule 10).
    ok = client.post("/api/checkout", headers=cust, json=cart)
    assert ok.status_code == 200, ok.text
    orders = ok.json()["buyurtmalar"]
    assert len(orders) == 2
    # Har bir buyurtmada alohida 6 xonali kod (phase 3.1).
    codes = {o["kod"] for o in orders}
    assert len(codes) == 2
    assert all(len(c) == 6 and c.isdigit() for c in codes)
    store_ids = {o["store_id"] for o in orders}
    assert store_ids == {store_a["store_id"], store_b["store_id"]}


# ===========================================================================
# phase 3.6: kod tekshirishда rate-limit (brute-force bloklanadi)
# ===========================================================================
def test_phase3_rate_limit_on_unlock():
    cust = customer_headers(1234)
    limit = settings.code_attempt_limit
    # limit martagacha ruxsat (noto'g'ri kod bo'lsa ham 200, ochildi=False).
    for _ in range(limit):
        r = client.post("/api/unlock", headers=cust, json={"kod": "XXXXXX"})
        assert r.status_code == 200, r.text
    # Keyingi urinish bloklanadi -> 429.
    blocked = client.post("/api/unlock", headers=cust, json={"kod": "XXXXXX"})
    assert blocked.status_code == 429, blocked.text


# ===========================================================================
# rule 9: sodiqlik do'konlar bo'yicha jamlanadi (phase 4 verification)
# ===========================================================================
def test_rule9_loyalty_aggregates_across_stores():
    store_a, store_b = setup_two_stores()
    pa = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "L-Tovar A", "narxi": 10000, "korinish": "ommaviy"},
    ).json()
    pb = client.post(
        f"/api/admin/stores/{store_b['store_id']}/products",
        headers=admin_headers(ADMIN_B),
        json={"nomi": "L-Tovar B", "narxi": 20000, "korinish": "ommaviy"},
    ).json()

    cust = customer_headers(4321)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+998900000000"})

    # A do'konidan xarid -> tasdiqlanadi.
    r1 = client.post(
        "/api/checkout",
        headers=cust,
        json={"items": [{"product_id": pa["id"], "soni": 1}], "manzil": "Uy 1"},
    ).json()
    kod1 = r1["buyurtmalar"][0]["kod"]
    # B do'konidan xarid -> tasdiqlanadi.
    r2 = client.post(
        "/api/checkout",
        headers=cust,
        json={"items": [{"product_id": pb["id"], "soni": 1}], "manzil": "Uy 1"},
    ).json()
    kod2 = r2["buyurtmalar"][0]["kod"]

    # Adminlar o'z buyurtma kodlarini tasdiqlaydi (phase 3.3).
    c1 = client.post(
        "/api/admin/orders/confirm-code",
        headers=admin_headers(ADMIN_A),
        json={"kod": kod1},
    )
    assert c1.status_code == 200, c1.text
    c2 = client.post(
        "/api/admin/orders/confirm-code",
        headers=admin_headers(ADMIN_B),
        json={"kod": kod2},
    )
    assert c2.status_code == 200, c2.text

    # rule 9: umumiy xaridlar 2 ta (ikki xil do'kondan jamlangan).
    loyalty = client.get("/api/loyalty", headers=cust).json()
    assert loyalty["umumiy_xaridlar"] == 2


def test_rule7_admin_cannot_confirm_other_store_code():
    """Admin boshqa do'kon buyurtma kodini tasdiqlay olmaydi (rule 7)."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "X-Tovar", "narxi": 5000, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(6060)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+998911112233"})
    order = client.post(
        "/api/checkout",
        headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 1"},
    ).json()["buyurtmalar"][0]

    # Admin B, A do'koni buyurtmasini tasdiqlashga urinadi -> 403.
    r = client.post(
        "/api/admin/orders/confirm-code",
        headers=admin_headers(ADMIN_B),
        json={"kod": order["kod"]},
    )
    assert r.status_code == 403, r.text


# ===========================================================================
# phase 8.6: do'konni o'chirish — faqat super-admin, to'liq tozalash
# ===========================================================================
def test_phase86_delete_store_super_admin_only():
    store_a, _ = setup_two_stores()
    sid = store_a["store_id"]
    p = client.post(
        f"/api/admin/stores/{sid}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "O'chadigan tovar", "narxi": 1000, "korinish": "ommaviy"},
    ).json()

    # Oddiy admin o'chira olmaydi -> 403.
    r = client.delete(
        f"/api/admin/stores/{sid}", headers=admin_headers(ADMIN_A)
    )
    assert r.status_code == 403, r.text

    # Super-admin o'chiradi.
    r2 = client.delete(
        f"/api/admin/stores/{sid}", headers=admin_headers(SUPER)
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["ochirildi"] is True

    # Do'kon va mahsulotlari katalogдан yo'qoladi.
    cat = client.get("/api/products", headers=customer_headers(9911)).json()
    assert "O'chadigan tovar" not in {x["nomi"] for x in cat}
    assert sid not in {x["store_id"] for x in cat}


# ===========================================================================
# spec2: chegirma, ombor, qabul qilish, qidirish, o'z do'konini ochish
# ===========================================================================
def test_spec_discount_price_applied():
    """Skidka 20%: 3200 -> 2560 (spec1 task_2 verification #3)."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Chegirmali", "narxi": 3200, "korinish": "ommaviy",
              "skidka_foizi": 20},
    ).json()
    assert p["yakuniy_narx"] == 2560.0

    cat = client.get("/api/products", headers=customer_headers(3311)).json()
    item = next(x for x in cat if x["nomi"] == "Chegirmali")
    assert item["sotuv_narxi"] == 2560.0
    assert item["skidka_foizi"] == 20

    # Checkout ham chegirmali narxда hisoblaydi.
    cust = customer_headers(3311)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700000001"})
    r = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 1"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["buyurtmalar"][0]["jami_narx"] == 2560.0


def test_spec_expired_discount_ignored():
    """Muddati o'tgan chegirma narxga qo'llanmaydi (spec2 task_5)."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Eski chegirma", "narxi": 1000, "korinish": "ommaviy",
              "skidka_foizi": 50, "skidka_muddati": "2020-01-01T00:00:00Z"},
    ).json()
    cat = client.get("/api/products", headers=customer_headers(3322)).json()
    item = next(x for x in cat if x["id"] == p["id"])
    assert item["sotuv_narxi"] == 1000.0  # chegirma o'tgan — asl narx


def test_spec_stock_flow_accept_and_out_of_stock():
    """Ombor: miqdor 1 -> qabul qilingach 0 -> 'Tugadi' -> checkout rad."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Oxirgi dona", "narxi": 500, "korinish": "ommaviy",
              "miqdor": 1},
    ).json()

    cust = customer_headers(4411)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700000002"})

    # 2 dona so'ralsa — rad (faqat 1 qolgan).
    r2 = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 2}], "manzil": "Uy 1"},
    )
    assert r2.status_code == 400, r2.text

    # 1 dona — o'tadi.
    ok = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 1"},
    )
    assert ok.status_code == 200, ok.text
    order = ok.json()["buyurtmalar"][0]

    # Boshqa admin qabul qila olmaydi (rule 7).
    forbidden = client.post(
        f"/api/admin/orders/{order['id']}/accept",
        headers=admin_headers(ADMIN_B),
    )
    assert forbidden.status_code == 403, forbidden.text

    # O'z admini qabul qiladi -> holat tayyorlanmoqda, miqdor 0, ogohlantirish.
    acc = client.post(
        f"/api/admin/orders/{order['id']}/accept",
        headers=admin_headers(ADMIN_A),
    )
    assert acc.status_code == 200, acc.text
    d = acc.json()
    assert d["order"]["holat"] == "tayyorlanmoqda"
    assert any("tugadi" in w.lower() for w in d["ogohlantirishlar"])
    assert d["user_telegram_id"] == 4411

    # Katalogда 'tugadi' belgisi.
    cat = client.get("/api/products", headers=customer_headers(4412)).json()
    item = next(x for x in cat if x["id"] == p["id"])
    assert item["tugadi"] is True

    # Endi sotib bo'lmaydi.
    cust2 = customer_headers(4412)
    client.post("/api/confirm-phone", headers=cust2, json={"tel": "+996700000003"})
    r3 = client.post(
        "/api/checkout", headers=cust2,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 1"},
    )
    assert r3.status_code == 400, r3.text


def test_spec_cancel_order_with_reason():
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Bekor tovar", "narxi": 700, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(5511)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700000004"})
    order = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 1"},
    ).json()["buyurtmalar"][0]

    r = client.post(
        f"/api/admin/orders/{order['id']}/cancel",
        headers=admin_headers(ADMIN_A),
        json={"sabab": "Mahsulot sifatsiz chiqdi"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["order"]["holat"] == "bekor_qilindi"


def test_spec_order_search_store_scoped():
    """Qidiruv faqat o'z do'koni doirasida (spec2 task_4 verification #4)."""
    store_a, store_b = setup_two_stores()
    pa = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Qidiruv A", "narxi": 100, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(6611)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700123456"})
    order = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": pa["id"], "soni": 1}], "manzil": "Uy 1"},
    ).json()["buyurtmalar"][0]

    # O'z do'konida kod bo'yicha topiladi.
    r = client.get(
        f"/api/admin/stores/{store_a['store_id']}/orders/search",
        headers=admin_headers(ADMIN_A),
        params={"q": order["kod"]},
    )
    assert r.status_code == 200 and len(r.json()) == 1

    # Telefon bo'yicha ham topiladi.
    r_tel = client.get(
        f"/api/admin/stores/{store_a['store_id']}/orders/search",
        headers=admin_headers(ADMIN_A),
        params={"q": "700123456"},
    )
    assert len(r_tel.json()) >= 1

    # B do'koni adminining qidiruvida A'ning kodi chiqmaydi.
    r_b = client.get(
        f"/api/admin/stores/{store_b['store_id']}/orders/search",
        headers=admin_headers(ADMIN_B),
        params={"q": order["kod"]},
    )
    assert r_b.status_code == 200 and r_b.json() == []


def test_spec_self_store_creation():
    """Do'koni yo'q foydalanuvchi o'ziga do'kon ochadi (spec1 task_3)."""
    r = client.post(
        "/api/admin/stores/self",
        headers=admin_headers(770077),
        json={"nomi": "O'z do'konim"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["mahfiy_kirish_kodi"]

    # Ikkinchi marta — rad ("allaqachon bor").
    r2 = client.post(
        "/api/admin/stores/self",
        headers=admin_headers(770077),
        json={"nomi": "Ikkinchi"},
    )
    assert r2.status_code == 400, r2.text


def test_spec_daily_report_and_discount_expiry():
    """Kunlik hisobot matni + muddati o'tgan chegirma nolga tushishi."""
    from app.tgbots import daily as daily_mod
    from app.database import SessionLocal
    from app.models import Product as ProductModel, Store as StoreModel
    from sqlalchemy import select as sa_select

    store_a, _ = setup_two_stores()
    client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Muddat tovar", "narxi": 2000, "korinish": "ommaviy",
              "skidka_foizi": 30, "skidka_muddati": "2020-06-01T00:00:00Z"},
    )

    db = SessionLocal()
    try:
        xabarlar = daily_mod.expire_discounts(db)
        assert store_a["store_id"] in xabarlar
        p = db.scalar(
            sa_select(ProductModel).where(ProductModel.nomi == "Muddat tovar")
        )
        assert (p.skidka_foizi or 0) == 0 and p.yakuniy_narx is None

        store = db.get(StoreModel, store_a["store_id"])
        text = daily_mod.build_store_report(db, store)
        assert "Kunlik hisobot" in text and "Tushum" in text
    finally:
        db.close()


def test_spec_image_aspect_ratio():
    """Rasm nisbati saqlanadi, katalogда qaytadi, noto'g'ri nisbat rad etiladi."""
    store_a, _ = setup_two_stores()
    # To'g'ri nisbat bilan.
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Nisbatli", "narxi": 100, "korinish": "ommaviy",
              "rasm_nisbati": "16:9", "rasm_urls": ["/media/abc"]},
    )
    assert p.status_code == 200, p.text
    assert p.json()["rasm_nisbati"] == "16:9"

    cat = client.get("/api/products", headers=customer_headers(8811)).json()
    item = next(x for x in cat if x["nomi"] == "Nisbatli")
    assert item["rasm_nisbati"] == "16:9"

    # Noto'g'ri nisbat -> 400.
    bad = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Yomon", "narxi": 100, "korinish": "ommaviy",
              "rasm_nisbati": "5:2"},
    )
    assert bad.status_code == 400, bad.text

    # Nisbatsiz -> standart 1:1.
    p2 = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Standart", "narxi": 100, "korinish": "ommaviy"},
    ).json()
    assert p2["rasm_nisbati"] == "1:1"


# ===========================================================================
# Yetkazib berish: kuryer manzil + punktdan olish (Savdo boti spec task_4)
# ===========================================================================
def test_delivery_courier_requires_address():
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Yetk tovar", "narxi": 5000, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(20001)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+998900000010"})

    # Kuryer, manzilsiz -> 400.
    r = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}],
              "yetkazish_turi": "kuryer"},
    )
    assert r.status_code == 400, r.text

    # Kuryer, manzil bilan -> 200, buyurtмада manzil saqlanadi.
    r2 = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}],
              "yetkazish_turi": "kuryer", "manzil": "Chilonzor 5"},
    )
    assert r2.status_code == 200, r2.text
    o = r2.json()["buyurtmalar"][0]
    assert o["yetkazish_turi"] == "kuryer" and o["manzil"] == "Chilonzor 5"


def test_delivery_pickup_flow():
    store_a, store_b = setup_two_stores()
    pa = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "P-tovar", "narxi": 3000, "korinish": "ommaviy"},
    ).json()

    # Admin A punkt qo'shadi.
    pp = client.post(
        f"/api/admin/stores/{store_a['store_id']}/pickup-points",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Filial 1", "manzil": "Yunusobod 3", "ish_vaqti": "9-18"},
    )
    assert pp.status_code == 200, pp.text
    pp_id = pp.json()["id"]

    # rule 7: Admin B, A'ning do'koniga punkt qo'sha olmaydi.
    forb = client.post(
        f"/api/admin/stores/{store_a['store_id']}/pickup-points",
        headers=admin_headers(ADMIN_B),
        json={"nomi": "X", "manzil": "Y"},
    )
    assert forb.status_code == 403, forb.text

    cust = customer_headers(20002)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+998900000011"})

    # Mijoz punktlar ro'yxatini ko'radi.
    pts = client.get(
        f"/api/pickup-points?store_ids={store_a['store_id']}", headers=cust
    ).json()
    assert any(x["id"] == pp_id for x in pts)

    # Punkt tanlanmasa (pickup, lekin punktsiz) -> 400.
    bad = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": pa["id"], "soni": 1}],
              "yetkazish_turi": "pickup", "pickup_points": {}},
    )
    assert bad.status_code == 400, bad.text

    # To'g'ri punkt bilan -> 200.
    ok = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": pa["id"], "soni": 1}],
              "yetkazish_turi": "pickup",
              "pickup_points": {str(store_a["store_id"]): pp_id}},
    )
    assert ok.status_code == 200, ok.text
    o = ok.json()["buyurtmalar"][0]
    assert o["yetkazish_turi"] == "pickup" and o["pickup_point_id"] == pp_id

    # Boshqa do'kon punkti bilan -> 400 (punkt do'konга tegishli emas).
    pb = client.post(
        f"/api/admin/stores/{store_b['store_id']}/products",
        headers=admin_headers(ADMIN_B),
        json={"nomi": "P-tovar-B", "narxi": 3000, "korinish": "ommaviy"},
    ).json()
    wrong = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": pb["id"], "soni": 1}],
              "yetkazish_turi": "pickup",
              "pickup_points": {str(store_b["store_id"]): pp_id}},
    )
    assert wrong.status_code == 400, wrong.text


def test_bot_me_endpoint():
    """Onboarding uchun /api/bot/me telefon holatini qaytaradi."""
    import os
    tok = os.environ["INTERNAL_API_TOKEN"]
    h = {"X-Internal-Token": tok, "X-Telegram-User-Id": "20003"}
    r = client.get("/api/bot/me", headers=h)
    assert r.status_code == 200
    assert r.json()["tel_tasdiqlangan"] is False
    client.post(
        "/api/bot/confirm-phone", headers=h, json={"tel": "+998900000012"}
    )
    r2 = client.get("/api/bot/me", headers=h)
    assert r2.json()["tel_tasdiqlangan"] is True
