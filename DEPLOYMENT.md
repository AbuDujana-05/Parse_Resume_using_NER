# Deployment and Local Run

## Local Windows / PowerShell

From the single project root:

```powershell
npm install
npm run dev
```

Or use:

```powershell
.\START_LOCAL.ps1
```

The helper starts FastAPI at `http://localhost:8000` and Vite at `http://localhost:5173` in separate PowerShell windows. Vite proxies `/api` and `/static` to FastAPI during local development.

## Netlify

Netlify builds the React/Vite frontend from this same project root. It does **not** run the local PowerShell launcher or Python training scripts. `netlify.toml` sets:

- build: `npm ci && npm run build`
- publish: `dist`
- Node: `22`
- Functions: `netlify/functions`

The project includes `netlify/functions/api.mjs`, a same-origin proxy for `/api/*`. Set this Netlify environment variable:

`BACKEND_URL=https://YOUR-PUBLIC-FASTAPI-BACKEND`

The Python spaCy/OpenCV/Tesseract stack remains on a real Python host. The proxy returns explicit 503/502 responses when the backend is missing or unreachable.

## Upload limitations

The frontend blocks production uploads above 4 MB so requests stay below the configured Netlify Function safety ceiling.
