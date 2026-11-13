# CivicPulse

**Making civic problems visible. Making resolution accountable.**

CivicPulse is a full-stack civic issue reporting and prioritization app. Residents can submit a description, GPS/map location, and optional photo; browse issues on a Leaflet map; and see a report's current status after submission. Coordinators can verify reports, assign a team, and move issues through their resolution status.

Residents create an account at `/signup` and sign in at `/login`. A secure, HTTP-only session cookie keeps them signed in. Issue submission requires a signed-in account; community report browsing is available after sign-in.

Coordinators can mark suspicious reports as fake or restore them. Fake reports remain visible in the admin dashboard and are excluded from the public issue list and community totals.

## Stack

- **Frontend:** React + Vite
- **API:** FastAPI + SQLAlchemy
- **Database:** PostgreSQL or local SQLite
- **Maps:** Leaflet + OpenStreetMap
- **Photos:** Pillow watermarking + Cloudinary hosting
- **Analysis:** Pandas, NumPy, and scikit-learn TF-IDF similarity with location proximity

## Run locally

Python 3.10+ and Node.js 20+ are recommended. Open two terminals from the project root.

**Terminal 1 — API**

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r backend/requirements.txt
cd backend
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — React app**

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. Vite proxies `/api` requests to FastAPI on port 8000. For a built frontend, run `npm run build` in `frontend`; FastAPI then serves `frontend/dist` from `/`.

## Configuration

Copy `.env.example` to `.env` in the project root.

- Leave `DATABASE_URL` blank to use `civicpulse.db` (SQLite) in the project root. For PostgreSQL, set a SQLAlchemy URL such as `postgresql+psycopg://user:password@localhost:5432/civicpulse`.
- Promote an existing account to coordinator/admin with `cd backend && ../.venv/bin/python -m app.promote_admin account@example.com`. The command asks for confirmation. After promotion, use **Administrator login** with that account's email and password. Admin actions use the same HTTP-only account session as the rest of the app.
- `COOKIE_SECURE=false` is for local HTTP development. Set it to `true` when serving CivicPulse over HTTPS.
- Set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` to enable photo upload. Uploads are limited to 10 MB and JPEG, PNG, or WebP. Pillow normalizes the image and adds a CivicPulse watermark with its submitted coordinates and upload time before Cloudinary stores it.

Photo upload is optional. Reports can be submitted without Cloudinary credentials. Browser geolocation requires permission; users can also click the map to choose the report location. OpenStreetMap tiles require internet access.

## How prioritization works

New reports receive a review score from 0 to 100. Category weighting, urgent language in the report, nearby reports in the same category, and text similarity contribute to that score. The service compares reports within 300 metres and flags a likely duplicate when text similarity reaches its threshold. The score is a triage aid for coordinators, not an automated resolution decision. Coordinator analytics summarize issue counts by category/status, average score, and possible duplicates.

## API

- `GET /api/health` — service health
- `POST /api/auth/signup` — create an account and start a session
- `POST /api/auth/login` — sign in
- `POST /api/auth/admin-login` — sign in with an administrator account
- `POST /api/auth/logout` — end the current session
- `GET /api/auth/me` — get the signed-in user, if any
- `GET /api/categories` — available issue categories
- `GET /api/geocode/search?q=...` — explicit, user-submitted place search through OpenStreetMap Nominatim (cached and rate-limited)
- `GET /api/issues` — issue feed, ordered by priority; supports `category`, `status`, `q`, `limit`, and `offset`
- `GET /api/issues/stats` — status totals
- `GET /api/issues/{id}` — public issue detail
- `POST /api/issues` — submit an issue (signed-in account required); response includes its current status
- `POST /api/issues/upload` — watermark and upload a photo to Cloudinary
- `PATCH /api/admin/issues/{id}` — coordinator status, verification, and assignment updates (admin session required)
- `GET /api/admin/analytics` — coordinator analytics (admin session required)

FastAPI’s interactive docs are at <http://127.0.0.1:8000/docs>.

## Scope and deployment notes

This is a local-development MVP with a shared coordinator key. A public deployment should add individual coordinator accounts and roles, HTTPS, request and upload rate limits, retention/privacy policies for precise location and images, and operational database backups. Schema changes are managed with Alembic; run `alembic upgrade head` before starting against an existing database.
