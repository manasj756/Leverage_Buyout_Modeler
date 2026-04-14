# LBO Modeler — Frontend (React + Vite)

This is the UI for the LBO Modeler. It calls the backend API and renders deal KPIs, scenario comparisons, and sensitivity outputs.

## Local development

1. Start the backend API (from the repo root):
	- `python -m pip install -r backend/requirements.txt`
	- `python -m uvicorn backend.api:app --port 8001`

2. Start the frontend (from `frontend/`):
	- `npm ci`
	- `npm run dev`

The frontend reads the backend URL from `VITE_API_URL`.
- Copy `frontend/.env.example` to `frontend/.env` and edit if needed.

## Deploy to Vercel (frontend)

1. In Vercel, set the Root Directory to `frontend/`.
2. Add an Environment Variable:
	- `VITE_API_URL` = your deployed backend base URL
3. Deploy.

Note: the backend is FastAPI and should be deployed separately (e.g. Render/Railway/Fly.io) unless you intentionally convert it into Vercel serverless functions.
