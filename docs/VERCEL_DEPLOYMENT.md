# Fix for Vercel `[PYTHON_ENTRYPOINT_NOT_FOUND]`

## Root cause

The repository's `app.py` starts `ThreadingHTTPServer` on the developer machine, rather than exposing an ASGI/WSGI app object. The old version is Streamlit, which also is not a standard Python serverless app. Vercel auto-detects `app.py` and expects `app`, `application`, or `handler`.

**Do not** add a dummy `app` variable just to silence the error; the HTTP server, statefulness, Ollama, and LocalStack architecture still do not meet the requirements of a public serverless function.

## Safe public deployment using the static portfolio

1. Push the project **including `portfolio/`** to the intended GitHub repository and default branch.
2. Go to Vercel > Project > **Settings > Git** and confirm the Connected Git Repository and Production Branch match the repository you updated.
3. Go to Vercel > Project > **Settings > Build and Deployment** and set **Root Directory** = `portfolio`. If you cannot change the existing Vercel project, import the intended GitHub repository as a new Vercel project and choose the `portfolio` root during setup.
4. **Framework Preset** = `Other`; **Build Command** = blank/no override; **Output Directory** = `public` (specified by `portfolio/vercel.json`; you may leave an overridden UI setting blank).
5. Save and redeploy the latest GitHub commit. A successful deployment should serve the static HTML app at `/`. The deployment should not inspect or build root `app.py`.

## What works in the public version

- Incident overview, search, severity filtering, details, runbooks
- Scoped plan generation, one-use confirmation, simulated execution, audit events, CSV export, themes, responsive navigation

## What is intentionally disabled

- All network API calls; no Python runtime or AWS credentials
- Cloud and LocalStack modification; Ollama inference; persistent audit database

Sample content and demo state are stored only in the visitor's current browser tab. Refresh resets everything. Public browser data is not an authorization mechanism. Run the real Python/LocalStack lab locally with `python3 api_server.py` (not on Vercel).

## Validate before deployment

```bash
python3 -m unittest discover -s tests -v
node portfolio/test-demo.cjs
node --check portfolio/public/app.js
node --check portfolio/public/demo-api.js

# Optional static preview
cd portfolio/public
python3 -m http.server 8000 --bind 127.0.0.1
```
