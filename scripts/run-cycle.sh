#!/usr/bin/env bash
# Run one DSA reporting cycle: scrape all platforms → harvest into demo.db.
#
# Usage:
#   ./scripts/run-cycle.sh              # all platforms in registry
#   ./scripts/run-cycle.sh --service TikTok   # single platform
#   ./scripts/run-cycle.sh --tier vlop        # VLOPs only (August cycle)
#
# Prerequisites:
#   source .venv-scrape/bin/activate    # playwright + openpyxl
#   demo.db must exist (python seed.py)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

REGISTRY="$REPO/data/registry.json"
REPORTS_DIR="$REPO/data/reports"
DB="$REPO/demo.db"
SERVICE=""
TIER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service) SERVICE="$2"; shift 2 ;;
    --tier)    TIER="$2";    shift 2 ;;
    --help|-h)
      sed -n '2,12p' "$0" | sed 's/^# //'
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# Build scraper args
SCRAPE_ARGS=()
[[ -n "$SERVICE" ]] && SCRAPE_ARGS+=(--service "$SERVICE")

# Build harvest args
HARVEST_ARGS=()
[[ -n "$SERVICE" ]] && HARVEST_ARGS+=(--service "$SERVICE")

echo "=== DSA cycle run $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "Registry: $REGISTRY"
echo "Reports:  $REPORTS_DIR"
echo "DB:       $DB"
[[ -n "$SERVICE" ]] && echo "Service:  $SERVICE"
[[ -n "$TIER"    ]] && echo "Tier:     $TIER"
echo

# Step 1: Scrape — download report files
echo "--- Step 1: scrape ---"
python "$SCRIPT_DIR/scrape-reports.py" \
  --registry "$REGISTRY" \
  --out "$REPORTS_DIR" \
  "${SCRAPE_ARGS[@]}"

echo
echo "--- Step 2: harvest ---"

# If filtering by tier, find matching services from registry
if [[ -n "$TIER" && -z "$SERVICE" ]]; then
  SERVICES=$(python3 -c "
import json, sys
with open('$REGISTRY') as f:
    reg = json.load(f)
tier = '$TIER'
names = [e['service_name'] for e in reg if e.get('tier') == tier]
print('\n'.join(names))
")
  while IFS= read -r svc; do
    [[ -z "$svc" ]] && continue
    slug=$(echo "$svc" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_\|_$//g')
    src_dir="$REPORTS_DIR/$slug"
    if [[ -d "$src_dir" ]]; then
      echo "  Harvesting $svc from $src_dir"
      python "$SCRIPT_DIR/harvest-harmonized.py" \
        --service "$svc" \
        --source-dir "$src_dir" \
        --db "$DB" \
        --registry "$REGISTRY"
    else
      echo "  SKIP $svc — no data in $src_dir"
    fi
  done <<< "$SERVICES"
else
  # Harvest all (or single service)
  if [[ -n "$SERVICE" ]]; then
    slug=$(echo "$SERVICE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_\|_$//g')
    src_dir="$REPORTS_DIR/$slug"
    python "$SCRIPT_DIR/harvest-harmonized.py" \
      --service "$SERVICE" \
      --source-dir "$src_dir" \
      --db "$DB" \
      --registry "$REGISTRY"
  else
    # All services — find any that have a reports directory
    for src_dir in "$REPORTS_DIR"/*/; do
      [[ -d "$src_dir" ]] || continue
      slug=$(basename "$src_dir")
      # Find matching service name from registry
      svc=$(python3 -c "
import json, re
slug = '$slug'
with open('$REGISTRY') as f:
    reg = json.load(f)
for e in reg:
    s = re.sub(r'[^a-z0-9]+', '_', e['service_name'].lower()).strip('_')
    if s == slug:
        print(e['service_name'])
        break
")
      if [[ -n "$svc" ]]; then
        echo "  Harvesting $svc"
        python "$SCRIPT_DIR/harvest-harmonized.py" \
          --service "$svc" \
          --source-dir "$src_dir" \
          --db "$DB" \
          --registry "$REGISTRY" || echo "  ERROR harvesting $svc (continuing)"
      fi
    done
  fi
fi

echo
echo "=== Cycle complete ==="
