import pytest
from backend.app.models import Product, Store, User, YetkazishHudud, ObunaTarif


def auth_headers(client):
    response = client.post("/api/auth/register", json={"email": "user@test.local", "parol": "secret1", "ism": "Test User"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_register_me_and_profile(client):
    response = client.post("/api/auth/register", json={"email": "native@test.local", "parol": "secret1", "ism": "Native"})
    assert response.status_code == 200
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    updated = client.patch("/api/auth/me", headers=headers, json={"ism": "Yangilangan", "tel": "+996555000000"})
    assert updated.status_code == 200
    assert updated.json()["user"]["ism"] == "Yangilangan"


def test_guest_catalog_and_store(client):
    assert client.get("/api/products").status_code == 200
    assert client.get("/api/stores").status_code == 200
    assert client.get("/api/hududlar").status_code == 200


def test_promo_check_is_guest(client):
    response = client.post("/api/promo/check", json={"kod": "NONE"})
    assert response.status_code == 200
    assert "ok" in response.json()


def test_private_media_requires_owner_or_super_admin(client):
    register = client.post("/api/auth/register", json={"email": "private@test.local", "parol": "secret1"})
    token = register.json()["token"]
    media = client.post("/api/media/upload", headers={"Authorization": f"Bearer {token}"}, params={"maxfiy": "true"}, files={"rasm": ("selfie.jpg", b"image", "image/jpeg")})
    assert media.status_code == 200
    media_id = media.json()["id"]
    assert client.get(f"/media/db/{media_id}").status_code == 403
    assert client.get(f"/media/db/{media_id}", headers={"Authorization": f"Bearer {token}"}).status_code == 200
