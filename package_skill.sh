#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: sh package_skill.sh <skill-name>" >&2
  exit 1
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/package_skill.py" "$1"
