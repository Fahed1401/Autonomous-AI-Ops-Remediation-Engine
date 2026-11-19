# SentinelOps · Vercel public portfolio preview

This directory is a **static-only public portfolio demo**, intentionally separate from the unauthenticated Python / LocalStack lab.
All data, mock approvals, and mock remediation events are in-browser. There are **no remote API calls** and **no AWS/LocalStack/LLM integration** in this version.
Use the project root to run the real local lab via `python3 api_server.py`.

## Vercel deployment

1. Upload the project to GitHub, including this `portfolio/` directory.
2. In Vercel → Project → Settings → Build and Deployment, set **Root Directory** to `portfolio`.
3. Set **Framework Preset** to `Other`. Leave Build Command empty (no build required).
4. `portfolio/vercel.json` sets **Output Directory** to `public` and secures browser-only delivery with CSP.
5. Confirm Vercel has connected to the **correct GitHub repository and branch**.
6. Redeploy the latest commit. The root `/` serves `public/index.html`.

## Local static preview

```bash
cd portfolio/public
python3 -m http.server 8000 --bind 127.0.0.1
# open http://127.0.0.1:8000
```

The demo resets on refresh. It does not retain audit data across tabs or sessions.
No API secrets, privileged actions, or Python runtime are bundled into the Vercel site.
