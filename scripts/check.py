"""Check the external tools required for local video rendering."""
import shutil
import subprocess
import sys

missing = [name for name in ('ffmpeg', 'ffprobe') if not shutil.which(name)]
if missing:
    raise SystemExit('Missing ' + ', '.join(missing) + '. Install FFmpeg and add its bin folder to PATH; see README.md.')
filters = subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True, text=True, check=True).stdout
encoders = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True, check=True).stdout
if not all(name in filters for name in (' ass ', ' gblur ', ' tmix ')) or 'libx264' not in encoders:
    raise SystemExit('Your FFmpeg build needs libass subtitles, gblur, tmix and libx264. See README.md.')
print('FFmpeg, FFprobe, captions and video effects: ready.')
if not any(shutil.which(name) for name in ('node', 'deno', 'bun')):
    print('Tip: install a JavaScript runtime for YouTube imports. Uploaded videos do not need it.')
