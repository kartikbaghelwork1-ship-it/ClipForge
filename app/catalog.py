"""Declarative extension points. Add a style or preset here to expose it in the UI."""
STYLES = {
    "one_word": {"name":"One Word Glow","color":"#42FF23","animation":"single","size":64,"description":"One spoken word at a time · electric glow"},
    "magenta": {"name":"Hot Pink","color":"#FF00D9","animation":"solid_glow","size":48,"description":"Heavy magenta lettering · matching your second photo"},
    "money": {"name":"Money Green","color":"#89FF00","animation":"lines_glow","size":48,"description":"White first line · lime second line"},
    "hormozi": {"name":"Bold Highlight","color":"#FFFF00","animation":"reference","size":48,"description":"Ssemble-inspired bold white type and yellow accents"},
    "creator": {"name":"Creator Pop","color":"#49E5FF","animation":"pop","size":50,"description":"Ssemble-inspired compact creator captions"},
    "minimal": {"name":"Minimal","color":"#FFFFFF","animation":"fade","size":38,"description":"Ssemble-inspired clean white captions"},
    "reference": {"name": "Reference", "color": "#F7FF39", "animation": "reference", "size": 38, "description": "Compact phrases · colored spoken words"},
    "pop": {"name": "Pop", "color": "#B7FF42", "animation": "pop", "size": 68, "description": "Lime word accents in stable phrases"},
    "karaoke": {"name": "Karaoke", "color": "#FFDA57", "animation": "karaoke", "size": 59, "description": "Follow every spoken word"},
    "clean": {"name": "Clean", "color": "#FFFFFF", "animation": "fade", "size": 54, "description": "Quiet, crisp phrase fades"},
    "neon": {"name": "AE Neon", "color": "#FAFF00", "animation": "glow", "size": 48, "description": "Multi-color words · layered neon bloom"},
    "impact": {"name": "Impact", "color": "#FFFFFF", "animation": "impact", "size": 72, "description": "Bold white word emphasis"},
    "boxed": {"name": "Boxed", "color": "#FFFFFF", "animation": "box", "size": 54, "description": "Readable dark label"},
    "slide": {"name": "Slide", "color": "#D0B4FF", "animation": "slide", "size": 62, "description": "Soft phrase fades"},
    "typewriter": {"name": "Typewriter", "color": "#FFAD79", "animation": "type", "size": 56, "description": "Build a phrase word by word"},
}
PRESETS = {
    "reference": {"name": "Reference edit", "icon": "✦", "description": "Stable framing. Compact color captions.", "style": "reference", "zoom": 0, "interval": 8.0, "shake": 0, "sfx": "pop", "sfx_gain": 0.055},
    "viral": {"name": "Viral Shorts", "icon": "↗", "description": "Bold captions. Stable shots.", "style": "pop", "zoom": 0.10, "interval": 3.6, "shake": 0.002, "sfx": "pop", "sfx_gain": 0.14},
    "podcast": {"name": "Podcast", "icon": "◉", "description": "Let the conversation lead.", "style": "clean", "zoom": 0.035, "interval": 8.0, "shake": 0.0, "sfx": "whoosh", "sfx_gain": 0.035},
    "gaming": {"name": "Gaming", "icon": "✛", "description": "Bright captions. Preserve the action.", "style": "neon", "zoom": 0.14, "interval": 2.8, "shake": 0.006, "sfx": "bass", "sfx_gain": 0.18},
    "challenge": {"name": "Challenge", "icon": "ϟ", "description": "Clear phrases. Keep the reveal.", "style": "impact", "zoom": 0.12, "interval": 3.2, "shake": 0.004, "sfx": "whoosh", "sfx_gain": 0.16},
}
