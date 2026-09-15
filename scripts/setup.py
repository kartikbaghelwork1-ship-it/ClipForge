"""Cross-platform setup using only Python's standard library."""
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
if not (3, 11) <= sys.version_info[:2] <= (3, 13):
    raise SystemExit('Use Python 3.11, 3.12 or 3.13. Python 3.12 is recommended.')
venv.EnvBuilder(with_pip=True).create(ROOT / '.venv')
python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], check=True)
subprocess.run([str(python), str(ROOT / 'scripts/check.py')], check=True)
print('Ready. Run start.cmd on Windows, or ./start.sh on macOS/Linux.')
