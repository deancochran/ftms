#!/usr/bin/env sh
set -eu
# Backwards-compatible local entry point; CI supplies an exact prepared archive
# directly to scripts/consumer.py. No credentials are needed for either mode.
crate_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec "${PYTHON:-python3}" "$crate_dir/scripts/consumer.py" --allow-dirty "$@"
