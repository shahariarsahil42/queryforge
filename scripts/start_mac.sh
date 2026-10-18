#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v docker >/dev/null; then
  echo 'Docker not found. Install Docker Desktop and launch it first.'
  exit 1
fi
docker compose up --build -d
docker compose ps
printf '\nOpen http://localhost:8000 in your browser.\n'
