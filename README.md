# NotionPulse

NotionPulse is a reliability scoring product for Notion workspaces.

It analyzes a workspace, builds a page graph, measures structural and semantic drift, and returns a reliability score for each page. The project includes a FastAPI backend and a Next.js frontend.

## Product Summary

The backend handles crawling, feature extraction, embeddings, scoring, and cached results.

The frontend handles the connect flow, demo flow, ranked dashboard, and page detail screens.

The current repo supports both a demo workspace and a live Notion workspace.

## Core Features

1. Demo scoring flow using the bundled workspace fixture
2. Live workspace scoring through the backend API
3. Notion OAuth connect flow on the frontend
4. Ranked dashboard with reliability bands
5. Page detail view with feature level explanations
6. Graph data endpoint for page relationships

## How It Works

1. The app loads a workspace snapshot from the demo fixture or from the Notion API
2. The backend builds a graph of page relationships
3. Structural features are extracted from page activity and graph context
4. Semantic features are computed from page content embeddings
5. A model estimates staleness probability
6. The API returns a reliability score derived from that probability

## Repository Layout

`backend/` contains the API, crawler, feature pipeline, model logic, fixture data, and tests.

`frontend/` contains the web app, OAuth routes, dashboard, detail page, and shared UI components.

`render.yaml` contains the backend deployment configuration for Render.

## Main API Routes

1. `GET /health`
2. `POST /score`
3. `POST /score/demo`
4. `GET /scores`
5. `GET /page/{id}`
6. `GET /graph`

## Environment

The backend example environment file is `backend/.env.example`.

The frontend example environment file is `frontend/.env.local.example`.

For local frontend development, set `NEXT_PUBLIC_API_BASE_URL` to your backend URL, such as `http://127.0.0.1:8000`.

For live Notion OAuth, set `NOTION_OAUTH_CLIENT_ID`, `NOTION_OAUTH_CLIENT_SECRET`, and `NOTION_OAUTH_REDIRECT_URI` in the frontend environment.

For backend integrations, set `COHERE_API_KEY` if you want live Cohere embeddings. `NOTION_TOKEN` can also be set on the backend for direct token based scoring.

## Local Run

### Backend

1. Open `backend/`
2. Create a Python 3.12 virtual environment
3. Install packages from `requirements.txt`
4. Start the API with `uvicorn main:app`

### Frontend

1. Open `frontend/`
2. Copy `frontend/.env.local.example` to `frontend/.env.local`
3. Run `npm install`
4. Run `npm run dev`

Open `http://127.0.0.1:3000` in your browser.

## Verification

Backend verification uses `pytest backend/tests`.

Frontend verification uses `npm run build` from `frontend/`.

## Deployment

### Backend

Deploy the backend on Render using `render.yaml` or an equivalent web service configuration.

Set the backend root directory to `backend` and use the start command defined in `render.yaml`.

### Frontend

Deploy the frontend on Vercel with `frontend/` as the project root.

Set `NEXT_PUBLIC_API_BASE_URL` to the deployed backend URL.

If you want live Notion OAuth, register the callback URL with your Notion integration and set the matching frontend environment values.

## Limitations

1. The latest live scoring run is cached in memory, so a backend restart clears it
2. Live scoring depends on current Notion API behavior and granted access scope
3. The fallback model keeps the app functional, but broader training data would improve production quality
4. The frontend is currently verified by build success rather than a dedicated automated test suite
