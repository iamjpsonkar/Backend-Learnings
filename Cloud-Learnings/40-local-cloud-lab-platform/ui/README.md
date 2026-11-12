# Lab Platform UI

React + Vite dashboard for the Local Cloud Lab Platform.

## Development

```bash
cd ui
npm install
npm run dev
# Visit http://localhost:3001
```

The dev server proxies `/api` calls to `http://localhost:4567` (the FastAPI backend).

## Build

```bash
npm run build
# Output: dist/
```

## Production

The Dockerfile builds the app and serves it via Nginx on port 80.

## Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `LabList` | Lab catalog with search and filters |
| `/labs/:id` | `LabDetail` | Full lab details, tasks, hints, run validation |
| `/progress` | `ProgressPage` | Completion history and scores |
| `/services` | `ServicesPage` | Docker service health panel |

## API Client

All backend calls go through `src/api/client.js` which:
- Uses `VITE_API_URL` env var (default: `http://localhost:4567`)
- Handles errors and returns parsed JSON
- Supports: labs, progress, runner, services endpoints

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:4567` | Lab API base URL |
