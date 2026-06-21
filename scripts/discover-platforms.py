"""Discover DSA transparency report pages for platforms not yet in the registry.

Two modes:

  --from-names FILE
      Process a TSV file of platforms to add (columns: service_name, platform,
      tier — tab-separated, one per line, no header).  For each, runs web
      searches to find the platform's DSA transparency page URL and outputs a
      draft registry entry.

  --search-annex
      Search the open web for CSV/XLSX files matching the Annex I harmonized
      template headers (the column names are unique enough to identify these
      files reliably).  Extracts platform names and page URLs and outputs
      draft registry entries.

Both modes:
  • Use Playwright (headless Chromium) — no API key required.
  • Skip any service_name already present in --registry (default:
    data/registry.json).
  • Output a JSON array of draft entries to stdout (or --out FILE).
    Nothing is written to registry.json automatically — review first.

Requirements (same venv as scrape-reports.py):
    pip install playwright
    playwright install chromium

Usage:
    # Find transparency URLs for a list of known platforms:
    python scripts/discover-platforms.py --from-names data/platforms.tsv

    # Search for Annex I files published anywhere on the web:
    python scripts/discover-platforms.py --search-annex

    # Combine: names first, then annex search:
    python scripts/discover-platforms.py --from-names data/platforms.tsv \\
        --search-annex --out draft.json

    # Dry-run (skip web searches, just format draft entries with null URLs):
    python scripts/discover-platforms.py --from-names data/platforms.tsv --dry-run

Input TSV format (no header row):
    service_name<TAB>platform<TAB>tier
    Stripchat<TAB>WebGroup Czech Republic<TAB>vlop
    Reddit<TAB>Reddit<TAB>online-platform

Valid tier values:
    vlop             Very Large Online Platform (semi-annual reports)
    vlose            Very Large Online Search Engine (semi-annual)
    online-platform  Article 24 online platform (annual)
    hosting          Hosting service provider (annual)
    intermediary     Intermediary service (annual)
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent.parent
_DEFAULT_REGISTRY = HERE / "data" / "registry.json"

# Periods for the first harmonized cycle (reports published February 2026).
# VLOPs/VLOSEs cover H2 2025; all others cover the full calendar year 2025.
_PERIOD_SEMI = ("2025-07-01", "2025-12-31")   # VLOPs/VLOSEs
_PERIOD_ANNUAL = ("2025-01-01", "2025-12-31")  # everyone else

_SEMI_ANNUAL_TIERS = {"vlop", "vlose"}

# Annex I Part 1 column headers — unique to the harmonized template.
# Used in --search-annex queries.
_ANNEX_PHRASES = [
    '"Reporting period start date" "Service identifier"',
    '"Type of provider" "Date of publication" DSA',
    '"Service identifier" "Reporting period end date" transparency',
]

# URL scoring signals
_URL_POSITIVE = [
    "dsa", "transparency", "digital-services-act", "digital_services_act",
    "trust-safety", "trust_safety", "legal", "policies", "compliance",
    "reporting", "annex",
]
_URL_NEGATIVE = [
    "news", "article", "blog", "press", "linkedin.com", "twitter.com",
    "x.com", "facebook.com", "reddit.com", "medium.com", "substack.com",
    "ec.europa.eu", "europa.eu", "wikipedia.org",
]
_DOWNLOAD_EXTENSIONS = (".csv", ".xlsx", ".zip")


def _period_for_tier(tier: str) -> tuple[str, str]:
    return _PERIOD_SEMI if tier in _SEMI_ANNUAL_TIERS else _PERIOD_ANNUAL


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _score_url(url: str, service_name: str) -> float:
    """Higher = more likely to be a DSA transparency page for this platform."""
    u = url.lower()
    score = 0.0

    # Negative signals (third-party sites, news)
    if any(neg in u for neg in _URL_NEGATIVE):
        return -1.0

    # Positive signals
    score += sum(1.0 for pos in _URL_POSITIVE if pos in u)

    # Direct download file — very high value
    if any(u.endswith(ext) for ext in _DOWNLOAD_EXTENSIONS):
        score += 5.0

    # Platform name in URL (rough slug match)
    slug = _slug(service_name)
    first_word = slug.split("_")[0]
    if first_word and len(first_word) > 2 and first_word in u:
        score += 2.0

    # PDF is usable but lower priority than CSV/XLSX
    if u.endswith(".pdf"):
        score -= 1.0

    # Penalise very deep paths (likely individual report pages, not stable hub)
    depth = u.count("/") - 2  # subtract scheme + domain
    score -= max(0, depth - 4) * 0.2

    return score


def _dismiss_google_consent(page: Any) -> None:
    """Dismiss Google's GDPR consent page if shown (best-effort, never raises)."""
    try:
        for selector in [
            "button#L2AGLb",
            "button[jsname='b3VHJd']",
            "[aria-label='Accept all']",
            "[aria-label='Agree to all']",
        ]:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=1500):
                    btn.click(timeout=2000)
                    time.sleep(0.4)
                    return
            except Exception:
                continue
        for text in ["Accept all", "Agree to all", "I agree"]:
            try:
                btn = page.get_by_role("button", name=re.compile(text, re.IGNORECASE)).first
                if btn.is_visible(timeout=800):
                    btn.click(timeout=2000)
                    time.sleep(0.4)
                    return
            except Exception:
                continue
    except Exception:
        pass


def _search_google(page: Any, query: str) -> list[tuple[str, str, str]]:
    """Search Google; return [(title, url, snippet), ...]."""
    results: list[tuple[str, str, str]] = []
    try:
        encoded = urllib.parse.quote_plus(query)
        page.goto(
            f"https://www.google.com/search?q={encoded}&num=10&hl=en&gl=us",
            wait_until="domcontentloaded",
            timeout=20000,
        )
        _dismiss_google_consent(page)
        page.wait_for_load_state("networkidle", timeout=10000)

        # Google result links wrap an <h3> title; filter out google.com URLs
        links = page.locator("a:has(h3)").all()
        for link in links[:15]:
            try:
                href = link.get_attribute("href") or ""
                if not href.startswith("http") or "google." in href.lower():
                    continue
                title = (link.locator("h3").first.inner_text() or "").strip()
                results.append((title or href, href, ""))
            except Exception:
                continue
    except Exception as exc:
        print(f"  WARN search failed: {exc}", file=sys.stderr)
    return results


def _find_transparency_url(
    page: Any, service_name: str, platform: str, dry_run: bool
) -> str | None:
    """Search for a platform's DSA transparency page; return best URL or None."""
    if dry_run:
        return None

    queries = [
        f'"{service_name}" "DSA" "transparency report" 2026 download',
        f'"{service_name}" "digital services act" transparency report CSV XLSX',
        f'"{platform}" DSA transparency report 2026',
    ]

    candidates: list[tuple[float, str]] = []
    seen: set[str] = set()

    for query in queries:
        print(f"    search: {query[:70]}", file=sys.stderr)
        results = _search_google(page, query)
        for title, url, _snippet in results:
            if url in seen:
                continue
            seen.add(url)
            score = _score_url(url, service_name)
            if score >= 0:
                candidates.append((score, url))
        time.sleep(0.5)

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_url = candidates[0]
    print(f"    best ({best_score:.1f}): {best_url}", file=sys.stderr)
    return best_url if best_score > 0 else None


def _search_annex_files(page: Any, dry_run: bool) -> list[dict[str, Any]]:
    """Search for Annex I CSV/XLSX files in the wild; return draft entries."""
    if dry_run:
        return []

    found_urls: set[str] = set()
    drafts: list[dict[str, Any]] = []

    for phrase in _ANNEX_PHRASES:
        query = f"{phrase} filetype:csv OR filetype:xlsx 2026"
        print(f"  annex search: {query}", file=sys.stderr)
        results = _search_google(page, query)

        for title, url, snippet in results:
            if url in found_urls:
                continue
            found_urls.add(url)
            u = url.lower()
            # Only keep direct file links or pages that look like a DSA hub
            if any(u.endswith(ext) for ext in _DOWNLOAD_EXTENSIONS) or \
               any(kw in u for kw in ("dsa", "transparency", "digital-services")):
                # Guess service name from URL domain
                m = re.search(r"https?://(?:www\.|transparency\.)?([^./]+)\.", url)
                guessed_name = m.group(1).title() if m else "Unknown"
                drafts.append({
                    "_source": "annex-search",
                    "_url_found": url,
                    "_title": title,
                    "service_name": guessed_name,
                    "platform": guessed_name,
                    "tier": "online-platform",
                    "period_start": _PERIOD_ANNUAL[0],
                    "period_end": _PERIOD_ANNUAL[1],
                    "transparency_page_url": url if not any(
                        url.lower().endswith(ext) for ext in _DOWNLOAD_EXTENSIONS
                    ) else None,
                    "report_url": url if any(
                        url.lower().endswith(ext) for ext in _DOWNLOAD_EXTENSIONS
                    ) else None,
                    "click_steps": [],
                    "notes": "Auto-discovered via annex-search. Verify service_name and platform.",
                })
        time.sleep(1)

    return drafts


def _draft_entry(
    service_name: str,
    platform: str,
    tier: str,
    url: str | None,
) -> dict[str, Any]:
    period_start, period_end = _period_for_tier(tier)
    return {
        "service_name": service_name,
        "platform": platform,
        "tier": tier,
        "period_start": period_start,
        "period_end": period_end,
        "transparency_page_url": url,
        "click_steps": [],
        "report_url": None,
        "notes": None if url else "transparency_page_url not found — add manually",
    }


def _load_registry_names(registry_path: Path) -> set[str]:
    if not registry_path.exists():
        return set()
    with registry_path.open(encoding="utf-8") as f:
        entries = json.load(f)
    return {e["service_name"] for e in entries}


def _load_names_tsv(path: Path) -> list[tuple[str, str, str]]:
    """Read TSV of (service_name, platform, tier). Skips blank lines and # comments."""
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                print(f"  WARN skipping malformed line: {line!r}", file=sys.stderr)
                continue
            rows.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover DSA transparency report pages for new registry entries"
    )
    parser.add_argument(
        "--from-names", metavar="FILE",
        help="TSV file of platforms to add (service_name TAB platform TAB tier)"
    )
    parser.add_argument(
        "--search-annex", action="store_true",
        help="Search web for Annex I CSV/XLSX files to discover unknown platforms"
    )
    parser.add_argument(
        "--registry", default=str(_DEFAULT_REGISTRY),
        help="Path to registry.json (used to skip already-known services)"
    )
    parser.add_argument("--out", metavar="FILE", help="Write JSON output here instead of stdout")
    parser.add_argument("--dry-run", action="store_true", help="Skip web searches; emit null URLs")
    parser.add_argument("--headful", action="store_true", help="Show the browser window")
    args = parser.parse_args()

    if not args.from_names and not args.search_annex:
        parser.error("Specify --from-names FILE and/or --search-annex")

    existing_names = _load_registry_names(Path(args.registry))
    drafts: list[dict[str, Any]] = []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "ERROR playwright not installed. Run: pip install playwright && "
            "playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headful)
        context = browser.new_context()
        page = context.new_page()

        # --- Mode 1: from-names ---
        if args.from_names:
            rows = _load_names_tsv(Path(args.from_names))
            for service_name, platform, tier in rows:
                if service_name in existing_names:
                    print(f"  SKIP {service_name} (already in registry)", file=sys.stderr)
                    continue
                print(f"\n{service_name} ({platform}, {tier})", file=sys.stderr)
                url = _find_transparency_url(page, service_name, platform, args.dry_run)
                drafts.append(_draft_entry(service_name, platform, tier, url))

        # --- Mode 2: annex search ---
        if args.search_annex:
            print("\nSearching for Annex I files...", file=sys.stderr)
            annex_drafts = _search_annex_files(page, args.dry_run)
            # Filter out names already in registry
            for d in annex_drafts:
                if d["service_name"] not in existing_names:
                    drafts.append(d)

        context.close()
        browser.close()

    output = json.dumps(drafts, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"\nWrote {len(drafts)} draft entries to {args.out}", file=sys.stderr)
    else:
        print(output)

    print(f"\nDone — {len(drafts)} draft entries", file=sys.stderr)
    print("Review and add to registry.json manually (or merge with --registry).", file=sys.stderr)


if __name__ == "__main__":
    main()
