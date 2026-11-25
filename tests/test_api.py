import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "test.db"))
    main.init_db()
    return TestClient(main.app)


def login(client, email, password):
    r = client.post("/api/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r


def test_health_and_catalogue(client):
    assert client.get("/api/health").json()["status"] == "ok"
    products = client.get("/api/products?limit=200").json()
    assert len(products) >= 120
    assert len(client.get("/api/categories").json()) == 8


def test_seed_images_are_local(client):
    for p in client.get("/api/products?limit=200").json():
        assert p["image"].startswith(("/static/art/", "/photo/")), p["title"]
        assert client.get(p["image"]).status_code == 200, p["image"]
    assert client.get("/static/art/electronics.svg").status_code == 200


def test_login_rejects_wrong_password(client):
    r = client.post("/api/login", json={"email": "buyer@sindbad.com", "password": "wrong-password"})
    assert r.status_code == 401


def test_register_duplicate_email_conflicts(client):
    body = {"name": "New Buyer", "email": "new@example.com", "password": "longenough1",
            "role": "buyer", "company": "New Co", "country": "Egypt"}
    assert client.post("/api/register", json=body).status_code == 200
    assert client.post("/api/register", json=body).status_code == 409


def test_buyer_cannot_publish_products(client):
    login(client, "buyer@sindbad.com", "buyer1234")
    r = client.post("/api/products", json={"title": "Test item", "category": "Packaging", "price": 1.0})
    assert r.status_code == 403


def test_supplier_cannot_edit_another_suppliers_product(client):
    login(client, "demo@sindbad.com", "demo1234")
    other = next(p for p in client.get("/api/products?limit=200").json() if p["supplier_id"] != client.get("/api/me").json()["user"]["id"])
    r = client.put(f"/api/products/{other['id']}", json={"title": "Hijacked title", "category": other["category"], "price": 1.0})
    assert r.status_code == 403


def test_order_enforces_moq_and_reduces_stock(client):
    product = client.get("/api/products?limit=200").json()[0]
    login(client, "buyer@sindbad.com", "buyer1234")
    too_few = client.post("/api/orders", json={"items": [{"product_id": product["id"], "quantity": 1}]}) if product["moq"] > 1 else None
    if too_few is not None:
        assert too_few.status_code == 400
    qty = product["moq"]
    r = client.post("/api/orders", json={"items": [{"product_id": product["id"], "quantity": qty}]})
    assert r.status_code == 200, r.text
    assert r.json()["total"] == round(product["price"] * qty, 2)
    after = client.get(f"/api/products/{product['id']}").json()
    assert after["stock"] == product["stock"] - qty


def test_order_cannot_exceed_stock_across_lines(client):
    product = min(client.get("/api/products?limit=200").json(), key=lambda p: p["stock"])
    login(client, "buyer@sindbad.com", "buyer1234")
    half = max(product["moq"], product["stock"] // 2 + 1)
    r = client.post("/api/orders", json={"items": [{"product_id": product["id"], "quantity": half},
                                                    {"product_id": product["id"], "quantity": half}]})
    assert r.status_code in (400, 409)
    assert client.get(f"/api/products/{product['id']}").json()["stock"] == product["stock"]


def test_rfq_quote_flow(client):
    login(client, "buyer@sindbad.com", "buyer1234")
    assert client.post("/api/rfqs", json={"title": "500 cartons", "quantity": 500}).status_code == 200
    rfqs = client.get("/api/rfqs").json()
    assert rfqs
    rid = rfqs[0]["id"]
    client.post("/api/logout")
    login(client, "atlas@sindbad.com", "demo1234")
    assert client.post(f"/api/rfqs/{rid}/quotes", json={"price": 0.4}).status_code == 200
    assert client.post(f"/api/rfqs/{rid}/quotes", json={"price": 0.3}).status_code == 409


def test_recommendations_envelope(client):
    data = client.get("/api/recommendations?limit=5").json()
    assert {"items", "strategy", "model", "personalized"} <= set(data)
    assert 0 < len(data["items"]) <= 5


def test_product_photo_served(client):
    r = client.get('/photo/1.jpg')
    assert r.status_code == 200 and r.headers['content-type'] == 'image/jpeg'
    assert r.content[:2] == b'\xff\xd8'
    assert client.get('/photo/99999.jpg').status_code == 404


def test_similar_products_endpoint(client):
    r = client.get('/api/products/1/similar?k=5')
    assert r.status_code == 200
    items = r.json()['items']
    assert len(items) == 5 and all(i['id'] != 1 for i in items)
    assert set(items[0]['reason']) == {'bought_together', 'similar_text'}
    assert client.get('/api/products/99999/similar').status_code == 404
