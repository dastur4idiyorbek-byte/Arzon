from fastapi import HTTPException


def test_catalog_endpoint_is_guest_accessible(client):
    response = client.get("/api/products")
    assert response.status_code == 200


def test_checkout_requires_auth(client):
    response = client.post("/api/checkout", json={"items": [{"product_id": 1, "soni": 1}]})
    assert response.status_code == 401
