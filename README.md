# Clipforge

A personal, localhost video-to-shorts studio. FastAPI + plain JavaScript, with FFmpeg, faster-whisper, OpenCV, and yt-dlp. No paid API keys or frontend build step.

## 🚀 Quick Start

### Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| **Python** | 3.11 – 3.13 | Tested with 3.12 |
| **FFmpeg** | 7+ (tested with 9) | Must include `libass`, `libx264`, `afftdn`, `zoompan` |
| **Node.js** | 18+ | Required for YouTube downloads via yt-dlp |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/kartikbaghelwork1-ship-it/ClipForge.git
cd ClipForge

# 2. Run the setup script (creates .venv and installs dependencies)
./setup.sh

# On Windows:
# setup.cmd

# To specify a Python version:
# PYTHON=python3.12 ./setup.sh
```

### Run

```bash
# Start the server
./start.sh

# On Windows:
# start.cmd
```

Open **http://127.0.0.1:8000** in your browser. Stop with `Ctrl+C`.

To use a different port:
```bash
PORT=8001 ./start.sh
```

> **Note:** The first run downloads the speech model weights (~150 MB). Subsequent runs use the local cache. The tested environment uses the exact packages captured in `requirements-lock.txt`.

## Neon studio update

- **9:16 + Fill** is now the default. Auto framing always fills the portrait frame. Select **Fit** or **Safe auto** explicitly if you want the wide source preserved with blurred background.
- A dedicated **Open clip editor** panel provides trim, focal point, layout, caption style/size/position, palette, per-word color overrides, and finishing controls.
- **AE Neon** uses bundled Montserrat ExtraBold plus broad and tight colored glow layers under sharp text. **Hot Pink**, **Money Green**, and **One Word Glow** are based on the supplied screenshots. The one-word display option also works with other styles.
- Fifteen local caption styles include Bold Highlight, Creator Pop, Minimal, Karaoke, and Boxed treatments inspired by Ssemble's public gallery. These are independent implementations, not imported Ssemble templates or paid API calls.
- Adjustable black bars and blur strips independently cover the top/bottom of the video. Video glow is a soft screen-blended bloom; captions are composited afterward and stay sharp.
- The editor renders changes when you press **Apply edits · HD preview**. Its video shows the last rendered preview, not a live approximation of unsaved edits.
- Existing outputs are unchanged. **Apply neon + fill screen** upgrades an older clip; the editor allows finer changes.
- Montserrat is redistributed under the SIL Open Font License, included beside the font in static/fonts/OFL.txt.

Public style reference: https://www.ssemble.com/docs/endpoints/templates

## Reference-style quality update

The Reference edit preset is based on the supplied Short's visible treatment: compact uppercase phrases near the center, white text with colored spoken-word accents, and stable portrait composition. The reference file is 1080×1440 (3:4), 60 fps; the app now supports 3:4 as well as 9:16 and preserves source frame rates up to 60 fps.

- Removed the oscillating zoom/shake pipeline, including for older presets. No added camera shake.
- Previews are now 720 pixels wide at CRF 18. Exports default to 1080 pixels wide at CRF 16. Rendering starts from the original source, not from a preview.
- Framing locks a fixed crop within a shot. Uncertain/group shots use a full-scene layout with blurred fill. Center and manual crop controls are available; horizontal and vertical focal points are editable.
- Caption phrases retain their position as words change color. Adjustable size and vertical position; no repeated per-word scaling.
- Small is the default local speech model; cached weights are ready on this machine. Old clips can be re-transcribed by selecting **Apply reference edit**, or by checking **Re-transcribe this range**. Re-transcription replaces corrected text.
- Strong temporal video denoising was removed to avoid smearing motion. Enhancement now uses light sharpening and gentler audio cleanup.
- Sound accents and clip-edge fades are opt-in; reference defaults preserve the original sound and camera motion.
- Existing MP4s are unchanged until re-rendered. Use **Apply reference edit** on an old clip to update it. A separate **Reference revision · your Speed footage** project contains full-scene and tighter portrait variants of one existing clip.

Upscaling increases output resolution; it is not AI super-resolution and cannot restore detail absent from the source. Matching manually chosen story beats, music, visual jokes, and custom event effects still requires editorial choices; this update does not pretend to automate an identical copy of the reference.

## Use

1. Upload MP4, MOV, MKV, WebM, AVI, or M4V, or paste an HTTPS YouTube video URL. The limits are 2 GB and three hours.
2. Pick a preset, desired clip length and count, caption style, and finishing options.
3. Generate clips. The first use of a new speech model downloads public model weights; subsequent runs use the local cache. Video and audio processing stays local.
4. Review the vertical previews. Open **Adjust clip & captions** to change trim points, preset, style, or caption text. Click **Update preview**.
5. Choose 720p or 1080p, click **Export MP4**, then download the finished file. Previews use 720×960 or 720×1280; exports use 1080×1440 or 1080×1920 (or 720 pixels wide when selected) with H.264/AAC and burned captions.

Projects and outputs persist under `data/`. The server uses a single worker queue to keep CPU/memory usage manageable. You can switch projects while processing runs. A server restart marks unfinished processing as interrupted; completed projects remain available. To retry initial processing, create a new project. Clip render failures can be retried in the editor.

## Included in the MVP

- Upload and yt-dlp YouTube ingestion, with validation and error reporting.
- Local multilingual speech-to-text with word timing, language detection, and voice activity detection.
- Automatic highlight candidates ranked by hook phrases, speech density, and audio energy; sentence-end adjustment and overlap suppression.
- 3:4/9:16 shot-locked framing, full-scene fallback, and manual focal points.
- Nine caption styles: Reference, Pop, Karaoke, Clean, Neon, Impact, Boxed, Slide, Typewriter. ASS animation is burned into the actual video.
- Viral Shorts, Podcast, Gaming, and Challenge presets.
- Optional short fade-in/out transitions; artificial zoom oscillation and shake removed.
- Original, procedurally generated whoosh/pop/bass accents synchronized to preset zoom beats. No downloaded sound libraries.
- Light video sharpening, gentle audio denoise, and loudness normalization.
- Clip preview, trim adjustment, caption correction, and MP4 downloads.
- Host/origin checks, canonicalized YouTube URLs, constrained media paths, and argument-list media commands.

## Practical limits

This is a working MVP, not feature parity with OpusClip.

- Highlight scores are transparent heuristics, **not predicted virality** or a large language model's semantic judgment. Hook phrases currently favor English; transcription itself is multilingual. Speech-free sources fall back to audio energy or timeline sampling.
- Automatic framing chooses a fixed crop for each shot when detected subjects fit, and otherwise retains the full scene. It does **not** identify the active speaker by matching speech to lips. Profile faces, rapid cuts, multiple speakers, and game footage can require different framing; disable tracking for a centered crop. Manual mode also supports a vertical focal point.
- Editing is preset-driven. Sound effects match zoom beats rather than understanding events in the story. Transitions are clip-edge fades; silence removal, multi-shot jump cuts, and B-roll are not implemented.
- Caption corrections keep original word timings if the number of words is unchanged. Changed word counts are evenly distributed in the speech window. Use **Reset text to range** after trimming to restore matching source words. Very long words and languages without whitespace may need manual text adjustment.
- Enhancement is conventional filtering, not generative restoration or super-resolution. Upscaling cannot recover missing detail.
- If speech recognition fails, a visible warning appears and clip generation continues without automatic captions. You can enter caption text manually.
- YouTube availability depends on yt-dlp and YouTube restrictions. Private, age-gated, login-required, live, region-blocked, or rate-limited videos may fail; upload a local copy instead. Cookies/login import is intentionally not implemented.
- CPU processing can be slow on long videos. The default Small model favors accuracy; Tiny and Base are available for quicker drafts. No paid API or account is required.
- This is a single-user localhost app. Keep it bound to 127.0.0.1. It has no internet-facing authentication, distributed queue, project deletion UI, or automatic disk cleanup.

## Modular architecture

| File | Responsibility |
| --- | --- |
| `app/main.py` | API, persisted jobs, queue, uploads, render orchestration |
| `app/catalog.py` | Caption style and editing preset registry |
| `app/media.py` | FFmpeg probing, audio extraction, thumbnails |
| `app/transcribe.py` | Local Whisper model loading and word-timed transcription |
| `app/highlights.py` | Candidate selection, ranking, overlap suppression |
| `app/tracking.py` | Face detection and crop motion commands |
| `app/captions.py` | Safe ASS generation and timed caption animation |
| `app/effects.py` | Motion filter construction and synthesized sounds |
| `app/render.py` | Video/audio composition and encoding |
| `static/` | Responsive interface, project polling, editing controls |

To add a preset, add an entry to `PRESETS`; the UI reads it automatically. To add a caption appearance using an existing animation, add a `STYLES` entry. To add a new animation, also implement its renderer in `captions.py`. Effects are isolated in `effects.py`. Replace `highlights.rank` or `tracking.plan_framing` to improve analysis without replacing the UI or queue.

## Validation

```sh
# Activate your virtual environment first
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

python -m pytest -q tests
node --check static/app.js
```

Tests render real videos for every caption style, check output dimensions/duration/audio, handle silent portrait media, validate URL and subtitle-input handling, and exercise upload → preview → edited export → download through the API, including byte-range playback responses.

`tests/fixtures/sample.mp4` is a generated test pattern with synthetic speech, not user footage. It can be uploaded for a quick local demo.

## Quality roadmap

1. Evaluate candidate clips on your own podcast/gaming/challenge footage and tune ranking weights. Add scene boundaries, pause-aware cuts, and an optional local language model for coherent story selection.
2. Replace the face heuristic with a more robust detector and shot-aware tracker; add mouth-motion/audio active-speaker selection and a manual focal-point override.
3. Add forced alignment after caption editing, font selection and safe-area controls, and phrase emphasis based on prosody.
4. Add silence removal with caption remapping, event-triggered motion/SFX, beat-aware transitions, and optional B-roll.
5. Add cancellation, job recovery, project cleanup, and optional hardware encoding after quality comparisons.

## Upstream references

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — local transcription and word timestamps.
- [FFmpeg filter documentation](https://ffmpeg.org/ffmpeg-filters.html) — cropping, subtitles, motion, denoise, and audio mixing.
- [yt-dlp installation](https://github.com/yt-dlp/yt-dlp/wiki/Installation) — downloader setup and updates.

### Live studio revision — September 15

The clip editor now plays the original source with an immediate canvas preview, playback and a scrubber. Caption size, position, palette, individual word colors, crop, black bars, edge blur and video glow update without rendering. The preview stays visible while scrolling the controls, including narrow windows. Dark mode is the default; the header toggle remembers the browser's light/dark preference.

Captions default to a speech-timed float entrance and progressive word reveal. Choose Float, Pop or Still, or combine animated entrances with One Word display. A −2 to +2 second timing offset corrects consistent drift (positive means later). Word timestamps come from the local speech model; incorrect recognition/alignment may need transcript correction or retranscription. Changing the number of transcript words estimates timing, as indicated in the editor.

Motion blur adds adjustable temporal frame trails before caption compositing. This is a free frame-blending effect, not the proprietary RSMB plugin or optical-flow blur. Canvas blur/glow and fonts approximate FFmpeg output; Apply edits creates the authoritative HD preview. Automatic crop uses the last rendered shot positions; changing automatic framing/layout may require an HD render to refresh the crop. Manual framing is immediate. Existing clips retain their burned preview until Apply edits is pressed.

Unsupported browser codecs trigger a local H.264 source-preview conversion for the selected range, retaining the original source. Reopen the editor after saving a changed trim range when using this compatibility preview. All files stay within the project's local data directory.

Caption placement: in the clip editor, drag anywhere on the video or use the Left / right and Up / down percentage fields. Top, Center and Bottom shortcuts reset the horizontal center too. The position handle supports arrow keys (0.5% steps; Shift for 5%). Both axes cover 0–100% of the canvas; the caption block is centered on that point, so extreme positions can clip text. Coordinates are saved with clip settings and used for all exported caption layers and entrances.
