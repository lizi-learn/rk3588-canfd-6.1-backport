#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Offline source-release integrity checks; no device access or kernel build."""
import ast
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
for line in (root/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split('  ',1)
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise SystemExit('Checksum mismatch: '+name)
provenance=json.loads((root/'PROVENANCE.json').read_text())
for entry in provenance['files']:
    folder='reference/upstream-driver' if entry['file'].startswith('rockchip_canfd') or entry['file']=='Makefile' else 'reference/compatibility'
    path=root/folder/entry['file']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
        raise SystemExit('Upstream reference mismatch: '+str(path.relative_to(root)))
for path in list((root/'scripts').glob('*.py'))+list((root/'board').rglob('*.py'))+[root/'tools/lbm5-canfd-test',root/'board/assets/lbm5-interfaces']:
    ast.parse(path.read_text(),filename=str(path))
summary=json.loads((root/'evidence/verification-summary.json').read_text())
if summary['formal_application_frames']!=160000 or summary['external_receive_transmit_verified']:
    raise SystemExit('Unexpected validation claim')
for run in summary['runs']:
    if len(run['tests'])!=8 or run['status']!='pass':
        raise SystemExit('Unexpected test matrix')
    for case in run['tests']:
        if case['frames_checked']!=10000 or case['hardware_rx_frames']!=10000:
            raise SystemExit('Unexpected frame counts')
print('Offline checks passed: release hashes, pinned sources, Python syntax, validation boundaries.')

new=json.loads((root/'board/evidence/20261025-kit-final.json').read_text())
if new['pass'] or new['physical']['can_zero_error_pass']:
    raise SystemExit('Final hardware acceptance must retain the known failure.')
if new['physical']['rs485_turnaround']['completed_turns']!=200 or not all(t['pass'] for t in new['physical']['rs485']):
    raise SystemExit('Unexpected RS485 evidence.')
failed=json.loads((root/'board/evidence/20261025-fd5m-brp10-repeat-failed.json').read_text())
if failed['pass'] or failed['error_delta']['can0']['bus_error']!=49 or failed['error_delta']['can1']['bus_error']!=45:
    raise SystemExit('CAN FD repetition failure must not be lost.')
print('Board evidence preserved: health/RS485 pass, CAN zero-error acceptance remains failed.')
