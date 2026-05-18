#!/bin/bash
# Sharp GUI - verbose launcher for Linux/macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/run.sh" --verbose "$@"
