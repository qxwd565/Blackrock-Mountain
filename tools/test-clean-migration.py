#!/usr/bin/env python3
"""Reproduce initial migration from the pinned source in an isolated temporary clone."""
from pathlib import Path
import tempfile,subprocess,shutil,sys,json,importlib.util
r=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('date_tests',r/'tools/test-date-schema.py');sys.path.insert(0,str(r/'tools'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='brm-date-clean-',dir='/tmp') as tmp:
 root=Path(tmp)/'repo'
 subprocess.run(['git','clone','--quiet','--no-hardlinks',str(r),str(root)],check=True)
 subprocess.run(['git','-C',str(root),'checkout','--quiet','--detach',m.SOURCE],check=True)
 shutil.copytree(r/'tools',root/'tools',dirs_exist_ok=True)
 for tool in ['migrate-date-schema.py','build-api.py']:
  subprocess.run([sys.executable,str(root/'tools'/tool)],check=True,capture_output=True)
 files=[*(r/'data').glob('*.json'),*(r/'metadata').glob('*.json'),*[r/f for f in ['cards.json','render.json','history.json','cards-date.json','render-date.json','history-date.json']]]
 diff=[str(p.relative_to(r)) for p in files if p.read_bytes()!=(root/p.relative_to(r)).read_bytes()]
 assert not diff,diff
 # Exercise the required failure path without creating or changing any commit.
 empty=Path(tmp)/'no-source';empty.mkdir();subprocess.run(['git','init','--quiet',str(empty)],check=True)
 try:m.require_source_commit(empty,m.SOURCE)
 except RuntimeError as e:assert 'fetch-depth: 0' in str(e)
 else:raise AssertionError('Missing pinned source silently accepted')
 report={'result':'pass','cleanPinnedSourceRegenerationByteMatches':len(files),'missingPinnedSourceFailsExplicitly':True,'sourceCommit':m.SOURCE}
 print(json.dumps(report))
 (r/'tools/clean-rebuild-validation.json').write_text(json.dumps(report,indent=2)+'\n')
