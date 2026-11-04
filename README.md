# Sindbad 2.0 — AI-Powered Global B2B Marketplace

A local development build of a bilingual (Arabic/English) B2B sourcing marketplace.

## Run on Windows
1. Install Python 3.10+ (Python 3.13 is supported).
2. Extract this folder.
3. Double-click `START.bat` and keep the terminal open.
4. Your browser should open automatically. If it does not, visit http://127.0.0.1:8000

## Demo accounts
- Supplier: `demo@sindbad.com` / `demo1234`
- Buyer: `buyer@sindbad.com` / `buyer1234`
- Additional suppliers: `atlas@sindbad.com` and `nova@sindbad.com` (password `demo1234`)

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

## Main API routes
- `POST /api/register`, `POST /api/login`, `GET /api/me`, `POST /api/logout`
- `GET /api/products`, `GET /api/products/{id}`, `POST/PUT/DELETE /api/products`
- `GET /api/categories`, `GET /api/suppliers`
- `POST /api/interactions`, `GET /api/recommendations`
- `GET/POST /api/favorites`, `POST /api/favorites/{product_id}`
- `POST /api/orders`, `GET /api/orders`
- `POST /api/rfqs`, `GET /api/rfqs`, `POST/GET /api/rfqs/{id}/quotes`, `GET /api/dashboard`, `GET /api/supplier/products`

## Important deployment note
This is a local MVP/dev build. Before public production deployment, configure a strong `SINDBAD_SECRET`, HTTPS, PostgreSQL, migrations, rate limiting, CSRF protection, audit logs, backups, supplier verification, and real payment/shipping integrations. Demo checkout does not charge money.


## Sindbad catalogue + recommendation update

- The demo catalogue is expanded to **120 wholesale listings** across 8 B2B categories and 3 demo supplier companies. Listings are clearly sample marketplace data and should be replaced/verified before public launch.
- Existing `sindbad.db` files are upgraded additively: missing sample products are inserted by title; user accounts, orders, RFQs and existing interactions are not deleted.
- `/api/recommendations` now returns a response envelope with `items`, `strategy`, `model`, and `personalized`. The frontend consumes this format.
- Hybrid ranking combines category/tag content affinity, weighted user-user collaborative filtering (cosine similarity), and a popularity prior for anonymous/new buyers.
- Product detail views, add-to-cart events and favorites feed interaction signals. The recommendation cards explain why an item was suggested.
- Test endpoints: `GET /api/health`, `GET /api/products?limit=200`, and `GET /api/recommendations?limit=12`.
