#!/usr/bin/env python3
import json,hashlib,pathlib,xml.etree.ElementTree as ET,collections
import argparse,re
parser=argparse.ArgumentParser(description="Re-extract the36 pinned BRM snapshots from local full CardDefs XML archives.")
parser.add_argument('--archive-dir',type=pathlib.Path,action='append',required=True)
args=parser.parse_args()
r=pathlib.Path(__file__).resolve().parents[1]
source=json.loads((r/'tools/brm-client-numeric.json').read_text())['buildSources']
source=dict(sorted(source.items(),key=lambda item:tuple(map(int,item[0].split('.')))))
ids={p.stem for p in (r/'data').glob('*.json')}
filemap={}
for p in [p for directory in args.archive_dir for p in directory.glob('*CardDefs.xml')]:
 with p.open() as f: head=f.read(300)
 import re
 build=re.search(r'build="(\d+)"',head)
 if build:filemap[build[1]]=p
# Narrow ability vocabulary; do not conflate targeting metadata, rarity, class or stats.
mechs={'32':'TRIGGER_VISUAL','189':'WINDFURY','190':'TAUNT','191':'STEALTH','192':'SPELLPOWER','194':'DIVINE_SHIELD','197':'CHARGE','208':'FREEZE','217':'DEATHRATTLE','218':'BATTLECRY','219':'SECRET','220':'COMBO','215':'OVERLOAD','311':'CANT_BE_TARGETED_BY_SPELLS','332':'CANT_BE_TARGETED_BY_HERO_POWERS','362':'AURA','363':'POISONOUS','212':'ENRAGED','685':'LIFESTEAL','1077':'CASTS_WHEN_DRAWN','791':'RUSH','1207':'MEGA_WINDFURY','1211':'ELUSIVE','443':'CHOOSE_ONE'}
selected=set(mechs)|{'45','47','48','187','199','200','202','203','321','1635','2540','2542','2543','1720','1584','296','349','350','370','377','388','389','292'}
report={'schema':1,'scope':'41 BRM IDs, 36 selected archived builds; bounded observations, not full rule-engine or every-build verification.','tagMeaning':'Actual Tag and ReferencedTag children are separate. ReferencedTag alone never proves an intrinsic ability; The card’s own text and functional behavior may supply additional evidence.','mechanicTags':mechs,'builds':[]}
for build,url in source.items():
 p=filemap[build.split('.')[-1]];root=ET.parse(p).getroot();cards={}
 for e in root:
  cid=e.get('CardID')
  if cid not in ids:continue
  cards[cid]={kind:{t.get('enumID'):t.get('value') for t in e if t.tag==kind and t.get('enumID') in selected and t.get('value') is not None} for kind in ('Tag','ReferencedTag')}
  cards[cid]['name']=e.findtext('./Tag[@enumID="185"]/koKR')
  cards[cid]['rawText']=e.findtext('./Tag[@enumID="184"]/koKR')
  cards[cid]['actualMechanics']=[name for tag,name in mechs.items() if int(cards[cid]['Tag'].get(tag,0))>0]
 assert set(cards)==ids if tuple(map(int,build.split('.'))) >= (5,0) else set(cards)==ids-{'OG_044b'}
 report['builds'].append({'build':build,'source':url,'xmlSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cards':cards})
(r/'tools/brm-mechanics-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'selectedBuilds':len(report['builds']),'cardObservations':sum(len(b['cards']) for b in report['builds'])}))
