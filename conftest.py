"""Pytest configuration — runs before any test file is imported.

Builds a small VLOP-DSA-shaped SQLite DB (via seed.build_db, the same code path
the real seed uses) and sets DB_PATH/API_KEYS_JSON env vars so main.py picks
them up at module-level import time, which happens after this file is loaded.
"""
import os
import tempfile

import seed

_tmp = tempfile.mkdtemp()
_DB = os.path.join(_tmp, "test.db")

# A tiny but representative slice of the vlop-dsa.json shape: 2 services across
# 2 platforms, a couple of categories/sections/indicators/scopes/surfaces, and a
# few fact rows per report table (chosen so aggregations have known totals).
_FIXTURE = {
    "meta": {"period": "2025-07-01/2025-12-31", "generated": "2026-05-13"},
    "services": ["YouTube", "Facebook"],
    "service_platforms": ["Google", "Meta"],
    "categories": ["TOTAL", "STATEMENT_CATEGORY_ILLEGAL_OR_HARMFUL_SPEECH"],
    "category_labels": {"TOTAL": "All the entries",
                        "STATEMENT_CATEGORY_ILLEGAL_OR_HARMFUL_SPEECH": "Illegal or harmful speech"},
    "sections": ["Internal complaints mechanism"],
    "indicators": ["Number of complaints submitted to the internal-complaints mechanism", "Summary"],
    "scopes": ["Total number", "Decisions upheld"],
    "surfaces": ["All", "Ads"],
    # t3: [svc, cat, scope, orders_to_act, items, orders_to_provide_info]
    "t3": [[0, 0, 0, 11, 22, 3], [1, 0, 0, 5, 6, 1]],
    # t4: [svc, cat, notices, tf_notices, items, tf_items, median, tf_median, act_law, tf_act_law, act_tos, tf_act_tos]
    "t4": [[0, 0, 100, 10, 200, 20, 5, None, 30, 3, 70, 7],
           [0, 1, 40, 4, 80, 8, 6, None, 10, 1, 30, 3],
           [1, 0, 50, 5, 90, 9, 4, None, 20, 2, 30, 3]],
    # t5: 18 cols [svc, cat, measures, automated, 7 vis_*, 3 monetary_*, service x2, account x2]
    "t5": [[0, 0, 9, 4, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]],
    # t6: t5 + surface_id
    "t6": [[0, 0, 9, 4, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]],
    # t7/t8: [svc, section, indicator, scope, value, surface]
    "t7": [[0, 0, 0, 0, 1000, 0], [1, 0, 0, 0, 500, 0]],
    "t8": [[0, 0, 0, 0, 7, 0]],
    # t9: [svc, section, indicator, scope, value]
    "t9": [[0, 0, 0, 0, 12]],
    # t10: [svc, scope, value]
    "t10": [[0, 0, 64767887], [1, 0, 50000000]],
    # t11: [svc, indicator, value_text] — the second row's leading "=" exercises
    # the CSV formula-injection escaping (test_csv_download_escapes_formula_cells).
    "t11": [[0, 1, "YouTube qualitative summary text."],
            [1, 1, '=HYPERLINK("http://evil.example/x")'],
            # A substantial description so build_dsa_narratives indexes it (short
            # cells like the two above are below the prose threshold and skipped).
            [0, 1, "YouTube uses automated tools supplemented by human review to "
                   "moderate content across its products, and reports the outcome "
                   "of appeals against those content-moderation decisions."]],
}

seed.build_db(_FIXTURE, _DB)

_GR_FIXTURE = {
    "periods": ["January - June 2019", "July - December 2019"],
    "countries": ["US", "DE"],
    "country_names": ["United States", "Germany"],
    "requestors": ["Government Officials", "Court Order directed at Google"],
    "products": ["Web Search", "YouTube"],
    "reasons": ["Defamation", "National security"],
    "rows": [
        [0, 0, 0, 0, 0, 5, 100, 80, 5, 10, 3, 2, 0],
        [0, 1, 1, 1, 1, 3, 50, 40, 2, 5, 2, 1, 0],
        [1, 0, 0, 0, 0, 7, 120, 90, 8, 12, 5, 5, 0],
    ],
}
seed.build_gr_db(_GR_FIXTURE, _DB)

# A small slice of the Apple Transparency dataset (apple-transparency.json shape).
_APPLE_MEASURES = [
    "requests_received", "items_specified", "requests_data_provided",
    "pct_data_provided", "requests_challenged_rejected", "requests_no_data",
    "content_provided", "noncontent_provided", "accounts_preserved",
    "accounts_restricted", "accounts_deleted", "requests_app_removed",
    "apps_removed", "appeals_received", "appeals_granted", "apps_reinstated",
]
_APPLE_FIXTURE = {
    "measures": _APPLE_MEASURES,
    "periods": ["2024 H1", "2024 H2"],
    "countries": ["Germany", "United States of America"],
    "request_types": ["device", "account"],
    # [period, country, request_type] + 16 measures (order = _APPLE_MEASURES).
    # device populates received/specified/data_provided/pct; account adds
    # content/non-content; all other measures stay NULL.
    "rows": [
        [0, 1, 0, 12043, 42747, 10377, 86.0] + [None] * 12,
        [0, 0, 0, 200, 300, 150, 75.0] + [None] * 12,
        # account US 2024 H2: received, specified, (no data_provided), pct,
        # challenged=100, (no no_data), content=4000, noncontent=1000, rest NULL.
        [1, 1, 1, 5000, 9000, None, 90.0, 100, None, 4000, 1000] + [None] * 8,
    ],
    # [period, country, ns_type, req_low, req_high, acc_low, acc_high]
    "ns_rows": [
        [0, 1, "National Security", 0, 249, 0, 249],
        [1, 1, "FISA Content", 250, 499, 250, 499],
    ],
}
seed.build_apple_db(_APPLE_FIXTURE, _DB)

# A small slice of the GitHub Transparency dataset (github-transparency.json shape).
# [year, period, dataset, government, iso2, category, metric, count_low, count_high]
_GITHUB_FIXTURE = {
    "columns": ["year", "period", "dataset", "government", "iso2", "category",
                "metric", "count_low", "count_high"],
    "rows": [
        [2025, "", "government_takedowns_received", "Brazil", "BR", "", "received", 4, 4],
        [2025, "", "user_info_requests", "", "", "criminal court order", "received", 115, 115],
        [2025, "", "user_info_requests", "", "", "criminal court order", "disclosed", 82, 82],
        # national_security: a banded range (count_low != count_high).
        [2025, "Jul-Dec", "national_security", "", "", "Affected accounts", "count", 1000, 1249],
    ],
}
seed.build_github_db(_GITHUB_FIXTURE, _DB)

# A small slice of the Snap Transparency dataset (snap-transparency.json shape).
# [period, section, category, sub_category_1, sub_category_2, metric, value]
_SNAP_FIXTURE = {
    "columns": ["period", "section", "category", "sub_category_1",
                "sub_category_2", "metric", "value"],
    "rows": [
        ["2024-H1", "Ads Moderation", "Global", "", "", "total_ads_removed", 10711],
        ["2024-H1", "Overview of Our T&S Enforcements", "Country", "Afghanistan",
         "Drugs", "total_enforcements", 27],
        # a median metric — must not be summed
        ["2024-H1", "Overview of Our T&S Enforcements", "Country", "Afghanistan",
         "Child Sexual Exploitation", "median_turnaround_time_minutes", 51.68],
        ["2024-H2", "Governmental Content & Account Removal Requests", "Global",
         "", "", "total_requests", 42],
    ],
}
seed.build_snap_db(_SNAP_FIXTURE, _DB)

# A small slice of the India IT Rules dataset (india-it-rules.json shape).
# [platform, period, section, category, metric, unit, value]
_INDIA_FIXTURE = {
    "columns": ["platform", "period", "section", "category", "metric", "unit", "value"],
    "rows": [
        ["Facebook", "2023-06", "content_actioned_proactive",
         "Adult Nudity and Sexual Activity", "content_actioned", "approx_count", 2300000],
        ["Facebook", "2023-06", "content_actioned_proactive",
         "Adult Nudity and Sexual Activity", "proactive_rate", "percent", 97.7],
        ["Facebook", "2023-06", "grievances_received", "BullyingorHarassment",
         "reports", "count", 10038],
        ["Instagram", "2023-06", "grievances_received", "BullyingorHarassment",
         "reports", "count", 5485],
        ["Meta", "2023-06", "gac_orders", "", "orders_received", "count", 3],
        ["Twitter", "2022-10", "grievances", "Abuse / Harassment",
         "grievances_received", "count", 582],
        ["Moj", "2021-06", "complaints", "", "complaints_received", "count", 1958124],
    ],
}
seed.build_india_db(_INDIA_FIXTURE, _DB)

# A small slice of the Korea transparency dataset (korea-transparency.json shape).
# [platform, service, period, category, metric, unit, value]
_KOREA_FIXTURE = {
    "columns": ["platform", "service", "period", "category", "metric", "unit", "value"],
    "rows": [
        ["Naver", "", "2025-H2", "seizure_warrant", "requests", "count", 4355],
        ["Naver", "", "2025-H2", "seizure_warrant", "processed", "count", 3028],
        ["Naver", "", "2025-H2", "seizure_warrant", "accounts", "count", 371271],
        ["Naver", "", "2025-H2", "seizure_warrant", "processed_rate", "percent", 70],
        ["Naver", "", "2025-H2", "seizure_warrant", "accounts_per_processed", "average", 123],
        ["Kakao", "Kakao", "2024-H2", "seizure_warrant", "requests", "count", 14596],
        ["Kakao", "Daum", "2024-H2", "comm_confirmation_data", "requests", "count", 759],
        # zero is reported data (both platforms stopped providing 통신자료 in 2012)
        ["Kakao", "Kakao", "2024-H2", "comm_user_information", "processed", "count", 0],
    ],
}
seed.build_korea_db(_KOREA_FIXTURE, _DB)

# A small slice of the Taiwan Anti-Fraud dataset (taiwan-anti-fraud.json shape).
# [publisher, period, section, category, metric, unit, value]
_TAIWAN_FIXTURE = {
    "columns": ["publisher", "period", "section", "category", "metric", "unit", "value"],
    "rows": [
        ["NPA-165", "2025-12", "dns_blocked_sites", "金融保險", "sites_blocked", "count", 7000],
        ["NPA-165", "2025-12", "dns_blocked_sites", "電子商務", "sites_blocked", "count", 2100],
        ["NPA-165", "2026-05", "dns_blocked_sites", "金融保險", "sites_blocked", "count", 6500],
        ["NPA-165", "2026-05", "dns_blocked_sites", "釣魚網站", "sites_blocked", "count", 33],
        # Platform statutory reports: coverage-window periods, empty category.
        ["Google", "2024-07..2025-06", "afa_transparency_report", "", "government_requests", "count", 236],
        ["Google", "2024-07..2025-06", "afa_transparency_report", "", "urls_removed", "count", 3564],
        ["LINE", "2024-08..2025-09", "afa_transparency_report", "", "art33_accounts_suspended", "count", 102359],
        ["TikTok", "2025-01..2025-09", "platform_enforcement", "", "fraud_ads_removed_taiwan", "count", 23164],
    ],
}
seed.build_taiwan_db(_TAIWAN_FIXTURE, _DB)

# A small slice of the Türkiye Law 5651 dataset (turkey-law5651.json shape):
# Meta (Facebook + Instagram, both request streams — individual Art. 9/9-A and
# authority Art. 8/8-A with the per-authority breakdown, blank category) plus X
# (individual stream broken down by issue category, with a requests count and an
# action_rate percent).
# [platform, period, section, category, metric, unit, value]
_TURKEY_FIXTURE = {
    "columns": ["platform", "period", "section", "category", "metric", "unit", "value"],
    "rows": [
        ["Facebook", "2024 H2", "individual_requests", "", "applications_received", "count", 294],
        ["Facebook", "2024 H2", "authority_requests", "", "requests_total", "count", 2724],
        ["Facebook", "2024 H2", "authority_requests", "", "requests_icta", "count", 2350],
        ["Facebook", "2024 H2", "authority_requests", "", "requests_consumer_policy", "count", 118],
        ["Facebook", "2024 H2", "authority_requests", "", "requests_court_orders", "count", 256],
        ["Instagram", "2024 H2", "individual_requests", "", "applications_received", "count", 303],
        ["Instagram", "2024 H2", "authority_requests", "", "requests_total", "count", 2842],
        ["Instagram", "2025 H1", "authority_requests", "", "requests_total", "count", 9471],
        ["X", "2024 H2", "individual_requests", "Abuse", "requests", "count", 228623],
        ["X", "2024 H2", "individual_requests", "Abuse", "action_rate", "percent", 52.87],
        ["X", "2024 H2", "individual_requests", "Copyright", "requests", "count", 6083],
        ["X", "2024 H2", "individual_requests", "Copyright", "action_rate", "percent", 68.95],
        ["X", "2025 H1", "individual_requests", "Abuse", "requests", "count", 563954],
        ["X", "2025 H1", "individual_requests", "Abuse", "action_rate", "percent", 0.05],
    ],
}
seed.build_turkey_db(_TURKEY_FIXTURE, _DB)

# A small slice of the Meta CSER dataset (meta-cser.json shape): Facebook +
# Instagram, a couple of policy areas and quarters, mixing count metrics
# (Content Actioned) and percent metrics (Proactive rate, prevalence bounds),
# plus a 'Cross-Policy Data' aggregate row.
# [app, policy_area, metric, period, unit, value]
_CSER_FIXTURE = {
    "columns": ["app", "policy_area", "metric", "period", "unit", "value"],
    "rows": [
        ["Facebook", "Hateful Conduct", "Content Actioned", "2025 Q3", "count", 8100000],
        ["Facebook", "Hateful Conduct", "Content Actioned", "2025 Q4", "count", 7500000],
        ["Facebook", "Hateful Conduct", "Proactive rate", "2025 Q4", "percent", 94.4],
        ["Facebook", "Hateful Conduct", "Lowerbound Prevalence", "2025 Q4", "percent", 0.06],
        ["Facebook", "Hateful Conduct", "Upperbound Prevalence", "2025 Q4", "percent", 0.08],
        ["Facebook", "Spam", "Content Actioned", "2025 Q4", "count", 1200000000],
        ["Facebook", "Spam", "Proactive rate", "2025 Q4", "percent", 99.7],
        ["Facebook", "Cross-Policy Data", "Content Appealed", "2025 Q4", "count", 500000],
        ["Instagram", "Hateful Conduct", "Content Actioned", "2025 Q4", "count", 3300000],
    ],
}
seed.build_cser_db(_CSER_FIXTURE, _DB)

# A small slice of the Singapore IMDA Online Safety dataset
# (singapore-online-safety.json shape): the 'assessment' benchmark (action_rate
# percent + time_to_action days per service × round) and 'platform_report'
# per-service Singapore figures (Meta per-category, YouTube by-reason).
# [service, period, section, category, metric, unit, value]
_SINGAPORE_FIXTURE = {
    "columns": ["service", "period", "section", "category", "metric", "unit", "value"],
    "rows": [
        ["Facebook", "2023-08..2024-07", "assessment", "", "action_rate", "percent", 53],
        ["Facebook", "2024-04..2025-03", "assessment", "", "action_rate", "percent", 81],
        ["Facebook", "2024-04..2025-03", "assessment", "", "time_to_action", "days", 4],
        ["TikTok", "2023-08..2024-07", "assessment", "", "action_rate", "percent", 39],
        ["TikTok", "2024-04..2025-03", "assessment", "", "action_rate", "percent", 25],
        ["Facebook", "2024-04..2025-03", "platform_report", "Hateful Conduct", "content_actioned_sg", "count", 26300],
        ["Facebook", "2024-04..2025-03", "platform_report", "Hateful Conduct", "proactive_rate_sg", "percent", 90.6],
        ["YouTube", "2024-04..2025-03", "platform_report", "Child Abuse", "flags_received_sg", "count", 21685],
        ["YouTube", "2024-04..2025-03", "platform_report", "Child Safety", "videos_removed_sg", "count", 14644],
        ["X", "2024-04..2025-03", "platform_report", "", "median_time_to_action_hours", "hours", 69],
    ],
}
seed.build_singapore_db(_SINGAPORE_FIXTURE, _DB)

# A small slice of the Japan 情プラ法 dataset (japan-info-platform.json shape):
# LY Corporation services, a quarter + the annual total, mixing count metrics
# (posts, posts_removed) with a percent (removal_rate).
# [service, period, metric, unit, value]
_JAPAN_FIXTURE = {
    "columns": ["service", "period", "metric", "unit", "value"],
    "rows": [
        ["Yahoo! Chiebukuro", "2024-04..2024-06", "posts", "count", 17294266],
        ["Yahoo! Chiebukuro", "2024-04..2024-06", "posts_removed", "count", 111889],
        ["Yahoo! Chiebukuro", "2024-04..2025-03", "posts", "count", 66199309],
        ["Yahoo! Chiebukuro", "2024-04..2025-03", "posts_removed", "count", 444727],
        ["Yahoo! Chiebukuro", "2024-04..2025-03", "removal_rate", "percent", 0.7],
        ["LINE OpenChat", "2024-04..2025-03", "posts", "count", 5514828787],
        ["LINE OpenChat", "2024-04..2025-03", "posts_removed", "count", 6980935],
        ["LINE OpenChat", "2024-04..2025-03", "removal_rate", "percent", 0.1],
    ],
}
seed.build_japan_db(_JAPAN_FIXTURE, _DB)

# A small slice of the Google user-data dataset (google-user-data.json shape).
# [dataset, period, country, iso2, product, legal_process, assisting_country,
#  metric, unit, value_low, value_high]
_GOOGLE_UD_FIXTURE = {
    "columns": ["dataset", "period", "country", "iso2", "product", "legal_process",
                "assisting_country", "metric", "unit", "value_low", "value_high"],
    "rows": [
        ["global", "2011-H2", "Brazil", "BR", "", "All", "", "requests", "count", 1615, 1615],
        ["global", "2011-H2", "Brazil", "BR", "", "All", "", "pct_disclosed", "percent", 90, 90],
        ["global", "2011-H2", "Brazil", "BR", "", "All", "", "accounts", "count", 2222, 2222],
        ["global", "2024-H1", "United States", "US", "", "Search Warrants", "", "requests", "count", 31839, 31839],
        ["global", "2024-H1", "United States", "US", "", "Subpoenas", "", "requests", "count", 20006, 20006],
        ["global_diplomatic", "2024-H1", "Brazil", "BR", "", "", "United States", "requests", "count", 12, 12],
        ["enterprise", "2024-H1", "United States", "US", "Google Workspace", "Search Warrants", "", "requests", "count", 77, 77],
        # US national-security figures are banded ranges (non-additive).
        ["us_nsl", "2009-H1", "United States", "US", "", "", "", "requests", "count", 0, 499],
        ["us_nsl", "2009-H1", "United States", "US", "", "", "", "accounts", "count", 500, 999],
    ],
}
seed.build_google_userdata_db(_GOOGLE_UD_FIXTURE, _DB)

# A small slice of the Microsoft LERR dataset (microsoft-lerr.json shape).
# [period, section, country, metric, unit, value]
_MICROSOFT_FIXTURE = {
    "columns": ["period", "section", "country", "metric", "unit", "value"],
    "rows": [
        ["2013-H1", "combined", "Argentina", "requests", "count", 455],
        ["2013-H1", "combined", "Argentina", "accounts_specified", "count", 675],
        ["2013-H1", "skype", "Argentina", "requests", "count", 12],
        ["2024-H2", "criminal", "Germany", "requests", "count", 5924],
        ["2024-H2", "criminal", "Germany", "disclosed_noncontent", "count", 4433],
        ["2024-H2", "emergencies", "Germany", "requests", "count", 29],
        ["2024-H2", "civil", "United States", "requests", "count", 110],
    ],
}
seed.build_microsoft_db(_MICROSOFT_FIXTURE, _DB)

# A small slice of the LinkedIn dataset (linkedin-transparency.json shape).
# [dataset, period, country, metric, unit, value_low, value_high]
_LINKEDIN_FIXTURE = {
    "columns": ["dataset", "period", "country", "metric", "unit",
                "value_low", "value_high"],
    "rows": [
        ["member_data_requests", "2025-H2", "United States", "requests", "count", 443, 443],
        ["member_data_requests", "2025-H2", "United States", "pct_disclosed", "percent", 80, 80],
        ["member_data_requests", "2025-H2", "Australia", "requests", "count", 11, 11],
        ["us_breakdown", "2025-H2", "United States", "requests", "count", 443, 443],
        ["us_breakdown", "2025-H2", "United States", "pct_subpoenas", "percent", 66, 66],
        # National-security figures are banded ranges (non-additive).
        ["us_breakdown", "2025-H2", "United States", "nsl_received", "count", 0, 499],
        ["content_removal_requests", "2025-H2", "Australia", "requests", "count", 4, 4],
        ["content_removal_requests", "2025-H2", "Australia", "action_taken", "count", 2, 2],
    ],
}
seed.build_linkedin_db(_LINKEDIN_FIXTURE, _DB)

# A small slice of the TikTok Government & Legal Requests dataset
# (tiktok-transparency.json shape). [dataset, period, country, metric, unit, value]
_TIKTOK_FIXTURE = {
    "columns": ["dataset", "period", "country", "metric", "unit", "value"],
    "rows": [
        # government_removals — per-country rows plus the global 'All' aggregate.
        ["government_removals", "2025-H2", "United States", "total_requests_received", "count", 28],
        ["government_removals", "2025-H2", "United States", "content_specified", "count", 15],
        ["government_removals", "2025-H2", "United States", "removal_rate", "percent", 0.875],
        ["government_removals", "2025-H2", "All", "total_requests_received", "count", 5000],
        ["government_removals", "2019-H1", "United States", "total_requests_received", "count", 99],
        # information_requests
        ["information_requests", "2025-H2", "United States", "legal_requests", "count", 100],
        ["information_requests", "2025-H2", "United States", "pct_legal_disclosed", "percent", 0.5],
        # ip_removals — global-only.
        ["ip_removals", "2025-H2", "All", "total_ip_requests", "count", 476553],
        ["ip_removals", "2025-H2", "All", "pct_successful", "percent", 0.636682594],
    ],
}
seed.build_tiktok_db(_TIKTOK_FIXTURE, _DB)

# A small slice of the Discord Transparency Reports dataset
# (discord-transparency.json shape). [period, section, category, metric, unit, value]
_DISCORD_FIXTURE = {
    "columns": ["period", "section", "category", "metric", "unit", "value"],
    "rows": [
        # enforcement — accounts disabled by policy category
        ["2024-H1", "accounts_disabled", "Child Safety", "accounts_disabled", "count", 178165],
        ["2024-H1", "accounts_disabled", "Hateful Conduct", "accounts_disabled", "count", 5457],
        # appeals — carries a percentage rate
        ["2024-H1", "appeals", "Child Safety", "appeals", "count", 36202],
        ["2024-H1", "appeals", "Child Safety", "pct_of_appeals_granted", "percent", 2.14],
        # government/legal requests by country / request type
        ["2024-H1", "us_gov_info_requests", "Subpoenas", "requests", "count", 2065],
        ["2024-H1", "us_gov_info_requests", "Subpoenas", "information_produced", "count", 1609],
        ["2024-H1", "international_government_information_requests", "Germany", "requests", "count", 90],
        # era-varying section label (older quarterly report)
        ["2023-Q3", "us_gov_info_requests", "Subpoenas", "requests", "count", 100],
    ],
}
seed.build_discord_db(_DISCORD_FIXTURE, _DB)

# A small slice of the Google Traffic & Disruptions catalogue (google-traffic.json
# shape). A flat catalogue: one row per disruption event. The Syria row omits its
# start_date/year (Google published only an end date) so the suite exercises the
# null-grouping + "nulls last" ordering the endpoint relies on.
_TRAFFIC_FIXTURE = {
    "columns": ["country", "iso2", "product", "start_date", "end_date", "year",
                "source", "source_url", "title", "excerpt", "disruption_url"],
    "rows": [
        ["Sudan", "SD", "Web Search", "2021-10-25", "2021-11-18", "2021",
         "Quartz", "https://qz.com/x", "Sudan shuts down the internet",
         "coup aftermath", "https://transparencyreport.google.com/traffic/overview?a=1"],
        ["Burkina Faso", "BF", "Web Search", "2021-11-21", "2021-11-28", "2021",
         "Bloomberg", "https://bloomberg.com/x", "Burkina Faso extends outage",
         "before protests", "https://transparencyreport.google.com/traffic/overview?a=2"],
        ["Bangladesh", "BD", "YouTube", "2009-03-06", "2009-03-11", "2009",
         "BBC", "http://news.bbc.co.uk/x", "Bangladesh blocks YouTube",
         "leaked recording", "https://transparencyreport.google.com/traffic/overview?a=3"],
        ["Syria", "SY", "YouTube", None, "2011-02-08", None,
         "Associated Press", "http://ap.org/x", "Syria appears to lift ban",
         "first time in three years", "https://transparencyreport.google.com/traffic/overview?a=4"],
    ],
}
seed.build_google_traffic_db(_TRAFFIC_FIXTURE, _DB)

# A small slice of the Android ecosystem security (PHA rates) dataset
# (android-security.json shape). Covers all five sections and both metrics/units,
# so the suite exercises the rate-vs-percent distinction and the SUM guardrail.
# [section, period, category, metric, unit, value]
_ANDROID_FIXTURE = {
    "columns": ["section", "period", "category", "metric", "unit", "value"],
    "rows": [
        ["devices_with_pha", "2024-12-31", "All Devices", "pha_rate", "rate", 0.00099],
        ["devices_with_pha", "2024-12-31", "Enterprise devices", "pha_rate", "rate", 5.6e-05],
        ["devices_by_version", "2024-12-31", "15", "pha_rate", "rate", 0.00026],
        ["devices_by_version", "2024-12-31", "KitKat", "pha_rate", "rate", 0.0111],
        ["installs", "2024-12-31", "Google Play", "pha_rate", "rate", 0.00082],
        ["installs_by_country", "2024-12-31", "US", "pha_rate", "rate", 0.00032],
        ["installs_by_country", "2024-12-31", "IN", "pha_rate", "rate", 0.00202],
        # by-category yields two measures per source row: the rate and its share.
        ["installs_by_category", "2024-12-31", "Riskware", "pha_rate", "rate", 9.9e-05],
        ["installs_by_category", "2024-12-31", "Riskware", "category_share", "percent", 21.43],
        ["installs_by_category", "2024-12-31", "Backdoor", "category_share", "percent", 2.9],
    ],
}
seed.build_android_db(_ANDROID_FIXTURE, _DB)

# A small slice of the non-VLOP report-locations catalogue (report-locations.csv).
_RL_FIXTURE = [
    # Reddit deliberately omits the optional columns (company / harmonised_template /
    # format_period / url_label) so the suite exercises NULL handling in the API
    # JSON projection and the CSV export.
    {"platform": "Reddit", "category": "Social, messaging, community & video",
     "confidence": "likely", "url": "https://support.reddithelp.com/hc/en-us/articles/dsa"},
    {"platform": "Discord", "company": "Discord Netherlands B.V.", "category": "Social, messaging, community & video",
     "confidence": "verified", "harmonised_template": "yes", "format_period": "ZIP (template); 2024 & 2025",
     "url_label": "Hub", "url": "https://discord.com/safety-transparency",
     "archived": "https://github.com/krMaynard/dsa-transparency-data/tree/main/pdf-reports/discord"},
    {"platform": "Vinted", "company": "Vinted UAB", "category": "E-commerce marketplaces & retail",
     "confidence": "verified", "harmonised_template": "yes", "format_period": "XLSX; 2024 & 2025",
     "url_label": "Safety hub", "url": "https://www.vinted.com/safety"},
]
seed.build_report_locations(_RL_FIXTURE, _DB)

# A tiny slice of the NY Social Media ToS catalogue: one publicly-archived filing
# and one login-gated one, so the access facet + archived-link rendering are both
# exercised.
_NY_TOS_FIXTURE = [
    {"company": "Snap Inc", "platform": "", "period": "2025 Q3", "upload_date": "01-01-2026",
     "access": "public", "source_url": "https://ag.ny.gov/sites/default/files/social-media-policy-report/2025-q3-snap-inc-policy.pdf",
     "filename": "2025-q3-snap-inc.pdf",
     "archived": "https://github.com/krMaynard/dsa-transparency-data/blob/main/ny-tos-reports/pdfs/2025-q3-snap-inc.pdf",
     "sha256": "abc123", "bytes": "11222370"},
    {"company": "TikTok Inc", "platform": "", "period": "2025 Q4", "upload_date": "04-01-2026",
     "access": "auth-required", "source_url": "https://ag.ny.gov/system/files/webform/social_media_terms_of_service_re/106547/2025-q4-tiktok-inc-policy.pdf",
     "filename": "", "archived": "", "sha256": "", "bytes": ""},
]
seed.build_ny_tos_reports(_NY_TOS_FIXTURE, _DB)

# A tiny slice of the NY ToS report narratives (ny-tos-narratives.json shape),
# seeded into the FTS5 table. The Snap page matches the archived Snap filing so
# the archived-PDF deep link (#page=) is exercised; the TikTok page has no
# public archive. [company, platform, period, page, heading, text]
_NARRATIVES_FIXTURE = {
    "columns": ["company", "platform", "period", "page", "heading", "text"],
    "rows": [
        ["Snap Inc", "", "2025 Q3", 5, "Hateful Content",
         "Snap prohibits hate speech and removes content that demeans a protected group."],
        ["Snap Inc", "", "2025 Q3", 7, "",
         "We disclose the number of appeals received and how many were granted."],
        ["TikTok Inc", "", "2025 Q4", 3, "",
         "This report describes our approach to misinformation and coordinated harassment."],
    ],
}
seed.build_ny_tos_narratives(_NARRATIVES_FIXTURE, _DB)

# A tiny slice of the California AB 587 ToS catalogue (ca-ab587-reports.csv shape).
# Two platforms across two periods; archived/sha256/bytes blank (the AB 587 PDFs
# aren't mirrored in-repo — the catalogue points at oag.ca.gov).
_CA_AB587_FIXTURE = [
    {"company": "Snap Inc.", "platform": "Snap", "period": "2025 H2",
     "period_original": "Q3/Q4 2025", "access": "public",
     "source_url": "https://oag.ca.gov/sites/default/files/Snap%20AB587%20Q3-Q4%202025.pdf",
     "filename": "snap-2025-h2-aa11bb.pdf", "archived": "", "sha256": "", "bytes": ""},
    {"company": "Reddit, Inc.", "platform": "Reddit", "period": "2024 H1",
     "period_original": "Q1/Q2 2024", "access": "public",
     "source_url": "https://oag.ca.gov/sites/default/files/Reddit%20AB587%20Q1-Q2%202024.pdf",
     "filename": "reddit-2024-h1-cc22dd.pdf", "archived": "", "sha256": "", "bytes": ""},
]
seed.build_ca_ab587_reports(_CA_AB587_FIXTURE, _DB)

# A tiny slice of the AB 587 narratives (source='ca-ab587'), same page-per-row
# shape as the NY ToS narratives. [company, platform, period, page, heading, text]
_CA_AB587_NARRATIVES_FIXTURE = {
    "columns": ["company", "platform", "period", "page", "heading", "text"],
    "rows": [
        ["Snap Inc.", "Snap", "2025 H2", 4, "Extremism",
         "Snap's California AB 587 report explains how it defines extremism and enforces its policy against violent radicalization campaigns."],
        ["Reddit, Inc.", "Reddit", "2024 H1", 2, "",
         "Reddit's California report describes its disinformation policy and how it handles coordinated inauthentic behavior."],
    ],
}
seed.build_ca_ab587_narratives(_CA_AB587_NARRATIVES_FIXTURE, _DB)

# Index the DSA Table-11 qualitative prose (source='dsa') from the seeded t11
# rows — the same code path seed.main() runs after the harmonised append.
seed.build_dsa_narratives(_DB)

# A small slice of the normalized NY ToS stats (ny-tos-normalized.csv shape):
# a count + a percent for Snap (unit mixing), a Strava category_total + its
# format breakdown (grain double-count), and a Discord row (cross-company).
_NY_STATS_FIXTURE = [
    {"company": "snap-inc", "period": "2025 Q3", "shha_category": "hate_speech_or_racism",
     "original_label": "Hate Speech", "content_format": "", "grain": "category_total",
     "metric": "human_report", "submetric": "flagged_total", "value": "482240",
     "unit": "count", "page": "4"},
    {"company": "snap-inc", "period": "2025 Q3", "shha_category": "hate_speech_or_racism",
     "original_label": "Hate Speech", "content_format": "", "grain": "category_total",
     "metric": "human_report", "submetric": "vvr_human_pct", "value": "0.000205",
     "unit": "percent", "page": "4"},
    {"company": "strava-inc", "period": "2025 Q3", "shha_category": "harassment",
     "original_label": "Harassment", "content_format": "", "grain": "category_total",
     "metric": "flagged", "submetric": "flagged_total", "value": "20000",
     "unit": "count", "page": "3"},
    {"company": "strava-inc", "period": "2025 Q3", "shha_category": "harassment",
     "original_label": "Harassment - Profile", "content_format": "Profile",
     "grain": "breakdown", "metric": "flagged", "submetric": "flagged_total",
     "value": "6665", "unit": "count", "page": "4"},
    {"company": "discord-inc", "period": "2025 Q3", "shha_category": "hate_speech_or_racism",
     "original_label": "(A) Hate speech or racism", "content_format": "",
     "grain": "category_total", "metric": "Accounts Disabled", "submetric": "",
     "value": "279", "unit": "count", "page": "13"},
]
seed.build_ny_tos_stats(_NY_STATS_FIXTURE, _DB)

os.environ.setdefault("DB_PATH", _DB)
os.environ.setdefault("API_KEYS_JSON", '{"momo":{"name":"momo"},"honggildong":{"name":"honggildong"}}')
# Google sign-in config for the auth tests (token verification is monkeypatched).
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")
# Enables POST /api/ask; the LLM translation call itself is monkeypatched in tests,
# so no real Anthropic request is ever made.
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
# Don't let the rate limiters interfere with the HTTP tests (they share one
# TestClient IP / API key). The 429 paths are exercised with isolated stores.
os.environ.setdefault("PORTAL_REGISTER_MAX_PER_WINDOW", "10000")
os.environ.setdefault("QUERY_RATE_MAX_PER_WINDOW", "100000")
os.environ.setdefault("EXPLORE_RATE_MAX_PER_WINDOW", "100000")
os.environ.setdefault("LOG_FORMAT", "text")  # readable pytest output
# Allow webhook callbacks to loopback so the end-to-end test can hit a local
# capture server. The SSRF guard itself is unit-tested with the flag off.
os.environ.setdefault("CALLBACK_ALLOW_PRIVATE", "1")
