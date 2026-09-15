import json
from fractions import Fraction
import subprocess
from pathlib import Path


def run(args, timeout=1800):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr[-2200:] or result.stdout[-1000:] or "Media command failed")
    return result.stdout


def probe(path):
    data = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path], 30))
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if not video:
        raise ValueError("This file has no video stream.")
    duration = float(data.get("format", {}).get("duration", video.get("duration", 0)))
    if not 1 <= duration <= 10800:
        raise ValueError("Use a video between 1 second and 3 hours long.")
    # OpenCV and FFmpeg both autorotate phone footage.
    rotated = any(abs(int(s.get("rotation", 0))) % 180 == 90 for s in video.get("side_data_list", []))
    w, h = int(video["width"]), int(video["height"])
    return {"duration": duration, "width": h if rotated else w, "height": w if rotated else h,
            "fps": float(Fraction(video.get("avg_frame_rate", "30/1"))) if video.get("avg_frame_rate") not in {None,"0/0"} else 30,
            "has_audio": any(s["codec_type"] == "audio" for s in data["streams"])}


def extract_audio(source, target):
    run(["ffmpeg", "-y", "-v", "error", "-i", source, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", target])


def thumbnail(source, target, at=0):
    run(["ffmpeg", "-y", "-v", "error", "-ss", at, "-i", source, "-frames:v", "1", "-vf", "scale=480:-2", target], 60)
