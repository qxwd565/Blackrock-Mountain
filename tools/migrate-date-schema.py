#!/usr/bin/env python3
"""Lossless BRM wrapper to date-map migration; idempotent and source-pinned."""
from pathlib import Path
from date_schema import load,put,migrate_document,validate_timeline
import json,subprocess
ROOT=Path(__file__).resolve().parents[1]
SOURCE='0773e288056208e120d64f8fd11bf0834fa47b4a'
def main():
 catalog=load(ROOT/'cards.json');assert catalog['set']=='Blackrock Mountain'
 current={c['id']:c for c in catalog['cards']}
 audit={c['id']:c for c in load(ROOT/'tools/brm-release-audit.json')['cards']}
 evidence=load(ROOT/'tools/brm-mechanics-evidence.json');changed=0
 for p in sorted((ROOT/'data').glob('*.json')):
  doc=load(p)
  if 'card' not in doc:
   validate_timeline(doc);assert (ROOT/'metadata'/p.name).exists();continue
  original=json.loads(subprocess.check_output(['git','show',SOURCE+':data/'+p.name],cwd=ROOT))
  assert doc==original,'Migration input differs from reviewed pinned source'
  assert not (ROOT/'metadata'/p.name).exists(),'Refusing to overwrite original-source evidence'
  timeline,meta=migrate_document(doc,current[p.stem],SOURCE)
  reviewed=audit[p.stem]
  meta['baselineEvidence']=reviewed
  meta['currentOnlyFields']=sorted(set(current[p.stem])-set(meta['canonicalFields'])-{'releasedAt','releaseStatus'})
  meta['availabilityScope']='User-selected Korean ordinary constructed-match availability by wing/reward acquisition; excludes client preload and earlier adventure challenge use. Generated entities follow their producer, including OG_044b on 2016-04-27.'
  meta['dateRecheckEvidence']='tools/brm-date-recheck.json'
  if p.stem in ('BRM_010a','BRM_010b','BRM_010t','BRM_010t2'):
   meta['historicalDateConfidence']={'2022-11-30':'Retained 25.0 secondary-race date from actual archive tags plus Korean patch schedule. No independent card-specific server-live confirmation; client preload alone is insufficient. See tools/brm-date-recheck.json.'}
  meta['confidenceNote']='All existing dates and numeric evidence are preserved.14 initial Korean name/text timelines and3 rarity timelines remain provisional. No fully verified baseline or exact cosmetic transition is invented.'
  meta['undatedEvidence']={'historicalTextObservations':doc.get('historicalTextObservations',[]),'reason':'Client observation ranges are not Korean effective dates.'}
  meta['abilityImplementationObservations']=[];previous=None
  for b in evidence['builds']:
   if p.stem not in b['cards']:continue
   c=b['cards'][p.stem]
   observed={kind:{tag:v for tag,v in c[kind].items() if tag in evidence['mechanicTags']} for kind in ('Tag','ReferencedTag')}
   if observed!=previous:
    meta['abilityImplementationObservations'].append({'build':b['build'],'source':b['source'],**observed,'dateStatus':'Observation only, not an asserted Korean effective date.'});previous=observed
   else:meta['abilityImplementationObservations'][-1]['lastObservedBuild']=b['build']
  if p.stem in ('BRM_010a','BRM_010b','BRM_022t'):
   observations=[];previous=object()
   for b in evidence['builds']:
    value=b['cards'][p.stem]['Tag'].get('203')
    if value!=previous:observations.append({'build':b['build'],'rawTag203':value,'present':value is not None});previous=value
    else:observations[-1]['lastObservedBuild']=b['build']
   meta['fieldUncertainty']={'rarity':{'preservedValue':doc['card']['rarity'],'meaning':'Provisional inherited display value, not verified historical rarity.','observations':observations,'unresolved':'Exact effective dates and generated-entity display semantics. No dated rarity patch invented.','source':'tools/brm-mechanics-evidence.json'}}
  if p.stem=='BRM_027h':meta['heroEvidence']={'role':'transformed-hero-entity','health':8,'heroPowerDbfId':2319,'stats':'Only health is actually tagged in release and latest archives; zero cost/attack/armor/durability are exporter placeholders. No playable HERO template applied.','source':'tools/brm-mechanics-evidence.json'}
  put(ROOT/'metadata'/p.name,meta);put(p,timeline);changed+=1
 print(json.dumps({'migrated':changed,'format':'date-map-1'}))
if __name__=='__main__':main()
