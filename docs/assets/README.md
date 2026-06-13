# Demo media assets

| File | Purpose |
|------|---------|
| `meridian-demo.gif` | Hero animation for README (map → simulator → copilot) |
| `meridian-demo.mp4` | Optional full walkthrough for LinkedIn |

Record using [`docs/DEMO.md`](./DEMO.md). Recommended tools: Loom, Kap, or `ffmpeg` from a screen capture.

```bash
# Example: convert a short MP4 to GIF (requires ffmpeg)
ffmpeg -i meridian-demo.mp4 -vf "fps=12,scale=1280:-1" -loop 0 meridian-demo.gif
```

Until a GIF is added, README shows a static placeholder screenshot path.
