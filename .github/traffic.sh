#!/usr/bin/env bash
# GitHub keeps only a 14-day traffic window. This appends that window to a
# permanent daily series, so a plugin installed with `/plugin marketplace add`
# (which is a git clone) gets counted without shipping any phone-home code.
set -euo pipefail

REPO="${REPO:-amj-lang/anderson}"
OUT="${OUT:-metrics/traffic.json}"
BADGE="${BADGE:-metrics/badge.json}"
INSTALLS="${INSTALLS:-metrics/installs.json}"
INSTALLS_BADGE="${INSTALLS_BADGE:-metrics/installs-badge.json}"
# Nothing before this date is recorded. The first version of this script backfilled
# the 14-day window it happened to find, which mixed a launch spike and a fortnight
# of crawler traffic into the running total; the series starts clean instead.
SINCE="${SINCE:-2026-09-14}"

# GitHub's number for *today* grows through the day, and a day eventually falls
# out of the 14-day window, so a re-run keeps the larger value per field and
# never drops a date already recorded.
MERGE='
  def maxmerge($old; $new):
    reduce ($new | keys_unsorted[]) as $k ($old; .[$k] = ([$new[$k], (.[$k] // 0)] | max));
  .[0] as $old | .[1] as $new
  | reduce ($new | keys_unsorted[]) as $d ($old; .[$d] = maxmerge(($old[$d] // {}); $new[$d]))
'

selftest() {
  local got want
  got=$(printf '%s\n' \
    '{"2026-09-01":{"clones":5,"unique_clones":2}}' \
    '{"2026-09-01":{"clones":3,"unique_clones":9},"2026-09-02":{"views":7}}' \
    | jq -s -c "$MERGE")
  want='{"2026-09-01":{"clones":5,"unique_clones":9},"2026-09-02":{"views":7}}'
  [ "$got" = "$want" ] || { echo "selftest FAILED: $got != $want" >&2; exit 1; }
  echo "selftest ok"
}

if [ "${1:-}" = "--selftest" ]; then selftest; exit 0; fi

mkdir -p "$(dirname "$OUT")" "$(dirname "$BADGE")"
[ -f "$OUT" ] || echo '{}' > "$OUT"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# The traffic endpoints need push access, which the Actions GITHUB_TOKEN does not
# have and cannot be granted (`administration` is not a workflow permission). With
# only that token the clone half is skipped and the install half still runs; set a
# TRAFFIC_TOKEN secret (a PAT that can read this repo's traffic) to record clones.
clones=$(gh api "repos/$REPO/traffic/clones" \
  --jq '[.clones[] | {key: .timestamp[0:10], value: {clones: .count, unique_clones: .uniques}}] | from_entries' 2>"$tmp/err") || clones=""

if [ -n "$clones" ]; then
  views=$(gh api "repos/$REPO/traffic/views" \
    --jq '[.views[] | {key: .timestamp[0:10], value: {views: .count, unique_views: .uniques}}] | from_entries')

  jq -n --argjson c "$clones" --argjson v "$views" --arg since "$SINCE" \
    '$c * $v | with_entries(select(.key >= $since))' > "$tmp/new.json"
  jq -s "$MERGE | to_entries | sort_by(.key) | from_entries" "$OUT" "$tmp/new.json" > "$tmp/merged.json"
  mv "$tmp/merged.json" "$OUT"

  # Unique cloners summed over days: a proxy for installs, not a headcount. The
  # same person on two days counts twice, and CI or mirrors count at all.
  total=$(jq '[.[].unique_clones // 0] | add // 0' "$OUT")
  jq -n --argjson t "$total" \
    '{schemaVersion: 1, label: "unique clones", message: ($t | tostring), color: "8A2BE2"}' > "$BADGE"

  echo "$OUT: $(jq length "$OUT") days recorded, $total unique clones"
else
  echo "traffic: clones skipped, this token cannot read them ($(tr -d '\n' < "$tmp/err")). Set a TRAFFIC_TOKEN secret."
fi

# Installs, counted by the plugin itself: every release carries a one-byte
# `ping` asset that the SessionStart hook fetches once per version per machine,
# and GitHub publishes download_count per asset. Cumulative and authoritative,
# so this file is rewritten rather than merged.
gh api "repos/$REPO/releases" --paginate \
  --jq '.[] | select(any(.assets[]; .name == "ping")) | {(.tag_name): ([.assets[] | select(.name == "ping") | .download_count] | add)}' \
  | jq -s 'add // {} | to_entries | sort_by(.key) | from_entries' > "$INSTALLS"

installs=$(jq '[.[]] | add // 0' "$INSTALLS")
jq -n --argjson t "$installs" \
  '{schemaVersion: 1, label: "installs", message: ($t | tostring), color: "8A2BE2"}' > "$INSTALLS_BADGE"

echo "$INSTALLS: $(jq length "$INSTALLS") releases, $installs installs"
