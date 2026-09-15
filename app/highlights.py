"""Explainable, offline ranking. No claim of an AI virality prediction."""
import math
import re
import wave
import numpy as np

HOOKS = re.compile(r"\b(secret|why|how|never|best|worst|imagine|surprising|actually|mistake|finally|unbelievable|wait|but|amazing|first|million|won|lost)\b", re.I)


def audio_energy(path):
    if not path or not path.exists():
        return []
    with wave.open(str(path)) as f:
        rate = f.getframerate()
        raw = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    values = [float(np.sqrt(np.mean(raw[i:i+rate] ** 2))) for i in range(0, len(raw), rate)]
    peak = max(values, default=1) or 1
    return [x / peak for x in values]


def rank(segments, energy, duration, length, count):
    length = min(float(length), duration)
    starts = {0.0}
    if segments:
        starts.update(max(0, float(s["start"]) - 0.15) for s in segments)
    else:
        starts.update(float(t) for t in range(0, max(1, math.ceil(duration-length+1)), max(3, int(length/3))))
    candidates = []
    for start in sorted(starts):
        if start + min(length, 8) > duration:
            continue
        start = min(start, max(0, duration-length))
        end = min(duration, start+length)
        # End on a nearby sentence boundary when possible.
        boundaries = [s["end"] for s in segments if start+length*0.78 <= s["end"] <= min(duration, start+length*1.12)]
        if boundaries:
            end = min(boundaries, key=lambda x: abs(x-end))
        selected = [s for s in segments if s["end"] > start and s["start"] < end]
        text = " ".join(s["text"].strip() for s in selected)
        hooks = len(HOOKS.findall(text))
        activity = float(np.mean(energy[int(start):max(int(start)+1, math.ceil(end))])) if energy[int(start):math.ceil(end)] else 0
        speech = sum(max(0, min(end, s["end"])-max(start, s["start"])) for s in selected) / max(1, end-start)
        score = min(98, round(30 + min(hooks, 5)*6 + activity*22 + min(speech,1)*16))
        reasons = []
        if hooks:
            reasons.append("Hook language")
        if activity > 0.35:
            reasons.append("Audio energy")
        if speech > 0.55:
            reasons.append("Strong speech density")
        if not reasons:
            reasons = ["Timeline candidate — review manually"]
        title = (selected[0]["text"].strip()[:75] if selected else f"Moment at {int(start)//60}:{int(start)%60:02}")
        candidates.append({"start": round(start,2), "end": round(end,2), "score": score, "title": title, "text": text, "reasons": reasons})
    chosen = []
    for c in sorted(candidates, key=lambda x: x["score"], reverse=True):
        if any(max(0, min(c["end"],p["end"])-max(c["start"],p["start"])) > 0.25*min(c["end"]-c["start"],p["end"]-p["start"]) for p in chosen):
            continue
        chosen.append(c)
        if len(chosen) >= count:
            break
    return chosen
