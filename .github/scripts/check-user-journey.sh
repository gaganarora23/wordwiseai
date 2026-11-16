#!/usr/bin/env bash
# User-impact check of the live WordWise API (issue #82).
# Usage: check-user-journey.sh [base-url]   (or env API_URL; empty -> default)
# Needs only bash, curl and jq.
set -u

DEFAULT_URL="https://wordwise-api-xji2.onrender.com"
BASE="${1:-${API_URL:-}}"
[ -z "$BASE" ] && BASE="$DEFAULT_URL"
BASE="${BASE%/}"

MAX_TIME="${CHECK_MAX_TIME:-120}"   # tolerate a ~2 minute cold start
RETRY_DELAY="${CHECK_RETRY_DELAY:-10}"

BODY_FILE="$(mktemp)"
trap 'rm -f "$BODY_FILE"' EXIT

# fetch URL -> sets STATUS (000 on connection/DNS/timeout failure) and CURL_ERR
fetch() {
  local url="$1" err
  : > "$BODY_FILE"
  STATUS="$(curl -sS --max-time "$MAX_TIME" -o "$BODY_FILE" -w '%{http_code}' "$url" 2>"$BODY_FILE.err")" || true
  CURL_ERR="$(tr '\n' ' ' < "$BODY_FILE.err" 2>/dev/null)"
  rm -f "$BODY_FILE.err"
  STATUS="${STATUS:-000}"
}

# attempt_health / attempt_words: return 0 on pass, else set FAIL_MSG and return 1
attempt_health() {
  local url="$BASE/api/v1/health"
  fetch "$url"
  if [ "$STATUS" = "000" ]; then
    FAIL_MSG="GET $url failed to connect or timed out: ${CURL_ERR:-no response}"; return 1
  fi
  if [ "$STATUS" != "200" ]; then
    FAIL_MSG="GET $url returned status $STATUS, expected 200"; return 1
  fi
  return 0
}

attempt_words() {
  local url="$BASE/api/v1/grades/5/words" count
  fetch "$url"
  if [ "$STATUS" = "000" ]; then
    FAIL_MSG="GET $url failed to connect or timed out: ${CURL_ERR:-no response}"; return 1
  fi
  if [ "$STATUS" != "200" ]; then
    FAIL_MSG="GET $url returned status $STATUS, expected 200"; return 1
  fi
  if ! count="$(jq -e 'if type == "array" then length else error("not an array") end' "$BODY_FILE" 2>/dev/null)"; then
    FAIL_MSG="GET $url returned status 200 but the body is not a valid JSON array of words"; return 1
  fi
  if [ "$count" != "50" ]; then
    FAIL_MSG="GET $url returned status 200 with $count words, expected exactly 50"; return 1
  fi
  return 0
}

run_check() {
  local name="$1" fn="$2"
  if ! "$fn"; then
    echo "Check '$name' failed ($FAIL_MSG); retrying once in ${RETRY_DELAY}s" >&2
    sleep "$RETRY_DELAY"
    if ! "$fn"; then
      echo "::error::$FAIL_MSG"
      return 1
    fi
  fi
  echo "PASS: $name ($BASE)"
}

rc=0
run_check "health" attempt_health || rc=1
run_check "grade 5 words (50 items)" attempt_words || rc=1
exit "$rc"
