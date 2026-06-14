#!/usr/bin/env bash
# Validate deploy configuration files exist (no credentials required).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

REQUIRED=(
  "frontend/vercel.json"
  "railway.toml"
  "Dockerfile"
  "docs/DEPLOY_QUICKSTART.md"
  "frontend/.env.example"
)

missing=0
for f in "${REQUIRED[@]}"; do
  if [[ -f "${f}" ]]; then
    echo "OK  ${f}"
  else
    echo "MISSING  ${f}"
    missing=$((missing + 1))
  fi
done

if [[ ${missing} -gt 0 ]]; then
  echo ""
  echo "${missing} required deploy file(s) missing."
  exit 1
fi

echo ""
echo "Deploy config check passed."
echo "Next: vercel link (frontend/) + railway up — see docs/DEPLOY_QUICKSTART.md"
