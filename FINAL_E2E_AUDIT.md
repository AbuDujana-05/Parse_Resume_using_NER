# Final End-to-End Audit — Parse Resume using NER

## Local runtime wiring
- Root `npm run dev` invokes `START_LOCAL.ps1`.
- The launcher stops stale listeners on ports 8000 and 5173.
- It checks/imports backend dependencies and installs `backend/requirements.txt` only when needed.
- It starts FastAPI first and waits for `GET /api/health` with `model_loaded=true`.
- Only after the backend is healthy does it start Vite through `npm run dev:frontend`.
- The browser API client detects localhost/port 5173 and routes directly to `http(s)://<browser-host>:8000`; it does not use the Netlify proxy for local runs.

## API tests performed against a fresh backend process
- `GET /api/health` -> 200, model loaded.
- `GET /api/metrics` -> 200.
- `GET /api/samples/{domain}` -> 200 for all 10 domains.
- `POST /api/parse` JSON text -> 200.
- Multipart PDF -> 200.
- Multipart DOCX -> 200.
- Multipart PPTX -> 200.
- Multipart PNG -> 200.
- All 10 domain samples were fetched and parsed successfully (no HTTP 500).

## Model wiring
`backend/models/ner_model` loads as a spaCy pipeline with the custom NER component. The service returns entity groups plus spaCy displaCy HTML.

## Packaging
- Single project root in archive.
- No nested `frontend/` npm project.
- No `node_modules` shipped.
- `package.json` and `package-lock.json` are at archive root.

## Netlify
Netlify configuration remains in `netlify.toml` and `netlify/functions/api.mjs`, but the local terminal path does not depend on those files.

## Remaining environment dependency
Image OCR requires the Tesseract executable on a normal Windows installation. The Python package is included in requirements; Docker support includes the OS-level OCR dependencies. PDF, DOCX and PPTX extraction do not require an external cloud service.
