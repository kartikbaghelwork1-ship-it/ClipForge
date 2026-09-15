"""Procedural, royalty-free sound design and reusable video filters."""
import wave
import numpy as np


def sound_track(path, duration, preset):
    rate = 48000
    output = np.zeros(int(duration*rate), dtype=np.float32)
    rng = np.random.default_rng(42)
    for index, at in enumerate(np.arange(preset["interval"], duration-0.3, preset["interval"])):
        n = int(rate*0.24)
        t = np.arange(n)/rate
        kind = preset["sfx"]
        if kind == "bass":
            signal = np.sin(2*np.pi*(100*t-100*t*t))*np.exp(-22*t)
        elif kind == "pop":
            signal = np.sin(2*np.pi*(650*t-850*t*t))*np.exp(-32*t)
        else:
            noise = rng.normal(0,1,n)
            signal = np.convolve(noise,np.ones(6)/6,mode="same")*np.sin(np.pi*t/0.24)**2
        signal = signal/(max(1., float(np.max(np.abs(signal))))) * preset["sfx_gain"]
        offset = int(at*rate)
        output[offset:offset+n] += signal[:len(output[offset:offset+n])]
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((np.clip(output,-1,1)*32767).astype(np.int16).tobytes())


def motion_filter(preset, width, height, duration, enabled, fps=30):
    # No zoompan: alternating integer crops caused shimmer and artificial camera shake.
    base = f"scale={width}:{height}:flags=lanczos,setsar=1,fps={fps}"
    if enabled:
        base += f",fade=t=in:st=0:d=0.08,fade=t=out:st={max(0,duration-0.1):.3f}:d=0.10"
    return base
