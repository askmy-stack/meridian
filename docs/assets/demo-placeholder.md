# Demo asset placeholder

Record a **~2 minute** walkthrough GIF for README and LinkedIn portfolio (Flaw #21).

## Target file

Save to: `docs/assets/meridian-demo.gif` (≤ 15 MB, ~15 fps, 1920×1080)

Until recorded, use a static screenshot at `docs/assets/demo-screenshot.png` (optional).

## ffmpeg screen record (macOS)

```bash
# List devices
ffmpeg -f avfoundation -list_devices true -i ""

# Record display 1 for 120 seconds
ffmpeg -f avfoundation -i "1" -t 120 -r 15 \
  -vf "scale=1920:-2" docs/assets/meridian-demo.raw.mp4

# Convert to GIF (palette for size)
ffmpeg -i docs/assets/meridian-demo.raw.mp4 -vf "fps=12,scale=1280:-1:flags=lanczos,palettegen" palette.png
ffmpeg -i docs/assets/meridian-demo.raw.mp4 -i palette.png -lavfi "fps=12,scale=1280:-1:flags=lanczos[x];[x][1:v]paletteuse" docs/assets/meridian-demo.gif
rm palette.png docs/assets/meridian-demo.raw.mp4
```

## Script

Follow `docs/DEMO.md` — emphasize SCRI honesty banners:

1. **ModelStatusBanner** — demo vs validated calibration
2. **Band-first SCRI** — LOW/MEDIUM/HIGH/CRITICAL before percentage
3. **Feature provenance** — live vs static feature counts
4. **Simulator bands** — Monte Carlo p10/p50/p90

Narration hook: *"Every major disruption was visible in signals weeks early — Meridian connects them to your suppliers with honest calibration labels."*
