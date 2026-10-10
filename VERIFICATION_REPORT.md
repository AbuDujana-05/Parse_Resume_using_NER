# Final Verification Report — Parse Resume using NER

## Backend / ML
- Python syntax: PASS
- spaCy model load: PASS
- `/api/health`: PASS (`model_loaded: true`)
- JSON `/api/parse`: PASS
- multipart DOCX `/api/parse`: PASS
- multipart image `/api/parse`: PASS
- unsupported extension handling: PASS (415)
- upload-size handling: PASS (413 above 4 MB)
- `/api/metrics`: PASS
- displaCy HTML generation: PASS
- long OCR text protection: spaCy `max_length` raised to 2,000,000 characters

## Verified training artifact
- Engine: spaCy v3 statistical NER
- Labels: 12
- Train examples: 196
- Dev examples: 42
- Epochs: 15
- Dropout: 0.25
- Precision: 0.9410
- Recall: 0.9922
- Entity F1: 0.9659
- Loss chart: present
- Confusion matrix: present
- Serialized model: `backend/models/ner_model/`

## Dataset evidence
- Exact annotated seed data is bundled under `backend/datasets/processed/`.
- Exact processed train/dev JSON and spaCy DocBins are bundled under `backend/data/`.
- `VERIFIED_DATA_AUDIT.json` records SHA-256 hashes of the shipped dataset artifacts.
- Public dataset sources and a reproducible downloader are bundled under `backend/datasets/raw/` and `backend/download_public_datasets.py`.
- The verified bundled model truthfully reports `external_examples: 0`: this execution environment could not retrieve the public binary archives, so no external records are falsely claimed as training data.

## Frontend
- Existing React/Vite 3-tab architecture retained.
- GhostFibers retained; background grain set to `0` in the app as requested for a clean/no-noise visual.
- Project title: `PARSE RESUME USING NER`.
- Credits: Abu Dujana, Nithish & Pravina.
- Production API errors now surface backend details instead of only `HTTP 500`.
- Proof dashboard falls back to bundled metrics/charts, so it does not break when the Python backend is offline.

## Netlify
- Root `netlify.toml`: PASS parse/structure check.
- Base directory: `frontend`.
- Build command: `npm ci && npm run build`.
- Publish: `dist`.
- Node: 22.
- Same-origin `/api/*` proxy function present at `netlify/functions/api.mjs`.
- Function with missing backend returns a controlled 503, not a function crash.
- SPA rewrite present.
- Production uploads capped at 4 MB to stay below Netlify buffered binary request limits.
- `node_modules` excluded from final archive.

## Important deployment architecture
Netlify hosts the React/Vite frontend. The custom spaCy/OpenCV/Tesseract backend remains a Python service. The integrated Netlify function forwards `/api/*` to `BACKEND_URL`. The project also includes `backend/Dockerfile` with Tesseract and Poppler for a Python-capable host.

A live Netlify parse requires `BACKEND_URL` (or `VITE_API_BASE_URL`) to point at a public HTTPS FastAPI backend. This is an architecture requirement, not a frontend build failure.
