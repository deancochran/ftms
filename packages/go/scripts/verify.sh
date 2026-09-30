#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export GOWORK=off
export PYTHONDONTWRITEBYTECODE=1
report_dir="${FTMS_GO_REPORT_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/ftms-go-reports}"
mkdir -p "$report_dir"
report_dir="$(cd "$report_dir" && pwd)"
test -z "$(gofmt -l .)"
cmp LICENSE ../../LICENSE
python3 scripts/validate-corpora.py > "$report_dir/schema-validation.json"
python3 scripts/test_capability_fixtures.py > "$report_dir/capability-fixtures.log" 2>&1
go vet ./...
go test -race ./...
FTMS_GO_REPORT="$report_dir/conformance.json" go test -count=1 -tags conformance -v ./... > "$report_dir/conformance.log"
go build ./...
python3 scripts/verify-consumer.py > "$report_dir/consumer.log"
printf 'Go verification passed; reports: %s\n' "$report_dir"
