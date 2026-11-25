import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import dbcompat
    main._ML["key"] = None
    if dbcompat.USE_PG:
        # Same tests against PostgreSQL: every test gets its own throw-away schema.
        import uuid, psycopg2
        schema = "t_" + uuid.uuid4().hex[:10]
        admin = psycopg2.connect(dbcompat.DATABASE_URL)
        admin.autocommit = True
        admin.cursor().execute("CREATE SCHEMA " + schema)
        monkeypatch.setattr(dbcompat, "SCHEMA", schema)
        monkeypatch.setattr(dbcompat, "_pool", None)
        main.init_db()
        yield TestClient(main.app)
        if dbcompat._pool:
            dbcompat._pool.closeall()
        admin.cursor().execute("DROP SCHEMA " + schema + " CASCADE")
        admin.close()
    else:
        monkeypatch.setattr(main, "DB", str(tmp_path / "test.db"))
        main.init_db()
        yield TestClient(main.app)


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


def test_recommendations_anonymous_is_popularity_fallback(client):
    d = client.get('/api/recommendations?limit=12').json()
    assert d['personalized'] is False and d['model'] == 'popularity'
    cats = [i['category'] for i in d['items']]
    assert max(cats.count(c) for c in set(cats)) <= 2


def test_recommendations_change_after_user_activity(client):
    login(client, 'buyer@sindbad.com', 'buyer1234')
    before = client.get('/api/recommendations?limit=8').json()
    # act like a construction-site buyer: helmets, gloves, boots, pumps
    for pid in (13, 1, 22, 11):
        assert client.post('/api/interactions', json={'product_id': pid, 'event_type': 'cart'}).status_code == 200
    after = client.get('/api/recommendations?limit=8').json()
    assert after['personalized'] is True and after['model'] == 'hybrid-ml-v1'
    ids = [i['id'] for i in after['items']]
    assert not {13, 1, 22, 11} & set(ids)            # items already touched are not recommended back
    assert ids != [i['id'] for i in before['items']]  # the row actually changed
    assert all(i['recommendation_reason'].startswith('Because you showed interest in') for i in after['items'])


def test_schema_has_users_roles_suppliers_events_and_resources(client):
    d = client.get('/api/resources').json()
    counts = d['row_counts']
    assert counts['products'] == 120 and counts['roles'] == 3 and counts['event_types'] == 5
    assert counts['user_roles'] >= counts['users'] > 0 and counts['suppliers'] >= 3
    assert counts['synthetic_interactions'] > 8000
    syn = [r for r in d['resources'] if r['name'] == 'synthetic_interactions'][0]
    assert syn['is_synthetic'] == 1
    assert d['backend'] in ('sqlite', 'postgresql')


def test_new_signup_gets_role_and_supplier_rows(client):
    r = client.post('/api/register', json={'name': 'Sam', 'email': 'sam@example.com', 'password': 'longpass123', 'role': 'supplier', 'company': 'Sam Trading', 'country': 'Egypt'})
    assert r.status_code == 200, r.text
    c = main.db()
    uid = c.execute("SELECT id FROM users WHERE email='sam@example.com'").fetchone()['id']
    assert c.execute('SELECT role FROM user_roles WHERE user_id=?', (uid,)).fetchone()['role'] == 'supplier'
    assert c.execute('SELECT company FROM suppliers WHERE user_id=?', (uid,)).fetchone()['company'] == 'Sam Trading'
    c.close()


def test_admin_db_viewer_is_admin_only_and_hides_secrets(client):
    assert client.get('/api/admin/db').status_code == 401
    client.post('/api/register', json={'name': 'Ann Admin', 'email': 'ann@example.com', 'password': 'longpass123', 'role': 'buyer', 'company': 'Ann Co', 'country': 'Egypt'})
    assert client.get('/api/admin/db').status_code == 403
    c = main.db()
    uid = c.execute("SELECT id FROM users WHERE email='ann@example.com'").fetchone()['id']
    c.execute("INSERT INTO user_roles(user_id,role,granted_at) VALUES(?,?,?)", (uid, 'admin', 'now')); c.commit(); c.close()
    d = client.get('/api/admin/db').json()
    assert any(x['table'] == 'products' and x['rows'] == 120 for x in d['tables'])
    rows = client.get('/api/admin/db/users').json()['rows']
    assert rows and all(r['password_hash'] == '(hidden)' and r['salt'] == '(hidden)' for r in rows)
    assert client.get('/api/admin/db/sqlite_master').status_code == 404
    assert client.get('/admin/db').status_code == 200
