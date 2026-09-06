# Production checklist

The supported production target is the Docker Compose stack on this host,
published through Cloudflare Tunnel at `https://api.krm.fyi`. The operational
commands and rollback procedure are in
[`DEPLOY-SELFHOST.md`](DEPLOY-SELFHOST.md).

## Current architecture

| Layer | Production setup |
|---|---|
| Public edge | Cloudflare DNS, TLS, and named tunnel |
| Application origin | `web:8080`, published only as `127.0.0.1:18080` |
| Legacy redirects | Caddy on `127.0.0.1:18081` |
| Mutable state | Persistent local Redis on the private Docker network |
| Query data | Read-only SQLite database seeded into the image at build time |
| Process supervision | Docker restart policies plus `cloudflared-transparency.service` |
| Delivery | Explicit build and rollout on the host; pushes do not deploy production |

## Release checklist

- [ ] The release commit is reviewed and tests pass.
- [ ] Vendored datasets are current and the image has been rebuilt when they changed.
- [ ] `.env` has production auth, secrets, and `APP_VERSION=<release SHA>`.
- [ ] `ALLOW_DEMO_KEYS=0` and `PUBLIC_BASE_URL=https://api.krm.fyi`.
- [ ] The web container is healthy after recreation; Redis and Caddy remained up.
- [ ] `cloudflared-transparency.service` is active.
- [ ] Loopback `/readyz` and `/version` checks pass.
- [ ] Public `/readyz` and `/version` checks pass and expose the expected SHA.
- [ ] The dashboard, sign-in, query, result, and signed-download flows work.

## Security and reliability notes

- Keep ports `18080` and `18081` bound to loopback. Cloudflare Tunnel is the
  only public ingress.
- Keep `.env` and tunnel credentials out of version control.
- Keep `DOWNLOAD_URL_SECRET` stable across releases so existing signed links
  remain valid.
- Back up the `redis-data` volume if issued keys and sessions must survive host
  loss.
- The image is immutable and self-contained; use a prior commit to roll back the
  application without replacing Redis.
- Add horizontal workers or managed state only when traffic or availability
  requirements justify moving beyond the current single-host design.

## Optional hardening

| When | Consider |
|---|---|
| The host becomes a single point of failure you cannot accept | A second origin and replicated state |
| Webhooks must survive host restarts | A durable callback queue |
| Results routinely exceed about 1 MB | Object storage with short-lived signed URLs |
| Query volume outgrows one process | Separate durable job workers |
| Clients need large result pagination | Cursor pagination for result endpoints |
| API contracts begin changing incompatibly | Versioned `/api/v1` routes and deprecation headers |
