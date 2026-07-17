# transparency-report-api — Claude context

## What this is

A FastAPI service that accepts **structured query parameters** (not SQL) via
HTTP, runs the resulting query asynchronously on background worker threads, and
returns results as JSON or CSV. Backed by a read-only SQLite database seeded from
transparency-reporting datasets: the aggregated **EU Digital Services Act (DSA)
VLOP transparency reports** (content-moderation statistics for 25 designated Very
Large Online Platforms / Search Engines, H2 2025, tables 3–11 of the DSA
Implementing Regulation template), **Google Government content-removal
requests**, the **Apple Transparency Report** (government/private-party data
requests + App Store takedowns, biannual since 2013 H1), the **GitHub
Transparency Report** (government takedowns, user-information requests, DMCA,
automated detection, appeals, EU-DSA MAU), the **Snap Transparency Report**
(T&S enforcements, government content/account-removal & information requests,
DMCA takedowns, by country × violation category), **India's IT Rules 2021
monthly compliance reports** (proactive content actioned, user grievances,
accounts actioned, GAC orders — Facebook/Instagram/Twitter/Moj/ShareChat/Roblox/Google/Pinterest), **South Korea's Naver + Kakao transparency reports** (government data requests
under the Telecommunications Business Act / Protection of Communications
Secrets Act, half-yearly since 2012), **Taiwan's Anti-Fraud Act data**
(NPA Art. 42 DNS-blocked fraud sites by month × category, plus the designated
platforms' statutory fraud-prevention reports — Google/LINE/TikTok 2025;
Meta's not yet retrievable), **Google government requests for user
information** (the biannual bulk export: global/diplomatic/enterprise requests
+ banded US national-security ranges, 2009 H2 onward), the **Microsoft Law
Enforcement Requests Report** (per-country demands + disclosure outcomes,
half-yearly since 2013), the **LinkedIn Government Requests Report**
(member-data requests, the US legal-process breakdown, and content-removal
requests), the **TikTok Government & Legal Requests reports**
(government content-removal requests + user-information requests per country +
IP/copyright removal requests, half-yearly since 2019), the **Discord
Transparency Reports** (Trust & Safety enforcement by policy category +
government/legal requests by country, quarterly since 2022), Google's
**Traffic & Disruptions catalogue** (government-ordered internet shutdowns,
blocks and outages affecting Google products, with news-source citations —
a historical dataset Google froze at 2009–2021), Google's **Android
ecosystem security** report (Potentially Harmful Application / malware rates on
devices and in Google Play, by version × country × category, 2017–2024), and
**Türkiye's Law No. 5651 platform transparency reports** (the six-monthly
content-removal / access-blocking figures platforms publish for Türkiye —
individual Art. 9/9-A applications and Art. 8/8-A authority requests by
requesting body; Meta's Facebook & Instagram 2023–2025 as report-level totals,
plus X/Twitter 2021–2025 broken down by issue category with request volumes and
action rates), Meta's **Community Standards Enforcement Report** (Meta's
flagship *voluntary* content-moderation report — prevalence, content actioned,
proactive rate and appeals for Facebook & Instagram across ~16 policy areas,
quarterly 2017 Q4 onward), and TikTok's **Community Guidelines Enforcement
Report** (TikTok's *voluntary* content-moderation report — videos/accounts/
comments removed, proactive & removal-speed rates, by policy × moderation task,
quarterly 2020 Q3 onward).

Built to demonstrate two things:

1. The **async-job / poll pattern**: `POST /query` returns `202 + job_id`
   immediately; the client polls `/jobs/{id}` until `status=done`, then
   fetches `/jobs/{id}/result`.
2. A **safe, no-SQL query interface** modelled on the TikTok Research API: a
   query names a `table` (one of the 9 DSA report tables), then a boolean
   `and`/`or`/`not` clause of `{operation, field_name, field_values}`, plus
   `group_by`, `aggregates`, `sort`, and `max_count`. The server validates
   everything against that table's fixed field registry (`TABLES`/`TableSpec`)
   and compiles it into a single parameterised SELECT (`compile_query` in
   `main.py`). Arbitrary SQL is never accepted or executed.

## Repo layout

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app — all endpoints, job runner, in-memory job registry |
| `seed.py` | Build `demo.db` from a `vlop-dsa.json` (`--source`/`SEED_SOURCE_JSON`; default = sibling repo) — `build_db()` is reused by `conftest.py`. Also loads gr removals, `report_locations`, the Apple transparency dataset (`build_apple_db`, `--apple-source`), the GitHub transparency dataset (`build_github_db`, `--github-source`), the Snap transparency dataset (`build_snap_db`, `--snap-source`), India's IT Rules monthly compliance reports (`build_india_db`, `--india-source`), the Korea transparency dataset (`build_korea_db`, `--korea-source`), the Taiwan anti-fraud dataset (`build_taiwan_db`, `--taiwan-source`), the Türkiye Law 5651 platform reports (`build_turkey_db`, `--turkey-source`), the EU Terrorist Content Online Regulation transparency reports (`build_tco_db`, `--tco-source`), the EU AI Act training-data transparency summaries (`build_ai_training_db`, `--ai-training-source`), the regional content-moderation transparency-law reports (`build_regional_db`, `--regional-source`), the China CIIRC (12377) online-report handling statistics (`build_ciirc_db`, `--ciirc-source`), the China 12321 telecom-spam report-handling statistics (`build_china12321_db`, `--china12321-source`), the Meta Community Standards Enforcement Report (`build_cser_db`, `--cser-source`), the TikTok Community Guidelines Enforcement Report (`build_tiktok_cger_db`, `--tiktok-cger-source`), Google user-data requests (`build_google_userdata_db`, `--google-ud-source`), the Microsoft LERR (`build_microsoft_db`, `--microsoft-source`), the LinkedIn report (`build_linkedin_db`, `--linkedin-source`), TikTok's government & legal requests (`build_tiktok_db`, `--tiktok-source`), the Discord transparency reports (`build_discord_db`, `--discord-source`), the Google Traffic & Disruptions catalogue (`build_google_traffic_db`, `--traffic-source`), the Google Android ecosystem security dataset (`build_android_db`, `--android-source`), the EU DSA Transparency Database Statements of Reasons (`build_dsa_tdb_db`, `--dsa-tdb-source`), the NY ToS report narratives full text (`build_ny_tos_narratives`, `--narratives-source`), the California AB 587 ToS reports catalogue (`build_ca_ab587_reports`, `--ca-ab587`) + its narratives full text (`build_ca_ab587_narratives`, `--ca-ab587-narratives`), the Japan LY Corp report narratives (`build_japan_narratives`, `--japan-narratives`), the California AB 2013 AI-training summary narratives (`build_ca_ab2013_narratives`, `--ca-ab2013-narratives`), and the non-VLOP harmonised reports; after loading, `build_dsa_narratives` indexes the DSA Table-11 prose for search |
| `seed_harmonised.py` | Append the **non-VLOP harmonised-template reports** into the same `t3`–`t11` star schema (`build_harmonised_facts()`): one new `reports` row (tier ≠ `vlop`) + `services` row per platform, dimensions interned/extended. Reads the vendored `data/harmonised-reports.json` snapshot (or the sibling repo's extracted CSVs in dev); `write_snapshot()` rebuilds the snapshot. For t6/t7/t8 the per-row surface comes from a trailing `Surface` cell (`Core`/`Ads`) when present — the sibling extractor folds Google's ads-surface split (Hotels/Workspace) into the base section — else defaults to `All` |
| `data/vlop-dsa.json` | Vendored dataset snapshot — what the Docker image is seeded from (refresh via `scripts/refresh-dataset.sh`) |
| `data/harmonised-reports.json` | Vendored snapshot of the 49 extracted non-VLOP harmonised-template reports (sibling `dsa-transparency-data/harmonised-reports/extracted/`) — seeded into `t3`–`t11` by `seed_harmonised.py` |
| `data/report-locations.csv` | Vendored snapshot of the non-VLOP DSA report-locations catalogue (sibling `dsa-transparency-data/dsa_reports.csv`) — seeded into the read-only `report_locations` table by `seed.py` |
| `data/apple-transparency.json` | Vendored snapshot of the Apple Transparency Report (sibling `dsa-transparency-data/apple-transparency/build_apple.py`) — interned `periods`/`countries`/`request_types` + fact rows; seeded into `ap_*`/`apple_*` tables by `seed.build_apple_db` |
| `data/github-transparency.json` | Vendored snapshot of the GitHub Transparency Report (sibling `dsa-transparency-data/github-transparency/build_github.py`) — a tidy-long `columns`+`rows` list; seeded into the `github_metrics` table by `seed.build_github_db` |
| `data/snap-transparency.json` | Vendored snapshot of the Snap Transparency Report (sibling `dsa-transparency-data/snap-transparency/build_snap.py`) — a tidy-long `columns`+`rows` list; seeded into the `snap_metrics` table by `seed.build_snap_db` |
| `data/india-it-rules.json` | Vendored snapshot of India's IT Rules 2021 monthly compliance reports (sibling `dsa-transparency-data/india-it-rules/build_india.py`) — a tidy-long `columns`+`rows` list across publishers; seeded into the `india_metrics` table by `seed.build_india_db` |
| `data/korea-transparency.json` | Vendored snapshot of the Korea (Naver + Kakao) transparency reports (sibling `dsa-transparency-data/korea-transparency/build_korea.py`) — a tidy-long `columns`+`rows` list; seeded into the `korea_metrics` table by `seed.build_korea_db` |
| `data/taiwan-anti-fraud.json` | Vendored snapshot of Taiwan's Anti-Fraud Act data (sibling `dsa-transparency-data/taiwan-anti-fraud/build_taiwan.py`) — a tidy-long `columns`+`rows` list; seeded into the `taiwan_metrics` table by `seed.build_taiwan_db` |
| `data/turkey-law5651.json` | Vendored snapshot of Türkiye's Law No. 5651 platform transparency reports (sibling `dsa-transparency-data/turkey-law5651/build_turkey.py`) — a tidy-long `columns`+`rows` list; seeded into the `turkey_metrics` table by `seed.build_turkey_db` |
| `data/meta-cser.json` | Vendored snapshot of Meta's Community Standards Enforcement Report (sibling `dsa-transparency-data/meta-cser/build_cser.py`) — a tidy-long `columns`+`rows` list; seeded into the `cser_metrics` table by `seed.build_cser_db` |
| `data/esafety-bose.json` | Australia eSafety BOSE (Basic Online Safety Expectations) transparency findings — a tidy-long `columns`+`rows` list; **built in-repo by `scripts/build_esafety_bose.py`** (no sibling extractor; figures transcribed from the archived eSafety reports); seeded into the `esafety_bose_metrics` table by `seed.build_esafety_bose_db` |
| `scripts/build_esafety_bose.py` | Builds `data/esafety-bose.json` from the transcribed eSafety report figures (CSEA periodic Figure 4 + AI-companion findings), with page citations inline and a fail-loud cross-check that the four Meta services sum to the report's stated Meta aggregate |
| `data/tiktok-cger.json` | Vendored snapshot of TikTok's Community Guidelines Enforcement Report (sibling `dsa-transparency-data/tiktok-cger/build_cger.py`) — a tidy-long `columns`+`rows` list (global `All`-location cut); seeded into the `tiktok_cger_metrics` table by `seed.build_tiktok_cger_db` |
| `data/tco-regulation.json` | Vendored snapshot of the EU Terrorist Content Online Regulation transparency reports (sibling `dsa-transparency-data/tco-regulation/build_tco.py`) — a tidy-long `columns`+`rows` list across the authority (Art. 8 / Commission) and platform (Art. 7) streams; seeded into the `tco_metrics` table by `seed.build_tco_db` |
| `data/ai-training-transparency.json` | Vendored snapshot of the EU AI Act Art. 53(1)(d) training-data transparency summaries (sibling `dsa-transparency-data/ai-training-transparency/build_ai_training.py`) — a tidy-long `columns`+`rows` list across providers' public summaries of training content (Google + Meta + OpenAI PDFs + Microsoft Hugging Face cards); seeded into the `ai_training_metrics` table by `seed.build_ai_training_db` |
| `data/regional-transparency.json` | Vendored snapshot of the regional content-moderation transparency-law reports (sibling `dsa-transparency-data/regional-transparency/build_regional.py`) — a tidy-long `columns`+`rows` list of YouTube's Texas HB 20 (§120.053) + Austria KoPl-G (§4) reports; seeded into the `regional_metrics` table by `seed.build_regional_db` |
| `data/china-ciirc.json` | Vendored snapshot of the China CIIRC (12377) online-report handling statistics (sibling `dsa-transparency-data/china-ciirc/build_ciirc.py`) — a tidy-long `columns`+`rows` list of the CAC reporting center's monthly 全国网络举报受理情况 figures by receiving body (2019→); seeded into the `ciirc_metrics` table by `seed.build_ciirc_db` |
| `data/china-12321.json` | Vendored snapshot of the China 12321 telecom-spam report-handling statistics (sibling `dsa-transparency-data/china-12321/build_12321.py`) — a tidy-long `columns`+`rows` list of the 12321 center's (Internet Society of China / MIIT) monthly reports received by category (apps, spam/illegal SMS, harassment calls, bad websites, …), 2016-09 → 2019-02 (discontinued); seeded into the `china12321_metrics` table by `seed.build_china12321_db` |
| `data/google-user-data.json` | Vendored snapshot of Google's government requests for user information (sibling `dsa-transparency-data/google-user-data/build_userdata.py`) — a tidy-long `columns`+`rows` list; seeded into the `google_userdata_metrics` table by `seed.build_google_userdata_db` |
| `data/microsoft-lerr.json` | Vendored snapshot of the Microsoft Law Enforcement Requests Report (sibling `dsa-transparency-data/microsoft-lerr/build_microsoft.py`) — a tidy-long `columns`+`rows` list; seeded into the `microsoft_metrics` table by `seed.build_microsoft_db` |
| `data/linkedin-transparency.json` | Vendored snapshot of the LinkedIn Government Requests Report (sibling `dsa-transparency-data/linkedin-transparency/build_linkedin.py`) — a tidy-long `columns`+`rows` list; seeded into the `linkedin_metrics` table by `seed.build_linkedin_db` |
| `data/tiktok-transparency.json` | Vendored snapshot of the TikTok Government & Legal Requests reports (sibling `dsa-transparency-data/tiktok-transparency/build_tiktok.py`) — a tidy-long `columns`+`rows` list; seeded into the `tiktok_metrics` table by `seed.build_tiktok_db` |
| `data/discord-transparency.json` | Vendored snapshot of the Discord Transparency Reports (sibling `dsa-transparency-data/discord-transparency/build_discord.py`) — a tidy-long `columns`+`rows` list; seeded into the `discord_metrics` table by `seed.build_discord_db` |
| `data/google-traffic.json` | Vendored snapshot of Google's Traffic & Disruptions catalogue (sibling `dsa-transparency-data/google-traffic/build_traffic.py`) — a flat-catalogue `columns`+`rows` list (one row per disruption event); seeded into the read-only `google_traffic` table by `seed.build_google_traffic_db` |
| `data/android-security.json` | Vendored snapshot of Google's Android ecosystem security report (sibling `dsa-transparency-data/android-security/build_android.py`) — a tidy-long `columns`+`rows` list of PHA (malware) rates; seeded into the `android_metrics` table by `seed.build_android_db` |
| `data/dsa-tdb.json` | Vendored snapshot of the EU DSA Transparency Database — Statements of Reasons, **re-aggregated** from the Commission's pre-made monthly aggregates (sibling `dsa-transparency-data/dsa-tdb/build_dsa_tdb.py`, via the `dsa-tdb` toolbox) — a tidy-long `columns`+`rows` list (SoR counts by platform × month × dimension, top 60 platforms, 2023-09→); seeded into the `dsa_tdb_metrics` table by `seed.build_dsa_tdb_db` |
| `data/ny-tos-narratives.json` | Vendored snapshot of the **narrative text** of the NY ToS filings (sibling `dsa-transparency-data/ny-tos-reports/extract_narrative.py`) — one `columns`+`rows` entry per page of prose; seeded into the FTS5 `ny_tos_narratives` table by `seed.build_ny_tos_narratives` |
| `data/template-crosswalk.json` | Vendored `{original-language label → canonical English}` map for the template's `sections`/`indicators`/`scopes`, applied by `seed.normalize_dimensions` to stamp each dim row's language-neutral `key`. Regenerate with `scripts/build_template_crosswalk.py` |
| `scripts/build_template_crosswalk.py` | Learns `data/template-crosswalk.json` by aligning same-structure non-VLOP report sheets to an English reference (drops ambiguous labels) — reads the sibling repo's extracted CSVs |
| `demo.py` | Narrated walkthrough script (run after starting the server) |
| `static/index.html` | Public VLOP dashboard (served at `/reports`) — Chart.js overview + interactive query builder + "Compare tables" composite panel + NL "Ask" box (`GET /api/overview`, `POST /api/explore`, `POST /api/ask`) |
| `static/catalog.html` | Public report-locations catalogue page (served at `/catalog`) — the "Where platforms publish their reports" filterable table over `GET /api/report-locations` |
| `static/ny-tos.html` | Public NY Terms-of-Service reports page (served at `/ny-tos`) — filterable filings catalogue over `GET /api/ny-tos-reports` + an "Enforcement statistics" panel over `POST /api/explore` (`ny_tos_stats`) |
| `static/ca-ab587.html` | Public California AB 587 Terms-of-Service reports page (served at `/ca-ab587`) — the "California AB 587 Terms-of-Service reports" filterable filings catalogue over `GET /api/ca-ab587-reports` (a flat catalogue like `/ny-tos`, no stats panel) |
| `static/apple.html` | Public Apple Transparency Report dataset page (served at `/apple`) — overview tables over `POST /api/explore` (`apple_requests`) |
| `static/github.html` | Public GitHub Transparency Report dataset page (served at `/github`) — overview tables over `POST /api/explore` (`github_metrics`) |
| `static/snap.html` | Public Snap Transparency Report dataset page (served at `/snap`) — overview tables over `POST /api/explore` (`snap_metrics`) |
| `static/india.html` | Public India IT Rules compliance-reports dataset page (served at `/india`) — Trends charts + overview tables over `POST /api/explore` (`india_metrics`) |
| `static/korea.html` | Public Korea (Naver + Kakao) transparency dataset page (served at `/korea`) — Trends charts + overview tables over `POST /api/explore` (`korea_metrics`) |
| `static/taiwan.html` | Public Taiwan Anti-Fraud Act dataset page (served at `/taiwan`) — Trends charts + overview tables + the "Platform statutory reports" panel over `POST /api/explore` (`taiwan_metrics`) |
| `static/turkey.html` | Public Türkiye Law No. 5651 transparency-reports dataset page (served at `/turkey`) — Trends charts + overview tables over `POST /api/explore` (`turkey_metrics`) |
| `static/cser.html` | Public Meta Community Standards Enforcement Report dataset page (served at `/cser`) — Trends charts (prevalence trend, content actioned + proactive rate by policy area) + tables over `POST /api/explore` (`cser_metrics`) |
| `static/tiktok-cger.html` | Public TikTok Community Guidelines Enforcement Report dataset page (served at `/tiktok-cger`) — Trends charts (videos removed, proactive rate, videos by policy) + removal-quality-rates table over `POST /api/explore` (`tiktok_cger_metrics`) |
| `static/tco.html` | Public EU Terrorist Content Online Regulation dataset page (served at `/tco`) — charts (removal orders issued by Member State, content removed via orders by platform) + tables over `POST /api/explore` (`tco_metrics`); English-only, like `/mandates` |
| `static/ai-training.html` | Public EU AI Act training-data transparency dataset page (served at `/ai-training`) — charts (text training-data size by model, size rank by modality) + size-band + data-source matrix tables over `POST /api/explore` (`ai_training_metrics`); English-only, like `/mandates` |
| `static/regional.html` | Public regional content-moderation transparency-law dataset page (served at `/regional`) — charts (YouTube videos removed by reason + by country, Texas HB 20) + Texas enforcement-by-period + Austria KoPl-G complaints tables over `POST /api/explore` (`regional_metrics`); English-only, like `/mandates` |
| `static/china.html` | Public China CIIRC (12377) dataset page (served at `/china`) — charts (reports handled nationally by month, by receiving body) + a by-body-and-month table over `POST /api/explore` (`ciirc_metrics`); English-only, like `/mandates` |
| `static/china-12321.html` | Public China 12321 telecom-spam dataset page (served at `/china-12321`) — charts (reports received by category by month, SMS spam vs. illegal) + a by-category-and-month table over `POST /api/explore` (`china12321_metrics`); English-only, like `/mandates` |
| `static/user-data.html` | Public Google user-data requests dataset page (served at `/user-data`) — Trends charts + overview tables over `POST /api/explore` (`google_userdata_metrics`) |
| `static/microsoft.html` | Public Microsoft LERR dataset page (served at `/microsoft`) — Trends charts + overview tables over `POST /api/explore` (`microsoft_metrics`) |
| `static/linkedin.html` | Public LinkedIn Government Requests dataset page (served at `/linkedin`) — Trends charts + overview tables over `POST /api/explore` (`linkedin_metrics`) |
| `static/tiktok.html` | Public TikTok Government & Legal Requests dataset page (served at `/tiktok`) — Trends charts + overview tables over `POST /api/explore` (`tiktok_metrics`) |
| `static/discord.html` | Public Discord Transparency Reports dataset page (served at `/discord`) — Trends charts + overview tables over `POST /api/explore` (`discord_metrics`) |
| `static/disruptions.html` | Public Google Traffic & Disruptions catalogue page (served at `/disruptions`) — the "Government internet shutdowns" filterable table over `GET /api/traffic-disruptions` (a flat catalogue like `/catalog`, not `/api/explore`) |
| `static/android.html` | Public Android ecosystem security dataset page (served at `/android`) — Trends charts + overview tables over `POST /api/explore` (`android_metrics`); PHA rates shown as percentages |
| `static/dsa-db.html` | Public EU DSA Transparency Database (Statements of Reasons) dataset page (served at `/dsa-db`) — Trends charts (SoRs/month, top platforms, by category, decision ground) + a by-platform table over `POST /api/explore` (`dsa_tdb_metrics`); English-only, like `/china-12321` |
| `static/narratives.html` | Public narrative full-text search page (served at `/narratives`) — a search box + highlighted result snippets over `GET /api/narratives` (SQLite FTS5) spanning the NY ToS filings (deep-linking into the archived PDFs), the California AB 587 filings, Google's California AB 2013 AI-training summary, the DSA reports' Table-11 prose, and LY Corporation's bilingual Japan 情プラ法 Media Transparency Report |
| `data/ny-tos-reports.csv` | Vendored snapshot of New York's Social Media ToS-reports catalogue (sibling `dsa-transparency-data/ny_tos_reports.csv`) — seeded into the read-only `ny_tos_reports` table by `seed.py` |
| `data/ca-ab587-reports.csv` | Vendored snapshot of California's AB 587 Terms-of-Service reports catalogue (sibling `dsa-transparency-data/ca-ab587/ca_ab587_reports.csv`) — seeded into the read-only `ca_ab587_reports` table by `seed.build_ca_ab587_reports` |
| `data/ca-ab587-narratives.json` | Vendored snapshot of the **narrative text** of the CA AB 587 filings (sibling `dsa-transparency-data/ca-ab587/extract_narrative.py`) — one `columns`+`rows` entry per page of prose; seeded into the FTS5 `report_narratives` table (`source='ca-ab587'`) by `seed.build_ca_ab587_narratives` |
| `data/japan-narratives.json` | Vendored snapshot of the **bilingual narrative text** of LY Corporation's Media Transparency Report (sibling `dsa-transparency-data/japan-info-platform/build_japan_narratives.py`) — one `columns`+`rows` entry per section, each `text` an English translation + the Japanese original (the source is JA-only); seeded into the FTS5 `report_narratives` table (`source='japan'`) by `seed.build_japan_narratives` |
| `data/ca-ab2013-narratives.json` | Vendored snapshot of the **narrative text** of Google's California AB 2013 AI Training Data Transparency Summary (sibling `dsa-transparency-data/ca-ab2013/build_ca_ab2013_narratives.py`) — one `columns`+`rows` entry per section of prose; seeded into the FTS5 `report_narratives` table (`source='ca-ab2013'`) by `seed.build_ca_ab2013_narratives` |
| `data/ny-tos-normalized.csv` | Vendored snapshot of the **normalized NY ToS enforcement statistics** (sibling `dsa-transparency-data/ny-tos-reports/ny_tos_normalized.csv` — per-category figures mapped onto the Stop Hiding Hate Act's five categories; see that repo's `NORMALIZATION.md`) — seeded into the queryable `ny_tos_stats` table by `seed.build_ny_tos_stats` |
| `static/mcp.html` | Public MCP-server info page (served at `/mcp`) — documents `mcp_server.py`, its 8 tools, and host config; static, no page JS |
| `static/methodology.html` | Public methodology page (served at `/methodology`) — how the dataset is sourced, processed (double-count handling, cross-language keys), queried, and cited, plus known limitations; static, no page JS |
| `static/vendor/chart.umd.js` | Vendored Chart.js 4.4.4 (self-hosted, not a CDN) — served by the `/static/vendor/{filename}` route so the dashboard CSP stays `script-src 'self'` |
| `static/api-key.html` | API-key sign-in page (served at `/api-key`; formerly the "researcher portal") — Google sign-in + demo fallback. `/portal` 308-redirects here |
| `static/schema.html` | Public dataset-schema browser (served at `/schema`) — report tables + dimensions/measures, no sign-in (reads `/api/tables` + `/api/schema/{table}`) |
| `static/{es,fr,de,it,ja,zh,ko}/*.html` | Localized copies of the twenty-four pages, served under a locale prefix (`/es`, `/es/reports`, …). **Generated** — never hand-edit; see `scripts/localize_static.py` |
| `scripts/localize_static.py` | Generates the localized pages from the English originals + per-locale translation tables (the single source of UI translations). Re-run after any English page change |
| `Dockerfile` | Self-contained image: installs deps, seeds `demo.db` at build time, runs uvicorn on `$PORT` as non-root |
| `service.yaml` | Cloud Run (Knative) manifest — prod env + startup/liveness probes |
| `scripts/refresh-dataset.sh` | Re-vendor `data/vlop-dsa.json` from the canonical sibling-repo dataset |
| `scripts/revendor_data.py` | Re-vendor the **non-VLOP** snapshots (`data/harmonised-reports.json` + `data/report-locations.csv`) from the sibling `dsa-transparency-data` repo and report any extracted platform still missing a `seed_harmonised.SLUG_META` entry. Run by the `revendor-data.yml` workflow (nightly / on dispatch); also runnable locally (`--check` for a dry run) |
| `scripts/_demo_server.py` | Shared helper: seed DB + run a temp server (used by the GIF generators) |
| `scripts/make_gifs.py` | Headless terminal-demo GIF generator (pyte + Pillow) → `docs/gifs/` |
| `scripts/make_portal_gifs.py` | Portal-workflow GIF generator (Playwright + Pillow) → `docs/gifs/portal-*.gif` |
| `requirements.txt` | `fastapi` + `uvicorn[standard]` + `anthropic` (NL queries) |
| `demo.db` | SQLite DB (git-ignored, produced by `seed.py`) |
| `clients/cli/` | Generated Go CLI + MCP server for this API (CLI Printing Press, from `/openapi.json`) — own module; built on demand, excluded from the Docker/Cloud Build image |
| `mcp_server.py` | Native Python MCP **stdio** server — a thin HTTP front end over the API (8 tools: `list_tables`/`describe_table`/`dataset_overview`/`run_query`/`ask`/`register`/`submit_query`/`poll_job`). Does **not** import `main`; talks to a running server over `httpx`, so its deps (`mcp`+`httpx`) stay out of the app image and clear of the `fastapi`/`starlette` pins. Configured via `TRANSPARENCY_API_URL`/`_API_KEY`/`_API_TIMEOUT`. See [`docs/MCP.md`](docs/MCP.md) |
| `requirements-mcp.txt` | Deps for `mcp_server.py` only (`mcp`, `httpx`) — install into a separate venv (`make mcp`); kept out of `requirements.txt`/the Docker image |
| `mcp-config.example.json` | Example MCP host config (Claude Desktop / Claude Code) for `mcp_server.py` |
| `test_mcp_server.py` | Tests for `mcp_server.py` — drives the tool functions against the app via an in-process `TestClient` (no network, no `mcp` SDK needed; the `build_server()` test self-skips when the SDK is absent) |
| `.github/workflows/ci.yml` | CI: `pyflakes` lint + `pytest` on every PR/push (Python 3.11 & 3.12) |
| `.github/workflows/deploy.yml` | CD: build/push image + deploy to Cloud Run on push to `main` (WIF; skips until configured) |
| `.github/workflows/revendor-data.yml` | Auto-vendoring: regenerate the non-VLOP snapshots from `dsa-transparency-data` and open/update a single `auto/revendor-data` PR when they change. Triggers: nightly schedule, `workflow_dispatch`, or a `data-updated` `repository_dispatch` from the data repo. Validates by reseeding + `pytest` before opening the PR |
| `.gcloudignore` | Trims the Cloud Build upload context (keeps Dockerfile + `data/`) |

## Localization

The static pages are localized into **Spanish (`/es`), French (`/fr`),
German (`/de`), Italian (`/it`), Japanese (`/ja`), Chinese (`/zh`), and Korean
(`/ko`)** alongside the English originals (served at the root). English is the
source of truth; the
translations are **generated**, not hand-written:

- `scripts/localize_static.py` holds the per-locale translation tables (chrome +
  page strings, including inline-JS UI strings) and emits `static/<locale>/*.html`
  from `static/*.html`. After **any** change to an English page, re-run
  `python scripts/localize_static.py` so all four languages stay in sync, and
  commit the regenerated files. Never edit `static/{es,fr,de}/*.html` by hand.
- Routing: a loop in `main.py` registers `/<locale>`, `/<locale>/reports`,
  `/<locale>/removals`, `/<locale>/catalog`, `/<locale>/ny-tos`, `/<locale>/ca-ab587`, `/<locale>/apple`, `/<locale>/github`, `/<locale>/snap`, `/<locale>/india`, `/<locale>/korea`, `/<locale>/taiwan`, `/<locale>/turkey`, `/<locale>/cser`, `/<locale>/japan`, `/<locale>/tiktok-cger`, `/<locale>/user-data`, `/<locale>/microsoft`, `/<locale>/linkedin`, `/<locale>/tiktok`, `/<locale>/discord`, `/<locale>/disruptions`, `/<locale>/android`, `/<locale>/narratives`, `/<locale>/mcp`, `/<locale>/methodology`, `/<locale>/schema`,
  `/<locale>/api-key`, `/<locale>/privacy` for each locale (plus a `/<locale>/portal` → `/<locale>/api-key`
  redirect), all through `_serve_page` (so each localized file gets its own recomputed
  per-page CSP hash). The JSON API (`/api/*`), Swagger (`/docs`) and operational
  endpoints stay locale-agnostic; localized pages call the same `/api/*`.
- The globe **language switcher** (formerly a cross-site link to
  kieranmaynard.com) now switches the transparency site's own language —
  English / Español / Français / Deutsch / Italiano / … — pointing at the equivalent page in
  each locale. The switcher block is rebuilt by the generator, so it is
  consistent across every page and locale.

## CI

GitHub Actions runs `pyflakes`, `mypy` (config in `mypy.ini`, over
`main.py`/`seed.py`/`demo.py`/`conftest.py`/`mcp_server.py`), and `pytest
test_api.py test_mcp_server.py` on every pull request and push to `main`
(`ci.yml`). Keep all three green — the suite is hermetic (no Redis/server/MCP
SDK/`demo.db` needed; `conftest.py` builds a temp DB and `test_mcp_server.py`
drives the API in-process via `TestClient`). Run them locally before pushing
(`make lint typecheck test`).

`deploy.yml` builds + pushes the image and rolls a Cloud Run revision on push to
`main` via Workload Identity Federation, stamping the commit SHA as `APP_VERSION`.
It deploys with `--no-traffic`, smoke-tests the new revision's `/readyz`, then
promotes it with `update-traffic --to-latest`. Gated on the `GCP_PROJECT_ID` repo
variable, so it **skips** (not fails) until GCP is configured — see README →
"Continuous deployment". `.gcloudignore` keeps the Cloud Build upload lean.

## Data re-vendoring (automated)

The API serves a **frozen snapshot** of the data-collection pipeline that lives
in the sibling `dsa-transparency-data` repo (scrapers, raw archives, the
canonical extracted CSVs, the catalogue). The two vendored artifacts the image is
seeded from — `data/harmonised-reports.json` and `data/report-locations.csv` —
are kept in sync **automatically** rather than by hand:

- **`scripts/revendor_data.py`** does the mechanical half: regenerate the
  snapshot from the sibling repo's `harmonised-reports/extracted/` (via
  `seed_harmonised.write_snapshot`), copy `dsa_reports.csv` →
  `data/report-locations.csv` (header-validated), and print a Markdown summary
  that flags any extracted platform **not yet in `SLUG_META`** (those still seed
  under their raw slug, so the script suggests a paste-ready entry instead of
  guessing the display name/tier). `--check` dry-runs without writing.
- **`.github/workflows/revendor-data.yml`** runs it nightly / on
  `workflow_dispatch` / on a `data-updated` `repository_dispatch`, **validates**
  by reseeding + `pytest`, then opens/updates a single `auto/revendor-data` PR
  (body = the summary) only if something changed. A human still reviews it and
  finishes any `SLUG_META` naming — judgment stays with the human; the toil is
  automated.
- The data repo's **`.github/workflows/notify-revendor.yml`** pokes this workflow
  the moment its `main` changes (instant instead of waiting for nightly).

**Secrets (optional).** Both work with zero config (nightly schedule + anonymous
clone of the public data repo). To enable the instant path and let the auto-PR
trigger `ci.yml`, set a PAT: `REVENDOR_PAT` on this repo (used as the
create-pull-request token + private-repo clone) and `REVENDOR_DISPATCH_TOKEN` on
the data repo (scoped to dispatch this repo). Both jobs self-skip cleanly when
their secret is absent. Note: `schedule`/`workflow_dispatch`/`repository_dispatch`
only fire once the workflow is on `main`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# seed.py reads from the sibling repo — clone both into the same parent dir
python seed.py          # creates demo.db

uvicorn main:app --port 8000
```

Repos are expected as siblings:
```
parent/
  transparency-report-api/  ← this repo
  krMaynard.github.io/ ← source data lives at data/vlop-dsa.json
```

## Running the demo

```bash
python demo.py           # auto-advance
python demo.py --pause   # press Enter between steps (live demo mode)
```

## Auth

Two mechanisms, both presented as `X-API-Key` to the rest of the app:

- **Google sign-in (production).** The frontend uses Google Identity Services
  (FedCM in supporting browsers) to get an ID token and POSTs it to
  `/auth/google`. `_verify_id_token` validates it against `GOOGLE_CLIENT_ID`.
  Any verified Google account is **approved automatically on first sign-in**
  (no admin review); a login mints a first-party **session key** (`gs_…`) into
  `_key_store` (TTL `GOOGLE_SESSION_TTL`). Admins (`ADMIN_EMAILS`,
  comma-separated) keep a kill switch via `/admin/registrations/*` (revoke /
  restore). `_lookup_principal` re-checks the registration on every request, so
  an admin revoke kills live sessions at once. Durable account state lives in
  `_registrations` (Redis-backed when configured, else in-memory — same pattern
  as `_key_store`).
- **Demo keys (dev).** Hard-coded `momo`/`honggildong` + the open `/portal/register`.
  Gated by `ALLOW_DEMO_KEYS` (default on); set `ALLOW_DEMO_KEYS=0` in production.

Jobs are scoped per key — each principal only sees their own jobs (foreign IDs
return 404, not 403). `require_admin` gates the admin endpoints on the principal's
email being in `ADMIN_EMAILS`.

## Database schema

Seeded from `vlop-dsa.json` (compact interned format → star schema). Shared
dimension tables `services` (with `platform` = parent company), `categories`
(code + label), `sections`, `indicators`, `scopes`, `surfaces`, plus a `meta`
key/value table (`period`, `generated`). One **fact table per DSA report table**:

- **`t3_member_state_orders`** — Art. 9 & 10 orders, by category × scope
- **`t4_notices`** — Art. 16 notices, by category (+ Trusted-Flagger `tf_*`)
- **`t5_own_initiative_illegal`** / **`t6_own_initiative_tos`** — own-initiative actions, by category × 16 restriction types (t6 + surface)
- **`t7_appeals_recidivism`** / **`t8_automated_means`** — section × indicator × scope × surface → value
- **`t9_human_resources`** — section × indicator × scope → value
- **`t10_amar`** — Average Monthly Active Recipients, by scope
- **`t11_qualitative`** — free-text descriptions, by indicator (`value_text`)

Fact-row leading values are indices into the lookup arrays (= the dimension row
id), so seeding is positional. The DB is opened `mode=ro` as defence in depth.

Two dozen further datasets ride alongside, each exposed as an ordinary query table
via its own `TableSpec` (so `/api/query`/`/api/explore`/`/api/ask` reach them):
- **Google government removals** (`gr_*` dims + `gr_removals` facts).
- **Apple Transparency Report** — `ap_periods`/`ap_countries`/`ap_request_types`
  dims feeding `apple_requests` (one wide-sparse row per period × country ×
  request type; per-type-irrelevant measures are NULL) plus
  `apple_national_security` (US-NS/UK-IPA **banded ranges**: `requests_low/high`,
  `accounts_low/high`, not exact counts).
- **GitHub Transparency Report** — a single **tidy-long** `github_metrics` table
  (one row per measured value: `year`/`period`/`dataset`/`government`/`iso2`/
  `category`/`metric` + `count_low`/`count_high`; dims stored inline, no lookup
  tables). National-security & EU-DSA-MAU values are banded ranges
  (`count_low != count_high`); exact counts have `count_low == count_high`.
- **Snap Transparency Report** — a single **tidy-long** `snap_metrics` table
  (one row per measured value: `period`/`section`/`category`/`sub_category_1`/
  `sub_category_2`/`metric` + a `value`; dims stored inline, no lookup tables).
  `value` is `REAL` because some metrics are medians (e.g.
  `median_turnaround_time_minutes`) — don't SUM a median. Pin a `section` before
  aggregating; metrics aren't comparable across sections.
- **India IT Rules 2021 monthly compliance reports** — a single **tidy-long**
  `india_metrics` table (one row per measured value: `platform`/`period`/
  `section`/`category`/`metric`/`unit` + a `value`; dims stored inline, no lookup
  tables). Covers Facebook, Instagram, Twitter/X, Moj, ShareChat, Roblox, Google
  and Pinterest (+ `Meta` for report-level GAC orders; Roblox 2025-03→2026-05, with
  a redesigned layout + revised category taxonomy from 2026; Google 2021-04→ across
  all its SSMI surfaces, `complaints_received`/`removal_actions` by complaint reason,
  plus the half-yearly `gac_appeals` section 2023-03→ (Rule 3A(7) Grievance
  Appellate Committee appeals by Google service × outcome —
  `appeals_closed`/`_rejected`/`_allowed`/`_not_admitted`);
  Pinterest 2024-06→, `reports`/`voluntary_actions` by policy × object type).
  `value` is `REAL` and `unit` is `count` (exact),
  `approx_count` (Meta's abbreviated proactive figures like `2.3M` — rounded
  best-estimates) or `percent` (proactive-detection rates) — **never SUM across
  units**, and pin a `section` before aggregating.
- **Korea (Naver + Kakao) transparency reports** — a single **tidy-long**
  `korea_metrics` table (one row per measured value: `platform`/`service`/
  `period`/`category`/`metric`/`unit` + a `value`; dims stored inline). The
  half-yearly government data-request reports (2012-H1 onward) both companies
  publish under Korea's network laws, scraped from their public JSON endpoints.
  Four request types (`comm_user_information`/`comm_confirmation_data`/
  `comm_restriction`/`seizure_warrant`); Kakao splits by `service`
  (Daum/Kakao). `unit` is `count`, `percent` (Naver compliance rates) or
  `average` (Naver accounts-per-processed) — **never SUM non-count units**, and
  pin a `metric` (requests ≠ accounts) before aggregating.
- **Taiwan Anti-Fraud Act** — a single **tidy-long** `taiwan_metrics` table
  (one row per measured value: `publisher`/`period`/`section`/`category`/
  `metric`/`unit` + a `value`; dims stored inline). Two streams: the NPA's
  Art. 42 enforcement stream (`publisher='NPA-165'`, `section=
  'dns_blocked_sites'`): fraud sites DNS-blocked per Gregorian month ×
  official 網站性質 category (labels kept in Chinese); and the designated
  platforms' statutory 透明度報告 (`publisher` `Google`/`LINE`/`TikTok`;
  Meta's exists but isn't retrievable yet) — Art. 32/33 statistics in
  `section='afa_transparency_report'` + TikTok's voluntary proactive figures
  in `'platform_enforcement'`, with **coverage-window periods**
  (`YYYY-MM..YYYY-MM`, different per publisher). Pin a `section` (or
  `publisher`) **and a `metric`** before aggregating — requests ≠ URLs ≠
  accounts, and some metrics are parts/subsets of others
  (`urls_removed_legal`/`_policy` sum to `urls_removed`; the CIB figure is
  inside `art33_accounts_suspended`); `_leg_warnings` warns on both.
- **Türkiye Law No. 5651 platform reports** — a single **tidy-long**
  `turkey_metrics` table (one row per measured value: `platform`/`period`/
  `section`/`category`/`metric`/`unit` + a `value`; dims stored inline). The
  six-monthly transparency reports platforms publish under Türkiye's Law 5651
  (Additional Art. 4) on the content-removal / access-blocking decisions notified
  to them, from three publishers: **Meta**
  (`platform` `Facebook`/`Instagram`, H1 2023 → H1 2025, static English PDFs from
  `transparency.meta.com/sr/`), **X** (`platform` `X`, H1 2021 → H1 2025, from
  `transparency.x.com`), and **TikTok** (`platform` `TikTok`, 2021 H1 → 2025 H2,
  from its standalone Turkish "Bireysel Talepler Raporu" for the BTK at
  `tiktok.com/safety/tr-TR/transparency/btk-raporu` — an HTML page, no PDF).
  Two request streams (`section`): `individual_requests`
  (Art. 9/9-A — personality/privacy applications via a form) and
  `authority_requests` (Art. 8/8-A — the ICTA, the Consumer-Policy channel, and
  court orders). Meta reports both streams as report-level totals (blank
  `category`); X reports only the individual stream, broken down by issue
  `category` (`Abuse`/`Hateful Conduct`/`Copyright`/… kept verbatim) with a
  request volume (`metric='requests'`) and an `action_rate` (`unit='percent'`).
  TikTok, like X, reports only the individual stream (blank `category`), as its
  half-year `applications_received` total.
  `value` is `REAL` (to hold X's action-rate percentages). Pin a `section`
  **and a `metric`** before aggregating — requests ≠ reported entities ≠ removed
  entities, `requests_icta`/`_consumer_policy`/`_court_orders` are parts of
  `requests_total` (which they may not fully sum to, as Meta doesn't categorise
  every request; authority counts can also bundle Facebook + Instagram), and
  `action_rate` is a percent (never SUM); `_leg_warnings` warns on both. X's
  per-category `requests` are additive (disjoint issues), so summing them across
  categories is a legitimate grand total. **Google / YouTube** publishes no
  standalone Türkiye Law 5651 report (its Turkish figures live only in the global
  `transparencyreport.google.com` tool as a country slice).
- **EU Terrorist Content Online Regulation (TCOR)** — a single **tidy-long**
  `tco_metrics` table (one row per measured value: `publisher`/`role`/`period`/
  `section`/`category`/`metric`/`unit` + a `value`; dims stored inline). The
  annual transparency duties under Reg. (EU) 2021/784 around *terrorist content*.
  Two streams (`role`): **`authority`** (the Art. 8 / European-Commission side —
  per-Member-State `removal_orders_issued` from the Commission's implementation
  report COM(2024) 64, `category` = Member State (Germany 249 / Spain 62 /
  France 26 / Austria 8 / **Romania 2** / Czechia 2, 2022-06..2023-12) plus an
  `EU` summary total; and a national authority's activity — Ireland's Coimisiún
  na Meán) and **`platform`** (the Art. 7 side — each hosting provider's
  enforcement figures, `category` = the report's own sub-service: Spotify (per
  sub-service) + Meta/Facebook). Figures are **sparse** and **transcribed** from
  the archived reports with fail-loud anchor checks (the build raises if a report
  drifts). Metric scope is **each report's own** and not comparable across
  publishers (Spotify's `content_removed_proactive` is terrorism-only; Meta's
  covers broader policy areas and is `approx_count`). `unit` is `count` or
  `approx_count`. Pin `publisher` **and** `metric` before aggregating, and note
  the per-country rows sit beside the `category='EU'` summary total (summing both
  double-counts); `_leg_warnings` warns on all three. Coverage is a starting set —
  more Art. 7 platforms and national Art. 8 authorities slot in as archived. The
  `/tco` dataset page is English-only (like `/mandates`).
- **EU AI Act training-data transparency (Art. 53(1)(d))** — a single
  **tidy-long** `ai_training_metrics` table (one row per disclosed field:
  `provider`/`model`/`released`/`section`/`field`/`value` + a `size_rank`; dims
  stored inline). The **public summary of training content** every provider of a
  general-purpose AI model must publish on the AI Office's standardised template
  (Reg. (EU) 2024/1689, in force 2 Aug 2025). There is no single registry of the
  *filled* summaries — each provider self-publishes in its own format — so the
  builder reads three source shapes: **Microsoft's** machine-readable Hugging Face
  "data summary cards" (parsed by their stable numeric template codes, so any
  provider using that markdown template parses for free); the **PDF** filings
  (Google/Meta/OpenAI/xAI/Swiss AI/SpeakLeash — the size bands are checkbox
  selections, which render in the text layer for some (☒/☐) and not at all for
  others, so those values are curated from the rendered form and cross-checked
  with fail-loud anchors on the PDF text); and **HTML** summaries published as a
  web page or a Hugging Face Space rather than a document (Bria, SmolLM3 —
  archived under `raw/` and anchor-checked the same way). Three `section`s: **`modality`**
  (`field` = Text/Image/Audio/Video/Other; `value` = the banded training-data
  size, e.g. `More than 10 trillion tokens`; **`size_rank`** = 1/2/3 across the
  three bands, 0 = "Not applicable", so coarse sizes are **numerically comparable
  across providers**), **`general`** (`data_cutoff`, `ongoing_collection`) and
  **`data_source`** (`publicly_available`/`commercially_licensed`/
  `third_party_private`/`personal_data`/`crawled`/`user_data`/`synthetic`;
  `value` = Yes/No/…).
  `value` is text; `size_rank` is an **ordinal rank** — compare it with
  MIN/MAX/AVG, **never SUM** (`_leg_warnings` warns on a `size_rank` SUM).
  Coverage is a starting, expandable set (Google + Meta + Microsoft + OpenAI +
  xAI + Swiss AI + SpeakLeash + Hugging Face + Bria; 11 model entries) — Meta's,
  OpenAI's and xAI's are filed on the AI Office's full
  template (Meta groups Image & Video as one "Perception" modality, recorded on
  both rows; all three break out `crawled` / `user_data` data-source categories the
  others don't — OpenAI's `user_data` is Yes via data from other products
  (ChatGPT/Codex), though model-interaction data itself was not used).
  The rows are **sparse**: each summary fills only the categories it addresses, so
  a **missing `data_source` row means the summary is silent, not "No"**. Two
  filers deviate from the template and are **annotated in `value`** rather than
  normalised away: Meta's combined Image & Video band, and **Bria**, which wrote
  exact figures instead of ticking a band (`1 billion to 10 trillion tokens
  (reported as: up to 19.2 billion tokens)`; `size_rank` is the band those figures
  fall in) and files no Audio/Video/Other rows at all. Two filings are worth
  knowing about when reading the set: **xAI** (Grok 4.5, on the Union market
  14 Jul 2026) answers **Yes to every data-source category** and is the only filer
  that is **not** a Code-of-Practice signatory, while **Bria** (3.2) is the only
  one with **both** `publicly_available` = No **and** `crawled` = No — trained
  exclusively on commercially licensed data.
  The `/ai-training` dataset page is English-only (like `/mandates`).
- **Regional content-moderation transparency-law reports** — a single
  **tidy-long** `regional_metrics` table (one row per measured value:
  `jurisdiction`/`platform`/`period`/`section`/`category`/`metric`/`unit` + a
  `value`; dims inline). The periodic content-moderation reports platforms file
  under sub-national / national statutes, both filed by Google for **YouTube**:
  **Texas HB 20** (Business & Commerce Code §120.053, half-yearly 2024-H2→ —
  `monetization`, `age_restrictions`, `enforcement` (videos_removed / appeals /
  reinstatements), `coordinated_influence`, `human_flags`,
  `removals_by_detection`, `removals_by_reason`, `removals_by_country`; reduced
  to monetization + age_restrictions from 2025-H2) and **Austria KoPl-G**
  (Kommunikationsplattformen-Gesetz §4, biannual 2021-H2→ — `complaints`:
  reported_items / removed_items, sparse as the webform is "de facto not used").
  `unit` is `count`. Metric scope is each report's own — pin `jurisdiction`,
  `section` **and** `metric` before aggregating, and note the reason/detection
  breakdowns each partition the `enforcement` `videos_removed` total (summing a
  breakdown with the total double-counts); `_leg_warnings` warns on all three.
  The build cross-checks that each full Texas report's reason and detection
  breakdowns sum back to `videos_removed`. The `/regional` dataset page is
  English-only (like `/mandates`).
- **China CIIRC (12377) online-report handling** — a single **tidy-long**
  `ciirc_metrics` table (one row per measured value: `publisher`/`period`/
  `section`/`category`/`metric`/`unit` + a `value`; dims inline). The Central
  Cyberspace Administration of China (CAC) Illegal & Harmful Information
  Reporting Center's (中央网信办举报中心, the national **12377** hotline) monthly
  bulletin (全国网络举报受理情况) on how many public reports of illegal/harmful
  online information were handled that month, scraped from `www.12377.cn` (79
  months, Oct 2019→). `publisher='CAC-CIIRC'`, `section='reports_received'`;
  `category` is the receiving body — `central_center` / `local_departments` /
  `platforms` (of which `commercial_platforms` is a subset some months) — plus
  `national_total` = central + local + platforms. `unit` is `count` (figures are
  published in 万/ten-thousands, stored ×10,000). **Coarse aggregate volumes
  only — China discloses no per-platform or per-category breakdown.** Pin a
  `category` before aggregating: `national_total` already sums the three bodies
  and `commercial_platforms` ⊂ `platforms`, so summing categories double-counts;
  `_leg_warnings` warns on an unpinned category. The build reconciles
  central+local+platforms against the stated national total per month. The
  `/china` dataset page is English-only (like `/mandates`).
- **China 12321 telecom-spam report handling** — a single **tidy-long**
  `china12321_metrics` table (one row per measured value: `publisher`/`period`/
  `section`/`category`/`metric`/`unit` + a `value`; dims inline). The **12321
  网络不良与垃圾信息举报受理中心** (Internet Society of China / **MIIT**), China's
  national hotline for telecom/internet **nuisance & spam**, published a monthly
  report-handling bulletin from **2016-09 to 2019-02** (discontinued after Feb
  2019), scraped from `www.12321.cn` (26 bulletins; 2017-10's source link 404s).
  The **telecom-spam complement** to the CAC/12377 content-reporting series
  (`ciirc_metrics`) — a different agency and remit. `publisher='12321-ISC'`,
  `section='reports_received'`; `period` is `YYYY-MM` (or `YYYY-MM..YYYY-MM` for
  the few combined-month bulletins). `category` is the report type received:
  `app`, `sms` (monthly total), `sms_spam` (垃圾类) and `sms_illegal` (涉嫌违法类)
  — the two disjoint parts of `sms` — `harassment_calls`, `bad_websites`, and the
  2016-era-only `fraud_comms` and `spam_email`. `unit` is `count` (2016 bulletins,
  exact 件次) or `approx_count` (2017+, rounded to 万/ten-thousands, stored
  ×10,000) — don't mix the two precisions when comparing across years. Pin a
  `category` before aggregating: `sms` already sums `sms_spam` + `sms_illegal`, so
  summing categories double-counts; `_leg_warnings` warns on an unpinned category.
  The build cross-checks `sms_spam + sms_illegal` against the `sms` total within
  万-rounding slack. The `/china-12321` dataset page is English-only (like
  `/mandates`).
- **Meta Community Standards Enforcement Report (CSER)** — a single **tidy-long**
  `cser_metrics` table (one row per measured value: `app`/`policy_area`/`metric`/
  `period`/`unit` + a `value`; dims stored inline). Meta's flagship **voluntary**
  content-moderation report (not filed under any single law), Facebook +
  Instagram, quarterly 2017 Q4 → 2025 Q4, scraped from the CSER's GraphQL feed
  (one persisted query returns the whole dataset as a CSV; no static download).
  16 policy areas (Hateful Conduct, Bullying & Harassment, Fake Accounts, …) —
  `policy_area='Cross-Policy Data'` is an **across-policy aggregate**, not a peer
  of the individual areas. 14 metrics: Content Actioned/Removed/Appealed/Restored
  (counts) and Prevalence + Lowerbound/Upperbound Prevalence + UBP, Proactive
  rate, Enforcement Precision Lower/Upper Bound, False Positive Lower/Upper Bound.
  `unit` is `count` or `percent` (prevalence, proactive rate and precision are
  rates — never SUM). Pin a `metric` before aggregating (metrics aren't
  comparable), exclude `Cross-Policy Data` before summing over policy areas (it
  double-counts), and treat the Lower/Upper bounds as the ends of a range, not
  additive quantities; `_leg_warnings` warns when a SUM/AVG pins no `metric` or
  `policy_area`. `N/A` cells (a metric not reported for a policy × quarter) are
  dropped at build time.
- **Singapore IMDA Online Safety reports** — a single **tidy-long**
  `singapore_metrics` table (one row per measured value: `service`/`period`/
  `section`/`category`/`metric`/`unit` + a `value`; dims stored inline). The
  annual online safety reports the six Designated Social Media Services
  (Facebook, Instagram, TikTok, X, YouTube, HardwareZone) file under Singapore's
  **Code of Practice for Online Safety** (IMDA, Broadcasting Act), plus IMDA's
  own Online Safety Assessment Reports (OSAR). Two streams (`section`):
  `assessment` (IMDA's normalized, cross-service Mystery-Shopper benchmark —
  `action_rate` in `percent` and `time_to_action` in `days`, per service for the
  2024 and 2025 rounds, transcribed from the OSAR chart tables) and
  `platform_report` (each service's own Singapore figures for 2024-04..2025-03,
  parsed from the report PDFs — Meta's per-category `content_actioned_sg` +
  `proactive_rate_sg`, YouTube's by-reason `flags_received_sg`/
  `videos_removed_sg`, TikTok's headline figures, X's
  `median_time_to_action_hours`; HardwareZone reports no Singapore statistics so
  it appears only in `assessment`). `platform_report` metric names are each
  vendor's own and are **not** comparable across services — pin `service`,
  `section` **and** `metric` before aggregating, and never mix the
  `percent`/`days`/`hours`/`count` units; `_leg_warnings` warns on all three.
  The `/singapore` dataset page is English-only (like `/mandates`).
- **Australia eSafety BOSE (Basic Online Safety Expectations)** — a single
  **tidy-long** `esafety_bose_metrics` table (one row per measured value:
  `service`/`period`/`section`/`category`/`metric`/`unit` + a `value`; dims
  inline). The figures Australia's **eSafety Commissioner** publishes from the
  mandatory **transparency notices** it issues under the **Online Safety Act
  2021** (the BOSE regime — the online-safety-code analog to Singapore's Code of
  Practice). Unlike the other datasets there is **no sibling-repo extractor** —
  the figures are **transcribed** from the archived reports by
  `scripts/build_esafety_bose.py` (each row page/figure-cited in that builder,
  with a fail-loud cross-check that the four Meta services sum to the report's
  stated Meta aggregate). Two report streams. **`csea_periodic`** — the CSEA &
  sexual-extortion periodic report (notices given 22 Jul 2024; reporting period
  15 Jun–15 Dec 2024, `period='2024-06-15..2024-12-15'`; Aug 2025 report + Feb
  2026 update): per-service `user_reports_global` (count of user reports of child
  sexual exploitation & abuse) and `median_response_minutes` (median time a human
  moderator took to reach an outcome, in `minutes`) from **Figure 4**, plus
  Australia-specific and aggregate totals under the service labels
  `All services (total)` and `Meta services (aggregate)` (metrics
  `user_reports_global` / `user_reports_australia`). The **AI-companion**
  non-periodic findings (notices to Chai, Character.AI, Chub AI, Nomi; reporting
  period 1 Jul–30 Sep 2025, `period='2025-07-01..2025-09-30'`):
  `ai_companion_reports` (per-provider `user_reports` by `category` = harm type
  `pornography`/`csea`/`self_harm`), `ai_companion_staff` (`trust_safety_staff`
  headcount as at 30 Sep 2025 — Chai's `6.5` is a fractional FTE), and
  `survey_prevalence` (eSafety's 2026 representative survey of children aged
  10–17: `ever_used` / `used_past_4_weeks` percentages, per `AI companion` vs
  `AI companion or assistant` and per provider). `unit` is `count`, `minutes` or
  `percent` — **never SUM across units, or SUM a percent/median**. The
  `All services (total)` and `Meta services (aggregate)` rows **OVERLAP** the
  per-service rows (the four Meta services sum to the Meta aggregate 8,877,600,
  itself part of the 11,458,969 all-services total), so pin a single `service`
  (or exclude the total/aggregate labels) before summing; pin `section` **and**
  `metric` too. `_leg_warnings` warns on all three. No dataset page yet (query
  via `/api/query`/`/api/explore`/`/schema`).
- **Korea Network Act (illegal-sexual-content)** — a single **tidy-long**
  `korea_network_act_metrics` table (one row per measured value: `publisher`/
  `period`/`section`/`category`/`metric`/`unit` + a `value`; dims inline). The
  **annual transparency report** online service providers must publish under
  South Korea's **Network Act** (Art. 64-5) and **Telecommunications Business
  Act** (Art. 22-5) on the technical/managerial measures they take against the
  circulation of *illegal sexual content* (illegally-filmed content, deepfake /
  "fake" images and videos, and child/youth sexual-abuse material). Three
  `publisher`s: **Google** publishes one per calendar year covering **Search and
  YouTube jointly** (no per-product split), all six reports so far (2020 → 2025),
  and **Naver** + **Kakao** each file the standardized §64-5 template with the KCC
  (now KMCC), whose per-provider PDFs on board 1156 hold 2020 → 2025. Google's own
  report carries the fuller detail below; Naver and Kakao publish only the year's
  figures on the template, so they populate `annual_summary` **only** (received /
  removed, transcribed from the KMCC PDFs and cross-checked — received against the
  report's 피해자등+기관·단체 split; their by-reason splits aren't stored, as the
  reports allow a request to be double-counted across reasons). The **2024 and
  2025** Google reports publish a full **monthly**
  breakdown (`period` a month `YYYY-MM`) in four `section`s, each a **cross-cut
  of the SAME requests** (so NOT additive across sections): `requests_received`
  (by complainant — Victims/User + Agency/Gov, `metric='requests'`),
  `request_reasons` (by reason, `metric='requests'`), `processed_result` (by
  outcome — Removed + four `Not Removed - …` reasons + two `KCSC Assessment - …`
  rows, `metric='urls'`) and `removal_reasons` (the removed URLs by reason,
  `metric='urls_removed'`). Within a monthly section the categories are
  **disjoint** and sum to the section total (the report's "Total" rows are
  dropped), so summing over `category` within one section — or over `period`
  within a year — is a legitimate grand/annual total. The **2020–2023** reports
  are prose-only (2020 covers just 10–31 Dec, the law's implementation date);
  their headline URL counts, plus a rollup of 2024/2025, live in section
  **`annual_summary`** (`category='All'`, `period` a **year** `YYYY`, `metric`
  `urls_received` / `urls_removed`) — a comparable **2020→2025 series** that sits
  *beside* the monthly sections (a rollup of them, so don't sum it together with
  them). Pin a `section` **and** `metric` first, and never sum across sections
  (requests received ≠ processed outcomes ≠ removed URLs). The build cross-checks
  every monthly breakdown against the report's stated per-section totals and the
  derived annual against `annual_summary`, raising on a mismatch (note 2024's
  requests-received 158,052 vs processed 158,044 differ by 8 — a source quirk,
  preserved); `_leg_warnings` warns on both dims. The `/korea-network-act`
  dataset page is English-only (like `/mandates`).
- **Japan 情プラ法 (Information Distribution Platform Act)** — a single
  **tidy-long** `japan_metrics` table (one row per measured value: `service`/
  `period`/`section`/`category`/`metric`/`unit` + a `value`; dims inline). The
  Art. 28 implementation-status statistics MIC-designated large providers must
  publish under the amended Provider Liability Limitation Act (情プラ法, in force
  Apr 2025). **Three providers** so far (TikTok/X still publish only qualitative
  Art. 21 criteria): **LY Corporation** — its five services (Yahoo! Chiebukuro,
  Yahoo! Finance boards, LINE OpenChat, LINE VOOM, Yahoo! News comments) from its
  FY2024 Media Transparency Report, in section `posts_activity` (category `All`):
  `metric` `posts`/`posts_removed` (count) or `removal_rate` (percent), per
  FY2024 quarter (`2024-04..2024-06` … `2025-01..2025-03`) or the annual total
  (`2024-04..2025-03`); **Google (YouTube)** from its `2025-07-26..2026-03-31`
  report, across sections `legal_requests`/`legal_extended_review_notifications`/
  `legal_items`/`legal_removals` (the legal stream) and `user_flags`/
  `policy_removals`/`policy_detection_source`/`suspensions`/`appeals`/`platform`
  (the policy stream), with `category` a reason (`Total` = the section aggregate)
  and `metric` the measure (`requests`/`items_removed`/`flags`/`videos_removed`/
  `accounts_terminated`/…); and **Meta** — its designated services **Facebook**,
  **Instagram** and **Threads** (each reported separately, `2025-07-30..2026-03-31`),
  across sections `requests_received`/`decisions_within_7d`/`decisions_after_7d`/
  `requests_no_action` (the IDPA rights-report channel, `category` = a reporting
  reason like Portrait rights / Invasion of privacy), `content_actions`/
  `account_actions`/`user_report_actions`/`user_report_reviewed`/`proactive_actions`/
  `account_suspensions` (enforcement, `category` = a violation type like Spam /
  Fraud and Deception / Local Law Violations), `appeals` (metric per appeal type,
  category `All`) and `platform` (`content_pieces`/`monthly_active_users`, unit
  `approx_count` — Meta rounds them). Metrics and sections aren't comparable, and
  every section keeps a `Total`/`All` category beside its breakdown — pin
  `service`, `section`, `category` **and** `metric` before aggregating; never SUM
  `removal_rate`, don't add LY Corp's quarters to its annual total, and don't add
  YouTube's `policy_removals` and `policy_detection_source` (two cross-cuts of the
  same removed videos); `_leg_warnings` warns on all four dims. **Meta caveat:**
  its per-policy breakdowns are the report's own "most prevalent" categories — an
  ILLUSTRATIVE SUBSET, not a partition — so the `Total` category is a superset,
  **not** the sum of the listed categories (and Meta's own figures don't fully
  reconcile: `decisions_after_7d`'s Threads `Total` even sits below one of its
  categories, per the report's logging-issue footnotes). Two Meta tables are
  omitted (regulator requests 5.3.4 has a non-per-service column + Meta-flagged
  non-disaggregation; court orders 5.3.5 are all-zero). The `/japan` dataset page
  is localized into all seven locales.
- **TikTok Community Guidelines Enforcement Report (CGER)** — a single
  **tidy-long** `tiktok_cger_metrics` table (one row per measured value:
  `period`/`metric`/`policy_type`/`issue`/`task_type`/`task`/`unit` + a `value`;
  dims stored inline). TikTok's flagship **voluntary** content-moderation report
  (not filed under any single law), quarterly 2020 Q3 onward, from the cumulative
  CGER ZIP the report page links (the latest ZIP carries the full history). Only
  the global **`All`-location cut** is vendored (`policy_type`/`issue`/
  `task_type`/`task` = `All` for the headline metrics; the per-policy breakdown
  sets `policy_type='Policy'`). `unit` is `count` or `rate` (any metric whose
  name contains rate/share/percentage is a **fraction of 1** — never SUM). Pin a
  `metric` before aggregating (metrics aren't comparable), and pin the row grain
  (`issue`/`policy_type` and `task`/`task_type`) so a breakdown row isn't summed
  with its own `All` aggregate; `_leg_warnings` warns when a SUM/AVG pins no
  `metric`, or leaves `issue`/`policy_type` or `task`/`task_type` unpinned.
- **Google government requests for user information** — a single **tidy-long**
  `google_userdata_metrics` table (one row per measured value: `dataset`/
  `period`/`country`/`iso2`/`product`/`legal_process`/`assisting_country`/
  `metric`/`unit` + `value_low`/`value_high`; dims stored inline). The biannual
  bulk-CSV export (2009-H2 onward): global requests (requests/accounts/
  `pct_disclosed` per country × legal process), the diplomatic/MLAT slice,
  Enterprise Cloud (GCP/Workspace), and the US national-security datasets
  (FISA content / FISA non-content / NSLs) as **banded ranges**
  (`value_low != value_high`, non-additive). **2012-H2..2014-H1 report an
  `All` legal_process aggregate alongside the per-process split** — the two
  grains are disjoint by country × period (only the US is split in that
  window), so an unfiltered SUM is the exact global total, but restricting to
  one grain drops the other grain's volume; never SUM `percent` rows.
- **Microsoft Law Enforcement Requests Report** — a single **tidy-long**
  `microsoft_metrics` table (one row per measured value: `period`/`section`/
  `country`/`metric`/`unit` + a `value`; dims stored inline). Per-country
  demands + the four disclosure outcomes, half-yearly since 2013. The report
  split changes across eras (`combined` 2013–2016; `criminal`/`emergencies`
  from 2017; `civil` from 2017-H1; `skype` overlaps `combined` in 2013) — pin
  a `section` before aggregating; on civil sheets the outcome metrics count
  accounts, not requests.
- **LinkedIn Government Requests Report** — a single **tidy-long**
  `linkedin_metrics` table (one row per measured value: `dataset`/`period`/
  `country`/`metric`/`unit` + `value_low`/`value_high`; dims stored inline).
  Member-data requests per country (2016-H1→), the US legal-process breakdown
  (2015-H1→; `pct_*` metrics are percentages of requests, and the
  national-security rows are banded ranges), and government content-removal
  requests (2018-H1→). Scraped from the server-rendered report page.
- **TikTok Government & Legal Requests reports** — a single **tidy-long**
  `tiktok_metrics` table (one row per measured value: `dataset`/`period`/
  `country`/`metric`/`unit` + a `value`; dims stored inline). A stream distinct
  from TikTok's DSA content-moderation figures. Three datasets by country ×
  half-year (2019-H1→), from the cumulative CLIGR CSVs: `government_removals`
  (content-removal requests — requests/content/accounts received & actioned,
  removal rate), `information_requests` (legal/emergency/preservation requests,
  accounts specified, disclosure percentages) and `ip_removals` (global-only —
  copyright & trademark request/removal counts + success/appeal rates). `unit`
  is `count` or `percent` (every rate/percentage is a **fraction of 1** — never
  SUM). **The global `All` country row sits alongside the per-country rows**,
  and the `All` aggregate uses different metric names than the per-country rows
  (`total_government_requests`/`total_legal_requests`/… at `All` vs
  `total_requests_received`/`legal_requests`/… per country) — pin `country` (or
  the right metric grain) plus a `dataset` and `metric` before aggregating.
- **Discord Transparency Reports** — a single **tidy-long** `discord_metrics`
  table (one row per measured value: `period`/`section`/`category`/`metric`/
  `unit` + a `value`; dims stored inline). Walked from each report CSV's
  labelled sub-tables (quarterly 'YYYY-Qn' 2022-2023, half-yearly 'YYYY-Hn'
  2024+): Trust & Safety enforcement (accounts/servers/members actioned by
  policy category, `accounts_disabled`, `servers_removed`, `appeals`, reports,
  ncmec) and government/legal requests (`us_gov_info_requests`,
  `international_government_information_requests`, `preservation_requests`,
  `emergency_requests` — by country). `category` is the row dimension kept
  verbatim (a policy category, country, request type, or month); `unit` is
  `count` or `percent` (an appeal/report rate as the reported percentage
  number). **Section labels change across reporting eras** (Discord's own
  renaming — e.g. the US-legal-process section is `legal`/
  `united_states_government_information_requests`/`us_gov_info_requests` in
  different years); `_leg_warnings` warns when a SUM pins no `section`/`metric`.
  A known 2023-Q3 column-shift in the extractor's source is corrected +
  Total-validated upstream.
- **Google Android ecosystem security** — a single **tidy-long**
  `android_metrics` table (one row per measured value: `section`/`period`/
  `category`/`metric`/`unit` + a `value`; dims stored inline). Google's Android
  security Transparency Report — Potentially Harmful Application (PHA / malware)
  rates on devices and in Google Play (2017-Q1→2024-Q4). Five cuts (`section`):
  `devices_with_pha` (by market type, 12-mo rolling), `devices_by_version` (by
  Android version, quarterly), `installs` (by source, rolling),
  `installs_by_country` (by country ISO-2, rolling) and `installs_by_category`
  (by malware category, quarterly). `period` is a `YYYY-MM-DD` date (rolling end
  date / quarter end date). `metric` is `pha_rate` (every cut) or
  `category_share` (installs_by_category only); `unit` is `rate` (a **fraction
  of 1** — never SUM) or `percent` (the category share, sums to ~100/quarter).
  These are **rates, not counts** — `_leg_warnings` warns on any SUM and when a
  SUM/AVG pins no `section`/`metric`; prefer AVG/MIN/MAX.
- **EU DSA Transparency Database — Statements of Reasons** — a single
  **tidy-long** `dsa_tdb_metrics` table (one row per SoR count: `section`/
  `platform`/`period`/`category`/`metric`/`unit` + a `value`; dims inline). The
  **decision-level** DSA data (distinct from the Art. 15/24 aggregated reports in
  the `t3`–`t11` star schema): under the DSA every content-moderation decision an
  in-scope platform takes is filed to the
  [Transparency Database](https://transparency.dsa.ec.europa.eu/) as an
  individual **Statement of Reasons**. The raw DB is billions of rows / ~4 TB, so
  this is a compact **re-aggregation** of the Commission's own pre-made monthly
  aggregates via its **`dsa-tdb`** toolbox (sibling
  `dsa-transparency-data/dsa-tdb/build_dsa_tdb.py`, which runs `dsa-tdb-cli
  download-aggs` then rolls day→month and collapses to one-dimension cuts). Kept
  to the **top 60 platforms** by volume (~99.97% of all SoRs), 2023-09 onward.
  `metric` is always `statements`, `unit` always `count`; `period` is the SoR's
  `created_at` month `YYYY-MM`. Sections (`section`): `totals` (`category='All'`);
  the **single-select** cuts `by_category` (14 DSA statement categories),
  `by_decision_ground` (Illegal content / Incompatible with terms),
  `by_automated_detection` (Yes/No), `by_automated_decision` (Fully/Partially/Not),
  `by_source_type` (Article 16 notice / Trusted flagger / Own-initiative / Other);
  and the **multi-select** `by_decision_visibility` (Content removed / Access
  disabled / Demoted / …). Each single-select cut partitions the platform-month
  total, so a cut's categories sum back to `totals` — never sum a cut *together
  with* `totals` (double counts), and never sum `by_decision_visibility` to a
  total. Volumes are dominated by a few marketplaces (Google Shopping product
  delistings run to hundreds of millions/month), so pin a `section` **and usually
  a `platform`** before aggregating; `_leg_warnings` warns on both. The `/dsa-db`
  page is English-only (like `/china-12321`). `dsa-tdb` installs from the
  Commission's package index and is a **build-time-only** dep of the sibling
  builder — never in the API image.

**Dimension normalization** (`seed.normalize_dimensions`, run post-load by both
`build_db` and `build_harmonised_facts`, idempotent): the DSA template embeds an
aggregate **total** row next to its breakdown rows (AMAR's EU `TOTAL` beside the
per-member-state rows; the `All the entries` category beside per-category rows;
the `Total number` scope beside upheld/reversed outcomes; the `All` cross-surface
row beside the per-surface rows like `Core`/`Ads` in t6/t7/t8), so a naive `SUM`
double-counts. The pass sets **`is_total`** on the `scopes`/`categories` rows
whose label is an aggregate (TOTAL/GESAMT/"All the entries"/…) and on the
`surfaces` row named `All`, and **deletes fact rows** that reference mis-parsed
junk labels (`[...]`, header cells, blanks, numeric strays) leaked by some
non-VLOP extracts. `compile_query` exposes
`scope_is_total`/`category_is_total`/`surface_is_total` as filterable dimensions
so the curated tabs and the Explore "Rows" selector pick a single grain (totals
only / breakdown only) instead of summing a total together with its own parts.

**Cross-language canonical keys.** Non-VLOP reports are filed in any official EU
language, so the same template row arrives as different text (`Décisions
confirmées` / `Bestätigte Entscheidungen` / `Decisions upheld`). The seeder keeps
the original-language label for display (`name`) but stamps a language-neutral
**`key`** (canonical English) on each `sections`/`indicators`/`scopes` row from
the vendored `data/template-crosswalk.json` (built by
`scripts/build_template_crosswalk.py`, which learns the mapping by aligning
same-structure reports to an English reference and **drops anything ambiguous**).
`compile_query` exposes `section_key`/`indicator_key`/`scope_key` so a query can
group or filter across languages (e.g. the Appeals tab filters on `indicator_key`)
while the plain dimension still shows the filed text. (Greek extracts have a
column-shift in the source data, so most EL indicator/scope labels stay
un-normalized for now — correct-but-unmapped, never mis-mapped; category labels
aren't crosswalked yet.)

**Multi-tier reports.** The `reports` table (one row per submitted report, with a
`tier`) lets the same `t3`–`t11` schema hold more than the VLOP set. After the
VLOP load, `seed_harmonised.build_harmonised_facts()` appends the **non-VLOP
harmonised-template reports** (45 services / 46 reports — the 49 extracted minus
LinkedIn / Pinterest / Wikipedia, which are already VLOP services, with AboutYou's
second period attaching to its existing service): a new `reports` row
(tier `online-platform`/`hosting`/`intermediary`) + `services` row per platform,
with the shared dimensions interned/extended. So `POST /api/query` and
`/api/explore` span **both** VLOP and non-VLOP data, while the VLOP dashboard's
`GET /api/overview` stays scoped to `tier = 'vlop'` (it derives the VLOP service
set from vlop-tier facts) so its headline figures don't silently absorb them.

A standalone **`report_locations`** table (flat, not part of the star schema) is
also seeded — from `data/report-locations.csv` via `build_report_locations()` —
holding the non-VLOP DSA transparency-report catalogue (`platform`, `company`,
`category`, `confidence`, `harmonised_template`, `format_period`, `url_label`,
`url`, `archived`). `archived` is a GitHub URL to the report file(s) mirrored in
the sibling `dsa-transparency-data` repo (set in its catalogue by
`link_archives.py`) — surfaced as the catalogue page's "Archived" column. It
powers the public `GET /api/report-locations` endpoint and the dashboard's
"Where platforms publish their reports" panel.

A second standalone **`ny_tos_reports`** table (also flat) holds **New York's
Social Media Terms-of-Service reports** — the twice-yearly policy filings
social-media companies submit to the NY Attorney General under the Stop Hiding
Hate Act (a different jurisdiction/format from the EU DSA data; narrative policy
PDFs, not the 1–11 template). Seeded from `data/ny-tos-reports.csv` via
`build_ny_tos_reports()` (`company`, `platform`, `period`, `upload_date`,
`access`, `source_url`, `filename`, `archived`, `sha256`, `bytes`). `access` is
`public` (PDF mirrored in the sibling data repo, with `archived` GitHub link) or
`auth-required` (login-gated at the AG, catalogued with `source_url` only). It
powers the public `GET /api/ny-tos-reports` endpoint and the `/ny-tos` page.

A standalone **`ca_ab587_reports`** table (also flat) is the **California analogue
of `ny_tos_reports`** — **California's AB 587 Terms-of-Service reports**, the
semiannual filings social-media companies submit to the California Attorney
General (Bus. & Prof. Code §§ 22675-22681) on how their terms define and enforce
categories of content (the same five as NY's: hate speech, extremism,
disinformation, harassment, foreign political interference). Seeded from
`data/ca-ab587-reports.csv` via `build_ca_ab587_reports()` (`company`,
`platform`, `period`, `period_original`, `access`, `source_url`, `filename`,
`archived`, `sha256`, `bytes`). `access` is always `public`; unlike the 11 NY ToS
PDFs, the ~100 AB 587 PDFs (~300 MB) aren't mirrored in-repo, so `archived`/
`sha256`/`bytes` are blank and the catalogue points at `source_url` on
oag.ca.gov. `period` normalises the AG's own label (`Q3/Q4 2025` → `2025 H2`; the
earliest partial filings stay `2023 Q3`/`2023 Q4`), kept verbatim in
`period_original`. It powers the public `GET /api/ca-ab587-reports` endpoint and
the `/ca-ab587` page (memoise-and-filter-in-memory, like `/ny-tos`).

A third standalone **`google_traffic`** table (also flat) holds Google's
**Traffic & Disruptions catalogue** — one row per observed disruption of a
Google product in a country (government-ordered internet shutdowns, blocks and
outages), each with the news-source citation that documented it. A historical
dataset (Google froze it at 2009–2021). Seeded from `data/google-traffic.json`
via `build_google_traffic_db()` (`country`, `iso2`, `product`, `start_date`,
`end_date`, `year`, `source`, `source_url`, `title`, `excerpt`,
`disruption_url`; `start_date`/`year` are null for the two end-date-only rows).
Like `report_locations`, it's **not** a `TableSpec` query table — it powers the
memoised, read-only public `GET /api/traffic-disruptions` endpoint (filters:
`country`/`product`/`year`/`q`; `format=json|csv`) and the `/disruptions` page.

The **`ny_tos_stats`** table carries the **normalized NY ToS enforcement
statistics** — the figures extracted from those filings, with each company's
category labels mapped onto the Stop Hiding Hate Act's five categories
(`shha_category`; the filed text stays in `original_label`). Tidy-long, seeded
from `data/ny-tos-normalized.csv` via `build_ny_tos_stats()`, and registered as
a **queryable table** (`TableSpec`), so `/api/query`, `/api/explore` and
`/api/ask` all reach it. Only the category dimension is normalized —
`metric`/`submetric` keep each company's own measure names and are **not
comparable across companies**; `_leg_warnings` warns when a SUM/AVG over
`value` pins none of `unit` (count vs percent), `grain` (`category_total` vs
Strava's per-format `breakdown` — summing both double counts), or
`metric`/`submetric`. The `/ny-tos` page's "Enforcement statistics" panel reads
it via `POST /api/explore` at the category_total grain. Methodology + caveats:
the sibling repo's `ny-tos-reports/NORMALIZATION.md`.

The **`report_narratives`** table carries the **narrative full text** of the
report corpora — the *prose*, not the numbers — indexed for full-text search
(SQLite **FTS5**, `heading`/`text` tokenized `porter unicode61`; `source`/
`company`/`platform`/`period`/`page` UNINDEXED). Five `source`s ride in one table:
- **`ny-tos`** — one row per **page** of a NY ToS filing (how each platform
  defines/enforces hate speech / extremism / disinformation / harassment /
  foreign-interference), loaded by `seed.build_ny_tos_narratives` from
  `data/ny-tos-narratives.json` (extracted by the sibling repo's
  `ny-tos-reports/extract_narrative.py` from the publicly-archived PDFs).
- **`ca-ab587`** — one row per **page** of a California AB 587 filing (the same
  five content categories, filed with the California AG), loaded by
  `seed.build_ca_ab587_narratives` from `data/ca-ab587-narratives.json`
  (extracted by the sibling repo's `ca-ab587/extract_narrative.py` from the
  on-demand-fetched PDFs). Shares the page-based loader `_build_narratives` with
  `ny-tos`. No archived-PDF deep link (the PDFs aren't mirrored in-repo).
- **`ca-ab2013`** — Google's **California AB 2013** AI Training Data Transparency
  Summary (the *Generative AI: Training Data Transparency Act*, in force Jan 2026
  — how Google describes the datasets used to train its generative-AI products),
  loaded by `seed.build_ca_ab2013_narratives` from `data/ca-ab2013-narratives.json`
  (extracted by the sibling repo's `ca-ab2013/build_ca_ab2013_narratives.py`,
  which splits the single-page summary into four anchored sections). Also shares
  `_build_narratives`.
- **`dsa`** — one row per **DSA Table-11 qualitative description** (how each
  service describes its content-moderation approach, per indicator), derived at
  seed time by `seed.build_dsa_narratives` straight from the already-loaded
  `t11_qualitative` (VLOP + non-VLOP), skipping cells below a prose threshold.
  Runs **last** in `seed.main()`, after the harmonised append. No `page`.
- **`japan`** — one row per **section** of LY Corporation's **Media Transparency
  Report** (情プラ法 Art. 28 / qualitative context — how each of its five services
  describes its purpose, rules, response to violations, detection, plus the
  cross-service 共通編 sections), loaded by `seed.build_japan_narratives` from
  `data/japan-narratives.json` (extracted by the sibling repo's
  `japan-info-platform/build_japan_narratives.py`). The source report is
  **Japanese-only**, so each `text` is stored **bilingually** — a curated English
  translation followed by the Japanese original — so it's searchable in either
  language. English search is full (porter-stemmed); Japanese search is coarser
  (`unicode61` tokenizes a run between punctuation/spaces as one token, so it
  matches whole delimited runs like a bracketed 「利用のルール」). `page` is the PDF
  page the section starts on (a reference anchor; the PDF isn't mirrored in-repo,
  so no deep link).

It's **not** a `TableSpec` query table — it powers the public `GET /api/narratives`
full-text search endpoint (ranked by `bm25`, `snippet()`-highlighted, `q` +
`source`/`company`/`period` filters, source-scoped facets, IP-rate-limited) and
the `/narratives` page. The user query is compiled to a safe FTS5 MATCH
(`_fts_match`: keep only word tokens — ASCII **or CJK runs**, so Japanese queries
reach the `japan` corpus — quote each, so no user input reaches the FTS grammar
and a malformed `q` can't raise); matches are wrapped in private-use
sentinels the client HTML-escapes then swaps for `<mark>`, so raw report text
can't inject markup. `ny-tos` results deep-link into the archived PDF at the
matching page (`…pdf#page=N`, joined from `ny_tos_reports`); `dsa` results carry
the service + indicator as context.

## Query model

Requests are structured (see `QueryRequest`/`compile_query`/`TableSpec` in
`main.py`). A query **must name a `table`**; that table's `TableSpec` fixes the
FROM/joins and the registry of:

- **Dimensions** (text, `EQ`/`IN`): always `service_name`, `platform`; plus
  per-table `category_code`/`category_label`, `section`, `indicator`, `scope`,
  `surface`, or `qualitative_text` (t11); plus the derived `scope_is_total`/
  `category_is_total`/`surface_is_total` grain flags and the language-neutral
  `section_key`/`indicator_key`/`scope_key` canonical labels.
- **Measures** (numeric, `EQ`/`IN`/`GT`/`GTE`/`LT`/`LTE`): per-table count
  columns (e.g. t4 `notices`/`tf_notices`/…, t7–t10 `value`). t11 has none.
- **Aggregates**: `SUM`/`COUNT`/`AVG`/`MIN`/`MAX` over a measure, with an alias.
- `group_by`, `sort`, `max_count`, optional `callback_url` (webhook). `GET /tables`
  lists the tables; `GET /fields?table=…` and `GET /schema/{table}` document a
  table's fields.

`compile_query` is the single trust boundary — it resolves `req.table` to a
`TableSpec` and validates every field/operation against that table's registry.
Never build SQL by interpolating user values (always bind with `?`).

**Composite (cross-table) queries**: instead of `table`, a request may carry
`legs` (2–4 named single-table sub-queries, each validated against its own
`TableSpec`; ≤2 on public `/api/explore` via `EXPLORE_MAX_LEGS`), `join_on`
(merge keys — must be a dimension of every leg's table; each leg is implicitly
grouped by them), `derived` (four-function arithmetic over `leg.alias` refs,
parsed by `_compile_expr` into SQL with `NULLIF` division — never interpolated),
and `having` (the condition grammar over output columns). `_compile_composite`
emits one statement: leg CTEs + a `spine` CTE (UNION of leg keys → full-outer
semantics, unmatched keys kept with NULLs) + LEFT JOINs + an outer
having/sort/limit. `compile_query` dispatches on the presence of `legs`, so
every endpoint (query/explore/ask) gets composites through the same boundary.

## Key design decisions

- **Structured params, not SQL**: the only way to query is the validated
  parameter model, compiled to one parameterised SELECT — no caller SQL runs.
- **NL→query via LLM, same trust boundary** (`POST /api/ask`): an LLM (Claude;
  `ANTHROPIC_MODEL`, default `claude-opus-4-8`) translates a question into the
  *structured* `QueryRequest` using JSON-schema structured outputs — never SQL —
  which then goes through the exact same `compile_query` validation as everything
  else. The model only proposes; `compile_query` disposes (bad field → `422`).
  `_translate_question` is the single, lazily-imported, monkeypatchable seam (tests
  never call the API); off unless `ANTHROPIC_API_KEY` is set; IP-rate-limited.
  Before changing the LLM call, confirm the current model ID + Messages API schema
  (use the `claude-api` skill) — never hardcode a model ID from memory.
- **Researcher portal** (`/portal` + `POST /portal/register`): a demo onboarding
  UI. Registration mints a key into the **issued-key store** (`_key_store`:
  Redis-backed when configured, else in-memory — shares `_redis` with the job
  store), with an expiry (`ISSUED_KEY_TTL`) and per-IP/email rate limiting
  (`_key_store.incr`). `require_api_key` accepts configured keys *or* issued ones
  (`_lookup_principal`); `DELETE /portal/key` self-revokes. Still no real auth —
  production would front it with SSO.
- **202 + polling** instead of blocking HTTP: lets long queries run without
  tying up connections or timing out at proxies.
- **Signed download URLs**: a done job exposes `download_urls` (json/csv) —
  capability links carrying an HMAC-SHA256 of `job_id:format:expires`.
  `GET /jobs/{id}/download` verifies the signature (before any store lookup, so
  job existence isn't leaked) instead of an API key, so the URL alone authorises
  the download (presigned-URL style). Set `DOWNLOAD_URL_SECRET` in production so
  links survive restarts and span workers.
- **In-memory job registry** (`_jobs` dict + `threading.Lock`): simple for a
  demo; restart clears all jobs. Production would need persistent storage.
- **`sqlite3.interrupt()`** on `DELETE /jobs/{id}` while running: aborts the
  in-flight query without parsing SQL.
- **100k row cap + honest truncation**: results are capped at
  `min(max_count, ROW_LIMIT)`; the compiled SQL fetches one sentinel row past
  the cap so a cut result is flagged `truncated: true` on the job, the result
  body, and an `X-Result-Truncated` header (CSV too) — never silently short.
  Guardrail advisories also ride on CSV exports via `X-Query-Warnings`.
- **Per-key query rate limit**: `POST /query` is throttled per API key
  (`QUERY_RATE_MAX`/`QUERY_RATE_WINDOW`, default 60/60s) via `_key_store.incr` —
  the same counter primitive as portal registration. Over-limit → `429` +
  `Retry-After`, before a job is created.
- **Structured logging**: a dedicated `research_api` logger emits JSON lines
  (`JsonLogFormatter`, `LOG_FORMAT=json` default; `text` for humans). An HTTP
  middleware logs each request (method/path/status/`duration_ms`/`request_id`,
  echoed as `X-Request-ID`); the job runner logs `job_submitted`/`job_started`/
  `job_done`/`job_failed`. Pass fields via `extra={"data": {...}}`; never log keys.
- **Webhook callbacks**: an optional `callback_url` on `POST /query`. When the
  job reaches `done`/`failed`, `_dispatch_callback` POSTs the job object (with
  absolute links if `PUBLIC_BASE_URL` is set) to that URL on a **bounded callback
  thread pool** (`_callback_executor`, `CALLBACK_WORKERS`) — off the query
  workers — HMAC-signed (`X-Webhook-Signature`, same secret as download URLs),
  retried with backoff. SSRF-guarded: `_validate_callback_url` blocks non-http(s)
  and private/loopback/link-local/metadata targets, **unwrapping IPv4-mapped/6to4
  IPv6** so they can't smuggle a private v4; enforced at submit *and* before each
  send (narrows DNS rebinding — full closure needs network egress filtering);
  redirects aren't followed; the target must be **globally routable** (`not
  ip.is_global` is rejected, covering CGNAT and other non-private-but-non-public
  ranges). `CALLBACK_ALLOW_PRIVATE=1` bypasses for local dev.
- **Abuse hardening**: request bodies are capped via `Content-Length`
  (`MAX_BODY_BYTES`, default 1 MiB → `413`); query complexity is bounded in the
  Pydantic models (≤100 values per condition, ≤50 conditions per and/or/not
  clause, ≤50 fields/group_by/aggregates/sort entries) since `/api/explore`
  accepts the same model unauthenticated; CSV exports neutralise spreadsheet
  formula injection (`_csv_safe` prefixes text cells starting `=`/`+`/`-`/`@`
  with `'` — server-side and in the dashboard's `toCSV`); configured API keys
  are compared constant-time (`_configured_principal`).
- **Prometheus metrics** at `GET /metrics` (no auth): the same request middleware
  records `research_api_http_requests_total` + `_http_request_duration_seconds`,
  labelled by the **route template** (`/jobs/{job_id}`) to bound cardinality; the
  job runner tracks `research_api_jobs_in_flight`, `research_api_jobs_total{status}`, and
  `research_api_job_queue_depth` (inc'd on submit, dec'd when the worker picks the job
  up — no reliance on `ThreadPoolExecutor` internals).
- **Swagger UI** at `/docs` works out of the box — click Authorize and paste
  a key.
- **Browser hardening**: every response gets a set of hardening headers from the
  request middleware — `X-Content-Type-Options: nosniff`, `Referrer-Policy:
  no-referrer` (so the HMAC in a signed download URL never leaks via `Referer`),
  `X-Frame-Options: DENY`, `Permissions-Policy` (geolocation/camera/mic/payment
  off), and `Strict-Transport-Security` (HSTS). Every served HTML page gets a per-page
  **Content-Security-Policy** (`_serve_page`/`_page_csp`) — `script-src 'self'` +
  the page's inline-`<script>` **sha256 hash** (computed from the file, never
  stale); the dashboard needs no third-party script origin because **Chart.js is
  vendored same-origin** (`static/vendor/chart.umd.js`, served by the
  `/static/vendor/{filename}` route with a name allowlist + immutable caching),
  and the api-key page only allows `accounts.google.com` for Google sign-in. No
  `'unsafe-inline'` for scripts, `frame-ancestors 'none'`. DB values are
  HTML-escaped in the dashboard JS (`esc()`). If Chart.js is unavailable, the
  dashboard panels **fall back to data tables** instead of blank canvases
  (`chartReady()`/`miniTable()`).
- **Accessibility**: both HTML pages have a skip-link → `<main id="main">`
  landmark, a labelled `<nav>`, visible keyboard focus rings (`:focus-visible`),
  `role="alert"` live regions for errors, and `aria-busy`/loading states while
  data fetches. The chart `<canvas>` elements are `aria-hidden`; their data is
  exposed to assistive tech via an always-rendered table that is `.sr-only`
  (visually hidden) when the chart draws — so screen-reader users get the
  numbers either way. Honours `prefers-reduced-motion`.

## Code Review Workflow

**After opening or updating a pull request, always self-review the diff** and
post a comment summarising what you checked and any issues found + fixed (run
the tests/linters and note the result). Never leave a PR without a self-review.

Whenever a pull request is created or updated, **always check for Gemini
code-review comments** (`gemini-code-assist[bot]`) using the GitHub MCP tools:

1. Call `pull_request_read` with `method=get_reviews` to find the Gemini review summary.
2. Call `pull_request_read` with `method=get_review_comments` to get inline thread details.
3. Verify each finding against the actual source files before acting.
4. Apply confirmed fixes, commit, and push on the same branch.
5. **Always reply to every Gemini (GCA) comment** with `add_reply_to_pull_request_comment` —
   either describing the fix applied, or explaining why the suggestion isn't
   being taken. Never leave a GCA review comment unacknowledged.

## Endpoints

Combined-site layout: the **dashboard is served at `/`** and the JSON API lives
under **`/api/*`** on the same origin (no CORS). Operational endpoints
(`/healthz`, `/readyz`, `/metrics`, `/version`) and the `/schema` + `/api-key` pages stay at the
root. The API endpoints are registered on an `APIRouter` included with
`prefix=API_PREFIX` (`/api`); link builders (`status_url`/`result_url`/signed
`download_urls`/`Location`) are prefixed via `API_PREFIX`.

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/` | — | Public VLOP transparency dashboard (web UI) |
| GET | `/api/overview` | — | Public headline aggregates powering the dashboard |
| GET | `/api/report-locations` | — | Public: non-VLOP DSA report-locations catalogue (filters: `category`/`confidence`/`harmonised_template`/`q`; `format=json\|csv`) — memoised, read-only |
| GET | `/api/ny-tos-reports` | — | Public: New York Social Media ToS-reports catalogue (filters: `period`/`access`/`q`; `format=json\|csv`) — memoised, read-only |
| GET | `/api/ca-ab587-reports` | — | Public: California AB 587 ToS-reports catalogue (filters: `platform`/`period`/`q`; `format=json\|csv`) — memoised, read-only |
| GET | `/api/traffic-disruptions` | — | Public: Google Traffic & Disruptions catalogue (filters: `country`/`product`/`year`/`q`; `format=json\|csv`) — memoised, read-only |
| GET | `/api/narratives` | — | Public: full-text search over the report narratives — NY ToS + CA AB 587 filings, Google's CA AB 2013 AI-training summary, DSA Table-11 prose + LY Corp's bilingual Japan report (`q` + `source`/`company`/`period` filters) — SQLite FTS5, ranked, highlighted, IP-rate-limited |
| GET | `/api/explore/options` | — | Public: tables + dimensions/measures for the query builder |
| POST | `/api/explore` | — | Public: run a bounded structured query inline (row-capped, IP-rate-limited, ≤`EXPLORE_MAX_LEGS` composite legs) |
| POST | `/api/ask` | key | NL→query via an LLM (Claude) → structured `QueryRequest` → `compile_query`; requires an API key, IP-rate-limited; off unless `ANTHROPIC_API_KEY` set |
| GET | `/api` | — | API service info |
| GET | `/catalog` | — | Public report-locations catalogue page (web UI over `GET /api/report-locations`) |
| GET | `/ny-tos` | — | Public NY Terms-of-Service reports catalogue page (web UI over `GET /api/ny-tos-reports`) |
| GET | `/ca-ab587` | — | Public California AB 587 Terms-of-Service reports catalogue page (web UI over `GET /api/ca-ab587-reports`) |
| GET | `/india` | — | Public India IT Rules compliance-reports dataset page (web UI over `POST /api/explore`) |
| GET | `/korea` | — | Public Korea (Naver + Kakao) transparency dataset page (web UI over `POST /api/explore`) |
| GET | `/taiwan` | — | Public Taiwan Anti-Fraud Act dataset page (web UI over `POST /api/explore`) |
| GET | `/turkey` | — | Public Türkiye Law No. 5651 transparency-reports dataset page (web UI over `POST /api/explore`) |
| GET | `/cser` | — | Public Meta Community Standards Enforcement Report dataset page (web UI over `POST /api/explore`) |
| GET | `/singapore` | — | Public Singapore IMDA Online Safety dataset page (web UI over `POST /api/explore`; English-only, like `/mandates`) |
| GET | `/korea-network-act` | — | Public Korea Network Act illegal-sexual-content dataset page (web UI over `POST /api/explore`; English-only, like `/mandates`) |
| GET | `/japan` | — | Public Japan 情プラ法 (LY Corporation) dataset page (web UI over `POST /api/explore`) |
| GET | `/tiktok-cger` | — | Public TikTok Community Guidelines Enforcement Report dataset page (web UI over `POST /api/explore`) |
| GET | `/tco` | — | Public EU Terrorist Content Online Regulation dataset page (web UI over `POST /api/explore`; English-only, like `/mandates`) |
| GET | `/ai-training` | — | Public EU AI Act training-data transparency dataset page (web UI over `POST /api/explore`; English-only, like `/mandates`) |
| GET | `/regional` | — | Public regional content-moderation transparency-law dataset page (web UI over `POST /api/explore`; English-only, like `/mandates`) |
| GET | `/china` | — | Public China CIIRC (12377) online-report statistics dataset page (web UI over `POST /api/explore`; English-only, like `/mandates`) |
| GET | `/china-12321` | — | Public China 12321 telecom-spam report statistics dataset page (web UI over `POST /api/explore`; English-only, like `/mandates`) |
| GET | `/user-data` | — | Public Google user-data requests dataset page (web UI over `POST /api/explore`) |
| GET | `/microsoft` | — | Public Microsoft LERR dataset page (web UI over `POST /api/explore`) |
| GET | `/linkedin` | — | Public LinkedIn Government Requests dataset page (web UI over `POST /api/explore`) |
| GET | `/tiktok` | — | Public TikTok Government & Legal Requests dataset page (web UI over `POST /api/explore`) |
| GET | `/discord` | — | Public Discord Transparency Reports dataset page (web UI over `POST /api/explore`) |
| GET | `/disruptions` | — | Public Google Traffic & Disruptions catalogue page (web UI over `GET /api/traffic-disruptions`) |
| GET | `/android` | — | Public Android ecosystem security dataset page (web UI over `POST /api/explore`) |
| GET | `/dsa-db` | — | Public EU DSA Transparency Database (Statements of Reasons) dataset page (web UI over `POST /api/explore`; English-only, like `/china-12321`) |
| GET | `/narratives` | — | Public narrative full-text search page (web UI over `GET /api/narratives`; NY ToS + CA AB 587 + DSA prose) |
| GET | `/mcp` | — | Public MCP-server info page (web UI; documents `mcp_server.py`) |
| GET | `/methodology` | — | Public methodology page (web UI; how the dataset is sourced/processed/cited) |
| GET | `/schema` | — | Public dataset-schema browser (web UI; no sign-in) |
| GET | `/api-key` | — | API-key sign-in page (web UI: sign in → key). `/portal` 308-redirects here |
| POST | `/api/auth/google` | — | Verify a Google ID token → session key (any verified account) |
| POST | `/api/portal/register` | — | Demo: issue a key without auth (`ALLOW_DEMO_KEYS`) |
| DELETE | `/api/portal/key` | key | Revoke your own session / portal-issued key |
| GET | `/api/admin/registrations` | admin | List researcher registrations (`?status=`) |
| POST | `/api/admin/registrations/{email}/approve` | admin | Restore a revoked account |
| POST | `/api/admin/registrations/{email}/revoke` | admin | Revoke an account |
| GET | `/api/tables` | — | Public: list the DSA report tables + dataset period |
| GET | `/api/fields?table=…` | — | Public: fields + operations for a table (no arg → table overview) |
| GET | `/api/schema/{table}` | — | Public: field registry for a report table |
| POST | `/api/query` | key | Submit structured query — single-table or composite (optional `callback_url`) → 202 + job_id |
| GET | `/api/jobs` | key | List your jobs |
| GET | `/api/jobs/{id}` | key | Job status |
| GET | `/api/jobs/{id}/result?format=json\|csv` | key | Result (status=done only) |
| GET | `/api/jobs/{id}/download?format=…&expires=…&sig=…` | signed URL | Secure download, no key needed |
| DELETE | `/api/jobs/{id}` | key | Cancel or remove |
| GET | `/healthz` `/readyz` | — | Liveness / readiness probes (root) |
| GET | `/metrics` | — | Prometheus metrics |
| GET | `/version` | — | Deployed build (commit SHA via `APP_VERSION`); also the `X-Version` header |
