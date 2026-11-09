#!/usr/bin/env python3
"""All migration sources and six outputs must be stable on repeated builds."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
files=[p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts]
def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
before=hashes()
for _ in range(2):
    for tool in ('migrate-date-schema.py','build-api.py'):
        subprocess.run([sys.executable,str(ROOT/'tools'/tool)],check=True,capture_output=True)
    after=hashes()
    assert before==after,{'changed':[p for p in before if before[p]!=after[p]]}
print(json.dumps({'result':'pass','repeatedBuilds':2,'checkedFiles':len(files)}))
