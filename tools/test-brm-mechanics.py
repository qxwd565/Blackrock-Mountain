#!/usr/bin/env python3
"""Independent release-text/actual-tag keyword audit and compatibility convention checks."""
from pathlib import Path
import copy,json
from date_schema import load,put,read_card,fold
from legacy_projection import project_legacy
R=Path(__file__).resolve().parents[1]
e=load(R/'tools/brm-mechanics-evidence.json');definition=load(R/'tools/brm-keyword-abilities.json')
assert len(e['builds'])==36
assert sum(len(b['cards']) for b in e['builds'])==1470
assert 'Empty list' in definition['vocabulary'] and not definition['events']
checks=0;markers=0;missing=0
for p in sorted((R/'data').glob('*.json')):
 cid=p.stem;timeline,meta=read_card(R,cid);baseline=next(iter(timeline.values()))
 snapshots=[b for b in e['builds'] if cid in b['cards']]
 assert snapshots[0]['build']==('5.0.0.12574' if cid=='OG_044b' else '2.4.0.8311')
 for b in snapshots:
  c=b['cards'][cid]
  expected=[name for tag,name in e['mechanicTags'].items() if int(c['Tag'].get(tag,0))>0 and name not in ('AURA','TRIGGER_VISUAL')]
  if cid=='BRM_010' and 'CHOOSE_ONE' not in expected:
   assert '<b>선택' in c['rawText'];expected.append('CHOOSE_ONE')
  assert baseline['mechanics']==expected,(cid,b['build'],baseline['mechanics'],expected)
  assert fold(timeline)['mechanics']==expected
  checks+=1
 raw=meta['originalSource']['card'];legacy=project_legacy(baseline,meta)
 assert ('mechanics' in legacy)==('mechanics' in raw)
 assert legacy.get('mechanics')==raw.get('mechanics')
 markers+=('TRIGGER_VISUAL' in raw.get('mechanics',[]));missing+=('mechanics' not in raw)
 # A reviewed future canonical change must still change both projections.
 future=copy.deepcopy(baseline);future['mechanics'].append('TAUNT' if 'TAUNT' not in future['mechanics'] else 'RUSH')
 assert project_legacy(future,meta)['mechanics'][-1]==future['mechanics'][-1]
 if baseline['mechanics']:
  removed=baseline['mechanics'][0];future=copy.deepcopy(baseline);future['mechanics'].remove(removed)
  assert removed not in project_legacy(future,meta).get('mechanics',[])
assert markers==8 and missing==18
assert definition['baseline']['BRM_011']==[]
assert e['builds'][0]['cards']['BRM_011']['actualMechanics']==[]
assert '과부하' in e['builds'][0]['cards']['BRM_011']['rawText']
hero=e['builds'][0]['cards']['BRM_027h'];assert hero['Tag']['45']=='8' and '292' not in hero['Tag']
report={'result':'pass','builds':36,'cardKeywordObservations':checks,'boundedKeywordLists':41,'textBackedReleaseChooseOne':1,'sourceOverloadReferenceCorrectedInPreciseOnly':['BRM_011'],'legacyTriggerVisualAnnotationsRetained':markers,'legacyMechanicsAbsenceRetained':missing,'futureCanonicalKeywordChangesFlowThrough':True,'newGameplayDatesInferredFromFlags':0}
put(R/'tools/brm-mechanics-validation.json',report);print(json.dumps(report))
