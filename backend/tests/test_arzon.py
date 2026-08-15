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


def give_balance(telegram_id: int, amount: float) -> None:
    """Testда mijozga ACOM coin balansи beradi (checkout coin bilan ishlaydi).

    Foydalanuvchi mavjud bo'lmasa yaratiladi. Xaridlar endi balansdan yechiladi
    (ACOM_Coin_Tizimi rule 1/3), shuning uchun checkout testlari balans talab qiladi.
    """
    from decimal import Decimal

    from app.models import User

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == telegram_id).first()
        if u is None:
            u = User(telegram_id=telegram_id)
            db.add(u)
            db.commit()
            db.refresh(u)
        u.coin_balans = Decimal(str(amount))
        db.commit()
    finally:
        db.close()


def get_balance(telegram_id: int) -> float:
    from app.models import User

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == telegram_id).first()
        return float(u.coin_balans or 0) if u else 0.0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures uchun sodda o'rnatuvchi: ikkita do'kon + adminlar + mahsulotlar
# ---------------------------------------------------------------------------
SUPER = 999999
MANAGER = 777777  # conftest MENEJER_IDS bilan mos
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
        "manzil": "Bishkek, Chuy 1",
    }

    # Telefon tasdiqlanmagan -> checkout rad etiladi (rule 8, 2-bosqich).
    denied = client.post("/api/checkout", headers=cust, json=cart)
    assert denied.status_code == 428, denied.text

    # Kontaktni ulashish.
    conf = client.post(
        "/api/confirm-phone", headers=cust, json={"tel": "+996700111222"}
    )
    assert conf.status_code == 200
    give_balance(888, 100000)  # ACOM coin balansi (xarid balansdan yechiladi)

    # Endi checkout ikkita alohida buyurtma yaratadi (rule 10).
    ok = client.post("/api/checkout", headers=cust, json=cart)
    assert ok.status_code == 200, ok.text
    orders = ok.json()["buyurtmalar"]
    assert len(orders) == 2
    # Har bir buyurtmada alohida 6 xonali kod (phase 3.1).
    codes = {o["kod"] for o in orders}
    assert len(codes) == 2
    assert all(len(c) == 6 and c.isalnum() for c in codes)
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
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700000000"})
    give_balance(4321, 100000)

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
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700112233"})
    give_balance(6060, 100000)
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
    give_balance(3311, 100000)
    r = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 1"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["buyurtmalar"][0]["jami_narx"] == 2660.0  # 2560 + 100 yetkazish


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
    give_balance(4411, 100000)

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
    give_balance(4412, 100000)
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
    give_balance(5511, 100000)
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


def test_customer_delete_finished_order():
    """Mijoz faqat tugagan buyurtмани o'chira oladi (faolни emas)."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "O'chir tovar", "narxi": 500, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(5522)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700000009"})
    give_balance(5522, 100000)
    order = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 1"},
    ).json()["buyurtmalar"][0]

    # Faol (yangi) buyurtмани o'chirib bo'lmaydi.
    r = client.delete(f"/api/orders/{order['id']}", headers=cust)
    assert r.status_code == 400, r.text

    # Bekor qilinsa — tugagan holatga o'tadi, endi o'chirса bo'ladi.
    client.post(
        f"/api/admin/orders/{order['id']}/cancel",
        headers=admin_headers(ADMIN_A),
        json={"sabab": "test"},
    )
    r = client.delete(f"/api/orders/{order['id']}", headers=cust)
    assert r.status_code == 200, r.text
    assert r.json()["ochirildi"] is True
    # Tarixдан yo'qoladi.
    orders = client.get("/api/orders", headers=cust).json()
    assert all(o["id"] != order["id"] for o in orders)

    # Boshqa mijoz o'chira olmaydi (egasi emas).
    other = customer_headers(5523)
    client.post("/api/confirm-phone", headers=other, json={"tel": "+996700000010"})
    order2 = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 2"},
    ).json()["buyurtmalar"][0]
    client.post(
        f"/api/admin/orders/{order2['id']}/cancel",
        headers=admin_headers(ADMIN_A),
        json={"sabab": "test"},
    )
    r = client.delete(f"/api/orders/{order2['id']}", headers=other)
    assert r.status_code == 403, r.text


def test_referral_rewards_go_to_referrer():
    """Referal orqali kelgan do'st harakatlari uchun mukofot REFERAL EGASIGA."""
    R, F = 7000, 7001
    # R (referal egasi) foydalanuvchi mavjud bo'lsin.
    client.get("/api/balance", headers=customer_headers(R))

    def r_balance():
        return client.get("/api/balance", headers=customer_headers(R)).json()["coin_balans"]

    b0 = r_balance()
    # F referal link orqali kirib start bosadi -> R ga +5 ACOM.
    both_F = {**INTERNAL, "X-Telegram-User-Id": str(F)}
    client.post("/api/bot/register-referral", headers=both_F,
                json={"referrer_telegram_id": R})
    b1 = r_balance()
    assert b1 - b0 == 5
    # Takroriy register — qo'shimcha mukofot yo'q.
    client.post("/api/bot/register-referral", headers=both_F,
                json={"referrer_telegram_id": R})
    assert r_balance() == b1

    # F Mini App'ni ochadi -> R ga +10 ACOM (bir marta).
    client.post("/api/miniapp-opened", headers=customer_headers(F))
    b2 = r_balance()
    assert b2 - b1 == 10
    client.post("/api/miniapp-opened", headers=customer_headers(F))  # takror
    assert r_balance() == b2

    # F xarid qiladi -> R ga xarid summasining 5% ACOM.
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Ref tovar", "narxi": 1000, "korinish": "ommaviy"},
    ).json()
    client.post("/api/confirm-phone", headers=customer_headers(F),
                json={"tel": "+996700007001"})
    give_balance(F, 100000)
    client.post(
        "/api/checkout", headers=customer_headers(F),
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 1"},
    )
    # Do'st xaridi ACOM bermaydi — referal egasiga chegirma vaucheri beriladi.
    assert r_balance() == b2
    loy = client.get("/api/loyalty", headers=customer_headers(R)).json()
    assert loy["chegirma_vaucherlar"] == 1

    # R o'zi xarid qiladi — vaucher 5% chegirma beradi (mahsulotga, yetkazishга emas).
    client.post("/api/confirm-phone", headers=customer_headers(R),
                json={"tel": "+996700007000"})
    give_balance(R, 100000)
    o = client.post(
        "/api/checkout", headers=customer_headers(R),
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 9"},
    ).json()["buyurtmalar"][0]
    assert o["jami_narx"] == 1050  # 1000*0.95 + 100 yetkazish
    # Vaucher ishlatildi — endi qolmadi.
    loy2 = client.get("/api/loyalty", headers=customer_headers(R)).json()
    assert loy2["chegirma_vaucherlar"] == 0


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
    give_balance(6611, 100000)
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
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700000010"})
    give_balance(20001, 100000)

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
        json={"nomi": "Filial 1", "manzil": "Bishkek, Ala-Too 3", "ish_vaqti": "9-18"},
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
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700000011"})
    give_balance(20002, 100000)

    # Mijoz punktlar ro'yxatini ko'radi.
    pts = client.get(
        f"/api/pickup-points?store_ids={store_a['store_id']}", headers=cust
    ).json()
    assert any(x["id"] == pp_id for x in pts)

    # task_3: google_maps_link bilan punkt — havola saqlanadi va qaytadi.
    pp2 = client.post(
        f"/api/admin/stores/{store_a['store_id']}/pickup-points",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Filial 2", "manzil": "Osh 5",
              "google_maps_link": "https://www.google.com/maps?q=40.5,72.8"},
    )
    assert pp2.status_code == 200, pp2.text
    pts2 = client.get(
        f"/api/pickup-points?store_ids={store_a['store_id']}", headers=cust
    ).json()
    match = [x for x in pts2 if x["id"] == pp2.json()["id"]]
    assert match and match[0]["google_maps_link"] == "https://www.google.com/maps?q=40.5,72.8"

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


def test_miniapp_variant_selection_recorded():
    """Mijoz tanlagan o'lcham/rang buyurtmaда saqlanadi (MiniApp task_3/4)."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={
            "nomi": "Krossovka",
            "narxi": 150000,
            "korinish": "ommaviy",
            "olcham": "40, 41, 42",
            "rang": "Qora, Oq",
        },
    ).json()
    # Katalogда variant ro'yxatlari ko'rinadi.
    cust = customer_headers(30001)
    katalog = client.get("/api/products", headers=cust).json()
    kp = next(x for x in katalog if x["id"] == p["id"])
    assert kp["olcham"] == "40, 41, 42" and kp["rang"] == "Qora, Oq"

    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700000013"})
    give_balance(30001, 500000)
    # Buy Now uslubida bitta mahsulot, tanlangan variant bilan.
    r = client.post(
        "/api/checkout",
        headers=cust,
        json={
            "items": [
                {"product_id": p["id"], "soni": 1, "olcham": "41", "rang": "Qora"}
            ],
            "manzil": "Bishkek, Chuy 5",
        },
    )
    assert r.status_code == 200, r.text
    item = r.json()["buyurtmalar"][0]["mahsulotlar"][0]
    assert item["olcham"] == "41" and item["rang"] == "Qora"


# ===========================================================================
# ACOM coin tizimi (ACOM_Coin_Tizimi_Prompt_1)
# ===========================================================================
def test_coin_purchase_settlement():
    """rule 4: 1000 som xarid, 5% komissiya -> mijozdan 1000, adminga 950."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Coin tovar", "narxi": 1000, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(40001)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700400001"})
    give_balance(40001, 5000)

    r = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Bishkek 1"},
    )
    assert r.status_code == 200, r.text
    # Mijozdan to'liq 1000 yechildi.
    assert get_balance(40001) == 3900.0  # 5000 - (1000 + 100 yetkazish)

    # Admin (do'kon) balansi 950 (1000 - 5%).
    from app.database import SessionLocal
    from app.models import Store
    from app.services import coin as coin_service
    db = SessionLocal()
    try:
        s = db.get(Store, store_a["store_id"])
        assert float(coin_service.store_balance(s)) == 990.0
    finally:
        db.close()


def test_coin_insufficient_balance_blocks_checkout():
    """rule 3: balans yetmasa xarid amalga oshmaydi (402)."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Qimmat tovar", "narxi": 5000, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(40002)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700400002"})
    give_balance(40002, 1000)  # kerakli 5000 dan kam

    r = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Bishkek 1"},
    )
    assert r.status_code == 402, r.text
    # Balans o'zgarmagan, buyurtma yaratilmagan.
    assert get_balance(40002) == 1000.0
    orders = client.get("/api/orders", headers=cust).json()
    assert all(o["jami_narx"] != 5000 for o in orders)


def test_coin_refund_on_cancel():
    """rule 5 / task_4: bekor qilinganда darhol teskari o'zgaradi."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Qaytar tovar", "narxi": 2000, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(40003)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700400003"})
    give_balance(40003, 5000)

    order = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Bishkek 1"},
    ).json()["buyurtmalar"][0]
    assert get_balance(40003) == 2900.0  # 5000 - (2000 + 100 yetkazish)

    from app.database import SessionLocal
    from app.models import Store
    from app.services import coin as coin_service
    db = SessionLocal()
    try:
        s = db.get(Store, store_a["store_id"])
        assert float(coin_service.store_balance(s)) == 1980.0  # 2000 - 1%
    finally:
        db.close()

    # Bekor qilish -> mijozga 2000 qaytadi, admindan 1900 ayiriladi.
    r = client.post(
        f"/api/admin/orders/{order['id']}/cancel",
        headers=admin_headers(ADMIN_A),
        json={"sabab": "Omborда yo'q"},
    )
    assert r.status_code == 200, r.text
    assert get_balance(40003) == 5000.0  # to'liq qaytdi
    db = SessionLocal()
    try:
        s = db.get(Store, store_a["store_id"])
        assert float(coin_service.store_balance(s)) == 0.0
    finally:
        db.close()


def test_coin_topup_requires_approval():
    """rule 2: to'ldirish so'rovi darhol coin bermaydi; tasdiqlangach beradi."""
    from app.database import SessionLocal
    from app.models import User
    from app.services import coin as coin_service

    # Foydalanuvchi yaratamiz.
    cust = customer_headers(40004)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700400004"})
    assert get_balance(40004) == 0.0

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == 40004).first()
        sorov = coin_service.create_topup_request(db, u, 10000, ai_summa=10000,
                                                   ai_xulosa="mos_keladi")
        # Hali coin berilmagan (AI mos desa ham).
        assert coin_service.balance(u) == 0
        assert sorov.holat == "kutilmoqda"
        # Super-admin tasdiqlaydi.
        coin_service.approve_topup(db, sorov, admin_id=SUPER)
        db.refresh(u)
        assert float(coin_service.balance(u)) == 10000.0
    finally:
        db.close()
    assert get_balance(40004) == 10000.0


def test_coin_topup_daily_limit():
    """task_1: kunlik so'rovlar chegarasi (3) oshsa rad etiladi."""
    from app.database import SessionLocal
    from app.models import User
    from app.services import coin as coin_service
    from fastapi import HTTPException

    cust = customer_headers(40005)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700400005"})
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.telegram_id == 40005).first()
        for _ in range(settings.kunlik_toldirish_soni_limit):
            coin_service.create_topup_request(db, u, 1000)
        # Keyingisi rad etiladi.
        try:
            coin_service.create_topup_request(db, u, 1000)
            assert False, "kunlik chegara ishlamadi"
        except HTTPException as e:
            assert e.status_code == 400
    finally:
        db.close()


def test_coin_withdraw_and_report():
    """task_5 + task_2: pul yechish balansdan ayiriladi; hisobot to'g'ri."""
    from app.database import SessionLocal
    from app.models import Store
    from app.services import coin as coin_service

    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Hisobot tovar", "narxi": 10000, "korinish": "ommaviy"},
    ).json()
    # Testlar umumiy bazani baham ko'radi — hisobotда DELTA tekshiramiz.
    db = SessionLocal()
    try:
        rep0 = coin_service.overall_report(db)
    finally:
        db.close()

    cust = customer_headers(40006)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700400006"})
    give_balance(40006, 20000)
    client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Bishkek 1"},
    )
    # Admin balansi 9500 (10000 - 5%).
    db = SessionLocal()
    try:
        s = db.get(Store, store_a["store_id"])
        assert float(coin_service.store_balance(s)) == 9900.0
        rep1 = coin_service.overall_report(db)
        assert rep1["bugun_xarid_summa"] - rep0["bugun_xarid_summa"] == 10000.0
        # Komissiya har doim xarid summasining 5% (identifikatsiya).
        assert rep1["bugun_komissiya"] == round(rep1["bugun_xarid_summa"] * 0.01, 2)
        # Pul yechish so'rovi.
        w = coin_service.create_withdraw(db, s, 5000, "1234567890123456", ADMIN_A)
        assert w.holat == "kutilmoqda"
        # Yechishдан oldin balans o'zgarmaydi.
        db.refresh(s)
        assert float(coin_service.store_balance(s)) == 9900.0
        # To'landi deb belgilash -> balans 4500.
        coin_service.mark_withdraw_paid(db, w)
        db.refresh(s)
        assert float(coin_service.store_balance(s)) == 4900.0
        rep2 = coin_service.overall_report(db)
        assert rep2["bugun_yechish_summa"] - rep0["bugun_yechish_summa"] == 5000.0
    finally:
        db.close()


def _bot_headers(telegram_id: int) -> dict:
    return {**INTERNAL, "X-Telegram-User-Id": str(telegram_id)}


def test_moliya_super_admin_only():
    """verification #6: Moliya endpointlariга faqat super-admin kira oladi."""
    # Oddiy admin -> 403.
    r = client.get("/api/moliya/topups", headers=admin_headers(ADMIN_A))
    assert r.status_code == 403, r.text
    # Super-admin -> 200.
    r2 = client.get("/api/moliya/topups", headers=admin_headers(SUPER))
    assert r2.status_code == 200, r2.text


def test_moliya_topup_full_flow():
    """rule 2: to'ldirish so'rovi -> super tasdiqlaydi -> balans oshadi."""
    # Mijoz mavjud bo'lsin.
    tid = 50001
    client.post("/api/bot/confirm-phone", headers=_bot_headers(tid),
                json={"tel": "+996700500001"})
    # To'ldirish so'rovi (bot endpointi orqali).
    r = client.post("/api/bot/coin/topup", headers=_bot_headers(tid),
                    json={"summa": 7500, "ai_summa": 7500, "ai_xulosa": "mos_keladi"})
    assert r.status_code == 200, r.text
    sorov_id = r.json()["sorov_id"]
    # Coin hali berilmagan.
    assert get_balance(tid) == 0.0
    # Moliya ro'yxatida ko'rinadi.
    lst = client.get("/api/moliya/topups", headers=admin_headers(SUPER)).json()
    assert any(x["id"] == sorov_id for x in lst)
    # Tasdiqlash.
    a = client.post(f"/api/moliya/topups/{sorov_id}/approve",
                    headers=admin_headers(SUPER))
    assert a.status_code == 200, a.text
    assert get_balance(tid) == 7500.0


def test_admin_withdraw_flow():
    """task_5: admin pul yechish so'rovi -> super to'landi -> balans kamayadi."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Yechim tovar", "narxi": 8000, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(50002)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700500002"})
    give_balance(50002, 10000)
    client.post("/api/checkout", headers=cust,
                json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Bishkek 1"})
    # Admin balansi 7600 (8000 - 5%). Yechish so'rovi.
    w = client.post(
        f"/api/admin/stores/{store_a['store_id']}/withdraw",
        headers=admin_headers(ADMIN_A),
        json={"summa": 5000, "karta_raqami": "1234567890"},
    )
    assert w.status_code == 200, w.text
    wid = w.json()["sorov_id"]
    # Super to'landi deb belgilaydi.
    paid = client.post(f"/api/moliya/withdraws/{wid}/paid",
                       headers=admin_headers(SUPER))
    assert paid.status_code == 200, paid.text
    # Balans 2600 (7600 - 5000).
    bal = client.get(f"/api/admin/stores/{store_a['store_id']}/balance",
                     headers=admin_headers(ADMIN_A)).json()
    assert bal["kutilayotgan_balans"] == 2920.0


def test_miniapp_balance_endpoint():
    """Mini App header uchun /api/balance (initData)."""
    give_balance(50003, 3300)
    r = client.get("/api/balance", headers=customer_headers(50003))
    assert r.status_code == 200
    assert r.json()["coin_balans"] == 3300.0


def test_coin_referral_bonus():
    """Referal mukofoti: register (5) + do'st xarididan 5% — hammasi referal egasiga."""
    # Taklif qiluvchi A mavjud bo'lsin.
    a_tid = 60001
    client.post("/api/bot/confirm-phone", headers=_bot_headers(a_tid),
                json={"tel": "+996700600001"})
    assert get_balance(a_tid) == 0.0

    # B (taklif qilingan) A havolasi orqali keladi.
    b_tid = 60002
    client.post("/api/bot/confirm-phone", headers=_bot_headers(b_tid),
                json={"tel": "+996700600002"})
    r = client.post("/api/bot/register-referral", headers=_bot_headers(b_tid),
                    json={"referrer_telegram_id": a_tid})
    assert r.status_code == 200, r.text
    # Register bosqichидаёк A ga +5 ACOM (do'st start bosdi).
    assert get_balance(a_tid) == 5.0

    # B birinchi xaridini qiladi.
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Ref tovar", "narxi": 1000, "korinish": "ommaviy"},
    ).json()
    give_balance(b_tid, 5000)
    ok = client.post("/api/checkout", headers=customer_headers(b_tid),
                     json={"items": [{"product_id": p["id"], "soni": 1}],
                           "manzil": "Bishkek 1"})
    assert ok.status_code == 200, ok.text

    # A ga: register (5 ACOM). Do'st xaridi ACOM bermaydi — chegirma vaucheri.
    assert get_balance(a_tid) == 5.0
    loy = client.get("/api/loyalty", headers=customer_headers(a_tid)).json()
    assert loy["chegirma_vaucherlar"] == 1


def test_moliya_payment_methods_crud():
    """task_2 + verification #1,#2: usul qo'shish, faol/nofaol, mijozга ko'rinish."""
    # Super yangi crypto usul qo'shadi.
    r = client.post("/api/moliya/tolov-usullari", headers=admin_headers(SUPER),
                    json={"turi": "crypto", "nomi": "USDT", "qiymat": "TXy9ab3F",
                          "izoh": "Faqat TRC20"})
    assert r.status_code == 200, r.text
    mid = r.json()["id"]
    assert r.json()["faol"] is True

    # Mijoz faol usullar ro'yxatida ko'radi.
    active = client.get("/api/tolov-usullari", headers=customer_headers(70001)).json()
    assert any(u["id"] == mid and u["turi"] == "crypto" for u in active)

    # Nofaol qilinса — mijozга ko'rinmaydi (verification #2).
    client.post(f"/api/moliya/tolov-usullari/{mid}/toggle", headers=admin_headers(SUPER))
    active2 = client.get("/api/tolov-usullari", headers=customer_headers(70001)).json()
    assert not any(u["id"] == mid for u in active2)

    # Oddiy admin usul qo'sha olmaydi (faqat super).
    forb = client.post("/api/moliya/tolov-usullari", headers=admin_headers(ADMIN_A),
                       json={"turi": "karta", "nomi": "X"})
    assert forb.status_code == 403, forb.text


def test_miniapp_topup_request_upload():
    """task_3 + verification #5: Mini App'дан chek yuklash -> so'rov yaratiladi."""
    # To'lov usuli mavjud bo'lsin.
    m = client.post("/api/moliya/tolov-usullari", headers=admin_headers(SUPER),
                    json={"turi": "karta", "nomi": "Optima", "qiymat": "5000****1234",
                          "egasi": "Aziz"}).json()
    tid = 70002
    client.post("/api/confirm-phone", headers=customer_headers(tid),
                json={"tel": "+996700700002"})
    # Kichik soxta JPEG bayti.
    img = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50
    r = client.post(
        "/api/topup-request",
        headers=customer_headers(tid),
        data={"summa": "8000", "tolov_usuli_id": str(m["id"])},
        files={"chek": ("chek.jpg", img, "image/jpeg")},
    )
    assert r.status_code == 200, r.text
    sorov_id = r.json()["sorov_id"]
    # Coin hali berilmagan (rule 2).
    assert get_balance(tid) == 0.0
    # Moliya ro'yxatида ko'rinadi, to'lov usuli bilan.
    lst = client.get("/api/moliya/topups", headers=admin_headers(SUPER)).json()
    assert any(x["id"] == sorov_id for x in lst)


def test_topup_single_method_autoselect():
    """verification #3: faqat bitta faol usul bo'lса — mijoz ro'yxatда bittasini oladi."""
    # Barcha eski usullarni nofaol qilamiz, bitta faol qoldiramiz.
    allm = client.get("/api/moliya/tolov-usullari", headers=admin_headers(SUPER)).json()
    for u in allm:
        if u["faol"]:
            client.post(f"/api/moliya/tolov-usullari/{u['id']}/toggle",
                        headers=admin_headers(SUPER))
    only = client.post("/api/moliya/tolov-usullari", headers=admin_headers(SUPER),
                       json={"turi": "telefon", "nomi": "Elsom",
                             "qiymat": "+996700123456", "egasi": "Ali"}).json()
    active = client.get("/api/tolov-usullari", headers=customer_headers(70003)).json()
    assert len(active) == 1 and active[0]["id"] == only["id"]


def test_delivery_fee_courier_vs_pickup():
    """Yetkazish narxi: kuryer +100 som, punktdan olish 0."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Yetk narx tovar", "narxi": 1000, "korinish": "ommaviy"},
    ).json()
    pp = client.post(
        f"/api/admin/stores/{store_a['store_id']}/pickup-points",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "F1", "manzil": "Bishkek 7"},
    ).json()
    cust = customer_headers(80001)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700800001"})
    give_balance(80001, 10000)

    # Kuryer -> jami = 1000 + 100 yetkazish.
    r1 = client.post("/api/checkout", headers=cust,
                     json={"items": [{"product_id": p["id"], "soni": 1}],
                           "manzil": "Bishkek, Chuy 1",
                           "lokatsiya_lat": 42.87, "lokatsiya_lng": 74.59})
    o1 = r1.json()["buyurtmalar"][0]
    assert o1["jami_narx"] == 1100.0
    assert o1["yetkazish_narxi"] == 100.0
    assert o1["lokatsiya_lat"] == 42.87

    # Punktdan olish -> yetkazish 0.
    r2 = client.post("/api/checkout", headers=cust,
                     json={"items": [{"product_id": p["id"], "soni": 1}],
                           "yetkazish_turi": "pickup",
                           "pickup_points": {str(store_a["store_id"]): pp["id"]}})
    o2 = r2.json()["buyurtmalar"][0]
    assert o2["jami_narx"] == 1000.0
    assert (o2["yetkazish_narxi"] or 0) == 0.0


def test_order_status_progression():
    """Admin holatni yangi->tayyorlanmoqda->yolda->topshirildi o'tkazadi (rule 7)."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Holat tovar", "narxi": 500, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(80002)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700800002"})
    give_balance(80002, 5000)
    order = client.post("/api/checkout", headers=cust,
                        json={"items": [{"product_id": p["id"], "soni": 1}],
                              "manzil": "Bishkek 1"}).json()["buyurtmalar"][0]
    oid = order["id"]

    # Qabul (yangi -> tayyorlanmoqda).
    client.post(f"/api/admin/orders/{oid}/accept", headers=admin_headers(ADMIN_A))

    # Boshqa admin holatni o'zgartira olmaydi (rule 7).
    forb = client.patch(f"/api/admin/orders/{oid}/status",
                        headers=admin_headers(ADMIN_B), json={"holat": "yolda"})
    assert forb.status_code == 403, forb.text

    # O'z admini: tayyorlanmoqda -> yolda -> topshirildi.
    r1 = client.patch(f"/api/admin/orders/{oid}/status",
                     headers=admin_headers(ADMIN_A),
                     json={"holat": "yolda", "kuryer_tel": "+996700111222"})
    assert r1.status_code == 200 and r1.json()["holat"] == "yolda", r1.text
    # task_2: kuryer telefon raqami saqlanadi va qaytariladi.
    assert r1.json()["kuryer_tel"] == "+996700111222"
    r2 = client.patch(f"/api/admin/orders/{oid}/status",
                     headers=admin_headers(ADMIN_A), json={"holat": "topshirildi"})
    assert r2.status_code == 200 and r2.json()["holat"] == "topshirildi"

    # Noto'g'ri o'tish rad etiladi (topshirildi -> yolda).
    bad = client.patch(f"/api/admin/orders/{oid}/status",
                      headers=admin_headers(ADMIN_A), json={"holat": "yolda"})
    assert bad.status_code == 400, bad.text


def test_punkt_lookup_and_topshirdim():
    """task_1: kod bo'yicha to'liq ma'lumot (tasdiqlamasdan) + Topshirdim."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Nike Air", "narxi": 3200, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(8801)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700123456"})
    give_balance(8801, 100000)
    o = client.post(
        "/api/checkout", headers=cust,
        json={"items": [{"product_id": p["id"], "soni": 1}], "manzil": "Uy 1"},
    ).json()["buyurtmalar"][0]

    # Kod bo'yicha ko'rish — mahsulot + mijoz, tasdiqlamasdan.
    look = client.get(f"/api/admin/orders/by-code/{o['kod']}", headers=admin_headers(ADMIN_A))
    assert look.status_code == 200, look.text
    d = look.json()
    assert d["mijoz_tel"] == "+996700123456"
    assert d["mahsulotlar"][0]["nomi"] == "Nike Air"
    assert d["tasdiqlangan"] is False

    # Boshqa admin ko'ra olmaydi (rule 7).
    forb = client.get(f"/api/admin/orders/by-code/{o['kod']}", headers=admin_headers(ADMIN_B))
    assert forb.status_code == 403, forb.text

    # Topshirdim -> topshirildi + tasdiqlangan.
    c = client.post("/api/admin/orders/confirm-code",
                    headers=admin_headers(ADMIN_A), json={"kod": o["kod"]})
    assert c.status_code == 200 and c.json()["holat"] == "topshirildi", c.text


def test_order_code_alphanumeric():
    """Buyurtma kodi harf+raqam aralash, 6 belgi, katta harflar."""
    store_a, _ = setup_two_stores()
    p = client.post(
        f"/api/admin/stores/{store_a['store_id']}/products",
        headers=admin_headers(ADMIN_A),
        json={"nomi": "Kod tovar", "narxi": 300, "korinish": "ommaviy"},
    ).json()
    cust = customer_headers(80003)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700800003"})
    give_balance(80003, 5000)
    kod = client.post("/api/checkout", headers=cust,
                      json={"items": [{"product_id": p["id"], "soni": 1}],
                            "manzil": "Bishkek 1"}).json()["buyurtmalar"][0]["kod"]
    assert len(kod) == 6
    assert kod == kod.upper()
    assert any(c.isalpha() for c in kod) and any(c.isdigit() for c in kod)

    # Kichik harf bilan qidirilса ham topiladi (case-insensitive).
    r = client.get(f"/api/admin/stores/{store_a['store_id']}/orders/search",
                   headers=admin_headers(ADMIN_A), params={"q": kod.lower()})
    assert r.status_code == 200 and len(r.json()) == 1


def test_dokon_sorovi_full_flow():
    """Do'kon ochish: so'rov -> hisobchi tasdiqlaydi -> do'kon ochiladi + limit."""
    # To'lov usuli bo'lsin.
    m = client.post("/api/moliya/tolov-usullari", headers=admin_headers(SUPER),
                    json={"turi": "karta", "nomi": "Optima", "qiymat": "5000****",
                          "egasi": "Ali"}).json()
    requester = 90001
    new_admin = 90002  # bo'lajak do'kon admini
    client.post("/api/bot/confirm-phone", headers=_bot_headers(requester),
                json={"tel": "+996700900001"})
    # 30 mahsulot -> 300 som.
    r = client.post("/api/bot/dokon-sorovi", headers=_bot_headers(requester),
                    json={"dokon_nomi": "Test Do'kon", "admin_telegram_id": new_admin,
                          "mahsulot_soni": 30, "tolov_usuli_id": m["id"],
                          "ai_summa": 300, "ai_xulosa": "mos_keladi"})
    assert r.status_code == 200, r.text
    assert r.json()["summa"] == 300.0
    sorov_id = r.json()["sorov_id"]

    # 1-bosqich: hisobchi (Moliya) to'lovni tasdiqlaydi.
    tl = client.get("/api/moliya/dokon-tolovlari", headers=admin_headers(SUPER)).json()
    assert any(x["id"] == sorov_id for x in tl)
    cf = client.post(f"/api/moliya/dokon-tolovlari/{sorov_id}/confirm", headers=admin_headers(SUPER))
    assert cf.status_code == 200, cf.text
    # 2-bosqich: endi Menejer ro'yxatida ko'rinadi.
    lst = client.get("/api/menejer/dokon-sorovlari", headers=admin_headers(MANAGER)).json()
    assert any(x["id"] == sorov_id and x["mahsulot_soni"] == 30 for x in lst)

    # Menejer tasdiqlaydi (oylik arenda 500 som bilan) -> do'kon ochiladi.
    a = client.post(f"/api/menejer/dokon-sorovlari/{sorov_id}/approve",
                    headers=admin_headers(MANAGER), json={"arenda_summasi": 500})
    assert a.status_code == 200, a.text
    store_id = a.json()["store_id"]
    assert a.json()["mahfiy_kirish_kodi"]

    # Yangi admin o'z do'koniga mahsulot qo'sha oladi (rule 7).
    for i in range(30):
        rp = client.post(f"/api/admin/stores/{store_id}/products",
                         headers=admin_headers(new_admin),
                         json={"nomi": f"M{i}", "narxi": 100, "korinish": "ommaviy"})
        assert rp.status_code == 200, rp.text
    # 31-mahsulot limit tufayli rad etiladi.
    over = client.post(f"/api/admin/stores/{store_id}/products",
                       headers=admin_headers(new_admin),
                       json={"nomi": "Ortiqcha", "narxi": 100, "korinish": "ommaviy"})
    assert over.status_code == 400, over.text
    assert "limit" in over.json()["detail"].lower()


def test_dokon_sorovi_manager_only():
    """Do'kon so'rovlarini faqat menejer ko'radi (oddiy admin ham, super ham emas)."""
    # Oddiy admin -> 403.
    r = client.get("/api/menejer/dokon-sorovlari", headers=admin_headers(ADMIN_A))
    assert r.status_code == 403, r.text
    # Super-admin (menejer emas) ham -> 403 (rule 2: alohida ruxsat).
    r2 = client.get("/api/menejer/dokon-sorovlari", headers=admin_headers(SUPER))
    assert r2.status_code == 403, r2.text
    # Menejer -> 200.
    r3 = client.get("/api/menejer/dokon-sorovlari", headers=admin_headers(MANAGER))
    assert r3.status_code == 200, r3.text


def test_dokon_sorovi_invalid_count():
    """Mahsulot soni faqat o'ntalik (10..100) bo'lishi kerak."""
    tid = 90003
    client.post("/api/bot/confirm-phone", headers=_bot_headers(tid),
                json={"tel": "+996700900003"})
    r = client.post("/api/bot/dokon-sorovi", headers=_bot_headers(tid),
                    json={"dokon_nomi": "X", "admin_telegram_id": tid,
                          "mahsulot_soni": 25})
    assert r.status_code == 400, r.text


def test_menejer_v3_new_admin_can_access_boshqaruv():
    """V3: Menejer tasdiqlagach, so'rovchi Boshqaruv botга (admin sifatida) kiradi."""
    requester = 91001
    new_admin = 91002
    client.post("/api/bot/confirm-phone", headers=_bot_headers(requester),
                json={"tel": "+996700910001"})
    sr = client.post("/api/bot/dokon-sorovi", headers=_bot_headers(requester),
                     json={"dokon_nomi": "V3 Do'kon", "admin_telegram_id": new_admin,
                           "mahsulot_soni": 20})
    sid_req = sr.json()["sorov_id"]
    client.post(f"/api/moliya/dokon-tolovlari/{sid_req}/confirm", headers=admin_headers(SUPER))
    # Tasdiqлашдан oldin new_admin'да do'kon yo'q.
    before = client.get("/api/admin/my-stores", headers=admin_headers(new_admin)).json()
    assert not any(s["nomi"] == "V3 Do'kon" for s in before)
    # Menejer tasdiqlaydi.
    client.post(f"/api/menejer/dokon-sorovlari/{sid_req}/approve",
                headers=admin_headers(MANAGER), json={"arenda_summasi": 300})
    after = client.get("/api/admin/my-stores", headers=admin_headers(new_admin)).json()
    assert any(s["nomi"] == "V3 Do'kon" for s in after)


def test_menejer_v4_arenda_suspend_but_products_visible():
    """V4: muddat o'tса bloklanadi, mahsulot ko'rinadi, admin qo'sha olmaydi."""
    from datetime import timedelta

    from app.database import SessionLocal
    from app.models import Store, _now
    from app.tgbots import daily

    # Menejer do'kon ochadi (arenda bilan).
    requester, new_admin = 92001, 92002
    client.post("/api/bot/confirm-phone", headers=_bot_headers(requester),
                json={"tel": "+996700920001"})
    sr = client.post("/api/bot/dokon-sorovi", headers=_bot_headers(requester),
                     json={"dokon_nomi": "V4 Do'kon", "admin_telegram_id": new_admin,
                           "mahsulot_soni": 20})
    _sid = sr.json()['sorov_id']
    client.post(f"/api/moliya/dokon-tolovlari/{_sid}/confirm", headers=admin_headers(SUPER))
    ap = client.post(f"/api/menejer/dokon-sorovlari/{_sid}/approve",
                     headers=admin_headers(MANAGER), json={"arenda_summasi": 300}).json()
    store_id = ap["store_id"]
    # Mahsulot qo'shamiz (hali faol).
    p = client.post(f"/api/admin/stores/{store_id}/products",
                    headers=admin_headers(new_admin),
                    json={"nomi": "V4 tovar", "narxi": 500, "korinish": "ommaviy"})
    assert p.status_code == 200, p.text

    # Arenda muddatini o'tган qilib qo'yamiz + kunlik tekshiruv.
    db = SessionLocal()
    try:
        s = db.get(Store, store_id)
        s.arenda_muddati_tugashi = _now() - timedelta(days=1)
        db.commit()
        xabarlar = daily.check_arenda(db)
        db.refresh(s)
        assert s.holat == "vaqtincha_toxtatilgan"
        assert new_admin in xabarlar  # adminга ogohlantirish
    finally:
        db.close()

    # Mahsulot mijoz katalogида hali ko'rinadi (sotilaveradi).
    cat = client.get("/api/products", headers=customer_headers(92003)).json()
    assert any(x["nomi"] == "V4 tovar" for x in cat)

    # Admin endi mahsulot qo'sha olmaydi (bloklangan).
    blocked = client.post(f"/api/admin/stores/{store_id}/products",
                          headers=admin_headers(new_admin),
                          json={"nomi": "Yangi", "narxi": 100, "korinish": "ommaviy"})
    assert blocked.status_code == 403, blocked.text

    # Menejer arendani uzaytiradi -> blokdan chiqadi.
    ext = client.post(f"/api/menejer/stores/{store_id}/arenda-uzaytir",
                      headers=admin_headers(MANAGER))
    assert ext.status_code == 200 and ext.json()["holat"] == "faol"
    ok = client.post(f"/api/admin/stores/{store_id}/products",
                     headers=admin_headers(new_admin),
                     json={"nomi": "Endi bo'ladi", "narxi": 100, "korinish": "ommaviy"})
    assert ok.status_code == 200, ok.text


def test_menejer_v5_report_matches_moliya():
    """V5: Menejer hisoboti Moliya hisoboti bilan bir xil (bir xil backend)."""
    rm = client.get("/api/moliya/report", headers=admin_headers(SUPER)).json()
    rmg = client.get("/api/menejer/report", headers=admin_headers(MANAGER)).json()
    assert rm == rmg


def test_menejer_delete_store_and_product():
    """Menejer moderatsiya: do'kon va mahsulot o'chirish."""
    store_a, _ = setup_two_stores()
    p = client.post(f"/api/admin/stores/{store_a['store_id']}/products",
                    headers=admin_headers(ADMIN_A),
                    json={"nomi": "Mod tovar", "narxi": 100, "korinish": "ommaviy"}).json()
    # Mahsulot o'chirish.
    dp = client.delete(f"/api/menejer/products/{p['id']}", headers=admin_headers(MANAGER))
    assert dp.status_code == 200, dp.text
    # Do'kon o'chirish.
    ds = client.delete(f"/api/menejer/stores/{store_a['store_id']}",
                       headers=admin_headers(MANAGER))
    assert ds.status_code == 200, ds.text
    # O'chirilgach ro'yxatda yo'q.
    stores = client.get("/api/menejer/stores", headers=admin_headers(MANAGER)).json()
    assert not any(s["id"] == store_a["store_id"] for s in stores)


def test_menejer_admin_add_remove():
    """Menejer do'konga admin qo'shadi va olib tashlaydi."""
    store_a, _ = setup_two_stores()
    sid = store_a["store_id"]
    add = client.post(f"/api/menejer/stores/{sid}/admins",
                      headers=admin_headers(MANAGER), json={"telegram_id": 55555})
    assert add.status_code == 200 and 55555 in add.json()["admin_ids"]
    rm = client.delete(f"/api/menejer/stores/{sid}/admins/55555",
                       headers=admin_headers(MANAGER))
    assert rm.status_code == 200 and 55555 not in rm.json()["admin_ids"]


def test_dokon_two_stage_moliya_then_menejer():
    """To'lov tasdiqlanmaguncha Menejer ro'yxatида ko'rinmaydi (2 bosqich)."""
    tid = 93001
    client.post("/api/bot/confirm-phone", headers=_bot_headers(tid),
                json={"tel": "+996700930001"})
    sr = client.post("/api/bot/dokon-sorovi", headers=_bot_headers(tid),
                     json={"dokon_nomi": "2bosqich", "admin_telegram_id": tid,
                           "mahsulot_soni": 10})
    sid = sr.json()["sorov_id"]
    # Hisobchi tasdiqlashдан OLDIN — Menejerда yo'q, Moliyada bor.
    men = client.get("/api/menejer/dokon-sorovlari", headers=admin_headers(MANAGER)).json()
    assert not any(x["id"] == sid for x in men)
    mol = client.get("/api/moliya/dokon-tolovlari", headers=admin_headers(SUPER)).json()
    assert any(x["id"] == sid for x in mol)
    # Menejer to'lov tasdiqlanmagan so'rovni tasdiqlay olmaydi.
    early = client.post(f"/api/menejer/dokon-sorovlari/{sid}/approve",
                        headers=admin_headers(MANAGER), json={"arenda_summasi": 0})
    assert early.status_code == 400, early.text
    # Hisobchi to'lovni tasdiqlaydi -> endi Menejerда ko'rinadi.
    client.post(f"/api/moliya/dokon-tolovlari/{sid}/confirm", headers=admin_headers(SUPER))
    men2 = client.get("/api/menejer/dokon-sorovlari", headers=admin_headers(MANAGER)).json()
    assert any(x["id"] == sid for x in men2)
    # Endi Menejer tasdiqlaydi -> do'kon ochiladi.
    ap = client.post(f"/api/menejer/dokon-sorovlari/{sid}/approve",
                     headers=admin_headers(MANAGER), json={"arenda_summasi": 0})
    assert ap.status_code == 200 and ap.json()["store_id"]


def test_arenda_auto_from_product_count():
    """Oylik arenda mahsulot soniга qarab avtomatik (30 -> 300 som/oy)."""
    from app.database import SessionLocal
    from app.models import Store

    tid, new_admin = 94001, 94002
    client.post("/api/bot/confirm-phone", headers=_bot_headers(tid),
                json={"tel": "+996700940001"})
    sr = client.post("/api/bot/dokon-sorovi", headers=_bot_headers(tid),
                     json={"dokon_nomi": "Arenda auto", "admin_telegram_id": new_admin,
                           "mahsulot_soni": 30})
    sid = sr.json()["sorov_id"]
    client.post(f"/api/moliya/dokon-tolovlari/{sid}/confirm", headers=admin_headers(SUPER))
    ap = client.post(f"/api/menejer/dokon-sorovlari/{sid}/approve",
                     headers=admin_headers(MANAGER)).json()  # summa YUBORILMAYDI
    store_id = ap["store_id"]
    db = SessionLocal()
    try:
        s = db.get(Store, store_id)
        assert float(s.arenda_summasi) == 300.0  # 30/10 * 100
        assert s.arenda_muddati_tugashi is not None
    finally:
        db.close()

    # Arenda uzaytirilганда o'sha summa saqlanadi (menejer qayta yozmaydi).
    ext = client.post(f"/api/menejer/stores/{store_id}/arenda-uzaytir",
                      headers=admin_headers(MANAGER))
    assert ext.status_code == 200
    db = SessionLocal()
    try:
        assert float(db.get(Store, store_id).arenda_summasi) == 300.0
    finally:
        db.close()


def test_pickup_direct_handover():
    """Punktdan olish: tayyorlanmoqda -> topshirildi to'g'ridan-to'g'ri (kuryersiz)."""
    store_a, _ = setup_two_stores()
    p = client.post(f"/api/admin/stores/{store_a['store_id']}/products",
                    headers=admin_headers(ADMIN_A),
                    json={"nomi": "Punkt tovar", "narxi": 500, "korinish": "ommaviy"}).json()
    pp = client.post(f"/api/admin/stores/{store_a['store_id']}/pickup-points",
                     headers=admin_headers(ADMIN_A),
                     json={"nomi": "P1", "manzil": "Bishkek 9"}).json()
    cust = customer_headers(95001)
    client.post("/api/confirm-phone", headers=cust, json={"tel": "+996700950001"})
    give_balance(95001, 5000)
    order = client.post("/api/checkout", headers=cust,
                        json={"items": [{"product_id": p["id"], "soni": 1}],
                              "yetkazish_turi": "pickup",
                              "pickup_points": {str(store_a["store_id"]): pp["id"]}}).json()["buyurtmalar"][0]
    oid = order["id"]
    client.post(f"/api/admin/orders/{oid}/accept", headers=admin_headers(ADMIN_A))
    # Punkt: tayyorlanmoqda -> topshirildi (yolda'siz).
    r = client.patch(f"/api/admin/orders/{oid}/status",
                     headers=admin_headers(ADMIN_A), json={"holat": "topshirildi"})
    assert r.status_code == 200 and r.json()["holat"] == "topshirildi", r.text


def test_super_admin_cannot_upload_to_other_store():
    """Rule 1: super-admin boshqa (o'ziniki bo'lmagan) do'konга mahsulot yuklolmaydi."""
    store_a, _ = setup_two_stores()  # admin_ids=[ADMIN_A], SUPER emas
    # SUPER o'z ID'idan store_a'ga mahsulot qo'shmoqchi -> 403.
    r = client.post(f"/api/admin/stores/{store_a['store_id']}/products",
                    headers=admin_headers(SUPER),
                    json={"nomi": "Ruxsatsiz", "narxi": 100, "korinish": "ommaviy"})
    assert r.status_code == 403, r.text
    # SUPER'ning my-stores'i ham bo'sh (o'ziga do'kon biriktirilmagan).
    ms = client.get("/api/admin/my-stores", headers=admin_headers(SUPER)).json()
    assert not any(s["id"] == store_a["store_id"] for s in ms)
    # Faqat haqiqiy admin (ADMIN_A) qo'sha oladi.
    ok = client.post(f"/api/admin/stores/{store_a['store_id']}/products",
                     headers=admin_headers(ADMIN_A),
                     json={"nomi": "To'g'ri", "narxi": 100, "korinish": "ommaviy"})
    assert ok.status_code == 200, ok.text


def test_menejer_broadcast():
    """Menejer e'lon yuboradi (adminlar / mijozlar) — faqat menejer."""
    setup_two_stores()  # ADMIN_A, ADMIN_B adminlar
    client.post("/api/bot/confirm-phone", headers=_bot_headers(96001),
                json={"tel": "+996700960001"})
    # Adminlarga e'lon.
    ra = client.post("/api/menejer/broadcast", headers=admin_headers(MANAGER),
                     json={"target": "admin", "matn": "Yangilik: tez orada aksiya!"})
    assert ra.status_code == 200 and ra.json()["yuborildi"] >= 2, ra.text
    # Mijozlarga e'lon.
    rc = client.post("/api/menejer/broadcast", headers=admin_headers(MANAGER),
                     json={"target": "customer", "matn": "Chegirmalar boshlandi!"})
    assert rc.status_code == 200 and rc.json()["yuborildi"] >= 1, rc.text
    # Oddiy admin e'lon yubora olmaydi.
    forb = client.post("/api/menejer/broadcast", headers=admin_headers(ADMIN_A),
                       json={"target": "admin", "matn": "x"})
    assert forb.status_code == 403, forb.text


# ===========================================================================
# Native ilova autentifikatsiyasi (Phase 2)
# ===========================================================================
def test_auth_email_register_login_me():
    r = client.post("/api/auth/register",
                    json={"email": "Aziz@Mail.com", "parol": "parol123", "ism": "Aziz"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["token"] and d["roles"] == ["mijoz"]
    assert d["user"]["email"] == "aziz@mail.com"  # normallashtirilgan

    # Takroriy email -> 409.
    dup = client.post("/api/auth/register",
                      json={"email": "aziz@mail.com", "parol": "boshqa1"})
    assert dup.status_code == 409

    # Login: noto'g'ri parol.
    bad = client.post("/api/auth/login",
                      json={"email": "aziz@mail.com", "parol": "notogri"})
    assert bad.status_code == 401
    # Login: to'g'ri.
    ok = client.post("/api/auth/login",
                     json={"email": "aziz@mail.com", "parol": "parol123"})
    assert ok.status_code == 200, ok.text
    token = ok.json()["token"]

    # /me — token bilan.
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["user"]["email"] == "aziz@mail.com"
    # Tokensiz -> 401.
    assert client.get("/api/auth/me").status_code == 401


def test_auth_password_reset():
    client.post("/api/auth/register",
                json={"email": "reset@mail.com", "parol": "eski1234"})
    f = client.post("/api/auth/forgot", json={"email": "reset@mail.com"})
    assert f.status_code == 200
    token = f.json()["reset_token"]
    rr = client.post("/api/auth/reset", json={"token": token, "yangi_parol": "yangi1234"})
    assert rr.status_code == 200
    # Yangi parol bilan kirish ishlaydi, eski ishlamaydi.
    assert client.post("/api/auth/login",
                       json={"email": "reset@mail.com", "parol": "yangi1234"}).status_code == 200
    assert client.post("/api/auth/login",
                       json={"email": "reset@mail.com", "parol": "eski1234"}).status_code == 401


def test_auth_role_by_email():
    # super_admin_emails ro'yxatidagi email -> 'moliya' roli.
    r = client.post("/api/auth/register",
                    json={"email": "boss@arzon.kg", "parol": "boss1234"})
    assert r.status_code == 200
    assert "moliya" in r.json()["roles"]
    m = client.post("/api/auth/register",
                    json={"email": "menejer@arzon.kg", "parol": "mng12345"})
    assert "menejer" in m.json()["roles"]


def test_native_jwt_accesses_customer_endpoints():
    """Native JWT (Bearer) mijoz endpointlarига kira oladi (initData'siz)."""
    reg = client.post("/api/auth/register",
                      json={"email": "shop@mail.com", "parol": "shop1234", "ism": "Shopper"})
    token = reg.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    # /api/balance — JWT bilan ishlaydi.
    b = client.get("/api/balance", headers=h)
    assert b.status_code == 200 and "coin_balans" in b.json(), b.text
    # /api/products — ochiq katalog.
    p = client.get("/api/products", headers=h)
    assert p.status_code == 200
    # Yaroqsiz token -> 401.
    assert client.get("/api/balance", headers={"Authorization": "Bearer xxx"}).status_code == 401
