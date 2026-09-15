import os
from pathlib import Path

_model = None
_model_name = None


def transcribe(audio, model_name, cache_dir):
    global _model, _model_name
    from faster_whisper import WhisperModel
    if _model is None or _model_name != model_name:
        local = cache_dir / model_name
        source = str(local) if (local / "model.bin").exists() else model_name
        _model = WhisperModel(source,device="cpu",compute_type="int8",download_root=str(cache_dir),cpu_threads=4)
        _model_name = model_name
    segments, info = _model.transcribe(str(audio),beam_size=5,word_timestamps=True,vad_filter=True)
    result, words = [], []
    for segment in segments:
        result.append({"start":segment.start,"end":segment.end,"text":segment.text.strip()})
        for w in segment.words or []:
            if w.end > w.start:
                words.append({"start":w.start,"end":w.end,"word":w.word.strip()})
    return result, words, info.language
