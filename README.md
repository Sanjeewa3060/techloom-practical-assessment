# Techloom.ai Software Engineer Intern: Practical Assessment

| | Link |
|---|---|
| Repository | `https://github.com/<you>/<repo>` |
| Task 01 live app (POS) | `https://<task-01-frontend>.vercel.app` |
| Task 01 API docs | `https://<task-01-api>.onrender.com/docs` |
| Task 02 live app (Storefront) | `https://<task-02-frontend>.vercel.app` |
| Task 02 API docs | `https://<task-02-api>.onrender.com/docs` |
| Demo video (optional) | `https://...` |

> The free Render tier sleeps after inactivity. The first request can take ~30-60 s to wake up.

## Tech stack
Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL (Neon), React 18 + Vite, deployed on Render (API) and Vercel (UI).

```
task-01/   POS Order & Inventory System   (backend/ + frontend/)
task-02/   E-Commerce Checkout & Payment  (backend/ + frontend/)
```

## Run locally

```bash
# Postgres (or skip this and use the SQLite fallback by leaving DATABASE_URL unset)
docker run --name pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=pos -p 5432:5432 -d postgres:16

cd task-01/backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env && export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload                          # http://localhost:8000/docs

cd ../frontend
npm install && cp .env.example .env && npm run dev     # http://localhost:5173
```
Task 02 is identical: use port 8001 for its API if both run at once
(`uvicorn app.main:app --port 8001`, and set `VITE_API_URL=http://localhost:8001`).

## Environment variables

| Variable | Where | Default | Meaning |
|---|---|---|---|
| `DATABASE_URL` | API | `sqlite:///./pos.db` | Postgres connection string |
| `RESERVATION_TTL_SECONDS` | API | `300` | Stock hold time (5 min). Use `20` for demos |
| `EXPIRY_SWEEP_SECONDS` | API | `5` | How often the expiry job runs |
| `CORS_ORIGINS` | API | `*` | Comma-separated frontend URLs |
| `SEED_ON_START` | API | `true` | Insert sample products if the table is empty |
| `VITE_API_URL` | UI | `http://localhost:8000` | Base URL of the API |

## Deploy
1. **Database:** create a free Postgres project on Neon and copy its connection string.
2. **API (Render):** New Web Service, pick this repo, Root Directory `task-01/backend`,
   Build `pip install -r requirements.txt`, Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
   Set `DATABASE_URL` and `CORS_ORIGINS` (your Vercel URL). Repeat for `task-02/backend`
   (use a second Neon database or branch so the two apps do not share tables).
3. **UI (Vercel):** import the repo, Root Directory `task-01/frontend` (framework: Vite),
   set `VITE_API_URL` to the Render URL. Repeat for `task-02/frontend`.
4. Open both live URLs, then paste them at the top of this README.

## StudyHub demo catalogue and product images
Both apps ship with the same 22-item school-supplies catalogue (backpack, notebooks, pens, calculator, ...).
Product images are illustrations in `frontend/public/images/` and are referenced by path (`/images/backpack.svg`),
so they deploy with the frontend. To use real photos, add e.g. `backpack.jpg` to that folder and change the file
name in `backend/app/seed.py`, then reload the data:
```bash
cd task-02/backend && python -m app.seed --reset   # wipes products, carts and orders, then re-seeds
```
(For the deployed database, set `DATABASE_URL` to the Neon connection string first.)
Task 02 paginates products (`page`, `page_size`; the match count is returned in the `X-Total-Count` header).

## How the hard parts work

| Requirement | Approach |
|---|---|
| **No overselling** | Stock changes only through atomic `UPDATE ... WHERE stock_total - stock_reserved >= qty`. `rowcount == 0` means "not enough stock". Postgres row locks serialise competing buyers. DB `CHECK` constraints are a second safety net. |
| **Reservation + 5 min expiry** | Checkout increments `stock_reserved` and sets `orders.expires_at`. A background task sweeps expired orders every 5 s, and expiry is also enforced lazily on pay / list / checkout, so stock is correct even if the server slept. |
| **Duplicates** | `Idempotency-Key` header, backed by a UNIQUE index on `orders` and `payments`. Replays return the original result. Paying an already-paid order returns 409. The cart rows are deleted with a row-count check so one cart can never become two orders. |
| **Order lifecycle** | `app/state.py` holds the allowed transitions. Each change is a compare-and-set `UPDATE ... WHERE status = :old`, so racing requests can only win once. Invalid moves return 409. |
| **Consistency** | Each action (checkout, pay, cancel, expire) is one DB transaction. Any exception rolls everything back. |
| **Mock gateway** | `outcome` = `success` (to PAID, stock sold), `failure` (to FAILED, stock released), `timeout` (to EXPIRED, stock released). Omit it for a random result. |

State machine: `PENDING -> RESERVED -> PAID`; `RESERVED -> FAILED | EXPIRED | CANCELLED`; `PAID -> CANCELLED` (restores stock; Task 02 also records a simulated refund).

## How to test each feature

Automated:
```bash
cd task-01/backend && pytest -q                         # lifecycle, payments, duplicates, expiry
python tests/concurrency_check.py http://localhost:8000 --stock 5 --buyers 30
cd ../../task-02/backend && pytest -q                   # + search/filters, refunds
```
The concurrency script fires 30 simultaneous checkouts for 5 units and asserts exactly 5 succeed.
Run it against Postgres (or the live API) for the most meaningful result.

Manual (UI):
- **Inventory CRUD:** Task 01, Inventory tab. Add, edit, delete. The Available column updates live.
- **Reservation:** Register tab, add items, "Reserve stock and check out". Watch Available drop and the countdown start.
- **Expiry:** run the API with `RESERVATION_TTL_SECONDS=20`, check out, wait. The order becomes EXPIRED and stock returns.
- **Payments:** click Success / Failure / Timeout. Double-click Success: only one payment is recorded.
- **Cancel:** Orders tab, cancel a RESERVED or PAID order. Stock is restored.
- **Task 02 discovery:** search, category, price range, in-stock filter, product page.
- **Task 02 refund:** pay an order, then My orders, "Cancel and refund". A refund record appears and stock returns.

## API overview
`GET/POST /products`, `GET/PUT/DELETE /products/{id}`, `GET /products/stock`, `GET /cart`, `PUT /cart/items`,
`POST /checkout`, `POST /orders/{id}/pay`, `POST /orders/{id}/cancel`, `GET /orders`, `GET /orders/{id}`;
Task 02 adds search/filter/sort/pagination query params on `/products`, `GET /products/categories`, `POST /orders/{id}/refund`.
Full interactive docs at `/docs`.

## Assumptions and trade-offs
- No login: each browser gets a random user id sent as `X-User-Id` (demo-level identity).
- Tables are created at startup with `create_all`; a production system would use Alembic migrations.
- Task 02 deliberately reuses the Task 01 inventory engine and adds the storefront features on top.
