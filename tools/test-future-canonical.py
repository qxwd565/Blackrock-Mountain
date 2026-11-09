#!/usr/bin/env python3
"""Prove approved future state changes propagate instead of freezing current outputs."""
from pathlib import Path
import tempfile,shutil,subprocess,sys,json
from date_schema import load,put
r=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='brm-future-',dir='/tmp') as tmp:
 root=Path(tmp)
 for name in ('tools','data','metadata'):shutil.copytree(r/name,root/name)
 shutil.copy2(r/'cards.json',root/'cards.json')
 baseline=(r/'cards.json').read_bytes();p=root/'data/BRM_028.json';timeline=load(p)
 timeline['2090-01-01']={'cost':0,'mechanics':['TAUNT']};put(p,timeline)
 subprocess.run([sys.executable,str(root/'tools/build-api.py')],check=True,capture_output=True)
 for filename in ('cards.json','cards-date.json'):
  c=next(c for c in load(root/filename)['cards'] if c['id']=='BRM_028')
  assert c['cost']==0 and 'TAUNT' in c['mechanics']
 assert (r/'cards.json').read_bytes()==baseline
 assert load(root/'metadata/BRM_028.json')==load(r/'metadata/BRM_028.json')
 print(json.dumps({'result':'pass','futureCostZeroAndKeywordPropagateToBothTransports':True,'immutableMetadataPreserved':True}))
