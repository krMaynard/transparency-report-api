# Production deployment: Docker + Cloudflare Tunnel

Production runs on this host as a Docker Compose stack and is published through
a named Cloudflare Tunnel. Cloudflare terminates public TLS, so no application
container listens on a public interface and inbound ports 80/443 are not
required.

```text
api.krm.fyi -> Cloudflare -> named tunnel -> 127.0.0.1:18080 -> web:8080
legacy hosts -> Cloudflare -> named tunnel -> 127.0.0.1:18081 -> Caddy redirects
web -> redis:6379 (private Docker network)
```

The image contains the read-only SQLite database built from the vendored data.
Redis holds mutable jobs, sessions, registrations, and issued keys in the
`redis-data` Docker volume.

## Files and host services

| Component | Role |
|---|---|
| `docker-compose.prod.yml` | Runs `web`, persistent Redis, and the legacy redirect origin |
| `Caddyfile` | Internal HTTP reverse proxy and legacy-host redirects; it does not terminate public TLS |
| `.env` | Production configuration and secrets; never commit it |
| `cloudflared-transparency.service` | User-level systemd service running the named tunnel |
| `~/.cloudflared/config.yml` | Tunnel ingress rules and credentials path |

## 1. Prerequisites

- Docker Engine and the Compose plugin.
- A Cloudflare named tunnel with a DNS route for `api.krm.fyi`.
- A tunnel ingress rule forwarding the canonical hostname to
  `http://127.0.0.1:18080` and any legacy hostnames to
  `http://127.0.0.1:18081`.
- The tunnel credential file referenced by `~/.cloudflared/config.yml`.

Keep both published Compose ports bound to `127.0.0.1`. They are origins for
`cloudflared`, not public listeners.

## 2. Configure `.env`

```bash
cp .env.example .env
```

Set these production values:

| Variable | Production value |
|---|---|
| `SITE_ADDRESS` | `api.krm.fyi` |
| `DOWNLOAD_URL_SECRET` | Stable random secret, for example from `openssl rand -hex 32` |
| `ALLOW_DEMO_KEYS` | `0` |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Web client ID with `https://api.krm.fyi` as an authorized JavaScript origin |
| `ADMIN_EMAILS` | Comma-separated administrator addresses |
| `PUBLIC_BASE_URL` | `https://api.krm.fyi` |
| `APP_VERSION` | Commit SHA being deployed |
| `ANTHROPIC_API_KEY` | Optional; enables `/api/ask` |
| `ALLOWED_ORIGINS` | Empty for the same-origin bundled UI |

Leave `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` empty. Do not set
`REDIS_URL` in `.env`; Compose supplies `redis://redis:6379/0` to the web
container.

## 3. Deploy

Start the full stack the first time:

```bash
docker compose -f docker-compose.prod.yml up -d --build
systemctl --user enable --now cloudflared-transparency.service
```

For a routine application rollout, first make sure the working tree contains
only the reviewed release. Build the image, set `APP_VERSION` in `.env` to the
commit SHA, and recreate only the web container:

```bash
docker compose -f docker-compose.prod.yml build web
docker compose -f docker-compose.prod.yml up -d --no-deps --no-build --force-recreate web
```

When unrelated work is present in the checkout, build the exact committed tree
instead of the working directory:

```bash
git archive --format=tar HEAD | docker build --tag transparency-report-api-web:latest -
docker compose -f docker-compose.prod.yml up -d --no-deps --no-build --force-recreate web
```

This keeps Redis and Caddy running while the application container is replaced.

## 4. Verify

Check the containers and tunnel first:

```bash
docker compose -f docker-compose.prod.yml ps
systemctl --user status cloudflared-transparency.service
```

Then verify both the loopback origin and public route:

```bash
curl -fsS http://127.0.0.1:18080/readyz
curl -fsS http://127.0.0.1:18080/version
curl -fsS https://api.krm.fyi/readyz
curl -fsS https://api.krm.fyi/version
```

The public `/version` response and `X-Version` header should match the release
SHA, and the reported state backend should be `redis`.

## 5. Operations and rollback

```bash
# Application logs
docker compose -f docker-compose.prod.yml logs -f web

# Tunnel logs
journalctl --user -u cloudflared-transparency.service -f

# Back up Redis state
docker run --rm -v transparency-report-api_redis-data:/data -v "$PWD":/backup \
  alpine tar czf /backup/redis-backup.tar.gz -C /data .
```

To roll back, rebuild the last known-good commit, restore its SHA in
`APP_VERSION`, recreate only `web`, and repeat the verification checks. The
Redis volume is not replaced during an application rollback.

Refresh the vendored dataset before building when upstream data changes. Use
`scripts/refresh-dataset.sh` for the VLOP snapshot and
`scripts/revendor_data.py` for the other snapshots.
