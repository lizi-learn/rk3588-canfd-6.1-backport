#!/usr/bin/env python3
"""Refresh the manifest for tracked and unignored source files, excluding itself."""
import hashlib
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[1]
names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root).decode().strip('\0').split('\0')
rows = []
for name in sorted(set(names)):
    p = root / name
    if name != 'SHA256SUMS' and p.is_file():
        rows.append(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + name)
(root / 'SHA256SUMS').write_text('\n'.join(rows) + '\n')
print(f'Updated SHA256SUMS for {len(rows)} source files')
