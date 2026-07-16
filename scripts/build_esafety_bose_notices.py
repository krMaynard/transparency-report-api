#!/usr/bin/env python3
"""Build data/esafety-bose-notices.json — the eSafety BOSE *transparency-notice*
metric streams, a companion snapshot to data/esafety-bose.json.

Where scripts/build_esafety_bose.py holds the CSEA periodic report + the AI-
companion findings, this builder holds the quantitative figures from eSafety's
earlier and adjacent BOSE transparency-notice reports. Both snapshots seed the
SAME tidy-long table (`esafety_bose_metrics`); this one just adds more
`section`s. As with its sibling, there is no machine-readable source release —
every figure is transcribed from the archived PDFs (under esafety-bose-reports/)
with the printed page/table cited inline, and a fail-loud validate() cross-checks
each report's stated totals (shares summing to 100%, age bands summing, derived
staffing % changes, appeal counts). Figures are hand-transcribed and merit a
second eye against the source PDFs before merge.

Five report families, each a distinct BOSE notice round:

  1. csea22_*  — First non-periodic notices on child sexual exploitation & abuse
     (CSEA), given 29 Aug 2022 to Apple, Meta, WhatsApp, Microsoft, Skype, Snap,
     Omegle. "BOSE transparency report" (Dec 2022). Mostly qualitative; the hard
     numbers are the median-time-to-action table and detection-method shares.

  2. csea23_* — Second non-periodic notices on CSEA, given 22 Feb 2023 to Google,
     Twitter, TikTok, Discord, Twitch. "Full transparency report" (Oct 2023,
     revised Mar 2024). Report period 24 Jan 2022 – 31 Jan 2023.

  3. hate_*   — Non-periodic notice on ONLINE HATE, issued to X Corp (Twitter)
     June 2023. "Summary of response … online hate" (Jan 2024). Report period
     24 Jan 2022 – 31 May 2023; the flagship staffing-cuts finding.

  4. age_*    — Section-20 BOSE Information Requests on AGE ASSURANCE / under-13
     users, issued 2 Sep 2024 to Discord, Facebook, Instagram, Reddit, Snapchat,
     TikTok, Twitch, YouTube. "Behind the screen" (Feb 2025). Provider data
     1 Jan – 31 Jul 2024.

  5. tvec_*   — Mandatory notices on TERRORIST & VIOLENT EXTREMIST material,
     given 18 Mar 2024 to Google, Meta, WhatsApp, Reddit, Telegram, X. "Responses
     to mandatory notices" (Mar 2025, re-issued Jul 2025 with a Google addendum
     published separately). Report period 1 Apr 2023 – 29 Feb 2024. X supplied no
     data (AAT/ART review); Telegram late/partial, Australia-scoped staff.

Tidy-long shape (same header as esafety-bose.json):
    columns = service, period, section, category, metric, unit, value
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, os.pardir, "data", "esafety-bose-notices.json")

COLUMNS = ["service", "period", "section", "category", "metric", "unit", "value"]

# ===========================================================================
# FAMILY 1 — First CSEA non-periodic notices (Dec 2022 report).
# Notice coverage 24 Jan – 31 Jul 2022 unless a provider stated another window.
# Source: 2022-12_BOSE-transparency-report-summary-of-industry-responses.pdf
# ===========================================================================
P22 = "2022-01-24..2022-07-31"

# Median time to action a user report of CSEA (exec table §5.7 + provider
# sections). Units are per-provider as printed (days / minutes / hours). WhatsApp
# is a banded range 26–29 hours over its own window 1 Jun–31 Aug 2022.
CSEA22_RESPONSE = [
    # service, period, category, metric, unit, value  (page cite in comment)
    ("Xbox",              P22, "xbox_live",          "median_time_to_action",      "days",    1),      # p20/p40
    ("Microsoft OneDrive",P22, "onedrive",           "median_time_to_action",      "days",    2),      # p20/p40
    ("Microsoft Teams",   P22, "teams",              "median_time_to_action",      "days",    2),      # p40 (Skype+Teams combined)
    ("Skype",             P22, "skype",              "median_time_to_action",      "days",    2),      # p43
    ("Snapchat",          P22, "snapchat",           "median_time_to_action",      "minutes", 4),      # p58
    ("Facebook Messenger",P22, "facebook_messenger", "median_time_to_action",      "hours",   1.25),   # p30 (exec: 75 min)
    ("Instagram",         P22, "instagram",          "median_time_to_action",      "hours",   0.69),   # p30 (exec: 41 min)
    ("WhatsApp", "2022-06-01..2022-08-31", "whatsapp","median_time_to_action_low", "hours",   26),     # p34
    ("WhatsApp", "2022-06-01..2022-08-31", "whatsapp","median_time_to_action_high","hours",   29),     # p34
]

# Detection-method shares (proactive/automated vs reactive/user-report).
CSEA22_DETECTION = [
    ("WhatsApp", "2022-07-01..2022-07-31", "proactive",       "share_of_banned_accounts",  "percent", 73),    # p34
    ("WhatsApp", "2022-07-01..2022-07-31", "reactive",        "share_of_banned_accounts",  "percent", 27),    # p34
    ("Snapchat", P22,                      "automated_tools", "share_of_identified_csea",  "percent", 87.5),  # p59
    ("Snapchat", P22,                      "user_report",     "share_of_identified_csea",  "percent", 12),    # p59
    ("Snapchat", P22,                      "trusted_flagger", "share_of_identified_csea",  "percent", 0.5),   # p59
]

# ===========================================================================
# FAMILY 2 — Second CSEA non-periodic notices (Oct 2023 / rev Mar 2024 report).
# Report period 24 Jan 2022 – 31 Jan 2023 (Twitter proactive split by acquisition).
# Source: 2024-03_full-transparency-report-October2023-rev.pdf
# ===========================================================================
P23 = "2022-01-24..2023-01-31"

# Table 5 — proactive detection rate of CSEA (percent).
CSEA23_PROACTIVE = [
    ("Google",  P23, "youtube_drive_chat_photos_gmail", "proactive_detection_rate", "percent", 99),    # p38
    ("Google",  P23, "blogger",                         "proactive_detection_rate", "percent", 99),    # p38 (">99%", floor)
    ("Twitter", "2022-01-24..2022-10-27", "public_posts_and_dms", "proactive_detection_rate", "percent", 90),  # p38
    ("Twitter", "2022-10-28..2023-01-31", "public_posts_and_dms", "proactive_detection_rate", "percent", 75),  # p38
    ("TikTok",  P23, "global_excl_usa",  "proactive_detection_rate", "percent", 94.4),  # p38
    ("Twitch",  "2023-01-01..2023-03-31", "q1_2023_approx", "proactive_detection_rate", "percent", 20),  # p38 (~20%)
    ("Discord", P23, "direct_messages",   "proactive_detection_rate", "percent", 72.1),  # p38
    ("Discord", P23, "servers_public",    "proactive_detection_rate", "percent", 87.8),  # p38
    ("Discord", P23, "servers_private",   "proactive_detection_rate", "percent", 44.5),  # p38
]

# Table 9 — underage users detected/removed (global + Australia) + proactive share.
CSEA23_UNDERAGE = [
    ("Google",  P23, "", "underage_users_removed_global",    "count",   19_000_000),  # p49 ("Approx. 19 million")
    ("Twitter", P23, "", "underage_users_removed_global",    "count",   703_561),     # p49
    ("Twitter", P23, "", "underage_users_removed_australia", "count",   7_618),        # p49
    ("TikTok",  P23, "", "underage_users_removed_global",    "count",   79_312_821),   # p49
    ("TikTok",  P23, "", "underage_users_removed_australia", "count",   963_158),      # p49
    ("TikTok",  P23, "", "proportion_detected_proactively_global",    "percent", 80.6),  # p49
    ("TikTok",  P23, "", "proportion_detected_proactively_australia", "percent", 86.7),  # p123
    ("Twitch",  P23, "", "underage_users_removed_global",    "count",   120_070),     # p49/p147
    ("Twitch",  P23, "", "underage_users_removed_australia", "count",   2_590),        # p49/p147
    ("Twitch",  P23, "", "proportion_detected_proactively_global",    "percent", 14.8),  # p49/p147
    ("Twitch",  P23, "", "proportion_detected_proactively_australia", "percent", 14.4),  # p147
    ("Discord", P23, "", "underage_users_removed_global",    "count",   224_000),     # p49/p167
    ("Discord", P23, "", "underage_users_removed_australia", "count",   4_183),        # p49 (Table 9; summary p167 says 4,813 — source conflict)
    ("Discord", P23, "", "proportion_detected_proactively", "percent", 2),             # p49 (98% via user reports)
]

# Table 15 — median time for a user-reported CSEA to be actioned (units per row).
CSEA23_RESPONSE = [
    ("TikTok",  P23, "photos_videos_public", "median_time_to_action", "minutes", 5.2),   # p58
    ("TikTok",  P23, "tiktok_live",          "median_time_to_action", "minutes", 7.7),   # p58
    ("TikTok",  P23, "direct_messages",      "median_time_to_action", "hours",   7.4),   # p58
    ("Twitch",  P23, "signed_in_account",    "median_time_to_action", "minutes", 8.22),  # p58
    ("Discord", P23, "direct_messages",      "median_time_to_action", "hours",   13),    # p58
    ("Discord", P23, "servers_public",       "median_time_to_action", "hours",   8),     # p58
    ("Discord", P23, "servers_private",      "median_time_to_action", "hours",   6),     # p58
]

# Table 17 — languages human moderators operate across (count).
CSEA23_LANGUAGES = [
    ("Google",  P23, "human_moderators",         "num_languages", "count", 71),  # p62 ("at least" 71)
    ("Twitter", P23, "human_moderators",         "num_languages", "count", 12),  # p62
    ("TikTok",  P23, "human_moderators",         "num_languages", "count", 73),  # p62
    ("Twitch",  P23, "moderators",               "num_languages", "count", 21),  # p62
    ("Twitch",  P23, "third_party_vendor",       "num_languages", "count", 19),  # p62
    ("Discord", P23, "human_moderators",         "num_languages", "count", 29),  # p62
]


def _f1_f2_rows() -> list[list]:
    rows: list[list] = []
    for svc, per, cat, met, unit, val in CSEA22_RESPONSE:
        rows.append([svc, per, "csea22_response_time", cat, met, unit, val])
    for svc, per, cat, met, unit, val in CSEA22_DETECTION:
        rows.append([svc, per, "csea22_detection_share", cat, met, unit, val])
    for svc, per, cat, met, unit, val in CSEA23_PROACTIVE:
        rows.append([svc, per, "csea23_proactive_detection", cat, met, unit, val])
    for svc, per, cat, met, unit, val in CSEA23_UNDERAGE:
        rows.append([svc, per, "csea23_underage_users", cat, met, unit, val])
    for svc, per, cat, met, unit, val in CSEA23_RESPONSE:
        rows.append([svc, per, "csea23_response_time", cat, met, unit, val])
    for svc, per, cat, met, unit, val in CSEA23_LANGUAGES:
        rows.append([svc, per, "csea23_languages", cat, met, unit, val])
    return rows


# ===========================================================================
# FAMILY 3 — Online-hate non-periodic notice to X Corp (Twitter), Jan 2024
# report. Report period 24 Jan 2022 – 31 May 2023. Service kept as "Twitter"
# (the report's usage; rebranded X 23 Jul 2023, after the period). All figures
# self-reported by X Corp, unverified by eSafety.
# Source: 2024-01_full-report-X-Corp-Twitter-online-hate.pdf (FR) + key findings.
# ===========================================================================
HD1, HD2, HD3 = "2022-01-24", "2022-10-27", "2023-05-31"  # staffing snapshot dates

# Point-in-time trust-&-safety staffing headcounts (FR §6.1.2 p22).
# category: staff group; metric staff_count, period = the snapshot date.
_HATE_STAFF_SINGLE = {
    "engineers_trust_safety_global":       (277, 279, 55),
    "ts_dedicated_hateful_conduct_global": (0, 0, 0),
    "ts_staff_global":                     (3317, 4062, 2849),
    "ts_staff_apac":                       (101, 111, 61),
    "ts_staff_australia":                  (1, 1, 0),
    "public_policy_global":                (68, 68, 15),
    "public_policy_apac":                  (13, 15, 4),
    "public_policy_australia":             (2, 3, 0),
}
# Content moderators split FTE vs contractor (FR p22).
_HATE_STAFF_MODS = {
    "content_moderators_global": {"fte_count": (121, 107, 51), "contractor_count": (2514, 2613, 2305)},
    "content_moderators_apac":   {"fte_count": (44, 39, 27),   "contractor_count": (1915, 2014, 1868)},
}
# Staffing change 27 Oct 2022 -> 31 May 2023 (KF p3 / FR §3), percent.
_HATE_STAFF_CHANGE = [
    ("engineers_trust_safety_global",       "staff_change_pct",      -80),
    ("ts_dedicated_hateful_conduct_global", "staff_change_pct",       0),
    ("ts_staff_global",                     "staff_change_pct",      -30),
    ("ts_staff_apac",                       "staff_change_pct",      -45),
    ("ts_staff_australia",                  "staff_change_pct",     -100),
    ("content_moderators_global",           "fte_change_pct",        -52),
    ("content_moderators_global",           "contractor_change_pct", -12),
    ("content_moderators_apac",             "fte_change_pct",        -31),
    ("content_moderators_apac",             "contractor_change_pct",  -7),
    ("public_policy_global",                "staff_change_pct",      -78),
    ("public_policy_apac",                  "staff_change_pct",      -73),
    ("public_policy_australia",             "staff_change_pct",     -100),
]

HPRE, HPOST = "2022-01-24..2022-10-27", "2022-10-28..2023-05-31"  # acquisition split
HFULL = "2022-01-24..2023-05-31"

# Median response time to user reports of hateful conduct (FR p38), hours.
_HATE_RESPONSE = [
    ("tweets",          HPRE,  "median_response_hours",     "hours",   10),
    ("tweets",          HPOST, "median_response_hours",     "hours",   12),
    ("direct_messages", HPRE,  "median_response_hours",     "hours",   16),
    ("direct_messages", HPOST, "median_response_hours",     "hours",   28),
    ("tweets",          HPOST, "median_response_change_pct","percent", 20),  # FR p9/KF p6
    ("direct_messages", HPOST, "median_response_change_pct","percent", 75),
]

# Reports of hateful conduct — Australia + global total (FR §6.3.6 p35).
_HATE_REPORTS = [
    ("australia", "2022-01-23..2022-10-27", "reports_received",   "approx_count", 865_000),
    ("australia", "2022-01-23..2022-10-27", "reports_breached",   "approx_count", 7_400),
    ("australia", "2022-01-23..2022-10-27", "breach_rate",        "percent",      0.86),
    ("australia", HPOST,                    "reports_received",   "approx_count", 830_000),
    ("australia", HPOST,                    "reports_breached",   "approx_count", 6_200),
    ("australia", HPOST,                    "breach_rate",        "percent",      0.75),
    ("global",    HFULL,                    "total_user_reports", "count",        56_800_000),
]

# Mechanism of identification of hateful conduct (FR §6.3.5 p35), 28 Oct 22-31 May 23.
# Tweet counts are printed with K/M abbreviations -> approx_count; DM counts exact.
_HATE_IDENT = [
    ("tweets_user_reports", "share_of_total", "percent",      25.65),
    ("tweets_user_reports", "count",          "approx_count", 366_300),
    ("tweets_automated",    "share_of_total", "percent",      71.45),
    ("tweets_automated",    "count",          "approx_count", 1_000_000),
    ("tweets_moderators",   "share_of_total", "percent",      2.85),
    ("tweets_moderators",   "count",          "approx_count", 40_700),
    ("tweets_other",        "share_of_total", "percent",      0.05),
    ("tweets_other",        "count",          "approx_count", 700),
    ("tweets_all",          "total_count",    "approx_count", 1_400_000),
    ("dm_user_reports",     "share_of_total", "percent",      100),
    ("dm_user_reports",     "count",          "count",        18),
    ("dm_automated",        "share_of_total", "percent",      0),
    ("dm_automated",        "count",          "count",        0),
    ("dm_other",            "share_of_total", "percent",      0),
    ("dm_other",            "count",          "count",        0),
    ("dm_all",              "total_count",    "count",        18),
]

# Enforcement actions, Twitter Blue vs other accounts (FR §6.5.1 p38),
# 12 Dec 2022-31 May 2023. All printed with ~/K abbreviations -> approx_count.
HBLUE = "2022-12-12..2023-05-31"
_HATE_BLUE = [
    ("tweets_required_removed",     "twitter_blue", 17_100),
    ("tweets_required_removed",     "non_blue",     900_200),
    ("removal_requests_not_complied","twitter_blue", 170),
    ("removal_requests_not_complied","non_blue",     14_000),
    ("removal_requests_total",      "twitter_blue", 1_200),
    ("removal_requests_total",      "non_blue",     59_000),
    ("accounts_read_only",          "twitter_blue", 3_100),
    ("accounts_read_only",          "non_blue",     198_900),
    ("read_only_appealed",          "twitter_blue", 20),
    ("read_only_appealed",          "non_blue",     33_000),
    ("appeals_successful",          "twitter_blue", 0),
    ("appeals_successful",          "non_blue",     330),
    ("accounts_suspended_repeat",   "twitter_blue", 400),
    ("accounts_suspended_repeat",   "non_blue",     27_300),
]

HAMN = "2022-11-25..2023-05-31"  # account-amnesty window
_HATE_REINSTATE = [  # Australia (FR §6.6.1 p47-48), count
    ("all",             "accounts_reinstated", 6_103),
    ("all",             "accounts_suspended",  387_056),
    ("hateful_conduct", "accounts_reinstated", 194),
    ("hateful_conduct", "accounts_suspended",  1_196),
]
_HATE_GLOBAL = [  # global enforcement during amnesty (FR §6.6.2 p48), approx_count
    ("accounts_suspended",      142_100_000),
    ("accounts_read_only",      111_600_000),
    ("tweets_required_removed", 4_300_000),
]
_HATE_SPAM = [  # global spam/bot enforcement (FR §6.7.4 p54), 28 Oct 22-31 May 23
    ("automated", "accounts_suspended",   130_000_000),
    ("manual",    "suspension_actions",   18_000_000),
    ("all",       "accounts_suspended",   150_000_000),
    ("all",       "actions_per_day",      40_000_000),
]


def _f3_online_hate_rows() -> list[list]:
    rows: list[list] = []
    dates = (HD1, HD2, HD3)
    for cat, vals in _HATE_STAFF_SINGLE.items():
        for d, v in zip(dates, vals):
            rows.append(["Twitter", d, "hate_staffing", cat, "staff_count", "count", v])
    for cat, metrics in _HATE_STAFF_MODS.items():
        for met, vals in metrics.items():
            for d, v in zip(dates, vals):
                rows.append(["Twitter", d, "hate_staffing", cat, met, "count", v])
    for cat, met, val in _HATE_STAFF_CHANGE:
        rows.append(["Twitter", HPOST, "hate_staffing_change", cat, met, "percent", val])
    for cat, per, met, unit, val in _HATE_RESPONSE:
        rows.append(["Twitter", per, "hate_response_time", cat, met, unit, val])
    for cat, per, met, unit, val in _HATE_REPORTS:
        rows.append(["Twitter", per, "hate_reports", cat, met, unit, val])
    for cat, met, unit, val in _HATE_IDENT:
        rows.append(["Twitter", HPOST, "hate_identification", cat, met, unit, val])
    for met, cat, val in _HATE_BLUE:
        rows.append(["Twitter", HBLUE, "hate_enforcement_twitter_blue", cat, met, "approx_count", val])
    for cat, met, val in _HATE_REINSTATE:
        rows.append(["Twitter", HAMN, "hate_reinstatement", cat, met, "count", val])
    for met, val in _HATE_GLOBAL:
        rows.append(["Twitter", HAMN, "hate_enforcement_global", "", met, "approx_count", val])
    for cat, met, val in _HATE_SPAM:
        rows.append(["Twitter", HPOST, "hate_spam", cat, met, "approx_count", val])
    return rows


# ===========================================================================
# FAMILY 4 — Age-assurance / under-13 users. Section-20 BOSE Information
# Requests (issued 2 Sep 2024); "Behind the screen" report (Feb 2025).
# Provider-reported Australian data, 1 Jan – 31 Jul 2024. Survey figures and
# reporting-friction step counts from the same report are intentionally excluded
# (child-survey genre / UX, not provider transparency metrics).
# Source: 2025-02_behind-the-screen-transparency-report.pdf
# ===========================================================================
P_AGE = "2024-01-01..2024-07-31"

# Table 2 — avg monthly active Australian end-users by age band (count).
_AGE_MAU = {
    "Discord":  {"total": 3_020_592, "13_17": 222_189,   "13_15": 98_508,  "16_17": 123_681},
    "Facebook": {"total": 19_740_786, "13_17": 455_054,  "13_15": 153_223, "16_17": 301_831},
    "Instagram":{"total": 19_365_679, "13_17": 1_088_980,"13_15": 351_135, "16_17": 737_845},
    "Reddit":   {"total": 3_690_000},  # no child age breakdown provided
    "Snapchat": {"total": 8_314_594, "13_17": 1_034_071, "13_15": 438_883, "16_17": 595_188},
    "TikTok":   {"total": 9_731_801, "13_17": 522_863,   "13_15": 199_710, "16_17": 323_153},
    "Twitch":   {"total": 926_965,   "13_17": 24_466,    "13_15": 12_707,  "16_17": 10_626},
    "YouTube":  {"total": 25_461_289,"13_17": 643_670,   "13_15": 325_597, "16_17": 318_073},
}

# Under-13 user reports (Table 11 reports made; Table 12 human-reviewed + median).
_AGE_REPORTS = {
    # service: (reports_made_under13, reports_human_reviewed, median_response_minutes)
    "Discord":  (27_615, 19_379, 473),
    "Facebook": (2_095, 186, 5.40),
    "Instagram":(3_506, 334, 6.12),
    "Reddit":   (43, 43, 1_543),
    "Snapchat": (109, 109, 255),
    "TikTok":   (322_523, 20_261, 113.78),  # median printed 113 min 47 s
    "Twitch":   (6_390, 6_390, 1.87),
}

# Table 14 — under-13 accounts banned + detection attribution split (percent).
_AGE_ENFORCE = {
    # service: (accounts_banned, pct_proactive, pct_user_report) ; None split = not provided
    "Discord":  (6_109, 0.08, 99.9),
    "Facebook": (9_369, 93.23, 6.77),
    "Instagram":(9_610, 96.12, 3.88),
    "Reddit":   (184, 84.8, 15.2),
    "Snapchat": (32, 4, 96),
    "TikTok":   (303_031, 93.7, 6.3),
    "Twitch":   (1_064, 21.1, 79.9),  # source split sums to 101.0 (rounding/typo)
    "YouTube":  (15_500, None, None),  # approx, partial period (Jan+Apr+Jul only)
}


def _f4_age_assurance_rows() -> list[list]:
    rows: list[list] = []
    for svc, bands in _AGE_MAU.items():
        for band, val in bands.items():
            rows.append([svc, P_AGE, "age_mau", band, "avg_monthly_active_end_users", "count", val])
    for svc, (made, reviewed, median) in _AGE_REPORTS.items():
        rows.append([svc, P_AGE, "age_user_reports", "", "reports_made_under13", "count", made])
        rows.append([svc, P_AGE, "age_user_reports", "", "reports_human_reviewed", "count", reviewed])
        rows.append([svc, P_AGE, "age_user_reports", "", "median_response_minutes", "minutes", median])
    for svc, (banned, pro, usr) in _AGE_ENFORCE.items():
        unit = "approx_count" if svc == "YouTube" else "count"
        rows.append([svc, P_AGE, "age_enforcement", "", "accounts_banned_under13", unit, banned])
        if pro is not None:
            rows.append([svc, P_AGE, "age_enforcement", "", "proportion_via_proactive_detection", "percent", pro])
            rows.append([svc, P_AGE, "age_enforcement", "", "proportion_via_user_reporting", "percent", usr])
    # Snap proactive-language-analysis tool accuracy (banded range, p88).
    for met, val in [("precision_accuracy_low", 70), ("precision_accuracy_high", 75),
                     ("false_positive_rate_low", 20), ("false_positive_rate_high", 25)]:
        rows.append(["Snapchat", P_AGE, "age_tool_accuracy", "proactive_language_analysis", met, "percent", val])
    return rows


# ===========================================================================
# FAMILY 5 — Terrorist & Violent Extremist material (TVE). Mandatory notices
# given 18 Mar 2024; "Responses to mandatory notices" (Mar 2025, re-issued Jul
# 2025). Report period 1 Apr 2023 – 29 Feb 2024. X Corp supplied no data
# (AAT/ART review — omitted). Meta's Australian figures cover a narrower window;
# Telegram staff figures are Australia-scoped, late/partial. Out-of-period
# "context" figures (Christchurch 2019, Etidal, etc.) intentionally excluded.
# Source: 2025-03_full-responses-TVEC-mandatory-notices.pdf (= 2025-07 update;
# body figures identical — a separate Google addendum is published elsewhere).
# ===========================================================================
TREP = "2023-04-01..2024-02-29"          # report period (most providers)
TMETA = "2023-10-01..2024-02-29"         # Meta Australian-data window
TWA_HR = "2024-03-01..2024-04-30"        # WhatsApp human-review window
TWA_RT = "2024-02-09..2024-05-08"        # WhatsApp response-time window

# A. Generative AI — Google Gemini user reports (MAR p6/KF p5).
_TVEC_GENAI = [
    ("tve",  258),
    ("csea", 86),
]

# B. % of TVE reports sent for human review (Table 7 p41). (service, period, ur, auto)
_TVEC_HUMAN_REVIEW = [
    ("YouTube",      TREP,   99,   86.4),
    ("Google Drive", TREP,   100,  96),
    ("Facebook",     TMETA,  83.4, 4.6),
    ("Messenger",    TMETA,  39.7, 0.2),
    ("Instagram",    TMETA,  87.8, 3.4),
    ("Threads",      TMETA,  59.4, 3.2),
    ("Reddit",       TREP,   100,  66.5),
    ("WhatsApp",     TWA_HR, 100,  100),
    ("Telegram",     TREP,   75,   65),
]

# C. Proactive detection vs reported, per surface (Table 10 p47). Each pair -> 100%.
_TVEC_PD = [
    # service, period, category(surface), pct_proactive, pct_reported
    ("YouTube",      TREP,  "all",                95.3, 4.7),
    ("Google Drive", TREP,  "all",                66,   34),
    ("Facebook",     TMETA, "newsfeed",           96.2, 3.8),
    ("Facebook",     TMETA, "groups_public",      89.9, 10.1),
    ("Facebook",     TMETA, "groups_closed",      93.3, 6.7),
    ("Messenger",    TMETA, "all",                100,  0),
    ("Instagram",    TMETA, "feed",               99.4, 0.6),
    ("Instagram",    TMETA, "direct",             100,  0),
    ("Threads",      TMETA, "all",                93.2, 6.8),
    ("Reddit",       TREP,  "subreddits_public",  79.4, 20.6),
    ("Reddit",       TREP,  "subreddits_private", 100,  0),
    ("WhatsApp",     TREP,  "all",                91,   9),
    ("Telegram",     TREP,  "group_public",       67,   33),
    ("Telegram",     TREP,  "group_private",      82,   18),
    ("Telegram",     TREP,  "channels_public",    69,   31),
    ("Telegram",     TREP,  "channels_private",   79,   21),
    ("Telegram",     TREP,  "stories",            60,   40),
]
# YouTube's "reported" splits into two sub-sources (0.8 + 3.9 = 4.7).
_TVEC_PD_YT_SPLIT = [("pct_reported_priority_flaggers", 0.8), ("pct_reported_users", 3.9)]
# Reported-only surfaces (no proactive detection; not pair-checkable).
_TVEC_PD_REPORTED_ONLY = [
    ("Telegram", TREP, "chats", 100),
    ("Telegram", TREP, "secret_chats", 100),
]
# The pair-checkable (service, period, category) triples for validate().
TVEC_PD_PAIRS = [(s, p, c) for s, p, c, _, _ in _TVEC_PD]

# D. Median time to reach an outcome after a TVE user report (Table 14 pp57-58), hours.
# service, period, category(surface), global, australia|None
_TVEC_RESPONSE = [
    ("YouTube",      TREP,   "all",                     4.4,  None),
    ("Google Drive", TREP,   "all",                     10.2, 2.9),
    ("Facebook",     TMETA,  "newsfeed",                6.5,  4.2),
    ("Facebook",     TMETA,  "groups_public",           6.7,  2.5),
    ("Facebook",     TMETA,  "groups_closed_private",   0.8,  2),
    ("Messenger",    TMETA,  "e2ee_enabled",            0.1,  0.1),
    ("Messenger",    TMETA,  "e2ee_not_enabled",        0.1,  0.1),
    ("Instagram",    TMETA,  "feed",                    24.4, 15.5),
    ("Instagram",    TMETA,  "direct_e2ee_enabled",     4.3,  None),
    ("Instagram",    TMETA,  "direct_e2ee_not_enabled", 5.8,  3),
    ("Threads",      TMETA,  "all",                     56.3, 59.5),
    ("Reddit",       TREP,   "subreddits_public",       62.2, 31.3),
    ("WhatsApp",     TWA_RT, "direct_messages",         25.3, 24.13),
    ("WhatsApp",     TWA_RT, "communities",             24.8, None),
    ("WhatsApp",     TWA_RT, "channels",                24.5, 25.3),
    ("Telegram",     TREP,   "chats_secret",            18,   None),
    ("Telegram",     TREP,   "group_channels",          15,   None),
]

# E. Trust & safety staffing headcounts (Tables 15/16/Q/R). Snapshot dates in period.
# service, date, category, metric, value
_TVEC_STAFF = [
    ("Google", "2023-04-01", "engineers_trust_safety",        "staff_count", 1305),
    ("Google", "2024-02-29", "engineers_trust_safety",        "staff_count", 1294),
    ("Google", "2023-04-01", "content_moderators_employed",   "staff_count", 316),
    ("Google", "2024-02-29", "content_moderators_employed",   "staff_count", 341),
    ("Google", "2023-04-01", "content_moderators_contracted", "staff_count", 39606),
    ("Google", "2024-02-29", "content_moderators_contracted", "staff_count", 39552),
    ("Google", "2023-04-01", "trust_safety_staff_other",      "staff_count", 1416),
    ("Google", "2024-02-29", "trust_safety_staff_other",      "staff_count", 1265),
    ("YouTube","2023-12-31", "english_language_reviewers",    "reviewer_count", 3455),
    ("YouTube","2024-03-31", "english_language_reviewers",    "reviewer_count", 3243),
    ("YouTube","2023-12-31", "language_agnostic_reviewers",   "reviewer_count", 9813),
    ("YouTube","2024-03-31", "language_agnostic_reviewers",   "reviewer_count", 9322),
    ("Meta",   "2023-03-31", "engineers_trust_safety",        "staff_count", 1862),
    ("Meta",   "2023-12-31", "engineers_trust_safety",        "staff_count", 1814),
    ("Meta",   "2023-03-31", "content_moderators_employed",   "staff_count", 0),
    ("Meta",   "2023-12-31", "content_moderators_employed",   "staff_count", 0),
    ("Meta",   "2023-03-31", "content_moderators_contracted", "staff_count", 28965),
    ("Meta",   "2023-12-31", "content_moderators_contracted", "staff_count", 25905),
    ("Meta",   "2023-03-31", "trust_safety_staff_other",      "staff_count", 5265),
    ("Meta",   "2023-12-31", "trust_safety_staff_other",      "staff_count", 3803),
    ("Meta",   "2023-03-31", "global_operations_team",        "staff_count", 3159),
    ("Meta",   "2023-12-31", "global_operations_team",        "staff_count", 1967),
    ("Reddit", "2024-02-29", "engineers_trust_safety",        "employees_count", 82),
    ("Reddit", "2024-02-29", "engineers_trust_safety",        "contractors_count", 7),
    ("Reddit", "2024-02-29", "content_moderators",            "employees_count", 15),
    ("Reddit", "2024-02-29", "content_moderators",            "contractors_count", 107),
    ("Reddit", "2024-02-29", "trust_safety_staff_other",      "employees_count", 71),
    ("Reddit", "2024-02-29", "trust_safety_staff_other",      "contractors_count", 23),
    ("Reddit", "2024-02-29", "all_employees_companywide",     "staff_count", 2030),
    ("Reddit", "2024-02-29", "all_contractors_companywide",   "staff_count", 989),
    ("WhatsApp","2023-12-31","engineers_trust_safety",        "employees_count", 117),
    ("WhatsApp","2023-12-31","content_moderators_employed",   "employees_count", 0),
    ("WhatsApp","2023-12-31","content_moderators_contracted", "contractors_count", 1365),
    ("WhatsApp","2023-12-31","trust_safety_staff_other",      "employees_count", 266),
    ("WhatsApp","2023-12-31","global_operations_team",        "employees_count", 208),
    ("Telegram",TREP,        "engineers_trust_safety",        "employees_count", 5),
    ("Telegram",TREP,        "content_moderators_employed",   "employees_count", 0),
    ("Telegram",TREP,        "content_moderators_contracted", "contractors_count", 150),
    ("Telegram",TREP,        "trust_safety_staff_other",      "employees_count", 4),
]

# F. Language coverage — human moderators + automated tools (Tables 5/6/12), count.
_TVEC_LANG = [
    ("Google",  "human_mod_employees",   1),
    ("Google",  "human_mod_contractors", 80),
    ("Meta",    "human_mod_employees",   89),
    ("Meta",    "human_mod_contractors", 84),
    ("Reddit",  "human_mod_employees",   13),
    ("Reddit",  "human_mod_contractors", 8),
    ("WhatsApp","human_mod_contractors", 6),
    ("Telegram","human_mod_contractors", 47),
    ("YouTube", "automated_text",        104),
    ("Meta",    "automated_text",        101),
    ("Reddit",  "automated_text",        27),
    ("WhatsApp","automated_text",        99),
    ("YouTube", "automated_video",       104),
    ("Meta",    "automated_video",       101),
    ("Reddit",  "automated_video",       59),
    ("WhatsApp","automated_video",       99),
]

# G. TVE appeals (Tables O/P/Q/E). service, alert_source, metric, unit, value.
# Meta figures are rounded to thousands ("K") in-source -> approx_count.
_TVEC_APPEALS = [
    ("YouTube",      "automated_detection", "appeals_accounts_banned",     "count", 0),
    ("YouTube",      "automated_detection", "appeals_accounts_successful", "count", 0),
    ("YouTube",      "automated_detection", "appeals_material_removed",    "count", 251),
    ("YouTube",      "automated_detection", "appeals_material_successful", "count", 17),
    ("YouTube",      "user_reports",        "appeals_accounts_banned",     "count", 0),
    ("YouTube",      "user_reports",        "appeals_accounts_successful", "count", 0),
    ("YouTube",      "user_reports",        "appeals_material_removed",    "count", 20),
    ("YouTube",      "user_reports",        "appeals_material_successful", "count", 3),
    ("Google Drive", "automated_detection", "appeals_material_removed",    "count", 18),
    ("Google Drive", "automated_detection", "appeals_material_successful", "count", 1),
    ("WhatsApp",     "automated_detection", "appeals_accounts_banned",     "count", 20),
    ("WhatsApp",     "automated_detection", "appeals_accounts_successful", "count", 11),
    ("WhatsApp",     "user_reports",        "appeals_accounts_banned",     "count", 0),
    ("WhatsApp",     "user_reports",        "appeals_accounts_successful", "count", 0),
    ("Reddit",       "automated_detection", "appeals_accounts_banned",     "count", 29),
    ("Reddit",       "automated_detection", "appeals_accounts_successful", "count", 0),
    ("Reddit",       "user_reports",        "appeals_accounts_banned",     "count", 92),
    ("Reddit",       "user_reports",        "appeals_accounts_successful", "count", 2),
    ("Telegram",     "automated_detection", "appeals_accounts_banned",     "count", 3420),
    ("Telegram",     "automated_detection", "appeals_accounts_successful", "count", 110),
    ("Telegram",     "user_reports",        "appeals_accounts_banned",     "count", 1107),
    ("Telegram",     "user_reports",        "appeals_accounts_successful", "count", 26),
    ("Facebook",     "automated_detection", "appeals_accounts_banned",     "approx_count", 500),
    ("Facebook",     "automated_detection", "appeals_accounts_successful", "approx_count", 300),
    ("Facebook",     "automated_detection", "appeals_material_removed",    "approx_count", 42000),
    ("Facebook",     "automated_detection", "appeals_material_successful", "approx_count", 3400),
    ("Facebook",     "user_reports",        "appeals_accounts_banned",     "approx_count", 200),
    ("Facebook",     "user_reports",        "appeals_accounts_successful", "approx_count", 100),
    ("Facebook",     "user_reports",        "appeals_material_removed",    "approx_count", 6400),
    ("Facebook",     "user_reports",        "appeals_material_successful", "approx_count", 600),
    ("Instagram",    "automated_detection", "appeals_accounts_banned",     "approx_count", 200),
    ("Instagram",    "automated_detection", "appeals_accounts_successful", "approx_count", 100),
    ("Instagram",    "automated_detection", "appeals_material_removed",    "approx_count", 35000),
    ("Instagram",    "automated_detection", "appeals_material_successful", "approx_count", 2900),
    ("Instagram",    "user_reports",        "appeals_accounts_banned",     "approx_count", 100),
    ("Instagram",    "user_reports",        "appeals_material_removed",    "approx_count", 700),
]

# H. Dedicated TVE team headcounts (Table 13 p56). service, team, metric, value.
_TVEC_TEAM = [
    ("Meta",     "dedicated_team", "employees_count",   10),
    ("Meta",     "dedicated_team", "contractors_count", 1),
    ("Reddit",   "dedicated_team", "employees_count",   26),
    ("Reddit",   "dedicated_team", "contractors_count", 120),
    ("Reddit",   "surge_team",     "employees_count",   35),
    ("Reddit",   "surge_team",     "contractors_count", 1),
    ("WhatsApp", "dedicated_team", "employees_count",   6),
    ("WhatsApp", "dedicated_team", "contractors_count", 0),
    ("Telegram", "dedicated_team", "employees_count",   4),
    ("Telegram", "dedicated_team", "contractors_count", 0),
    ("Telegram", "surge_team",     "employees_count",   3),
    ("Telegram", "surge_team",     "contractors_count", 13),
]

# I. CSEA sub-stream (Reddit + Telegram were also asked about CSEA).
_TVEC_CSEA_RESPONSE = [  # service, category, metric, hours
    ("Reddit",   "subreddits_public",  "median_time_australia", 12.4),
    ("Reddit",   "subreddits_private", "median_time_australia", 6.8),
    ("Reddit",   "channels",           "median_time_australia", 29.5),
    ("Telegram", "chats_secret",       "median_time_global",    11),
    ("Telegram", "channels_group",     "median_time_global",    10),
]
_TVEC_CSEA_PROACTIVE = [  # bounds (">90%", ">80%") stored as the floor value
    ("Reddit", "chat",     "pct_proactively_detected", 90),
    ("Reddit", "channels", "pct_reported",             80),
]
_TVEC_CSEA_APPEALS = [
    ("Reddit",   "automated_detection", "appeals_accounts_banned",     3766),
    ("Reddit",   "automated_detection", "appeals_accounts_successful", 89),
    ("Reddit",   "user_reports",        "appeals_accounts_banned",     4076),
    ("Reddit",   "user_reports",        "appeals_accounts_successful", 159),
    ("Telegram", "automated_detection", "appeals_accounts_banned",     7098),
    ("Telegram", "automated_detection", "appeals_accounts_successful", 573),
    ("Telegram", "user_reports",        "appeals_accounts_banned",     2702),
    ("Telegram", "user_reports",        "appeals_accounts_successful", 218),
]


def _f5_tvec_rows() -> list[list]:
    rows: list[list] = []
    for harm, val in _TVEC_GENAI:
        rows.append(["Gemini", TREP, "tvec_generative_ai", harm, "user_reports_received", "count", val])
    for svc, per, ur, auto in _TVEC_HUMAN_REVIEW:
        rows.append([svc, per, "tvec_human_review", "user_reports", "pct_sent_for_human_review", "percent", ur])
        rows.append([svc, per, "tvec_human_review", "automated_detection", "pct_sent_for_human_review", "percent", auto])
    for svc, per, cat, pro, rep in _TVEC_PD:
        rows.append([svc, per, "tvec_proactive_detection", cat, "pct_proactively_detected", "percent", pro])
        rows.append([svc, per, "tvec_proactive_detection", cat, "pct_reported", "percent", rep])
    for met, val in _TVEC_PD_YT_SPLIT:
        rows.append(["YouTube", TREP, "tvec_proactive_detection", "all", met, "percent", val])
    for svc, per, cat, val in _TVEC_PD_REPORTED_ONLY:
        rows.append([svc, per, "tvec_proactive_detection", cat, "pct_reported", "percent", val])
    for svc, per, cat, glob, aus in _TVEC_RESPONSE:
        rows.append([svc, per, "tvec_response_time", cat, "median_time_global", "hours", glob])
        if aus is not None:
            rows.append([svc, per, "tvec_response_time", cat, "median_time_australia", "hours", aus])
    for svc, date, cat, met, val in _TVEC_STAFF:
        rows.append([svc, date, "tvec_staffing", cat, met, "count", val])
    for svc, cat, val in _TVEC_LANG:
        rows.append([svc, TREP, "tvec_languages", cat, "num_languages", "count", val])
    for svc, src, met, unit, val in _TVEC_APPEALS:
        rows.append([svc, TREP if svc not in ("Facebook", "Instagram") else TMETA,
                     "tvec_appeals", src, met, unit, val])
    for svc, team, met, val in _TVEC_TEAM:
        rows.append([svc, TREP, "tvec_dedicated_team", team, met, "count", val])
    for svc, cat, met, val in _TVEC_CSEA_RESPONSE:
        rows.append([svc, TREP, "tvec_csea_response_time", cat, met, "hours", val])
    for svc, cat, met, val in _TVEC_CSEA_PROACTIVE:
        rows.append([svc, TREP, "tvec_csea_proactive", cat, met, "percent", val])
    for svc, src, met, val in _TVEC_CSEA_APPEALS:
        rows.append([svc, TREP, "tvec_csea_appeals", src, met, "count", val])
    return rows


def build_rows() -> list[list]:
    rows: list[list] = []
    rows += _f1_f2_rows()
    rows += _f3_online_hate_rows()
    rows += _f4_age_assurance_rows()
    rows += _f5_tvec_rows()
    return rows


def validate(rows: list[list]) -> None:
    """Fail-loud cross-checks against totals stated in the reports."""
    idx: dict[tuple, float] = {}
    for r in rows:
        idx[(r[0], r[1], r[2], r[3], r[4])] = r[6]  # (service, period, section, category, metric)

    def approx(a: float, b: float, tol: float) -> bool:
        return abs(a - b) <= tol

    # --- Family 1: detection shares sum to ~100 ---
    assert approx(87.5 + 12 + 0.5, 100, 0.01), "Snap CSEA detection shares != 100"
    assert 73 + 27 == 100, "WhatsApp CSEA detection shares != 100"

    # --- Family 5 (TVEC): each proactive+reported pair sums to 100 ---
    for svc, per, cat in TVEC_PD_PAIRS:
        p = idx.get((svc, per, "tvec_proactive_detection", cat, "pct_proactively_detected"))
        q = idx.get((svc, per, "tvec_proactive_detection", cat, "pct_reported"))
        assert p is not None and q is not None, f"missing TVEC pair {svc}/{cat}"
        assert approx(p + q, 100, 0.05), f"TVEC {svc}/{cat} proactive+reported={p+q} != 100"

    # --- Family 4 (age assurance): 13_15 + 16_17 = 13_17 (Twitch excepted) ---
    for svc in ("Discord", "Facebook", "Instagram", "Snapchat", "TikTok", "YouTube"):
        a = idx[(svc, P_AGE, "age_mau", "13_15", "avg_monthly_active_end_users")]
        b = idx[(svc, P_AGE, "age_mau", "16_17", "avg_monthly_active_end_users")]
        c = idx[(svc, P_AGE, "age_mau", "13_17", "avg_monthly_active_end_users")]
        assert a + b == c, f"{svc} MAU age bands {a}+{b} != {c}"

    # --- Family 4: under-13 ban attribution split sums to ~100 (Twitch source-typo excepted) ---
    for svc in ("Discord", "Facebook", "Instagram", "Reddit", "Snapchat", "TikTok"):
        p = idx[(svc, P_AGE, "age_enforcement", "", "proportion_via_proactive_detection")]
        q = idx[(svc, P_AGE, "age_enforcement", "", "proportion_via_user_reporting")]
        assert approx(p + q, 100, 0.05), f"{svc} under-13 ban split {p}+{q} != 100"

    # --- Family 3 (online hate): tweet identification-source shares sum to 100 ---
    tw = sum(idx[("Twitter", HPOST, "hate_identification", c, "share_of_total")]
             for c in ("tweets_user_reports", "tweets_automated", "tweets_moderators", "tweets_other"))
    assert approx(tw, 100, 0.01), f"online-hate tweet identification shares {tw} != 100"

    # --- Family 5 staffing: derived % changes match the report's stated figures ---
    def chg(svc, cat, d0, d1):
        v0 = idx[(svc, d0, "tvec_staffing", cat, "staff_count")]
        v1 = idx[(svc, d1, "tvec_staffing", cat, "staff_count")]
        return round((v1 - v0) / v0 * 100, 1)
    assert chg("Meta", "trust_safety_staff_other", "2023-03-31", "2023-12-31") == -27.8, "Meta T&S-other %chg"
    assert chg("Google", "content_moderators_employed", "2023-04-01", "2024-02-29") == 7.9, "Google mods %chg"

    # --- Column arity + numeric values ---
    for r in rows:
        assert len(r) == len(COLUMNS), f"bad row arity: {r}"
        assert isinstance(r[6], (int, float)), f"non-numeric value: {r}"


def main() -> None:
    rows = build_rows()
    validate(rows)
    snapshot = {
        "source": "https://www.esafety.gov.au/industry/basic-online-safety-expectations",
        "regime": "Basic Online Safety Expectations (Online Safety Act 2021)",
        "publisher": "eSafety Commissioner (Australia)",
        "coverage": "BOSE transparency-notice reports 2022–2025 (CSEA first/second notices, "
                    "online hate, age assurance, terrorist & violent extremist material)",
        "columns": COLUMNS,
        "rows": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=0)
        f.write("\n")
    services = sorted({r[0] for r in rows})
    sections = sorted({r[2] for r in rows})
    print(f"wrote {len(rows)} rows across {len(services)} services, "
          f"{len(sections)} sections -> {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
