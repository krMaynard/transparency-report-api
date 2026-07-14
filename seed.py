"""Build demo.db from the aggregated EU DSA VLOP transparency dataset.

Default source: ../krMaynard.github.io/data/vlop-dsa.json
Override with --source <path> or the SEED_SOURCE_JSON env var.
Override output with --db <path> or the DB_PATH env var.

`vlop-dsa.json` is a compact interned format: shared lookup arrays (services,
service_platforms, categories, category_labels, sections, indicators, scopes,
surfaces) plus one fact array per DSA report table (t3–t11). Each fact row is a
list whose leading values are indices into the lookup arrays (= the row id in
the corresponding dimension table) and whose remaining values are the reported
measures. We expand it into a star schema: dimension tables + one fact table per
report table, queried independently via the API's `table` selector.
"""
import argparse
import json
import os
import sqlite3
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))

_DEFAULT_SOURCE = os.getenv(
    "SEED_SOURCE_JSON",
    os.path.normpath(os.path.join(HERE, "..", "krMaynard.github.io", "data", "vlop-dsa.json")),
)
_DEFAULT_GR_SOURCE = os.getenv(
    "SEED_GR_SOURCE_JSON",
    os.path.normpath(
        os.path.join(HERE, "..", "krMaynard.github.io", "data", "google-government-removals.json")
    ),
)
_DEFAULT_DB = os.getenv("DB_PATH", os.path.join(HERE, "demo.db"))
# Vendored in-repo catalogue (one row per non-VLOP report URL).
_DEFAULT_RL_SOURCE = os.getenv(
    "SEED_REPORT_LOCATIONS_CSV", os.path.join(HERE, "data", "report-locations.csv")
)
# Vendored in-repo catalogue of New York's Social Media Terms-of-Service reports
# (one row per filing; sibling dsa-transparency-data/ny_tos_reports.csv).
_DEFAULT_NY_TOS_SOURCE = os.getenv(
    "SEED_NY_TOS_CSV", os.path.join(HERE, "data", "ny-tos-reports.csv")
)
# Normalized NY ToS enforcement statistics (sibling
# dsa-transparency-data/ny-tos-reports/ny_tos_normalized.csv) — the extracted
# per-category figures mapped onto the Stop Hiding Hate Act's five categories.
_DEFAULT_NY_STATS_SOURCE = os.getenv(
    "SEED_NY_TOS_STATS_CSV", os.path.join(HERE, "data", "ny-tos-normalized.csv")
)
# Apple Transparency dataset — vendored in-repo (from the sibling data repo's
# apple-transparency/build_apple.py); not in krMaynard.github.io like gr/vlop.
_DEFAULT_APPLE_SOURCE = os.getenv(
    "SEED_APPLE_SOURCE_JSON", os.path.join(HERE, "data", "apple-transparency.json")
)
# GitHub Transparency dataset — vendored in-repo (from the sibling data repo's
# github-transparency/build_github.py).
_DEFAULT_GITHUB_SOURCE = os.getenv(
    "SEED_GITHUB_SOURCE_JSON", os.path.join(HERE, "data", "github-transparency.json")
)
# Snap Transparency dataset — vendored in-repo (from the sibling data repo's
# snap-transparency/build_snap.py).
_DEFAULT_SNAP_SOURCE = os.getenv(
    "SEED_SNAP_SOURCE_JSON", os.path.join(HERE, "data", "snap-transparency.json")
)
# India IT Rules 2021 monthly compliance reports — vendored in-repo (from the
# sibling data repo's india-it-rules/build_india.py).
_DEFAULT_INDIA_SOURCE = os.getenv(
    "SEED_INDIA_SOURCE_JSON", os.path.join(HERE, "data", "india-it-rules.json")
)
# Korea (Naver + Kakao) transparency reports — vendored in-repo (from the
# sibling data repo's korea-transparency/build_korea.py).
_DEFAULT_KOREA_SOURCE = os.getenv(
    "SEED_KOREA_SOURCE_JSON", os.path.join(HERE, "data", "korea-transparency.json")
)
# Taiwan Anti-Fraud Act dataset — vendored in-repo (from the sibling data
# repo's taiwan-anti-fraud/build_taiwan.py).
_DEFAULT_TAIWAN_SOURCE = os.getenv(
    "SEED_TAIWAN_SOURCE_JSON", os.path.join(HERE, "data", "taiwan-anti-fraud.json")
)
# Türkiye Law No. 5651 platform transparency reports — vendored in-repo (from the
# sibling data repo's turkey-law5651/build_turkey.py).
_DEFAULT_TURKEY_SOURCE = os.getenv(
    "SEED_TURKEY_SOURCE_JSON", os.path.join(HERE, "data", "turkey-law5651.json")
)
# EU Terrorist Content Online Regulation transparency reports (tco-regulation/
# build_tco.py).
_DEFAULT_TCO_SOURCE = os.getenv(
    "SEED_TCO_SOURCE_JSON", os.path.join(HERE, "data", "tco-regulation.json")
)
# EU AI Act training-data transparency summaries (ai-training-transparency/
# build_ai_training.py).
_DEFAULT_AI_TRAINING_SOURCE = os.getenv(
    "SEED_AI_TRAINING_SOURCE_JSON", os.path.join(HERE, "data", "ai-training-transparency.json")
)
# Regional content-moderation transparency-law reports (regional-transparency/
# build_regional.py) — Texas HB 20 + Austria KoPl-G YouTube reports.
_DEFAULT_REGIONAL_SOURCE = os.getenv(
    "SEED_REGIONAL_SOURCE_JSON", os.path.join(HERE, "data", "regional-transparency.json")
)
# China CIIRC (12377) monthly online-report handling statistics (china-ciirc/
# build_ciirc.py).
_DEFAULT_CIIRC_SOURCE = os.getenv(
    "SEED_CIIRC_SOURCE_JSON", os.path.join(HERE, "data", "china-ciirc.json")
)
# China 12321 telecom-spam report-handling statistics (china-12321/
# build_12321.py).
_DEFAULT_CHINA12321_SOURCE = os.getenv(
    "SEED_CHINA12321_SOURCE_JSON", os.path.join(HERE, "data", "china-12321.json")
)
# Meta Community Standards Enforcement Report — vendored in-repo (from the
# sibling data repo's meta-cser/build_cser.py).
_DEFAULT_CSER_SOURCE = os.getenv(
    "SEED_CSER_SOURCE_JSON", os.path.join(HERE, "data", "meta-cser.json")
)
# Singapore IMDA Online Safety reports — vendored in-repo (from the sibling
# data repo's singapore-online-safety/build_singapore.py).
_DEFAULT_SINGAPORE_SOURCE = os.getenv(
    "SEED_SINGAPORE_SOURCE_JSON",
    os.path.join(HERE, "data", "singapore-online-safety.json"),
)
# eSafety BOSE (Basic Online Safety Expectations) transparency findings —
# vendored in-repo (built by scripts/build_esafety_bose.py from the archived
# eSafety reports; no sibling-repo extractor, the figures are transcribed).
_DEFAULT_ESAFETY_SOURCE = os.getenv(
    "SEED_ESAFETY_SOURCE_JSON",
    os.path.join(HERE, "data", "esafety-bose.json"),
)
# Korea Network Act (illegal-sexual-content) transparency report — vendored
# in-repo (from the sibling data repo's korea-network-act/build_korea_network_act.py).
_DEFAULT_KOREA_NETWORK_ACT_SOURCE = os.getenv(
    "SEED_KOREA_NETWORK_ACT_SOURCE_JSON",
    os.path.join(HERE, "data", "korea-network-act.json"),
)
# Japan 情プラ法 (Information Distribution Platform Act) — vendored in-repo (from
# the sibling data repo's japan-info-platform/build_japan.py).
_DEFAULT_JAPAN_SOURCE = os.getenv(
    "SEED_JAPAN_SOURCE_JSON",
    os.path.join(HERE, "data", "japan-info-platform.json"),
)
# TikTok Community Guidelines Enforcement Report — vendored in-repo (from the
# sibling data repo's tiktok-cger/build_cger.py).
_DEFAULT_TIKTOK_CGER_SOURCE = os.getenv(
    "SEED_TIKTOK_CGER_SOURCE_JSON", os.path.join(HERE, "data", "tiktok-cger.json")
)
# Google government requests for user information — vendored in-repo (from the
# sibling data repo's google-user-data/build_userdata.py).
_DEFAULT_GOOGLE_UD_SOURCE = os.getenv(
    "SEED_GOOGLE_UD_SOURCE_JSON", os.path.join(HERE, "data", "google-user-data.json")
)
# Microsoft Law Enforcement Requests Report — vendored in-repo (from the
# sibling data repo's microsoft-lerr/build_microsoft.py).
_DEFAULT_MICROSOFT_SOURCE = os.getenv(
    "SEED_MICROSOFT_SOURCE_JSON", os.path.join(HERE, "data", "microsoft-lerr.json")
)
# LinkedIn Government Requests Report — vendored in-repo (from the sibling
# data repo's linkedin-transparency/build_linkedin.py).
_DEFAULT_LINKEDIN_SOURCE = os.getenv(
    "SEED_LINKEDIN_SOURCE_JSON", os.path.join(HERE, "data", "linkedin-transparency.json")
)
# TikTok Government & Legal Requests reports — vendored in-repo (from the
# sibling data repo's tiktok-transparency/build_tiktok.py).
_DEFAULT_TIKTOK_SOURCE = os.getenv(
    "SEED_TIKTOK_SOURCE_JSON", os.path.join(HERE, "data", "tiktok-transparency.json")
)
# Discord Transparency Reports — vendored in-repo (from the sibling data repo's
# discord-transparency/build_discord.py).
_DEFAULT_DISCORD_SOURCE = os.getenv(
    "SEED_DISCORD_SOURCE_JSON", os.path.join(HERE, "data", "discord-transparency.json")
)
# Google Traffic & Disruptions catalogue — vendored in-repo (from the sibling
# data repo's google-traffic/build_traffic.py).
_DEFAULT_TRAFFIC_SOURCE = os.getenv(
    "SEED_TRAFFIC_SOURCE_JSON", os.path.join(HERE, "data", "google-traffic.json")
)
# Google Android ecosystem security (PHA rates) — vendored in-repo (from the
# sibling data repo's android-security/build_android.py).
_DEFAULT_ANDROID_SOURCE = os.getenv(
    "SEED_ANDROID_SOURCE_JSON", os.path.join(HERE, "data", "android-security.json")
)
# EU DSA Transparency Database — Statements of Reasons (aggregated) — vendored
# in-repo (from the sibling data repo's dsa-tdb/build_dsa_tdb.py).
_DEFAULT_DSA_TDB_SOURCE = os.getenv(
    "SEED_DSA_TDB_SOURCE_JSON", os.path.join(HERE, "data", "dsa-tdb.json")
)
# NY ToS report narratives (full text) — vendored in-repo (from the sibling data
# repo's ny-tos-reports/extract_narrative.py).
_DEFAULT_NARRATIVES_SOURCE = os.getenv(
    "SEED_NARRATIVES_SOURCE_JSON", os.path.join(HERE, "data", "ny-tos-narratives.json")
)
# California AB 587 ToS reports — catalogue CSV + narrative full text, vendored
# in-repo (from the sibling data repo's ca-ab587/).
_DEFAULT_CA_AB587_SOURCE = os.getenv(
    "SEED_CA_AB587_CSV", os.path.join(HERE, "data", "ca-ab587-reports.csv")
)
_DEFAULT_CA_AB587_NARRATIVES_SOURCE = os.getenv(
    "SEED_CA_AB587_NARRATIVES_JSON", os.path.join(HERE, "data", "ca-ab587-narratives.json")
)
# Japan 情プラ法 — LY Corporation's Media Transparency Report prose, vendored
# in-repo (from the sibling data repo's japan-info-platform/build_japan_narratives.py).
# Bilingual (English translation + Japanese original) since the source is JA-only.
_DEFAULT_JAPAN_NARRATIVES_SOURCE = os.getenv(
    "SEED_JAPAN_NARRATIVES_JSON", os.path.join(HERE, "data", "japan-narratives.json")
)
# California AB 2013 — Google's AI Training Data Transparency Summary prose,
# vendored in-repo (from the sibling repo's ca-ab2013/build_ca_ab2013_narratives.py).
_DEFAULT_CA_AB2013_NARRATIVES_SOURCE = os.getenv(
    "SEED_CA_AB2013_NARRATIVES_JSON", os.path.join(HERE, "data", "ca-ab2013-narratives.json")
)


def _category_label(code: str, labels: dict[str, str] | None) -> str:
    """Human label for a category code.

    Use the dataset's explicit label when present; otherwise normalize the raw
    code (e.g. ``KEYWORD_OTHER_..._OR_DATA_VIOLATION``) into a readable label
    instead of surfacing the SCREAMING_SNAKE_CASE code in the UI — strip the
    namespace prefix, drop underscores, and sentence-case it.
    """
    explicit = labels.get(code) if labels else None
    if explicit:
        return explicit
    s = code
    for prefix in ("STATEMENT_CATEGORY_", "KEYWORD_"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    s = s.replace("_", " ").strip()
    return s.capitalize() if s else code


SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

-- Shared dimension tables. id = position in the source lookup array.
CREATE TABLE services   (id INTEGER PRIMARY KEY, name TEXT NOT NULL, platform TEXT NOT NULL);
CREATE TABLE categories (id INTEGER PRIMARY KEY, code TEXT NOT NULL, label TEXT NOT NULL, is_total INTEGER NOT NULL DEFAULT 0);
CREATE TABLE sections   (id INTEGER PRIMARY KEY, name TEXT NOT NULL, key TEXT NOT NULL DEFAULT '');
CREATE TABLE indicators (id INTEGER PRIMARY KEY, name TEXT NOT NULL, key TEXT NOT NULL DEFAULT '');
CREATE TABLE scopes     (id INTEGER PRIMARY KEY, name TEXT NOT NULL, is_total INTEGER NOT NULL DEFAULT 0, key TEXT NOT NULL DEFAULT '');
CREATE TABLE surfaces   (id INTEGER PRIMARY KEY, name TEXT NOT NULL, is_total INTEGER NOT NULL DEFAULT 0);

-- Report dimension: one row per submitted transparency report (one dataset = one report).
-- Supports multi-period ingestion when non-VLOP annual reports are added.
-- tier: vlop | vlose | vlop-vlose | online-platform | hosting | intermediary
CREATE TABLE reports (
    id           INTEGER PRIMARY KEY,
    period       TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end   TEXT NOT NULL,
    tier         TEXT NOT NULL DEFAULT 'vlop',
    generated    TEXT
);
CREATE INDEX idx_reports_period ON reports(period_start, period_end);

-- Table 3 — Member-State orders (Art. 9 & 10), by category × scope.
CREATE TABLE t3_member_state_orders (
    report_id INTEGER NOT NULL, service_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL, scope_id INTEGER NOT NULL,
    orders_to_act INTEGER, items INTEGER, orders_to_provide_info INTEGER
);

-- Table 4 — Notices (Art. 16), by category, with Trusted-Flagger breakdowns.
CREATE TABLE t4_notices (
    report_id INTEGER NOT NULL, service_id INTEGER NOT NULL, category_id INTEGER NOT NULL,
    notices INTEGER, tf_notices INTEGER, items INTEGER, tf_items INTEGER,
    median_time INTEGER, tf_median_time INTEGER,
    actions_law INTEGER, tf_actions_law INTEGER, actions_tos INTEGER, tf_actions_tos INTEGER
);

-- Table 5 — Own-initiative actions on illegal content, by category × restriction type.
CREATE TABLE t5_own_initiative_illegal (
    report_id INTEGER NOT NULL, service_id INTEGER NOT NULL, category_id INTEGER NOT NULL,
    measures INTEGER, automated INTEGER,
    vis_removal INTEGER, vis_disable INTEGER, vis_demoted INTEGER, vis_age_restricted INTEGER,
    vis_interaction_restricted INTEGER, vis_labelled INTEGER, vis_other INTEGER,
    monetary_suspension INTEGER, monetary_termination INTEGER, monetary_other INTEGER,
    service_suspension INTEGER, service_termination INTEGER,
    account_suspension INTEGER, account_termination INTEGER
);

-- Table 6 — Own-initiative actions on ToS violations (same shape as t5, + surface).
CREATE TABLE t6_own_initiative_tos (
    report_id INTEGER NOT NULL, service_id INTEGER NOT NULL, category_id INTEGER NOT NULL,
    measures INTEGER, automated INTEGER,
    vis_removal INTEGER, vis_disable INTEGER, vis_demoted INTEGER, vis_age_restricted INTEGER,
    vis_interaction_restricted INTEGER, vis_labelled INTEGER, vis_other INTEGER,
    monetary_suspension INTEGER, monetary_termination INTEGER, monetary_other INTEGER,
    service_suspension INTEGER, service_termination INTEGER,
    account_suspension INTEGER, account_termination INTEGER,
    surface_id INTEGER NOT NULL
);

-- Table 7 — Appeals & recidivism, by section × indicator × scope × surface.
CREATE TABLE t7_appeals_recidivism (
    report_id INTEGER NOT NULL, service_id INTEGER NOT NULL,
    section_id INTEGER NOT NULL, indicator_id INTEGER NOT NULL,
    scope_id INTEGER NOT NULL, value INTEGER, surface_id INTEGER NOT NULL
);

-- Table 8 — Use of automated means, by section × indicator × scope × surface.
CREATE TABLE t8_automated_means (
    report_id INTEGER NOT NULL, service_id INTEGER NOT NULL,
    section_id INTEGER NOT NULL, indicator_id INTEGER NOT NULL,
    scope_id INTEGER NOT NULL, value INTEGER, surface_id INTEGER NOT NULL
);

-- Table 9 — Human resources for content moderation, by section × indicator × scope.
CREATE TABLE t9_human_resources (
    report_id INTEGER NOT NULL, service_id INTEGER NOT NULL,
    section_id INTEGER NOT NULL, indicator_id INTEGER NOT NULL,
    scope_id INTEGER NOT NULL, value INTEGER
);

-- Table 10 — Average Monthly Active Recipients (AMAR), by scope.
CREATE TABLE t10_amar (
    report_id INTEGER NOT NULL, service_id INTEGER NOT NULL,
    scope_id INTEGER NOT NULL, value INTEGER
);

-- Table 11 — Qualitative description (free text), by indicator.
CREATE TABLE t11_qualitative (
    report_id INTEGER NOT NULL, service_id INTEGER NOT NULL,
    indicator_id INTEGER NOT NULL, value_text TEXT
);

CREATE INDEX idx_t3_service  ON t3_member_state_orders(service_id);
CREATE INDEX idx_t4_service  ON t4_notices(service_id);
CREATE INDEX idx_t5_service  ON t5_own_initiative_illegal(service_id);
CREATE INDEX idx_t6_service  ON t6_own_initiative_tos(service_id);
CREATE INDEX idx_t7_service  ON t7_appeals_recidivism(service_id);
CREATE INDEX idx_t8_service  ON t8_automated_means(service_id);
CREATE INDEX idx_t9_service  ON t9_human_resources(service_id);
CREATE INDEX idx_t10_service ON t10_amar(service_id);
CREATE INDEX idx_t11_service ON t11_qualitative(service_id);
CREATE INDEX idx_t3_report   ON t3_member_state_orders(report_id);
CREATE INDEX idx_t4_report   ON t4_notices(report_id);
CREATE INDEX idx_t5_report   ON t5_own_initiative_illegal(report_id);
CREATE INDEX idx_t6_report   ON t6_own_initiative_tos(report_id);
CREATE INDEX idx_t7_report   ON t7_appeals_recidivism(report_id);
CREATE INDEX idx_t8_report   ON t8_automated_means(report_id);
CREATE INDEX idx_t9_report   ON t9_human_resources(report_id);
CREATE INDEX idx_t10_report  ON t10_amar(report_id);
CREATE INDEX idx_t11_report  ON t11_qualitative(report_id);

-- Google Government Removal Requests (2011–2025)
CREATE TABLE gr_periods    (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE gr_countries  (id INTEGER PRIMARY KEY, code TEXT NOT NULL, name TEXT NOT NULL);
CREATE TABLE gr_requestors (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE gr_products   (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE gr_reasons    (id INTEGER PRIMARY KEY, name TEXT NOT NULL);

CREATE TABLE gr_removals (
    period_id       INTEGER NOT NULL,
    country_id      INTEGER NOT NULL,
    requestor_id    INTEGER NOT NULL,
    product_id      INTEGER NOT NULL,
    reason_id       INTEGER NOT NULL,
    num_requests    INTEGER,
    items_requested INTEGER,
    removed_legal   INTEGER,
    removed_policy  INTEGER,
    not_found       INTEGER,
    not_enough_info INTEGER,
    no_action       INTEGER,
    already_removed INTEGER
);

CREATE INDEX idx_gr_period  ON gr_removals(period_id);
CREATE INDEX idx_gr_country ON gr_removals(country_id);

-- Apple Transparency Report (government/private-party requests, App Store
-- takedowns), biannual since 2013 H1. Interned dims shared by both fact tables.
CREATE TABLE ap_periods       (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE ap_countries     (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE ap_request_types (id INTEGER PRIMARY KEY, name TEXT NOT NULL);

-- One row per (period, country, request_type). Heterogeneous per-type columns
-- are normalised onto this wide-sparse measure set; measures not reported for a
-- given request type are NULL. pct_data_provided is a percentage (avg, not sum).
CREATE TABLE apple_requests (
    period_id                    INTEGER NOT NULL,
    country_id                   INTEGER NOT NULL,
    request_type_id              INTEGER NOT NULL,
    requests_received            INTEGER,
    items_specified              INTEGER,
    requests_data_provided       INTEGER,
    pct_data_provided            REAL,
    requests_challenged_rejected INTEGER,
    requests_no_data             INTEGER,
    content_provided             INTEGER,
    noncontent_provided          INTEGER,
    accounts_preserved           INTEGER,
    accounts_restricted          INTEGER,
    accounts_deleted             INTEGER,
    requests_app_removed         INTEGER,
    apps_removed                 INTEGER,
    appeals_received             INTEGER,
    appeals_granted              INTEGER,
    apps_reinstated              INTEGER
);

-- US national-security & UK IPA requests are reported as banded ranges
-- (e.g. "0 - 249"), not exact counts, so they get low/high bounds, not measures.
CREATE TABLE apple_national_security (
    period_id     INTEGER NOT NULL,
    country_id    INTEGER NOT NULL,
    request_type  TEXT NOT NULL,
    requests_low  INTEGER,
    requests_high INTEGER,
    accounts_low  INTEGER,
    accounts_high INTEGER
);

CREATE INDEX idx_ap_period  ON apple_requests(period_id);
CREATE INDEX idx_ap_country ON apple_requests(country_id);

-- GitHub Transparency Report (open CC-BY CSVs): a heterogeneous set of small
-- metric series normalised onto one tidy-long fact table — one row per measured
-- value. count_low == count_high for exact counts; national-security letters and
-- EU-DSA MAU are banded ranges, so they carry distinct low/high bounds. Dims are
-- stored inline (the table is small, so no interned lookup tables).
CREATE TABLE github_metrics (
    year        INTEGER NOT NULL,
    period      TEXT NOT NULL,   -- sub-year label ('Jul-Dec', a month), else ''
    dataset     TEXT NOT NULL,   -- source series (government_takedowns_received, …)
    government  TEXT NOT NULL,   -- country (country-keyed series), else ''
    iso2        TEXT NOT NULL,   -- ISO-3166 alpha-2, else ''
    category    TEXT NOT NULL,   -- in-row breakdown (request/abuse/takedown type), else ''
    metric      TEXT NOT NULL,   -- count column when several are reported, else 'count'
    count_low   INTEGER,
    count_high  INTEGER
);
CREATE INDEX idx_gh_dataset ON github_metrics(dataset);

-- Snap (Snapchat) Transparency Report: Snap publishes its data already in a
-- tidy-long shape, so it maps onto one fact table — one row per measured value.
-- `value` is REAL (counts plus a few medians). Dims stored inline.
CREATE TABLE snap_metrics (
    period         TEXT NOT NULL,   -- e.g. '2024-H1'
    section        TEXT NOT NULL,   -- report section (Ads Moderation, Appeals, …)
    category       TEXT NOT NULL,   -- in-section breakdown (Country, Global, …)
    sub_category_1 TEXT NOT NULL,
    sub_category_2 TEXT NOT NULL,
    metric         TEXT NOT NULL,   -- the measured quantity
    value          REAL
);
CREATE INDEX idx_snap_section ON snap_metrics(section);

-- India IT Rules 2021 monthly compliance reports (india-it-rules/build_india.py).
-- Tidy-long: one row per measured value across publishers' monthly filings.
-- `value` is REAL because Meta's proactive figures are abbreviated approximations
-- and proactive rates are percentages (see `unit`). Dims stored inline.
CREATE TABLE india_metrics (
    platform TEXT NOT NULL,   -- Facebook/Instagram/Twitter/Moj/ShareChat/Roblox/Google/Pinterest/Meta
    period   TEXT NOT NULL,   -- covered month, 'YYYY-MM'
    section  TEXT NOT NULL,   -- content_actioned_proactive, grievances_received, …
    category TEXT NOT NULL,   -- policy area / complaint category / ban duration / ''
    metric   TEXT NOT NULL,   -- the measured quantity within the section
    unit     TEXT NOT NULL,   -- count / approx_count / percent
    value    REAL
);
CREATE INDEX idx_india_section ON india_metrics(section);

-- Korea (Naver + Kakao) transparency reports (korea-transparency/build_korea.py).
-- Tidy-long: one row per measured value from the half-yearly government
-- data-request reports. `value` is REAL because Naver also reports compliance
-- rates (percent) and accounts-per-request averages (see `unit`). Dims inline.
CREATE TABLE korea_metrics (
    platform TEXT NOT NULL,   -- Naver / Kakao (reporting company)
    service  TEXT NOT NULL,   -- Kakao splits by corp (Daum/Kakao); Naver = ''
    period   TEXT NOT NULL,   -- half-year, 'YYYY-H1' / 'YYYY-H2'
    category TEXT NOT NULL,   -- comm_user_information / comm_confirmation_data /
                              -- comm_restriction / seizure_warrant
    metric   TEXT NOT NULL,   -- requests / processed / accounts / processed_rate /
                              -- accounts_per_processed
    unit     TEXT NOT NULL,   -- count / percent / average
    value    REAL
);
CREATE INDEX idx_korea_category ON korea_metrics(category);

-- Taiwan Anti-Fraud Act data (taiwan-anti-fraud/build_taiwan.py). Tidy-long:
-- currently the NPA Art. 42 DNS-blocklist aggregate (sites blocked per month x
-- site-category); publisher-keyed so the designated platforms' statutory
-- transparency reports (Google/Meta/LINE/TikTok) slot in later. Dims inline.
CREATE TABLE taiwan_metrics (
    publisher TEXT NOT NULL,  -- NPA-165 (government stream); platforms later
    period    TEXT NOT NULL,  -- Gregorian month, 'YYYY-MM'
    section   TEXT NOT NULL,  -- dns_blocked_sites (per-publisher sections later)
    category  TEXT NOT NULL,  -- official 網站性質 site-category label (Chinese)
    metric    TEXT NOT NULL,  -- sites_blocked
    unit      TEXT NOT NULL,  -- count
    value     REAL
);
CREATE INDEX idx_taiwan_section ON taiwan_metrics(section);

-- Türkiye Law No. 5651 platform transparency reports (turkey-law5651/
-- build_turkey.py). Tidy-long: one row per measured value from the platforms'
-- six-monthly Law 5651 reports (Meta Facebook/Instagram + X/Twitter). Two
-- request streams (section): individual applications (Art. 9/9-A) and judicial
-- & administrative authorities (Art. 8/8-A). X reports the individual stream
-- broken down by issue `category` (blank for Meta's report-level totals) with a
-- request volume + an action_rate percent. Dims inline.
CREATE TABLE turkey_metrics (
    platform TEXT NOT NULL,     -- reporting service: Facebook / Instagram / X
    period   TEXT NOT NULL,     -- reporting half-year, 'YYYY HN'
    section  TEXT NOT NULL,     -- individual_requests / authority_requests
    category TEXT NOT NULL,     -- X issue label (Abuse/...); '' for Meta totals
    metric   TEXT NOT NULL,     -- applications_received, requests_icta, requests, action_rate, ...
    unit     TEXT NOT NULL,     -- count / percent
    value    REAL               -- REAL: X action_rate is a percentage
);
CREATE INDEX idx_turkey_section ON turkey_metrics(section);

-- EU Terrorist Content Online Regulation (2021/784) transparency reports
-- (tco-regulation/build_tco.py). Tidy-long: one row per measured value across the
-- two reporting streams (`role`): 'authority' (Art. 8 / Commission — per-Member-
-- State removal orders issued + national authority activity) and 'platform'
-- (Art. 7 — each hosting provider's enforcement figures). `category` is the row's
-- sub-dimension: a Member State (authority) or a sub-service (platform). Dims inline.
CREATE TABLE tco_metrics (
    publisher TEXT NOT NULL,    -- reporting body: European Commission / a MS authority / a platform
    role      TEXT NOT NULL,    -- authority / platform
    period    TEXT NOT NULL,    -- reporting window ('YYYY' or 'YYYY-MM..YYYY-MM')
    section   TEXT NOT NULL,    -- removal_orders_issued / authority_activity / platform_enforcement
    category  TEXT NOT NULL,    -- Member State (authority) or sub-service (platform)
    metric    TEXT NOT NULL,    -- removal_orders_issued, content_removed_via_orders, appeals_received, ...
    unit      TEXT NOT NULL,    -- count / approx_count
    value     REAL
);
CREATE INDEX idx_tco_role ON tco_metrics(role);

-- EU AI Act (Reg. 2024/1689) Art. 53(1)(d) training-data transparency summaries
-- (ai-training-transparency/build_ai_training.py). Tidy-long: one row per
-- disclosed field of a GPAI provider's public training-content summary. `section`
-- is 'modality' (field = Text/Image/Audio/Video/Other; value = banded size;
-- size_rank 1/2/3, 0 = not applicable), 'general' (data_cutoff/ongoing_collection)
-- or 'data_source' (publicly_available/commercially_licensed/…; value Yes/No).
CREATE TABLE ai_training_metrics (
    provider  TEXT NOT NULL,    -- GPAI provider: Google / Microsoft / …
    model     TEXT NOT NULL,    -- versioned model (family) name
    released  TEXT,             -- model release / market-placement date (as disclosed)
    section   TEXT NOT NULL,    -- modality / general / data_source
    field     TEXT NOT NULL,    -- Text/Image/…/data_cutoff/publicly_available/…
    value     TEXT,             -- the disclosed value (size band / date / Yes/No)
    size_rank INTEGER           -- 1/2/3 band rank for modality sizes (0 = n/a), else NULL
);
CREATE INDEX idx_ai_training_model ON ai_training_metrics(model);

-- Regional content-moderation transparency-law reports (regional-transparency/
-- build_regional.py). YouTube reports filed under Texas HB 20 (§120.053) and
-- Austria's KoPl-G. Tidy-long: one row per measured value, by jurisdiction ×
-- period × section × category × metric. Metric scope is each report's own.
CREATE TABLE regional_metrics (
    jurisdiction TEXT NOT NULL,  -- 'Texas (HB 20)' / 'Austria (KoPl-G)'
    platform     TEXT NOT NULL,  -- YouTube
    period       TEXT NOT NULL,  -- reporting half-year ('YYYY-Hn')
    section      TEXT NOT NULL,  -- monetization / enforcement / removals_by_reason / complaints / …
    category     TEXT NOT NULL,  -- reason / country / flagger type / detection source ('' where none)
    metric       TEXT NOT NULL,  -- videos_removed / demonetizations / appeals / reported_items / …
    unit         TEXT NOT NULL,  -- count
    value        REAL
);
CREATE INDEX idx_regional_jurisdiction ON regional_metrics(jurisdiction);

-- China CIIRC / 12377 online-report handling statistics (china-ciirc/
-- build_ciirc.py). The CAC reporting center's monthly bulletin on reports of
-- illegal/harmful online information handled, by receiving body. Tidy-long: one
-- row per measured value, by period × category (receiving body).
CREATE TABLE ciirc_metrics (
    publisher TEXT NOT NULL,     -- CAC-CIIRC
    period    TEXT NOT NULL,     -- 'YYYY-MM'
    section   TEXT NOT NULL,     -- reports_received
    category  TEXT NOT NULL,     -- national_total / central_center / local_departments / platforms / commercial_platforms
    metric    TEXT NOT NULL,     -- reports_received
    unit      TEXT NOT NULL,     -- count (万 × 10,000)
    value     REAL
);
CREATE INDEX idx_ciirc_period ON ciirc_metrics(period);

-- China 12321 telecom-spam report-handling statistics (china-12321/
-- build_12321.py). The 12321 Internet Bad & Spam Information Reporting Center
-- (Internet Society of China / MIIT) monthly bulletins on public reports of
-- telecom/internet nuisance & spam received, by category. Tidy-long: one row per
-- measured value, by period × category. Discontinued after Feb 2019.
CREATE TABLE china12321_metrics (
    publisher TEXT NOT NULL,     -- 12321-ISC
    period    TEXT NOT NULL,     -- 'YYYY-MM' (or 'YYYY-MM..YYYY-MM' combined-month)
    section   TEXT NOT NULL,     -- reports_received
    category  TEXT NOT NULL,     -- app / sms / sms_spam / sms_illegal / harassment_calls / bad_websites / fraud_comms / spam_email
    metric    TEXT NOT NULL,     -- reports_received
    unit      TEXT NOT NULL,     -- count (2016 exact) / approx_count (万-rounded, 2017+)
    value     REAL
);
CREATE INDEX idx_china12321_period ON china12321_metrics(period);

-- Meta Community Standards Enforcement Report (meta-cser/build_cser.py). Meta's
-- voluntary quarterly content-moderation report, Facebook + Instagram, 2017 Q4
-- onward. Tidy-long: one row per measured value. `policy_area` 'Cross-Policy
-- Data' is an across-policy aggregate (not a peer of the individual areas);
-- `unit` is count or percent (prevalence/proactive-rate/precision are rates).
CREATE TABLE cser_metrics (
    app         TEXT NOT NULL,  -- Facebook / Instagram
    policy_area TEXT NOT NULL,  -- violation type; 'Cross-Policy Data' = aggregate
    metric      TEXT NOT NULL,  -- Content Actioned, Prevalence, Proactive rate, ...
    period      TEXT NOT NULL,  -- reporting quarter, 'YYYY Qn'
    unit        TEXT NOT NULL,  -- count / percent
    value       REAL
);
CREATE INDEX idx_cser_policy ON cser_metrics(policy_area);

-- Singapore IMDA Online Safety reports (singapore-online-safety/
-- build_singapore.py). Tidy-long: one row per measured value from the six
-- Designated Social Media Services' annual reports + IMDA's Online Safety
-- Assessment Reports. Two streams (section): `assessment` (IMDA's normalized
-- Mystery-Shopper benchmark — action_rate + time_to_action per service × round)
-- and `platform_report` (each service's own Singapore harm-category figures).
-- Dims inline.
CREATE TABLE singapore_metrics (
    service  TEXT NOT NULL,     -- Facebook / Instagram / TikTok / X / YouTube / HardwareZone
    period   TEXT NOT NULL,     -- coverage window 'YYYY-MM..YYYY-MM'
    section  TEXT NOT NULL,     -- assessment / platform_report
    category TEXT NOT NULL,     -- harm/reason label; '' for assessment metrics
    metric   TEXT NOT NULL,     -- action_rate, time_to_action, content_actioned_sg, ...
    unit     TEXT NOT NULL,     -- percent / days / hours / count
    value    REAL
);
CREATE INDEX idx_singapore_section ON singapore_metrics(section);

-- eSafety BOSE (Basic Online Safety Expectations) transparency findings
-- (scripts/build_esafety_bose.py). Australia's eSafety Commissioner publishes
-- findings from the mandatory transparency notices it issues under the Online
-- Safety Act 2021. Tidy-long: one row per measured value. Two streams
-- (section): `csea_periodic` (the CSEA & sexual-extortion periodic report —
-- user reports of CSEA per service, global, + median human-moderator response
-- time in minutes; reporting period 15 Jun–15 Dec 2024) and the AI-companion
-- non-periodic findings (`ai_companion_reports` per-provider user reports by
-- harm, `ai_companion_staff` trust-&-safety headcount, `survey_prevalence`
-- eSafety's 2026 child-usage survey). Dims inline.
CREATE TABLE esafety_bose_metrics (
    service  TEXT NOT NULL,     -- platform/provider, or an aggregate/total label
    period   TEXT NOT NULL,     -- reporting window 'YYYY-MM-DD..YYYY-MM-DD' or 'YYYY'
    section  TEXT NOT NULL,     -- csea_periodic / ai_companion_reports / ai_companion_staff / survey_prevalence
    category TEXT NOT NULL,     -- harm/reason label; '' where not applicable
    metric   TEXT NOT NULL,     -- user_reports_global, median_response_minutes, user_reports, ...
    unit     TEXT NOT NULL,     -- count / minutes / percent
    value    REAL
);
CREATE INDEX idx_esafety_section ON esafety_bose_metrics(section);

-- Korea Network Act (illegal-sexual-content) transparency report
-- (korea-network-act/build_korea_network_act.py). Tidy-long: Google's annual
-- reports (2020–2025) under Network Act Art. 64-5 / Telecommunications Business
-- Act Art. 22-5 (illegal sexual content on Search + YouTube). 2024/2025 publish
-- a monthly Jan–Dec breakdown in four cross-cut sections (period 'YYYY-MM');
-- 2020–2023 (prose-only) + a rollup live in 'annual_summary' (period 'YYYY').
-- Pin a section before aggregating. Dims inline.
CREATE TABLE korea_network_act_metrics (
    publisher TEXT NOT NULL,    -- Google (Search + YouTube, jointly)
    period    TEXT NOT NULL,    -- month 'YYYY-MM' (detailed) or year 'YYYY' (annual_summary)
    section   TEXT NOT NULL,    -- requests_received / request_reasons / processed_result / removal_reasons / annual_summary
    category  TEXT NOT NULL,    -- complainant / reason / outcome label; 'All' for annual_summary
    metric    TEXT NOT NULL,    -- requests / urls / urls_removed / urls_received
    unit      TEXT NOT NULL,    -- count
    value     REAL
);
CREATE INDEX idx_korea_net_act_section ON korea_network_act_metrics(section);

-- Japan 情プラ法 (Information Distribution Platform Act) — the Art. 28
-- implementation statistics MIC-designated providers publish
-- (japan-info-platform/build_japan.py). Two providers so far: LY Corporation
-- (Media Transparency Report — posts/removals per service × FY2024 quarter, in
-- section 'posts_activity') and Google/YouTube (Japan IP Act report, 2025-07-26..
-- 2026-03-31 — legal/policy actions by reason across sections legal_requests /
-- legal_items / legal_removals / user_flags / policy_removals /
-- policy_detection_source / suspensions / appeals / platform, category = reason
-- or 'Total'). Tidy-long: one row per measured value. Dims inline.
CREATE TABLE japan_metrics (
    service  TEXT NOT NULL,     -- Yahoo! Chiebukuro / LINE OpenChat / YouTube / Facebook / ...
    period   TEXT NOT NULL,     -- coverage window 'YYYY-MM..YYYY-MM'
    section  TEXT NOT NULL,     -- posts_activity / legal_removals / content_actions / appeals / ...
    category TEXT NOT NULL,     -- reason label; 'All', or 'Total' (section aggregate)
    metric   TEXT NOT NULL,     -- posts / videos_removed / flags / actions / requests / ...
    unit     TEXT NOT NULL,     -- count / approx_count / percent
    value    REAL
);
CREATE INDEX idx_japan_service ON japan_metrics(service);
CREATE INDEX idx_japan_section ON japan_metrics(section);

-- TikTok Community Guidelines Enforcement Report (tiktok-cger/build_cger.py).
-- TikTok's voluntary quarterly content-moderation report, 2020 Q3 onward, the
-- Global cut. Tidy-long: one row per measured value. policy_type/issue and
-- task_type/task each carry an 'All' total beside the breakdown; `unit` is
-- count or rate (rates are fractions of 1 — never SUM).
CREATE TABLE tiktok_cger_metrics (
    period      TEXT NOT NULL,  -- reporting quarter, 'YYYY Qn'
    metric      TEXT NOT NULL,  -- Total videos removed, Proactive removal rate, ...
    policy_type TEXT NOT NULL,  -- All / Policy / Sub-policy / Ban reason...
    issue       TEXT NOT NULL,  -- community-guideline value; 'All' = top-level
    task_type   TEXT NOT NULL,  -- All / moderation-system / turnaround / view-band grouping
    task        TEXT NOT NULL,  -- All / Automation / Human moderation / bucket
    unit        TEXT NOT NULL,  -- count / rate
    value       REAL
);
CREATE INDEX idx_tiktok_cger_metric ON tiktok_cger_metrics(metric);

-- Google government requests for user information (google-user-data/
-- build_userdata.py). Tidy-long: one row per measured value from the biannual
-- bulk-CSV export (2009-H2 onward). Exact figures have value_low == value_high;
-- the US national-security datasets (FISA/NSL) are banded ranges
-- (value_low != value_high, non-additive). 2012-H2..2014-H1 report an 'All'
-- legal_process aggregate ALONGSIDE the per-process split — pin legal_process
-- before summing. Dims inline.
CREATE TABLE google_userdata_metrics (
    dataset           TEXT NOT NULL,  -- global / global_diplomatic / enterprise /
                                      -- enterprise_diplomatic / us_fisa_content /
                                      -- us_fisa_non_content / us_nsl
    period            TEXT NOT NULL,  -- half-year the window ends in, 'YYYY-H1/H2'
    country           TEXT NOT NULL,  -- requesting country (origin for diplomatic)
    iso2              TEXT NOT NULL,  -- CLDR territory code ('' when unlisted)
    product           TEXT NOT NULL,  -- GCP / Google Workspace / GSUITE ('' = all)
    legal_process     TEXT NOT NULL,  -- All / Subpoenas / Search Warrants / ...
    assisting_country TEXT NOT NULL,  -- diplomatic datasets only ('' elsewhere)
    metric            TEXT NOT NULL,  -- requests / accounts / customers / pct_disclosed
    unit              TEXT NOT NULL,  -- count / percent
    value_low         REAL,
    value_high        REAL
);
CREATE INDEX idx_google_ud_dataset ON google_userdata_metrics(dataset);

-- Microsoft Law Enforcement Requests Report (microsoft-lerr/build_microsoft.py).
-- Tidy-long: one row per measured value from the per-half-year workbooks
-- (2013-H1 onward). The report split changes across eras (combined 2013-2016;
-- criminal/emergencies from 2017; civil from 2017-H1) — pin a section before
-- aggregating, and never sum sections with 'combined' (skype overlaps combined
-- in 2013). Dims inline.
CREATE TABLE microsoft_metrics (
    period  TEXT NOT NULL,   -- half-year, 'YYYY-H1' / 'YYYY-H2'
    section TEXT NOT NULL,   -- combined / skype / criminal / emergencies / civil
    country TEXT NOT NULL,
    metric  TEXT NOT NULL,   -- requests / accounts_specified / disclosed_content /
                             -- disclosed_noncontent / no_data_found / rejected
    unit    TEXT NOT NULL,   -- count
    value   REAL
);
CREATE INDEX idx_microsoft_section ON microsoft_metrics(section);

-- LinkedIn Government Requests Report (linkedin-transparency/build_linkedin.py).
-- Tidy-long: one row per measured value scraped from the server-rendered
-- report page. Exact figures have value_low == value_high; the US
-- national-security rows are banded ranges (non-additive). The us_breakdown
-- legal-process rows (pct_*) are percentages of requests, not counts. Dims
-- inline.
CREATE TABLE linkedin_metrics (
    dataset    TEXT NOT NULL,  -- member_data_requests / us_breakdown /
                               -- content_removal_requests
    period     TEXT NOT NULL,  -- half-year, 'YYYY-H1' / 'YYYY-H2'
    country    TEXT NOT NULL,
    metric     TEXT NOT NULL,  -- requests / accounts_subject / pct_disclosed / ...
    unit       TEXT NOT NULL,  -- count / percent
    value_low  REAL,
    value_high REAL
);
CREATE INDEX idx_linkedin_dataset ON linkedin_metrics(dataset);

-- TikTok Government & Legal Requests reports (tiktok-transparency/build_tiktok.py).
-- Tidy-long: one row per measured value from the cumulative CLIGR CSVs. Three
-- datasets (government_removals / information_requests / ip_removals) by
-- country × half-year, 2019-H1 onward. `value` is REAL: exact integer counts
-- (unit='count') and rate/percentage rows carried as fractions of 1
-- (unit='percent', non-additive). The global 'All' country row sits alongside
-- the per-country rows (pin country before aggregating). Dims inline.
CREATE TABLE tiktok_metrics (
    dataset  TEXT NOT NULL,   -- government_removals / information_requests /
                              -- ip_removals
    period   TEXT NOT NULL,   -- half-year, 'YYYY-H1' / 'YYYY-H2'
    country  TEXT NOT NULL,   -- market name, or 'All' (global aggregate)
    metric   TEXT NOT NULL,   -- total_requests_received / legal_requests / ...
    unit     TEXT NOT NULL,   -- count / percent
    value    REAL
);
CREATE INDEX idx_tiktok_dataset ON tiktok_metrics(dataset);

-- Discord Transparency Reports (discord-transparency/build_discord.py).
-- Tidy-long: one row per measured value walked from the per-period report CSV's
-- labelled sub-tables. Trust & Safety enforcement + government/legal requests,
-- by section × category × metric × period ('YYYY-Qn' 2022-2023, 'YYYY-Hn'
-- 2024+). `value` is REAL: exact counts (unit='count') and appeal/report rates
-- as the reported percentage number (unit='percent', non-additive). Section
-- labels evolve across eras (Discord's own renaming). Dims inline.
CREATE TABLE discord_metrics (
    period    TEXT NOT NULL,  -- 'YYYY-Qn' (2022-2023) / 'YYYY-Hn' (2024+)
    section   TEXT NOT NULL,  -- accounts_disabled / appeals / us_gov_info_requests / ...
    category  TEXT NOT NULL,  -- policy category, country, request type, or month
    metric    TEXT NOT NULL,  -- individual_accounts / requests / pct_of_appeals_granted / ...
    unit      TEXT NOT NULL,  -- count / percent
    value     REAL
);
CREATE INDEX idx_discord_section ON discord_metrics(section);

-- Google Android ecosystem security — Potentially Harmful Application (PHA)
-- rates (android-security/build_android.py). Tidy-long: one row per measured
-- value across five cuts (`section`). `period` is a YYYY-MM-DD date (12-month
-- rolling end date for the rolling cuts; quarter end date for the quarterly
-- cuts). `value` is REAL: a PHA rate (unit='rate', a fraction of 1 — never SUM)
-- or the by-category share (unit='percent', sums to ~100/quarter). Dims inline.
CREATE TABLE android_metrics (
    section   TEXT NOT NULL,  -- devices_with_pha / devices_by_version / installs / installs_by_country / installs_by_category
    period    TEXT NOT NULL,  -- YYYY-MM-DD (rolling end date / quarter end date)
    category  TEXT NOT NULL,  -- market type, Android version, source, country ISO-2, or PHA category
    metric    TEXT NOT NULL,  -- pha_rate / category_share
    unit      TEXT NOT NULL,  -- rate / percent
    value     REAL
);
CREATE INDEX idx_android_section ON android_metrics(section);

-- EU DSA Transparency Database — Statements of Reasons (dsa-tdb/build_dsa_tdb.py).
-- Every content-moderation decision an in-scope platform takes under the DSA is
-- filed as an individual Statement of Reasons (SoR). The raw DB is ~4 TB, so this
-- is a compact RE-AGGREGATION of the Commission's own pre-made monthly aggregates
-- (via the `dsa-tdb` toolbox). Tidy-long: one row per SoR count, platform × month
-- × one dimension. `value` counts can reach ~1.5 billion/month (product delistings).
CREATE TABLE dsa_tdb_metrics (
    section  TEXT NOT NULL,     -- totals / by_category / by_decision_ground / by_automated_detection / by_automated_decision / by_source_type / by_decision_visibility
    platform TEXT NOT NULL,     -- reporting platform (top 60 by volume)
    period   TEXT NOT NULL,     -- SoR created_at month, 'YYYY-MM'
    category TEXT NOT NULL,     -- the dimension value for the section ('All' for totals)
    metric   TEXT NOT NULL,     -- always 'statements'
    unit     TEXT NOT NULL,     -- always 'count'
    value    INTEGER
);
CREATE INDEX idx_dsatdb_section  ON dsa_tdb_metrics(section);
CREATE INDEX idx_dsatdb_platform ON dsa_tdb_metrics(platform);

-- Non-VLOP DSA report-location catalogue: where other online platforms publish
-- their Art. 15/24 transparency reports. One row per report URL.
CREATE TABLE report_locations (
    id                  INTEGER PRIMARY KEY,
    platform            TEXT NOT NULL,
    company             TEXT,
    category            TEXT NOT NULL,
    confidence          TEXT NOT NULL,
    harmonised_template TEXT,
    format_period       TEXT,
    url_label           TEXT,
    url                 TEXT NOT NULL,
    archived            TEXT
);
CREATE INDEX idx_rl_category   ON report_locations(category);
CREATE INDEX idx_rl_confidence ON report_locations(confidence);

-- Google Traffic & Disruptions catalogue (google-traffic/build_traffic.py):
-- one row per observed disruption of a Google product in a country (government
-- internet shutdowns / blocks / outages), with the news-source citation. A flat
-- catalogue like report_locations, not part of the DSA star schema. Historical
-- (Google froze it at 2021); `year` is null for two end-date-only rows.
CREATE TABLE google_traffic (
    id             INTEGER PRIMARY KEY,
    country        TEXT NOT NULL,
    iso2           TEXT,
    product        TEXT NOT NULL,
    start_date     TEXT,
    end_date       TEXT,
    year           TEXT,
    source         TEXT,
    source_url     TEXT,
    title          TEXT,
    excerpt        TEXT,
    disruption_url TEXT
);
CREATE INDEX idx_gt_country ON google_traffic(country);
CREATE INDEX idx_gt_product ON google_traffic(product);
CREATE INDEX idx_gt_year    ON google_traffic(year);

-- New York's Social Media Terms-of-Service reports (Stop Hiding Hate Act): one
-- row per filing the AG publishes. A flat catalogue like report_locations, not
-- part of the DSA star schema. `access` is public|auth-required; `archived` is a
-- GitHub URL to the mirrored PDF when access=public.
CREATE TABLE ny_tos_reports (
    id           INTEGER PRIMARY KEY,
    company      TEXT NOT NULL,
    platform     TEXT,
    period       TEXT NOT NULL,
    upload_date  TEXT,
    access       TEXT NOT NULL,
    source_url   TEXT NOT NULL,
    filename     TEXT,
    archived     TEXT,
    sha256       TEXT,
    bytes        INTEGER
);
CREATE INDEX idx_ny_period ON ny_tos_reports(period);
CREATE INDEX idx_ny_access ON ny_tos_reports(access);

-- California's AB 587 Terms-of-Service reports: one row per filing the California
-- Attorney General publishes. The California analogue of ny_tos_reports (same
-- content categories, a US-state AG repository), also a flat catalogue. `archived`
-- is a GitHub URL to the mirrored PDF; `period_original` keeps the AG's own label.
CREATE TABLE ca_ab587_reports (
    id              INTEGER PRIMARY KEY,
    company         TEXT NOT NULL,
    platform        TEXT,
    period          TEXT NOT NULL,
    period_original TEXT,
    access          TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    filename        TEXT,
    archived        TEXT,
    sha256          TEXT,
    bytes           INTEGER
);
CREATE INDEX idx_ab587_period   ON ca_ab587_reports(period);
CREATE INDEX idx_ab587_platform ON ca_ab587_reports(platform);

-- Normalized NY ToS enforcement statistics: the per-category figures extracted
-- from the archived filings, mapped onto the Stop Hiding Hate Act's five
-- categories (sibling ny-tos-reports/NORMALIZATION.md documents the mapping and
-- its caveats). Tidy-long: one row per numeric cell; `metric`/`submetric` keep
-- each company's own measure names (NOT comparable across companies), `unit` is
-- count|percent, `grain` is category_total|breakdown (summing both double
-- counts Strava's format breakdowns with their own totals).
CREATE TABLE ny_tos_stats (
    company        TEXT NOT NULL,   -- filer slug, e.g. 'snap-inc'
    period         TEXT NOT NULL,   -- e.g. '2025 Q3'
    shha_category  TEXT NOT NULL,   -- hate_speech_or_racism | extremism_or_radicalization | …
    original_label TEXT NOT NULL,   -- the category label the company actually filed
    content_format TEXT NOT NULL,   -- Strava's per-format breakdown ('' elsewhere)
    grain          TEXT NOT NULL,   -- category_total | breakdown
    metric         TEXT NOT NULL,   -- source table / metric group (company's own terms)
    submetric      TEXT NOT NULL,   -- source column within the metric
    value          REAL,
    unit           TEXT NOT NULL,   -- count | percent
    page           INTEGER          -- page in the archived PDF (verifiability)
);
CREATE INDEX idx_nys_category ON ny_tos_stats(shha_category);
CREATE INDEX idx_nys_company  ON ny_tos_stats(company);

-- Narrative full text across the report corpora, indexed for full-text search
-- (SQLite FTS5). Prose, not numbers. Two `source`s ride in one table:
--   'ny-tos' — one row per page of a NY ToS filing (the language each platform
--     uses to describe its hate-speech/extremism/disinformation/harassment
--     policies), keyed to the archived PDF by page.
--   'dsa'    — one row per DSA Table-11 qualitative description (how each
--     service describes its content-moderation approach, per indicator),
--     derived at seed time from t11_qualitative (no page — `page` is NULL).
-- `heading`/`text` are tokenized (searchable); source/company/platform/period/
-- page are UNINDEXED (filter/return only). Powers the public GET /api/narratives
-- full-text search endpoint + the /narratives page.
CREATE VIRTUAL TABLE report_narratives USING fts5(
    source    UNINDEXED,
    company   UNINDEXED,
    platform  UNINDEXED,
    period    UNINDEXED,
    page      UNINDEXED,
    heading,
    text,
    tokenize = 'porter unicode61'
);
"""

_RL_COLUMNS = ("platform", "company", "category", "confidence",
               "harmonised_template", "format_period", "url_label", "url", "archived")
_NY_TOS_COLUMNS = ("company", "platform", "period", "upload_date", "access",
                   "source_url", "filename", "archived", "sha256", "bytes")
_CA_AB587_COLUMNS = ("company", "platform", "period", "period_original", "access",
                     "source_url", "filename", "archived", "sha256", "bytes")

# fact table name → (number of columns, source JSON key)
_FACT_TABLES = {
    "t3_member_state_orders": (6, "t3"),
    "t4_notices": (12, "t4"),
    "t5_own_initiative_illegal": (18, "t5"),
    "t6_own_initiative_tos": (19, "t6"),
    "t7_appeals_recidivism": (6, "t7"),
    "t8_automated_means": (6, "t8"),
    "t9_human_resources": (5, "t9"),
    "t10_amar": (3, "t10"),
    "t11_qualitative": (3, "t11"),
}


# ── Dimension normalization ──────────────────────────────────────────────────
# The DSA template embeds an aggregate "total" row alongside the breakdown rows
# (AMAR's EU TOTAL next to per-member-state rows; the "All the entries" category
# next to per-category rows; the "Total number" scope next to the upheld/reversed
# outcomes). Summing a measure across those rows double-counts. We flag the
# aggregate rows (is_total) so queries can pick a single grain, and we drop the
# mis-parsed header/placeholder cells that some non-VLOP extracts leak in as data.

# Labels (stripped, casefolded) that denote an aggregate/total row.
_TOTAL_LABELS = {
    "total", "totals", "total number", "all the entries", "all entries",
    # "total" in the official EU languages (reports are filed in any of them).
    "gesamt", "gesamtzahl", "nombre total", "número total", "numero total",
    "totale", "totaal", "ogółem", "totalt", "yhteensä", "celkem", "σύνολο",
    "összesen", "общо", "celkovo", "spolu", "iš viso", "kopā", "kokku",
    "skupaj", "ukupno", "iomlán", "i alt", "nifer cyfan", "iomlán líon",
}
# Labels that are mis-parsed header/placeholder cells, not real dimension values.
_JUNK_LABELS = {
    "", "scope", "category", "champ d’application", "champ d'application",
    "geltungsbereich", "categoría", "catégorie", "kategorie", "[...]", "...",
    "n/a", "na", "-",
}
# Fact tables by the dimension FK columns they carry (for junk-row deletion).
_SCOPE_FACTS = ("t3_member_state_orders", "t7_appeals_recidivism",
                "t8_automated_means", "t9_human_resources", "t10_amar")
_CATEGORY_FACTS = ("t3_member_state_orders", "t4_notices",
                   "t5_own_initiative_illegal", "t6_own_initiative_tos")


_CROSSWALK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "template-crosswalk.json")
# {dimension: {original-language label: canonical English label}} — see
# scripts/build_template_crosswalk.py. Maps DSA harmonised-template rows filed in
# other EU languages onto their canonical English term so the same logical
# section/indicator/scope can be grouped across languages (the `key` column),
# while the original-language label is preserved for display (the `name` column).
_CROSSWALK: dict[str, dict[str, str]] | None = None


def _crosswalk() -> dict[str, dict[str, str]]:
    global _CROSSWALK
    if _CROSSWALK is None:
        try:
            with open(_CROSSWALK_PATH, encoding="utf-8") as f:
                _CROSSWALK = json.load(f)
        except (OSError, ValueError):
            _CROSSWALK = {}
    return _CROSSWALK


def _is_total_label(label: str) -> bool:
    return (label or "").strip().casefold() in _TOTAL_LABELS


def _is_junk_label(label: str) -> bool:
    s = (label or "").strip()
    if not s or s.casefold() in _JUNK_LABELS:
        return True
    if any(ch.isalpha() for ch in s):
        return False
    # No letters: a mis-parsed cell. Drop pure-punctuation placeholders ("[...]",
    # "...", "-") and bare single numbers ("0", "168"), but KEEP meaningful numeric
    # labels that carry a separator — e.g. "9 & 10" (Art. 9 & 10), "1.1", "2024/25".
    if not any(ch.isalnum() for ch in s):
        return True
    return s.isdigit()


def normalize_dimensions(conn: sqlite3.Connection) -> dict[str, int]:
    """Post-load cleanup (idempotent). Flags aggregate 'total' scope/category
    rows via ``is_total`` and deletes fact rows that reference mis-parsed junk
    dimension labels. Safe to run repeatedly (e.g. after appending non-VLOP
    reports). Returns a small {what: count} summary."""
    flagged = 0
    for dim, col in (("scopes", "name"), ("categories", "label")):
        ids = [rid for rid, lab in conn.execute(f"SELECT id, {col} FROM {dim}")
               if _is_total_label(lab)]
        if ids:
            conn.executemany(f"UPDATE {dim} SET is_total = 1 WHERE id = ?",
                             [(i,) for i in ids])
            flagged += len(ids)

    # Surfaces: the "All" surface is the cross-surface aggregate (it sums Core +
    # Ads + the per-target breakdowns), so flag it as the total grain the same way
    # — letting queries pick "All" only or the per-surface breakdown, never both.
    # "All" isn't in _TOTAL_LABELS (plain "all" is too generic elsewhere), so match
    # it explicitly on the surface dimension alone.
    surf_ids = [rid for rid, n in conn.execute("SELECT id, name FROM surfaces")
                if (n or "").strip().casefold() == "all"]
    if surf_ids:
        conn.executemany("UPDATE surfaces SET is_total = 1 WHERE id = ?",
                         [(i,) for i in surf_ids])
        flagged += len(surf_ids)

    # Stamp the language-neutral canonical `key` on each template dimension row:
    # the crosswalk's English term where the label was filed in another language,
    # else the label itself (already English / unmapped). Lets queries group or
    # filter across languages while `name` keeps the original-language text.
    cw = _crosswalk()
    for dim, table in (("section", "sections"), ("indicator", "indicators"),
                       ("scope", "scopes")):
        m = cw.get(dim, {})
        conn.executemany(
            f"UPDATE {table} SET key = ? WHERE id = ?",
            [(m.get(name, name), rid)
             for rid, name in conn.execute(f"SELECT id, name FROM {table}")])

    deleted = 0
    junk_scopes = [rid for rid, n in conn.execute("SELECT id, name FROM scopes")
                   if _is_junk_label(n)]
    junk_cats = [rid for rid, l in conn.execute("SELECT id, label FROM categories")
                 if _is_junk_label(l)]
    if junk_scopes:
        ph = ",".join("?" * len(junk_scopes))
        for t in _SCOPE_FACTS:
            deleted += conn.execute(
                f"DELETE FROM {t} WHERE scope_id IN ({ph})", junk_scopes).rowcount
        # Drop the now-unreferenced junk dimension rows too, so they can't leak
        # into a distinct-scope listing.
        conn.execute(f"DELETE FROM scopes WHERE id IN ({ph})", junk_scopes)
    if junk_cats:
        ph = ",".join("?" * len(junk_cats))
        for t in _CATEGORY_FACTS:
            deleted += conn.execute(
                f"DELETE FROM {t} WHERE category_id IN ({ph})", junk_cats).rowcount
        conn.execute(f"DELETE FROM categories WHERE id IN ({ph})", junk_cats)
    conn.commit()
    return {"totals_flagged": flagged, "junk_facts_deleted": deleted}


def build_db(data: dict[str, Any], db_path: str) -> dict[str, int]:
    """Build the VLOP star schema at db_path from a parsed vlop-dsa.json dict.

    Returns a {table: row_count} summary. Rows are inserted positionally, so the
    leading lookup indices in each fact row land directly in the *_id columns.
    """
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)

        services = data["services"]
        platforms = data["service_platforms"]
        conn.executemany(
            "INSERT INTO services (id, name, platform) VALUES (?, ?, ?)",
            [(i, services[i], platforms[i]) for i in range(len(services))],
        )

        categories = data["categories"]
        labels = data.get("category_labels", {})
        conn.executemany(
            "INSERT INTO categories (id, code, label) VALUES (?, ?, ?)",
            [(i, code, _category_label(code, labels)) for i, code in enumerate(categories)],
        )

        for table, key in (("sections", "sections"), ("indicators", "indicators"),
                           ("scopes", "scopes"), ("surfaces", "surfaces")):
            conn.executemany(
                f"INSERT INTO {table} (id, name) VALUES (?, ?)",
                [(i, name) for i, name in enumerate(data[key])],
            )

        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [(k, str(v)) for k, v in data.get("meta", {}).items()],
        )

        meta = data.get("meta", {})
        period = meta.get("period", "/")
        period_start, _, period_end = period.partition("/")
        tier = meta.get("tier", "vlop")
        generated = meta.get("generated")
        conn.execute(
            "INSERT INTO reports (id, period, period_start, period_end, tier, generated) VALUES (0,?,?,?,?,?)",
            (period, period_start.strip(), period_end.strip(), tier, generated),
        )

        summary: dict[str, int] = {}
        for table, (ncols, key) in _FACT_TABLES.items():
            rows = data.get(key, [])
            # Prepend report_id=0 to each row (ncols describes the source JSON width).
            placeholders = ", ".join(["?"] * (ncols + 1))
            conn.executemany(
                f"INSERT INTO {table} VALUES ({placeholders})",
                [[0] + list(row) for row in rows],
            )
            summary[table] = len(rows)

        conn.commit()
        normalize_dimensions(conn)
        return summary
    finally:
        conn.close()


def build_gr_db(data: dict[str, Any], db_path: str) -> int:
    """Populate Google Government Removal tables in an existing DB at db_path.

    The DB must already contain the gr_* tables (created by SCHEMA above, i.e.
    build_db() must have been called first). Returns the number of fact rows inserted.
    """
    countries = data["countries"]
    country_names = data["country_names"]
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO gr_periods (id, name) VALUES (?, ?)",
                list(enumerate(data["periods"])),
            )
            conn.executemany(
                "INSERT INTO gr_countries (id, code, name) VALUES (?, ?, ?)",
                [(i, code, name) for i, (code, name) in enumerate(zip(countries, country_names))],
            )
            conn.executemany(
                "INSERT INTO gr_requestors (id, name) VALUES (?, ?)",
                list(enumerate(data["requestors"])),
            )
            conn.executemany(
                "INSERT INTO gr_products (id, name) VALUES (?, ?)",
                list(enumerate(data["products"])),
            )
            conn.executemany(
                "INSERT INTO gr_reasons (id, name) VALUES (?, ?)",
                list(enumerate(data["reasons"])),
            )
            rows = data["rows"]
            conn.executemany(
                "INSERT INTO gr_removals ("
                "period_id, country_id, requestor_id, product_id, reason_id, "
                "num_requests, items_requested, removed_legal, removed_policy, "
                "not_found, not_enough_info, no_action, already_removed"
                ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_apple_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the Apple Transparency tables in an existing DB at db_path.

    The DB must already contain the ap_*/apple_* tables (created by SCHEMA, i.e.
    build_db() must have run first). The dataset is the interned
    apple-transparency.json (periods/countries/request_types arrays + fact rows
    whose leading values index those arrays). Returns the fact-row count.
    """
    measures = data["measures"]
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany("INSERT INTO ap_periods (id, name) VALUES (?, ?)",
                             list(enumerate(data["periods"])))
            conn.executemany("INSERT INTO ap_countries (id, name) VALUES (?, ?)",
                             list(enumerate(data["countries"])))
            conn.executemany("INSERT INTO ap_request_types (id, name) VALUES (?, ?)",
                             list(enumerate(data["request_types"])))
            cols = ["period_id", "country_id", "request_type_id"] + measures
            conn.executemany(
                f"INSERT INTO apple_requests ({', '.join(cols)}) "
                f"VALUES ({', '.join(['?'] * len(cols))})",
                data["rows"],
            )
            conn.executemany(
                "INSERT INTO apple_national_security ("
                "period_id, country_id, request_type, "
                "requests_low, requests_high, accounts_low, accounts_high"
                ") VALUES (?,?,?,?,?,?,?)",
                data["ns_rows"],
            )
        return len(data["rows"]) + len(data["ns_rows"])
    finally:
        conn.close()


def build_github_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the github_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA, i.e. build_db()
    must have run first). The dataset is the tidy-long github-transparency.json
    (a `columns` header + `rows`, each row matching the table column order).
    Returns the fact-row count.
    """
    # Rows are inserted positionally, so refuse to seed if the snapshot's column
    # order ever drifts from the table's — otherwise values would silently land
    # in the wrong columns.
    expected_cols = ["year", "period", "dataset", "government", "iso2", "category",
                     "metric", "count_low", "count_high"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"github dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data["rows"]
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO github_metrics ("
                "year, period, dataset, government, iso2, category, metric, "
                "count_low, count_high) VALUES (?,?,?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_snap_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the snap_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long snap-transparency.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    expected_cols = ["period", "section", "category", "sub_category_1",
                     "sub_category_2", "metric", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"snap dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("snap dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO snap_metrics (period, section, category, "
                "sub_category_1, sub_category_2, metric, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_india_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the india_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long india-it-rules.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    expected_cols = ["platform", "period", "section", "category", "metric",
                     "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"india dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("india dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO india_metrics (platform, period, section, category, "
                "metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_korea_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the korea_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long korea-transparency.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    if data is None:
        raise ValueError("korea dataset is None")
    expected_cols = ["platform", "service", "period", "category", "metric",
                     "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"korea dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("korea dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO korea_metrics (platform, service, period, category, "
                "metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_taiwan_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the taiwan_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long taiwan-anti-fraud.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    if data is None:
        raise ValueError("taiwan dataset is None")
    expected_cols = ["publisher", "period", "section", "category", "metric",
                     "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"taiwan dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("taiwan dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO taiwan_metrics (publisher, period, section, "
                "category, metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_turkey_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the turkey_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long turkey-law5651.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    if data is None:
        raise ValueError("turkey dataset is None")
    expected_cols = ["platform", "period", "section", "category",
                     "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"turkey dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("turkey dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO turkey_metrics (platform, period, section, "
                "category, metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_tco_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the tco_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long tco-regulation.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    if data is None:
        raise ValueError("tco dataset is None")
    expected_cols = ["publisher", "role", "period", "section",
                     "category", "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"tco dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("tco dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO tco_metrics (publisher, role, period, section, "
                "category, metric, unit, value) VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_ciirc_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the ciirc_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long china-ciirc.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    if data is None:
        raise ValueError("ciirc dataset is None")
    expected_cols = ["publisher", "period", "section", "category", "metric",
                     "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"ciirc dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("ciirc dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO ciirc_metrics (publisher, period, section, category, "
                "metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_regional_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the regional_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long regional-transparency.json (`columns` header + `rows` in column
    order). Returns the fact-row count.
    """
    if data is None:
        raise ValueError("regional dataset is None")
    expected_cols = ["jurisdiction", "platform", "period", "section",
                     "category", "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"regional dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("regional dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO regional_metrics (jurisdiction, platform, period, "
                "section, category, metric, unit, value) VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_ai_training_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the ai_training_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long ai-training-transparency.json (`columns` header + `rows` in column
    order). Returns the fact-row count.
    """
    if data is None:
        raise ValueError("ai training dataset is None")
    expected_cols = ["provider", "model", "released", "section",
                     "field", "value", "size_rank"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"ai training dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("ai training dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO ai_training_metrics (provider, model, released, "
                "section, field, value, size_rank) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_singapore_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the singapore_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long singapore-online-safety.json (`columns` header + `rows` in column
    order). Returns the fact-row count.
    """
    if data is None:
        raise ValueError("singapore dataset is None")
    expected_cols = ["service", "period", "section", "category",
                     "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"singapore dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("singapore dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO singapore_metrics (service, period, section, "
                "category, metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_esafety_bose_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the esafety_bose_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long esafety-bose.json (`columns` header + `rows` in column order),
    built by scripts/build_esafety_bose.py. Returns the fact-row count.
    """
    if data is None:
        raise ValueError("esafety bose dataset is None")
    expected_cols = ["service", "period", "section", "category",
                     "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"esafety bose dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("esafety bose dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO esafety_bose_metrics (service, period, section, "
                "category, metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_korea_network_act_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the korea_network_act_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long korea-network-act.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    if data is None:
        raise ValueError("korea network act dataset is None")
    expected_cols = ["publisher", "period", "section", "category",
                     "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"korea network act dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("korea network act dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO korea_network_act_metrics (publisher, period, "
                "section, category, metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_japan_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the japan_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long japan-info-platform.json (`columns` header + `rows` in column
    order). Returns the fact-row count.
    """
    if data is None:
        raise ValueError("japan dataset is None")
    expected_cols = ["service", "period", "section", "category", "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"japan dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("japan dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO japan_metrics "
                "(service, period, section, category, metric, unit, value) "
                "VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_china12321_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the china12321_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long china-12321.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    if not isinstance(data, dict):
        raise ValueError("china-12321 dataset must be a dictionary")
    expected_cols = ["publisher", "period", "section", "category", "metric",
                     "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"china-12321 dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("china-12321 dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO china12321_metrics (publisher, period, section, "
                "category, metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_cser_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the cser_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long meta-cser.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    if data is None:
        raise ValueError("cser dataset is None")
    expected_cols = ["app", "policy_area", "metric", "period", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"cser dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("cser dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO cser_metrics (app, policy_area, metric, period, "
                "unit, value) VALUES (?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_tiktok_cger_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the tiktok_cger_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long tiktok-cger.json (`columns` header + `rows` in column order), the
    Global cut. Returns the fact-row count.
    """
    if data is None:
        raise ValueError("tiktok cger dataset is None")
    expected_cols = ["period", "metric", "policy_type", "issue",
                     "task_type", "task", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"tiktok cger dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("tiktok cger dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO tiktok_cger_metrics (period, metric, policy_type, "
                "issue, task_type, task, unit, value) VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_google_userdata_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the google_userdata_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is
    the tidy-long google-user-data.json (`columns` header + `rows` in column
    order). Returns the fact-row count.
    """
    if data is None:
        raise ValueError("google user-data dataset is None")
    expected_cols = ["dataset", "period", "country", "iso2", "product",
                     "legal_process", "assisting_country", "metric", "unit",
                     "value_low", "value_high"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"google user-data dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("google user-data dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO google_userdata_metrics (dataset, period, country, "
                "iso2, product, legal_process, assisting_country, metric, unit, "
                "value_low, value_high) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_microsoft_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the microsoft_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is
    the tidy-long microsoft-lerr.json (`columns` header + `rows` in column
    order). Returns the fact-row count.
    """
    if data is None:
        raise ValueError("microsoft dataset is None")
    expected_cols = ["period", "section", "country", "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"microsoft dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("microsoft dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO microsoft_metrics (period, section, country, "
                "metric, unit, value) VALUES (?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_linkedin_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the linkedin_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is
    the tidy-long linkedin-transparency.json (`columns` header + `rows` in
    column order). Returns the fact-row count.
    """
    if data is None:
        raise ValueError("linkedin dataset is None")
    expected_cols = ["dataset", "period", "country", "metric", "unit",
                     "value_low", "value_high"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"linkedin dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("linkedin dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO linkedin_metrics (dataset, period, country, "
                "metric, unit, value_low, value_high) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_tiktok_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the tiktok_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is
    the tidy-long tiktok-transparency.json (`columns` header + `rows` in column
    order). Returns the fact-row count.
    """
    if data is None:
        raise ValueError("tiktok dataset is None")
    expected_cols = ["dataset", "period", "country", "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"tiktok dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("tiktok dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO tiktok_metrics (dataset, period, country, metric, "
                "unit, value) VALUES (?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_discord_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the discord_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is
    the tidy-long discord-transparency.json (`columns` header + `rows` in column
    order). Returns the fact-row count.
    """
    if data is None:
        raise ValueError("discord dataset is None")
    expected_cols = ["period", "section", "category", "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"discord dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("discord dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO discord_metrics (period, section, category, metric, "
                "unit, value) VALUES (?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_dsa_tdb_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the dsa_tdb_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long dsa-tdb.json (`columns` header + `rows` in column order) — a compact
    re-aggregation of the EU DSA Transparency Database's Statements of Reasons.
    Returns the fact-row count.
    """
    if data is None:
        raise ValueError("dsa-tdb dataset is None")
    if not isinstance(data, dict):
        raise ValueError("dsa-tdb dataset must be a dict with 'columns'/'rows'")
    expected_cols = ["section", "platform", "period", "category", "metric",
                     "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"dsa-tdb dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("dsa-tdb dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO dsa_tdb_metrics (section, platform, period, category, "
                "metric, unit, value) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_android_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the android_metrics table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    tidy-long android-security.json (`columns` header + `rows` in column order).
    Returns the fact-row count.
    """
    if data is None:
        raise ValueError("android dataset is None")
    expected_cols = ["section", "period", "category", "metric", "unit", "value"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"android dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("android dataset is missing 'rows'")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO android_metrics (section, period, category, metric, "
                "unit, value) VALUES (?,?,?,?,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_google_traffic_db(data: dict[str, Any], db_path: str) -> int:
    """Populate the google_traffic table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). The dataset is the
    flat-catalogue google-traffic.json (`columns` header + `rows` in column
    order). Returns the row count.
    """
    if data is None:
        raise ValueError("google traffic dataset is None")
    expected_cols = ["country", "iso2", "product", "start_date", "end_date",
                     "year", "source", "source_url", "title", "excerpt",
                     "disruption_url"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"google traffic dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError("google traffic dataset is missing 'rows'")
    # A couple of rows carry only an end date (no start_date, so no `year` in
    # the source). Derive year from the end date so those disruptions remain
    # reachable through the Year filter/facet instead of matching only "All".
    i_end, i_year = expected_cols.index("end_date"), expected_cols.index("year")
    fixed = []
    for r in rows:
        if r[i_year] is None and r[i_end]:
            r = list(r)
            r[i_year] = int(str(r[i_end])[:4])
        fixed.append(r)
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO google_traffic (country, iso2, product, start_date, "
                "end_date, year, source, source_url, title, excerpt, "
                "disruption_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                fixed,
            )
        return len(fixed)
    finally:
        conn.close()


def build_report_locations(rows: list[dict[str, str]], db_path: str) -> int:
    """Populate the report_locations table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA, i.e. build_db()
    must have run first). `rows` are dicts keyed by `_RL_COLUMNS`. Returns the
    number of rows inserted.
    """
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO report_locations "
                "(platform, company, category, confidence, harmonised_template, "
                "format_period, url_label, url, archived) VALUES (?,?,?,?,?,?,?,?,?)",
                [tuple((r.get(c) or None) for c in _RL_COLUMNS) for r in rows],
            )
        return len(rows)
    finally:
        conn.close()


def _load_report_locations_csv(path: str) -> list[dict[str, str]]:
    import csv as _csv
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(_csv.DictReader(f))


def build_ny_tos_reports(rows: list[dict[str, str]], db_path: str) -> int:
    """Populate the ny_tos_reports table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). `rows` are dicts
    keyed by `_NY_TOS_COLUMNS`. Returns the number of rows inserted.
    """
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO ny_tos_reports "
                "(company, platform, period, upload_date, access, source_url, "
                "filename, archived, sha256, bytes) VALUES (?,?,?,?,?,?,?,?,?,?)",
                [tuple((r.get(c) or None) for c in _NY_TOS_COLUMNS) for r in rows],
            )
        return len(rows)
    finally:
        conn.close()


_NY_STATS_COLUMNS = ("company", "period", "shha_category", "original_label",
                     "content_format", "grain", "metric", "submetric",
                     "value", "unit", "page")


def build_ca_ab587_reports(rows: list[dict[str, str]], db_path: str) -> int:
    """Populate the ca_ab587_reports table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). `rows` are dicts
    keyed by `_CA_AB587_COLUMNS`. Returns the number of rows inserted.
    """
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO ca_ab587_reports "
                "(company, platform, period, period_original, access, source_url, "
                "filename, archived, sha256, bytes) VALUES (?,?,?,?,?,?,?,?,?,?)",
                [tuple((r.get(c) if r.get(c) not in (None, "") else None)
                       for c in _CA_AB587_COLUMNS) for r in rows],
            )
        return len(rows)
    finally:
        conn.close()


def _build_narratives(data: dict[str, Any], db_path: str, source: str) -> int:
    """Populate the report_narratives FTS5 table with one page-per-row prose
    dataset (`columns` header + `rows` in column order: company, platform, period,
    page, heading, text), tagged with `source`. Shared by every page-based
    narrative corpus (NY ToS filings, California AB 587 filings). Returns the count.
    """
    if data is None:
        raise ValueError(f"{source} narratives dataset is None")
    expected_cols = ["company", "platform", "period", "page", "heading", "text"]
    if data.get("columns") != expected_cols:
        raise ValueError(f"{source} narratives dataset columns {data.get('columns')} "
                         f"don't match the expected order {expected_cols}")
    rows = data.get("rows")
    if rows is None:
        raise ValueError(f"{source} narratives dataset is missing 'rows'")
    for i, r in enumerate(rows):
        if len(r) != len(expected_cols):
            raise ValueError(f"{source} narratives row {i} has length {len(r)}, "
                             f"expected {len(expected_cols)}")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO report_narratives (source, company, platform, period, "
                "page, heading, text) VALUES (?,?,?,?,?,?,?)",
                [(source, *r) for r in rows],
            )
        return len(rows)
    finally:
        conn.close()


def build_ny_tos_narratives(data: dict[str, Any], db_path: str) -> int:
    """Populate report_narratives with the NY ToS filing prose (source='ny-tos')."""
    return _build_narratives(data, db_path, "ny-tos")


def build_ca_ab587_narratives(data: dict[str, Any], db_path: str) -> int:
    """Populate report_narratives with the CA AB 587 filing prose (source='ca-ab587')."""
    return _build_narratives(data, db_path, "ca-ab587")


def build_japan_narratives(data: dict[str, Any], db_path: str) -> int:
    """Populate report_narratives with LY Corporation's Media Transparency Report
    prose (source='japan'). Bilingual: each `text` is an English translation
    followed by the Japanese original (the source report is Japanese-only)."""
    return _build_narratives(data, db_path, "japan")


def build_ca_ab2013_narratives(data: dict[str, Any], db_path: str) -> int:
    """Populate report_narratives with Google's California AB 2013 AI Training
    Data Transparency Summary prose (source='ca-ab2013')."""
    return _build_narratives(data, db_path, "ca-ab2013")


# A qualitative cell shorter than this (after trimming) is a placeholder — a bare
# "N/A", a dash, a "-", a lone URL fragment — not searchable prose, so it's skipped.
_DSA_NARRATIVE_MIN_CHARS = 60


def build_dsa_narratives(db_path: str) -> int:
    """Populate the report_narratives FTS5 table with the DSA Table-11 qualitative
    descriptions (source='dsa') from the already-loaded star schema.

    Must run AFTER every t11_qualitative row is loaded (both the VLOP load and the
    non-VLOP harmonised append), since it reads straight from that table. One row
    per description: company = service name, heading = indicator, text = the prose.
    Trivial/placeholder cells (< _DSA_NARRATIVE_MIN_CHARS) are skipped. Returns the
    row count inserted.
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT svc.name, svc.platform, rpt.period, ind.name, f.value_text "
            "FROM t11_qualitative f "
            "JOIN reports rpt    ON rpt.id = f.report_id "
            "JOIN services svc   ON svc.id = f.service_id "
            "JOIN indicators ind ON ind.id = f.indicator_id "
            "WHERE f.value_text IS NOT NULL "
            "AND length(trim(f.value_text)) >= ?",
            (_DSA_NARRATIVE_MIN_CHARS,),
        ).fetchall()
        with conn:
            # `rows` is already the (company, platform, period, heading, text)
            # 5-tuples the INSERT's five placeholders expect.
            conn.executemany(
                "INSERT INTO report_narratives (source, company, platform, period, "
                "page, heading, text) VALUES ('dsa',?,?,?,NULL,?,?)",
                rows,
            )
        return len(rows)
    finally:
        conn.close()


def build_ny_tos_stats(rows: list[dict[str, str]], db_path: str) -> int:
    """Populate the ny_tos_stats table in an existing DB at db_path.

    The DB must already contain the table (created by SCHEMA). `rows` are dicts
    keyed by `_NY_STATS_COLUMNS` (the ny_tos_normalized.csv header — validated
    so a drifted vendored snapshot fails loudly). Returns the row count.
    """
    if rows and (missing := set(_NY_STATS_COLUMNS) - set(rows[0])):
        raise ValueError(f"ny_tos_stats source is missing columns: {sorted(missing)}")
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO ny_tos_stats "
                "(company, period, shha_category, original_label, content_format, "
                "grain, metric, submetric, value, unit, page) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [tuple(r.get(c, "") if c not in ("value", "page")
                       # explicit None/"" check so a genuine 0 is stored, not NULLed
                       else (None if r.get(c) in (None, "") else r.get(c))
                       for c in _NY_STATS_COLUMNS)
                 for r in rows],
            )
        return len(rows)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo.db from the VLOP DSA dataset.")
    parser.add_argument("--source", default=_DEFAULT_SOURCE, help="Path to vlop-dsa.json")
    parser.add_argument("--gr-source", default=_DEFAULT_GR_SOURCE,
                        help="Path to google-government-removals.json")
    parser.add_argument("--db", default=_DEFAULT_DB, help="Output SQLite database path")
    parser.add_argument("--report-locations", default=_DEFAULT_RL_SOURCE,
                        help="Path to report-locations.csv (non-VLOP catalogue)")
    parser.add_argument("--ny-tos", default=_DEFAULT_NY_TOS_SOURCE,
                        help="Path to ny-tos-reports.csv (NY ToS catalogue)")
    parser.add_argument("--ny-stats", default=_DEFAULT_NY_STATS_SOURCE,
                        help="Path to ny-tos-normalized.csv (normalized NY ToS stats)")
    parser.add_argument("--ca-ab587", default=_DEFAULT_CA_AB587_SOURCE,
                        help="Path to ca-ab587-reports.csv (California AB 587 catalogue)")
    parser.add_argument("--ca-ab587-narratives", default=_DEFAULT_CA_AB587_NARRATIVES_SOURCE,
                        help="Path to ca-ab587-narratives.json")
    parser.add_argument("--japan-narratives", default=_DEFAULT_JAPAN_NARRATIVES_SOURCE,
                        help="Path to japan-narratives.json (LY Corp report prose)")
    parser.add_argument("--ca-ab2013-narratives", default=_DEFAULT_CA_AB2013_NARRATIVES_SOURCE,
                        help="Path to ca-ab2013-narratives.json (Google's CA AB 2013 summary prose)")
    parser.add_argument("--apple-source", default=_DEFAULT_APPLE_SOURCE,
                        help="Path to apple-transparency.json")
    parser.add_argument("--github-source", default=_DEFAULT_GITHUB_SOURCE,
                        help="Path to github-transparency.json")
    parser.add_argument("--snap-source", default=_DEFAULT_SNAP_SOURCE,
                        help="Path to snap-transparency.json")
    parser.add_argument("--india-source", default=_DEFAULT_INDIA_SOURCE,
                        help="Path to india-it-rules.json")
    parser.add_argument("--korea-source", default=_DEFAULT_KOREA_SOURCE,
                        help="Path to korea-transparency.json")
    parser.add_argument("--taiwan-source", default=_DEFAULT_TAIWAN_SOURCE,
                        help="Path to taiwan-anti-fraud.json")
    parser.add_argument("--turkey-source", default=_DEFAULT_TURKEY_SOURCE,
                        help="Path to turkey-law5651.json")
    parser.add_argument("--tco-source", default=_DEFAULT_TCO_SOURCE,
                        help="Path to tco-regulation.json")
    parser.add_argument("--ai-training-source", default=_DEFAULT_AI_TRAINING_SOURCE,
                        help="Path to ai-training-transparency.json")
    parser.add_argument("--regional-source", default=_DEFAULT_REGIONAL_SOURCE,
                        help="Path to regional-transparency.json")
    parser.add_argument("--ciirc-source", default=_DEFAULT_CIIRC_SOURCE,
                        help="Path to china-ciirc.json")
    parser.add_argument("--china12321-source", default=_DEFAULT_CHINA12321_SOURCE,
                        help="Path to china-12321.json")
    parser.add_argument("--cser-source", default=_DEFAULT_CSER_SOURCE,
                        help="Path to meta-cser.json")
    parser.add_argument("--singapore-source", default=_DEFAULT_SINGAPORE_SOURCE,
                        help="Path to singapore-online-safety.json")
    parser.add_argument("--esafety-source", default=_DEFAULT_ESAFETY_SOURCE,
                        help="Path to esafety-bose.json (Australia eSafety BOSE findings)")
    parser.add_argument("--korea-network-act-source", default=_DEFAULT_KOREA_NETWORK_ACT_SOURCE,
                        help="Path to korea-network-act.json")
    parser.add_argument("--japan-source", default=_DEFAULT_JAPAN_SOURCE,
                        help="Path to japan-info-platform.json")
    parser.add_argument("--tiktok-cger-source", default=_DEFAULT_TIKTOK_CGER_SOURCE,
                        help="Path to tiktok-cger.json")
    parser.add_argument("--google-ud-source", default=_DEFAULT_GOOGLE_UD_SOURCE,
                        help="Path to google-user-data.json")
    parser.add_argument("--microsoft-source", default=_DEFAULT_MICROSOFT_SOURCE,
                        help="Path to microsoft-lerr.json")
    parser.add_argument("--linkedin-source", default=_DEFAULT_LINKEDIN_SOURCE,
                        help="Path to linkedin-transparency.json")
    parser.add_argument("--tiktok-source", default=_DEFAULT_TIKTOK_SOURCE,
                        help="Path to tiktok-transparency.json")
    parser.add_argument("--discord-source", default=_DEFAULT_DISCORD_SOURCE,
                        help="Path to discord-transparency.json")
    parser.add_argument("--traffic-source", default=_DEFAULT_TRAFFIC_SOURCE,
                        help="Path to google-traffic.json")
    parser.add_argument("--android-source", default=_DEFAULT_ANDROID_SOURCE,
                        help="Path to android-security.json")
    parser.add_argument("--dsa-tdb-source", default=_DEFAULT_DSA_TDB_SOURCE,
                        help="Path to dsa-tdb.json")
    parser.add_argument("--narratives-source", default=_DEFAULT_NARRATIVES_SOURCE,
                        help="Path to ny-tos-narratives.json")
    args = parser.parse_args()

    with open(args.source, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = build_db(data, args.db)
    period = data.get("meta", {}).get("period", "?")
    total = sum(summary.values())
    print(
        f"Seeded {args.db}: {total} fact rows across {len(_FACT_TABLES)} report tables "
        f"for {len(data['services'])} services (period {period})."
    )
    for table, n in summary.items():
        print(f"  {table}: {n}")

    if os.path.isfile(args.gr_source):
        with open(args.gr_source, "r", encoding="utf-8") as f:
            gr_data = json.load(f)
        gr_rows = build_gr_db(gr_data, args.db)
        print(
            f"  gr_removals: {gr_rows} rows across "
            f"{len(gr_data['periods'])} periods, "
            f"{len(gr_data['countries'])} countries"
        )
    else:
        print(f"  (skipping Google removals — not found: {args.gr_source})")

    if os.path.isfile(args.report_locations):
        rl_rows = _load_report_locations_csv(args.report_locations)
        n = build_report_locations(rl_rows, args.db)
        print(f"  report_locations: {n} rows from {os.path.basename(args.report_locations)}")
    else:
        print(f"  (skipping report locations — not found: {args.report_locations})")

    if os.path.isfile(args.ny_tos):
        ny_rows = _load_report_locations_csv(args.ny_tos)
        n = build_ny_tos_reports(ny_rows, args.db)
        print(f"  ny_tos_reports: {n} rows from {os.path.basename(args.ny_tos)}")
    else:
        print(f"  (skipping NY ToS reports — not found: {args.ny_tos})")

    if os.path.isfile(args.ca_ab587):
        ab_rows = _load_report_locations_csv(args.ca_ab587)
        n = build_ca_ab587_reports(ab_rows, args.db)
        print(f"  ca_ab587_reports: {n} rows from {os.path.basename(args.ca_ab587)}")
    else:
        print(f"  (skipping CA AB 587 reports — not found: {args.ca_ab587})")

    if os.path.isfile(args.ny_stats):
        ny_stat_rows = _load_report_locations_csv(args.ny_stats)
        n = build_ny_tos_stats(ny_stat_rows, args.db)
        print(f"  ny_tos_stats: {n} rows from {os.path.basename(args.ny_stats)}")
    else:
        print(f"  (skipping NY ToS stats — not found: {args.ny_stats})")

    if os.path.isfile(args.apple_source):
        with open(args.apple_source, "r", encoding="utf-8") as f:
            apple_data = json.load(f)
        ap_rows = build_apple_db(apple_data, args.db)
        print(
            f"  apple transparency: {ap_rows} rows across "
            f"{len(apple_data['periods'])} periods, "
            f"{len(apple_data['countries'])} countries, "
            f"{len(apple_data['request_types'])} request types"
        )
    else:
        print(f"  (skipping Apple transparency — not found: {args.apple_source})")

    if os.path.isfile(args.github_source):
        with open(args.github_source, "r", encoding="utf-8") as f:
            gh_data = json.load(f)
        gh_rows = build_github_db(gh_data, args.db)
        print(f"  github transparency: {gh_rows} metric rows across "
              f"{len({r[2] for r in gh_data['rows']})} datasets")
    else:
        print(f"  (skipping GitHub transparency — not found: {args.github_source})")

    if os.path.isfile(args.snap_source):
        with open(args.snap_source, "r", encoding="utf-8") as f:
            snap_data = json.load(f)
        snap_rows = build_snap_db(snap_data, args.db)
        print(f"  snap transparency: {snap_rows} metric rows across "
              f"{len({r[0] for r in snap_data['rows']})} periods")
    else:
        print(f"  (skipping Snap transparency — not found: {args.snap_source})")

    if os.path.isfile(args.india_source):
        with open(args.india_source, "r", encoding="utf-8") as f:
            india_data = json.load(f)
        india_rows = build_india_db(india_data, args.db)
        print(f"  india IT Rules: {india_rows} metric rows across "
              f"{len({r[0] for r in india_data['rows']})} platforms, "
              f"{len({r[1] for r in india_data['rows']})} periods")
    else:
        print(f"  (skipping India IT Rules — not found: {args.india_source})")

    if os.path.isfile(args.korea_source):
        with open(args.korea_source, "r", encoding="utf-8") as f:
            korea_data = json.load(f)
        korea_rows = build_korea_db(korea_data, args.db)
        print(f"  korea transparency: {korea_rows} metric rows across "
              f"{len({r[0] for r in korea_data['rows']})} platforms, "
              f"{len({r[2] for r in korea_data['rows']})} periods")
    else:
        print(f"  (skipping Korea transparency — not found: {args.korea_source})")

    if os.path.isfile(args.taiwan_source):
        with open(args.taiwan_source, "r", encoding="utf-8") as f:
            taiwan_data = json.load(f)
        taiwan_rows = build_taiwan_db(taiwan_data, args.db)
        print(f"  taiwan anti-fraud: {taiwan_rows} metric rows across "
              f"{len({r[1] for r in taiwan_data['rows']})} periods, "
              f"{len({r[3] for r in taiwan_data['rows']})} categories")
    else:
        print(f"  (skipping Taiwan anti-fraud — not found: {args.taiwan_source})")

    if os.path.isfile(args.turkey_source):
        with open(args.turkey_source, "r", encoding="utf-8") as f:
            turkey_data = json.load(f)
        turkey_rows = build_turkey_db(turkey_data, args.db)
        print(f"  turkey law 5651: {turkey_rows} metric rows across "
              f"{len({r[0] for r in turkey_data['rows']})} platforms, "
              f"{len({r[1] for r in turkey_data['rows']})} periods")
    else:
        print(f"  (skipping Türkiye Law 5651 — not found: {args.turkey_source})")

    if os.path.isfile(args.tco_source):
        with open(args.tco_source, "r", encoding="utf-8") as f:
            tco_data = json.load(f)
        tco_rows = build_tco_db(tco_data, args.db)
        print(f"  tco regulation: {tco_rows} metric rows across "
              f"{len({r[0] for r in tco_data['rows']})} publishers")
    else:
        print(f"  (skipping TCO Regulation — not found: {args.tco_source})")

    if os.path.isfile(args.ai_training_source):
        with open(args.ai_training_source, "r", encoding="utf-8") as f:
            ai_data = json.load(f)
        ai_rows = build_ai_training_db(ai_data, args.db)
        print(f"  ai training transparency: {ai_rows} rows across "
              f"{len({r[1] for r in ai_data['rows']})} models")
    else:
        print(f"  (skipping AI training transparency — not found: {args.ai_training_source})")

    if os.path.isfile(args.regional_source):
        with open(args.regional_source, "r", encoding="utf-8") as f:
            regional_data = json.load(f)
        regional_rows = build_regional_db(regional_data, args.db)
        print(f"  regional law reports: {regional_rows} rows across "
              f"{len({r[0] for r in regional_data['rows']})} jurisdictions")
    else:
        print(f"  (skipping regional law reports — not found: {args.regional_source})")

    if os.path.isfile(args.ciirc_source):
        with open(args.ciirc_source, "r", encoding="utf-8") as f:
            ciirc_data = json.load(f)
        ciirc_rows = build_ciirc_db(ciirc_data, args.db)
        print(f"  china ciirc: {ciirc_rows} rows across "
              f"{len({r[1] for r in ciirc_data['rows']})} months")
    else:
        print(f"  (skipping China CIIRC — not found: {args.ciirc_source})")

    if os.path.isfile(args.china12321_source):
        with open(args.china12321_source, "r", encoding="utf-8") as f:
            china12321_data = json.load(f)
        china12321_rows = build_china12321_db(china12321_data, args.db)
        print(f"  china 12321: {china12321_rows} rows across "
              f"{len({r[1] for r in china12321_data['rows']})} bulletins")
    else:
        print(f"  (skipping China 12321 — not found: {args.china12321_source})")

    if os.path.isfile(args.cser_source):
        with open(args.cser_source, "r", encoding="utf-8") as f:
            cser_data = json.load(f)
        cser_rows = build_cser_db(cser_data, args.db)
        print(f"  meta CSER: {cser_rows} metric rows across "
              f"{len({r[0] for r in cser_data['rows']})} apps, "
              f"{len({r[1] for r in cser_data['rows']})} policy areas, "
              f"{len({r[3] for r in cser_data['rows']})} quarters")
    else:
        print(f"  (skipping Meta CSER — not found: {args.cser_source})")

    if os.path.isfile(args.singapore_source):
        with open(args.singapore_source, "r", encoding="utf-8") as f:
            singapore_data = json.load(f)
        singapore_rows = build_singapore_db(singapore_data, args.db)
        print(f"  singapore online safety: {singapore_rows} metric rows across "
              f"{len({r[0] for r in singapore_data['rows']})} services, "
              f"{len({r[2] for r in singapore_data['rows']})} sections")
    else:
        print(f"  (skipping Singapore online safety — not found: "
              f"{args.singapore_source})")

    if os.path.isfile(args.esafety_source):
        with open(args.esafety_source, "r", encoding="utf-8") as f:
            esafety_data = json.load(f)
        esafety_rows = build_esafety_bose_db(esafety_data, args.db)
        print(f"  esafety BOSE: {esafety_rows} metric rows across "
              f"{len({r[0] for r in esafety_data['rows']})} services, "
              f"{len({r[2] for r in esafety_data['rows']})} sections")
    else:
        print(f"  (skipping eSafety BOSE — not found: "
              f"{args.esafety_source})")

    if os.path.isfile(args.korea_network_act_source):
        with open(args.korea_network_act_source, "r", encoding="utf-8") as f:
            kna_data = json.load(f)
        kna_rows = build_korea_network_act_db(kna_data, args.db)
        print(f"  korea network act: {kna_rows} metric rows across "
              f"{len({r[2] for r in kna_data['rows']})} sections")
    else:
        print(f"  (skipping Korea Network Act — not found: "
              f"{args.korea_network_act_source})")

    if os.path.isfile(args.japan_source):
        with open(args.japan_source, "r", encoding="utf-8") as f:
            japan_data = json.load(f)
        japan_rows = build_japan_db(japan_data, args.db)
        print(f"  japan 情プラ法: {japan_rows} metric rows across "
              f"{len({r[0] for r in japan_data['rows']})} services")
    else:
        print(f"  (skipping Japan 情プラ法 — not found: {args.japan_source})")

    if os.path.isfile(args.tiktok_cger_source):
        with open(args.tiktok_cger_source, "r", encoding="utf-8") as f:
            ttcger_data = json.load(f)
        ttcger_rows = build_tiktok_cger_db(ttcger_data, args.db)
        print(f"  tiktok CGER: {ttcger_rows} metric rows across "
              f"{len({r[1] for r in ttcger_data['rows']})} metrics, "
              f"{len({r[0] for r in ttcger_data['rows']})} quarters")
    else:
        print(f"  (skipping TikTok CGER — not found: {args.tiktok_cger_source})")

    if os.path.isfile(args.google_ud_source):
        with open(args.google_ud_source, "r", encoding="utf-8") as f:
            gud_data = json.load(f)
        gud_rows = build_google_userdata_db(gud_data, args.db)
        print(f"  google user data: {gud_rows} metric rows across "
              f"{len({r[1] for r in gud_data['rows']})} periods, "
              f"{len({r[0] for r in gud_data['rows']})} datasets")
    else:
        print(f"  (skipping Google user data — not found: {args.google_ud_source})")

    if os.path.isfile(args.microsoft_source):
        with open(args.microsoft_source, "r", encoding="utf-8") as f:
            ms_data = json.load(f)
        ms_rows = build_microsoft_db(ms_data, args.db)
        print(f"  microsoft LERR: {ms_rows} metric rows across "
              f"{len({r[0] for r in ms_data['rows']})} periods, "
              f"{len({r[1] for r in ms_data['rows']})} sections")
    else:
        print(f"  (skipping Microsoft LERR — not found: {args.microsoft_source})")

    if os.path.isfile(args.linkedin_source):
        with open(args.linkedin_source, "r", encoding="utf-8") as f:
            li_data = json.load(f)
        li_rows = build_linkedin_db(li_data, args.db)
        print(f"  linkedin transparency: {li_rows} metric rows across "
              f"{len({r[1] for r in li_data['rows']})} periods, "
              f"{len({r[0] for r in li_data['rows']})} datasets")
    else:
        print(f"  (skipping LinkedIn transparency — not found: {args.linkedin_source})")

    if os.path.isfile(args.tiktok_source):
        with open(args.tiktok_source, "r", encoding="utf-8") as f:
            tt_data = json.load(f)
        tt_rows = build_tiktok_db(tt_data, args.db)
        print(f"  tiktok transparency: {tt_rows} metric rows across "
              f"{len({r[1] for r in tt_data['rows']})} periods, "
              f"{len({r[0] for r in tt_data['rows']})} datasets")
    else:
        print(f"  (skipping TikTok transparency — not found: {args.tiktok_source})")

    if os.path.isfile(args.discord_source):
        with open(args.discord_source, "r", encoding="utf-8") as f:
            dc_data = json.load(f)
        dc_rows = build_discord_db(dc_data, args.db)
        print(f"  discord transparency: {dc_rows} metric rows across "
              f"{len({r[0] for r in dc_data['rows']})} periods, "
              f"{len({r[1] for r in dc_data['rows']})} sections")
    else:
        print(f"  (skipping Discord transparency — not found: {args.discord_source})")

    if os.path.isfile(args.traffic_source):
        with open(args.traffic_source, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
        gt_rows = build_google_traffic_db(gt_data, args.db)
        print(f"  google traffic: {gt_rows} disruptions across "
              f"{len({r[0] for r in gt_data['rows']})} countries, "
              f"{len({r[2] for r in gt_data['rows']})} products")
    else:
        print(f"  (skipping Google traffic — not found: {args.traffic_source})")

    if os.path.isfile(args.android_source):
        with open(args.android_source, "r", encoding="utf-8") as f:
            an_data = json.load(f)
        an_rows = build_android_db(an_data, args.db)
        print(f"  android security: {an_rows} metric rows across "
              f"{len({r[0] for r in an_data['rows']})} sections, "
              f"{len({r[1] for r in an_data['rows']})} periods")
    else:
        print(f"  (skipping Android security — not found: {args.android_source})")

    if os.path.isfile(args.dsa_tdb_source):
        with open(args.dsa_tdb_source, "r", encoding="utf-8") as f:
            dsatdb_data = json.load(f)
        dsatdb_rows = build_dsa_tdb_db(dsatdb_data, args.db)
        print(f"  DSA-TDB statements of reasons: {dsatdb_rows} metric rows across "
              f"{len({r[1] for r in dsatdb_data['rows']})} platforms, "
              f"{len({r[2] for r in dsatdb_data['rows']})} months")
    else:
        print(f"  (skipping DSA-TDB — not found: {args.dsa_tdb_source})")

    if os.path.isfile(args.narratives_source):
        with open(args.narratives_source, "r", encoding="utf-8") as f:
            nar_data = json.load(f)
        nar_rows = build_ny_tos_narratives(nar_data, args.db)
        print(f"  ny tos narratives: {nar_rows} pages across "
              f"{len({r[0] for r in nar_data['rows']})} companies")
    else:
        print(f"  (skipping NY ToS narratives — not found: {args.narratives_source})")

    if os.path.isfile(args.ca_ab587_narratives):
        with open(args.ca_ab587_narratives, "r", encoding="utf-8") as f:
            ab_nar_data = json.load(f)
        ab_nar_rows = build_ca_ab587_narratives(ab_nar_data, args.db)
        print(f"  ca ab587 narratives: {ab_nar_rows} pages across "
              f"{len({r[1] or r[0] for r in ab_nar_data['rows']})} platforms")
    else:
        print(f"  (skipping CA AB 587 narratives — not found: {args.ca_ab587_narratives})")

    if os.path.isfile(args.japan_narratives):
        with open(args.japan_narratives, "r", encoding="utf-8") as f:
            jp_nar_data = json.load(f)
        jp_nar_rows = build_japan_narratives(jp_nar_data, args.db)
        print(f"  japan narratives: {jp_nar_rows} bilingual sections")
    else:
        print(f"  (skipping Japan narratives — not found: {args.japan_narratives})")

    if os.path.isfile(args.ca_ab2013_narratives):
        with open(args.ca_ab2013_narratives, "r", encoding="utf-8") as f:
            ab2013_nar_data = json.load(f)
        ab2013_nar_rows = build_ca_ab2013_narratives(ab2013_nar_data, args.db)
        print(f"  ca ab2013 narratives: {ab2013_nar_rows} sections")
    else:
        print(f"  (skipping CA AB 2013 narratives — not found: {args.ca_ab2013_narratives})")

    # Append the non-VLOP harmonised-template reports into the same star schema
    # (from the vendored snapshot, or the sibling repo's extracted CSVs in dev).
    import seed_harmonised
    h = seed_harmonised.build_harmonised_facts(args.db)
    if h:
        print(f"  harmonised reports: {h['services']} services, {h['reports']} reports, "
              f"{h['facts']} fact rows")
    else:
        print("  (skipping harmonised reports — no snapshot or extracted dir found)")

    # Index the DSA Table-11 qualitative prose for full-text search — LAST, so it
    # covers both the VLOP t11 rows and the non-VLOP harmonised ones just appended.
    dsa_nar = build_dsa_narratives(args.db)
    print(f"  dsa narratives: {dsa_nar} qualitative descriptions indexed")


if __name__ == "__main__":
    main()
