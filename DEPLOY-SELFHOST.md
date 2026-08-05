# Self-hosting on a single VPS

This is the lowest-cost way to run the API: one small VPS running the app,
a local Redis, and Caddy for automatic HTTPS — replacing managed **Cloud Run +
Upstash**. A ~$5/mo box (e.g. Hetzner CX22, 2 vCPU / 4 GB) comfortably runs the
whole stack with no cold starts and no per-request billing.

The image is self-contained (the read-only SQLite DB is seeded at build time),
so there is no external data dependency at runtime. The only mutable state is
Redis (jobs / issued keys / Google sessions), persisted to a Docker volume.

> The Cloud Run path (`service.yaml` + `.github/workflows/deploy.yml`) still
> works and is untouched — this is a parallel, cheaper option. See
> `PRODUCTIONIZE.md` for the hosting comparison.

## Files

| File | Role |
|------|------|
| `docker-compose.prod.yml` | web (this image) + redis (persistent) + caddy (TLS) |
| `Caddyfile` | reverse proxy + automatic Let's Encrypt certificate |
| `.env` | your production config (copy from `.env.example`) |

## 1. Prerequisites

- A VPS with a public IPv4 (and ideally IPv6), Docker Engine + the Compose plugin
  installed, and ports **80** and **443** open.
- A domain whose **A** (and **AAAA**) records point at the VPS. Set
  `SITE_ADDRESS` in `.env`; it defaults to `transparency.krm.fyi`.
- Clone this repo onto the box (the build context is the repo root).

## 2. Configure `.env`

```bash
cp .env.example .env
```

Then edit `.env`. The settings that matter for a real deployment:

| Variable | Set to | Why |
|---|---|---|
| `SITE_ADDRESS` | your public hostname | Hostname Caddy serves and provisions TLS for. |
| `UPSTASH_REDIS_REST_URL` / `_TOKEN` | **empty** (delete the placeholder lines) | The app prefers Upstash when these are set — leave them blank so it uses the local `REDIS_URL` that `docker-compose.prod.yml` injects. **Easy to miss:** the sample values in `.env.example` are non-empty. |
| `DOWNLOAD_URL_SECRET` | `openssl rand -hex 32` | Stable HMAC secret so signed download links survive restarts. |
| `ALLOW_DEMO_KEYS` | `0` | Disable the hard-coded demo keys + open registration in production. |
| `GOOGLE_CLIENT_ID` | your OAuth 2.0 **Web** client ID | Enables Google sign-in. Add the site origin to the client's Authorized JavaScript origins. |
| `ADMIN_EMAILS` | your email(s), comma-separated | Admin kill-switch over registrations. |
| `PUBLIC_BASE_URL` | `https://transparency.krm.fyi` | Absolute links in webhook callbacks / signed downloads. |
| `ANTHROPIC_API_KEY` | your key (optional) | Enables the NL "Ask" box. Leave empty to keep `/api/ask` off (503). |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` (default) | Model that translates questions → structured queries. Sonnet is the cost/quality middle tier; set `claude-haiku-4-5` to go cheaper or `claude-opus-4-8` for max quality. |
| `ALLOWED_ORIGINS` | empty (same-origin) | The bundled dashboard is same-origin; only set this if a separate frontend calls the API cross-origin. |

Do **not** set `REDIS_URL` in `.env` — the compose file provides it.

## 3. Launch

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Caddy will obtain a certificate on first start (needs DNS pointing at the box and
80/443 reachable). Watch it:

```bash
docker compose -f docker-compose.prod.yml logs -f caddy
```

## 4. Verify

```bash
# Liveness/readiness (through Caddy, over HTTPS):
curl -fsS https://transparency.krm.fyi/healthz
curl -fsS https://transparency.krm.fyi/readyz
# Build id + which Redis backend is active ("redis" expected, not "upstash"/"memory"):
curl -fsS https://transparency.krm.fyi/version
```

Open the dashboard at the domain root and confirm the "Ask" box works (if
`ANTHROPIC_API_KEY` is set).

## 5. Operations

```bash
# Logs
docker compose -f docker-compose.prod.yml logs -f web

# Update after pulling new code (rebuilds the image + re-seeds the DB)
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Back up the mutable state (issued keys / sessions / jobs)
docker run --rm -v transparency-report-api_redis-data:/data -v "$PWD":/backup \
  alpine tar czf /backup/redis-backup.tar.gz -C /data .
```

Notes:
- **Keep the `caddy-data` volume** — it holds the ACME account and issued
  certificates. Losing it forces re-issuance (subject to Let's Encrypt rate limits).
- The dataset is baked into the image; refresh it with
  `scripts/refresh-dataset.sh` (then rebuild) when the upstream data changes.
- To scale beyond one app replica later, the local Redis already makes the job /
  session / key stores shared — add replicas of `web` and let Caddy load-balance.
