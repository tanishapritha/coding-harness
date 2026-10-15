# Vercel + Render deployment

Forge has a Next.js frontend in `frontend/` and a FastAPI backend at `harness.api:app`.

## Vercel (frontend)

1. Import this repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. Select the Next.js framework preset.
4. Set `NEXT_PUBLIC_FORGE_API=https://YOUR-API.onrender.com`.
5. Deploy and copy the exact public frontend URL.

Never put provider keys, GitHub secrets, or database credentials in `NEXT_PUBLIC_*` variables.

## Render (backend)

Create a Web Service from this repository. The included `render.yaml` contains build/start commands and dashboard-managed secret placeholders. Add the values in `.env.example`. Set `FORGE_FRONTEND_URL` and `FORGE_CORS_ORIGINS` to the exact Vercel origin. Use a Neon PostgreSQL URL with SSL for `DATABASE_URL`.

Health check: `https://YOUR-API.onrender.com/health`.

## GitHub OAuth

Create a GitHub OAuth App and set the Authorization callback URL to `https://YOUR-API.onrender.com/auth/github/callback`. Store its client ID and secret on Render.

## GitHub App

Configure the app slug, app ID, and PEM private key on Render. Grant minimum repository metadata/content and pull-request permissions and install it only on repositories you intend to use. Verify the app installation callback flow before allowing other users.

## LLM provider

Choose one provider and set only its key on Render:
- Groq: `FORGE_PROVIDER=groq`, `GROQ_API_KEY=...`
- OpenRouter: `FORGE_PROVIDER=openrouter`, `OPENROUTER_API_KEY=...`
- OpenAI: `FORGE_PROVIDER=openai`, `OPENAI_API_KEY=...`

Keep `FORGE_MODEL` compatible with the selected provider. Leave `FORGE_BASE_URL` empty unless overriding the provider default.

## Runtime limitations and safety

- Standard Render Web Services do not provide a Docker daemon by default. The current `DockerSandbox` calls `docker.from_env()`, so hosted workspace execution will fail unless you connect an isolated runner service or use a host with a Docker daemon.
- SQLite memory and trajectory files live under `~/.forge`. Standard filesystems may be ephemeral; configure durable storage or migrate artifacts to a managed store before relying on history.
- Local-mode endpoints such as `POST /runs` accept filesystem paths, and run/history endpoints are not user-scoped. Do not expose the service to untrusted users before adding authentication and strict workspace isolation.
- The OAuth state is signed but is not compared against a browser-held nonce. This is a deployment baseline, not a security audit. Implement a real per-browser state round trip and fully verify GitHub App installation callbacks before public production use.

## Smoke checks

Backend: `curl https://YOUR-API.onrender.com/health`

Frontend build: `cd frontend && npm ci && npm run build`
