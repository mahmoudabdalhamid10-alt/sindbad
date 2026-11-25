<picture><img src="https://github.com/user-attachments/assets/eb75ff3d-5b09-49c5-88b1-041ab93652db" alt="Sindbad 2.0 - AI-Powered Global B2B Marketplace" width="100%" /></picture>

<p align="center"><strong>A local development build of a bilingual (Arabic/English) B2B sourcing marketplace.</strong></p>

<p align="center">
<img src="https://img.shields.io/badge/Python-0b1220?style=for-the-badge&logo=python&logoColor=67e8f9" alt="Python" />
<img src="https://img.shields.io/badge/FastAPI-0b1220?style=for-the-badge&logo=fastapi&logoColor=67e8f9" alt="FastAPI" />
<img src="https://img.shields.io/badge/SQLite-0b1220?style=for-the-badge&logo=sqlite&logoColor=67e8f9" alt="SQLite" />
</p>

<sub>Artwork is illustrative.</sub>

![Sindbad marketplace home page](docs/screenshot.svg)

## Run on Windows

1. Install Python 3.10+ (Python 3.13 is supported).
2. Extract this folder.
3. Double-click `START.bat` and keep the terminal open.
4. Your browser should open automatically. If it does not, visit http://127.0.0.1:8000

## Run on macOS or Linux

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Then open http://127.0.0.1:8000. The SQLite database (`sindbad.db`) is created and seeded on first start.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use a temporary database and cover login, registration, role checks, product ownership, MOQ and stock rules for orders, the RFQ and quotation flow, and the recommendation response.

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Supplier | `demo@sindbad.com` | `demo1234` |
| Buyer | `buyer@sindbad.com` | `buyer1234` |
| More suppliers | `atlas@sindbad.com`, `nova@sindbad.com` | `demo1234` |

## Included implementation

- Buyer/supplier registration, login and role checks.
- Product catalog with 120 seeded wholesale listings, search, category/origin/price filters and sorting.
- Supplier catalog publishing and product ownership checks.
- Product details, favorites, sourcing cart and demo order checkout (no payment is collected).
- RFQ publishing, supplier quotations, buyer quote comparison, and buyer RFQ/order dashboard.
- Supplier directory, supplier-side product management, open buying requests, and business statistics.
- Hybrid recommendation endpoint: category and tag affinity, weighted user-user collaborative filtering, popularity prior and cold-start fallback.
- Arabic/English UI with RTL/LTR switching.

## Recommendation system

`GET /api/recommendations` returns ranked products with a score and a reason. It uses a transparent hybrid baseline combining content/category affinity and collaborative-style aggregate popularity signals. It is an implementation-ready baseline, not a trained deep-learning model. For a research-grade model, collect a larger consented interaction dataset, add offline train/validation splits, compare content-based, item-item collaborative and hybrid models, and report Precision@K, Recall@K and NDCG@K.

The response envelope includes `items`, `strategy`, `model`, and `personalized`, and the frontend consumes this format. Product detail views, add-to-cart events and favorites feed interaction signals, and the recommendation cards explain why an item was suggested.

Test endpoints: `GET /api/health`, `GET /api/products?limit=200`, `GET /api/recommendations?limit=12`.

## Main API routes

- `POST /api/register`, `POST /api/login`, `GET /api/me`, `POST /api/logout`
- `GET /api/products`, `GET /api/products/{id}`, `POST/PUT/DELETE /api/products`
- `GET /api/categories`, `GET /api/suppliers`
- `POST /api/interactions`, `GET /api/recommendations`
- `GET/POST /api/favorites`, `POST /api/favorites/{product_id}`
- `POST /api/orders`, `GET /api/orders`
- `POST /api/rfqs`, `GET /api/rfqs`, `POST/GET /api/rfqs/{id}/quotes`, `GET /api/dashboard`, `GET /api/supplier/products`

## Catalogue data

The demo catalogue holds **120 wholesale listings** across 8 B2B categories and 3 demo supplier companies. Product pictures are local category illustrations (`static/art/`), not photos of the listed items, so the app works offline. Listings are clearly sample marketplace data and should be replaced/verified before public launch. Existing `sindbad.db` files are upgraded additively: missing sample products are inserted by title; user accounts, orders, RFQs and existing interactions are not deleted.

## Important deployment note

This is a local MVP/dev build. Before public production deployment, configure a strong `SINDBAD_SECRET`, HTTPS, PostgreSQL, migrations, rate limiting, CSRF protection, audit logs, backups, supplier verification, and real payment/shipping integrations. Demo checkout does not charge money.
