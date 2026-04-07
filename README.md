# NotionPulse

Knowledge reliability scoring for Notion workspaces.

NotionPulse crawls a Notion workspace, builds a page graph, extracts structural and semantic drift signals, and returns a calibrated reliability score for each page. The product ships as two services:

| Service | Stack | Purpose |
| --- | --- | --- |
| Frontend | Next.js 15 · TypeScript · Tailwind | Connect flow, ranked dashboard, page detail view |
| Backend | FastAPI · Python 3.12 · scikit-learn | Crawl, feature extraction, embeddings, model scoring |

## What is implemented

- Demo scoring flow with a 28-page fixture from the project plan
- Live Notion workspace scoring through the backend API
- Notion OAuth connect flow with server-side token storage via HTTP-only cookies
- Ranked dashboard with green / amber / red reliability bands
- Per-page feature breakdown with semantic neighbor comparisons
- Deployable backend config for Render

## Repo structure

```text
backend/
  main.py                FastAPI routes
  service.py             Scoring orchestration and run cache
  crawler.py             Live Notion API crawler
  snapshot.py            WorkspaceSnapshot dataclasses and fixture loader
  features.py            Structural features
  embeddings.py          Cohere embeddings plus SQLite cache
  model.py               Label generation, training, calibration, scoring
  demo_workspace.json    Demo fixture
  tests/test_api.py      Backend API tests

frontend/
  app/page.tsx                   Home and connect view
  app/dashboard/page.tsx         Ranked reliability dashboard
  app/page/[id]/page.tsx         Page detail view
  app/api/notion/*               OAuth and logout routes
  app/auth/notion/callback       OAuth callback handler
  app/api/score/live             Live workspace rescore route
  components/                    Shared UI components
  lib/                           API and auth helpers

render.yaml             Render deployment config for the backend
```

## Architecture

The backend supports two data sources behind one scoring pipeline:

1. Demo mode loads `backend/demo_workspace.json`
2. Live mode crawls Notion through the official API

Both sources feed the same pipeline:

1. Build a `WorkspaceSnapshot`
2. Build the page dependency graph
3. Extract structural features
4. Compute semantic features from embeddings
5. Load the bundled model, or retrain from the fixture if `model.pkl` is not portable in the current environment
6. Return calibrated reliability scores

The frontend uses the backend as the source of truth. For live mode, the user authenticates with Notion OAuth, the callback exchanges the authorization code for an access token, stores it in an HTTP-only cookie, triggers an initial score run, and redirects to the dashboard.

## Reliability signals

Each page is scored from these feature families:

- Structural: `days_since_edit`, `edit_frequency`, `inbound_backlinks`, `neighbor_recency_gap`, `is_orphan`
- Semantic: `cohere_drift`, `self_neighbor_sim`, `cluster_outlier_score`

The model output is a staleness probability. The API returns `1 - probability` as the reliability score.

Banding used by the UI:

- `red`: score `< 0.4`
- `amber`: `0.4 <= score < 0.7`
- `green`: score `>= 0.7`

## Environment variables

### Backend

Copy [backend/.env.example](/Users/mderaznasr/conductor/workspaces/notion-project/almaty/backend/.env.example#L1) into `backend/.env` if you want local secrets on the API side.

| Variable | Required | Purpose |
| --- | --- | --- |
| `NOTION_TOKEN` | No | Optional fallback token for direct live scoring |
| `COHERE_API_KEY` | No | Real Cohere embeddings. Without it, demo embeddings are deterministic pseudo-embeddings |

### Frontend

Copy [frontend/.env.local.example](/Users/mderaznasr/conductor/workspaces/notion-project/almaty/frontend/.env.local.example#L1) into `frontend/.env.local`.

| Variable | Required | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Yes | Backend base URL, for example `http://127.0.0.1:8000` |
| `NOTION_OAUTH_CLIENT_ID` | For OAuth | Notion OAuth client id |
| `NOTION_OAUTH_CLIENT_SECRET` | For OAuth | Notion OAuth client secret |
| `NOTION_OAUTH_REDIRECT_URI` | For OAuth | Must match the callback URL configured in Notion |

## Local development

### 1. Backend

Use Python 3.12 if possible.

```bash
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### 2. Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

The app will be available at `http://127.0.0.1:3000`.

## API surface

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | `GET` | Liveness check |
| `/score` | `POST` | Score a live workspace or demo mode via payload |
| `/score/demo` | `POST` | Score the fixture directly |
| `/scores` | `GET` | Read the latest cached workspace run |
| `/page/{id}` | `GET` | Page-level feature breakdown |
| `/graph` | `GET` | Page graph adjacency data |

### Example demo request

```bash
curl -X POST http://127.0.0.1:8000/score/demo
```

### Example live request

```bash
curl -X POST http://127.0.0.1:8000/score \
  -H "Content-Type: application/json" \
  -d '{"notion_token":"secret_xxx"}'
```

## Tests and verification

Backend:

```bash
. .venv/bin/activate
pytest backend/tests -q
```

Frontend:

```bash
cd frontend
npm run build
```

## Deployment

### Backend on Render

The repo includes [render.yaml](/Users/mderaznasr/conductor/workspaces/notion-project/almaty/render.yaml#L1). Create a new Render Blueprint or web service and set:

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Set the `COHERE_API_KEY` and `NOTION_TOKEN` environment variables if you need them.

### Frontend on Vercel

Create a Vercel project rooted at `frontend` and set:

- `NEXT_PUBLIC_API_BASE_URL` to your Render backend URL
- `NOTION_OAUTH_CLIENT_ID`
- `NOTION_OAUTH_CLIENT_SECRET`
- `NOTION_OAUTH_REDIRECT_URI` to `https://<your-domain>/auth/notion/callback`

Make sure the same redirect URI is registered in the Notion integration settings.

## Known limitations

- Live scoring depends on the current Notion API response shape and access scope granted to the integration
- The latest live run is cached in memory on the backend, so a process restart clears it
- The fallback model trained from the demo fixture keeps the app functional, but it is not a substitute for training on a broader dataset
- Frontend automated tests are not set up yet; the frontend is currently verified by production build only

## Version notes

- The crawler uses Notion API version `2026-03-11`
- The frontend uses `next@15.5.14`, which clears the current `npm audit` advisories verified in this workspace on April 7, 2026
