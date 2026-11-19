"""ARZON 2.0 migration regression tests."""
from backend.app.models import Store, Product, User


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == "2.0.0"


def test_native_registration_profile_and_guest_endpoints(client):
    response = client.post("/api/auth/register", json={"email": "native@example.test", "parol": "secret123", "ism": "Test"})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['token']}"}
    assert client.patch("/api/auth/me", headers=headers, json={"ism": "Edited", "tel": "+996555000000"}).status_code == 200
    assert client.get("/api/products").status_code == 200
    assert client.get("/api/stores").status_code == 200
    assert client.get("/api/hududlar").status_code == 200
    assert client.post("/api/promo/check", json={"kod": "NOTFOUND"}).status_code == 200


def test_catalog_marks_paused_store_products(client):
    from backend.app.database import SessionLocal
    with SessionLocal() as db:
        store = Store(nomi="Paused", turi="magazin", tarif_turi="pro", holat="vaqtincha_toxtatilgan")
        db.add(store); db.flush()
        db.add(Product(store_id=store.id, nomi="Item", narxi=100))
        db.commit()
    result = client.get("/api/products").json()
    assert len(result) == 1
    assert result[0]["sotish_toxtatilgan"] is True


def test_private_media_requires_owner(client):
    registered = client.post("/api/auth/register", json={"email": "media@example.test", "parol": "secret123"})
    headers = {"Authorization": f"Bearer {registered.json()['token']}"}
    response = client.post("/api/media/upload", headers=headers, params={"maxfiy": "true"}, files={"rasm": ("kyc.jpg", b"image-bytes", "image/jpeg")})
    assert response.status_code == 200
    media_id = response.json()["id"]
    assert client.get(f"/media/db/{media_id}").status_code == 403
    assert client.get(f"/media/db/{media_id}", headers=headers).status_code == 200
