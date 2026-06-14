#!/usr/bin/env bash
# Record a ~2 minute Meridian portfolio demo per docs/DEMO.md
# Requires: ffmpeg, running API (:8002) + frontend (:5173)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT}/docs/assets"
RAW_MP4="${OUT_DIR}/meridian-demo.raw.mp4"
GIF_OUT="${OUT_DIR}/meridian-demo.gif"
DURATION="${DEMO_RECORD_SECONDS:-120}"
FPS="${DEMO_RECORD_FPS:-15}"
WIDTH="${DEMO_RECORD_WIDTH:-1920}"

mkdir -p "${OUT_DIR}"

echo "Meridian demo recorder"
echo "  Script:    docs/DEMO.md"
echo "  Duration:  ${DURATION}s @ ${FPS}fps"
echo "  Output:    ${GIF_OUT}"
echo ""
echo "Prerequisites:"
echo "  1. docker compose up -d neo4j"
echo "  2. make portfolio-ready   # or make seed-all"
echo "  3. make dev               # API :8002"
echo "  4. make dev-frontend      # UI :5173"
echo ""
echo "Walkthrough scenes (2 min):"
echo "  • Command Center — ModelStatusBanner, band-first KPIs, export digest"
echo "  • Simulator — Red Sea preset, p10/p50/p90 bands"
echo "  • Risk Map — layers, entity drawer, feature provenance"
echo "  • Copilot + Sectors + Suppliers SHAP"
echo "  • Graph Health — /ops/graph-health completeness"
echo ""

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: ffmpeg not installed. Install via: brew install ffmpeg"
  exit 1
fi

echo "Listing avfoundation capture devices…"
ffmpeg -f avfoundation -list_devices true -i "" 2>&1 || true
echo ""
read -r -p "Enter avfoundation device index for screen capture [1]: " DEVICE
DEVICE="${DEVICE:-1}"

echo "Recording starts in 3 seconds — switch to browser at http://localhost:5173"
sleep 3

ffmpeg -f avfoundation -i "${DEVICE}" -t "${DURATION}" -r "${FPS}" \
  -vf "scale=${WIDTH}:-2" -y "${RAW_MP4}"

PALETTE="${OUT_DIR}/palette.png"
ffmpeg -y -i "${RAW_MP4}" -vf "fps=12,scale=1280:-1:flags=lanczos,palettegen" "${PALETTE}"
ffmpeg -y -i "${RAW_MP4}" -i "${PALETTE}" \
  -lavfi "fps=12,scale=1280:-1:flags=lanczos[x];[x][1:v]paletteuse" "${GIF_OUT}"

rm -f "${PALETTE}" "${RAW_MP4}"

echo ""
echo "Done: ${GIF_OUT}"
echo "Add to README: docs/assets/meridian-demo.gif"
