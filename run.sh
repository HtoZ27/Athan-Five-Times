#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Ensure we're in the project root
export PYTHONPATH="$DIR:$PYTHONPATH"

# Run the application — try python3 first, fall back to python
if command -v python3 &> /dev/null; then
    exec python3 -m backend.main "$@"
else
    exec python -m backend.main "$@"
fi
