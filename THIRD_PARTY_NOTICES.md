# Third-party components

Clipforge's original code uses the MIT license. Dependencies, model weights and fonts retain their own licenses.

- Montserrat ExtraBold: Copyright 2024 The Montserrat.Git Project Authors. SIL Open Font License 1.1; full text in `static/fonts/OFL.txt`. Source: https://github.com/JulietaUla/Montserrat
- FFmpeg: installed separately, not bundled. The license depends on the selected build; builds with libx264 generally use the GPL. See https://ffmpeg.org/legal.html.
- Speech recognition uses faster-whisper and downloaded Whisper-compatible model weights. Review their upstream licenses when redistributing models or binaries: https://github.com/SYSTRAN/faster-whisper and https://github.com/openai/whisper.
- Python dependencies are listed in `requirements.txt`; each retains its upstream license.

Caption presets are independently implemented visual styles. No Ssemble templates, proprietary RSMB code, or reference footage are included. This project is not affiliated with Ssemble, OpusClip, or other editing products.
