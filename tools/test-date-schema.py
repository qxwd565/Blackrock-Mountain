#!/usr/bin/env python3
"""Independent source replay, presence/type, all-date and preservation tests."""
from __future__ import annotations
import copy, hashlib, json, subprocess, sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from date_schema import (SPECS, REMOVE, apply, delta, fold, load, put, project,
                         read_card, resolve, validate_timeline, UncertainHistory, json_equal)
ROOT=Path(__file__).resolve().parents[1]
ABILITY_RELEASE=load(ROOT/"tools/brm-mechanics-evidence.json")["builds"][0]["cards"]
SOURCE='0773e288056208e120d64f8fd11bf0834fa47b4a'


def require_source_commit(root, commit):
    result=subprocess.run(['git','cat-file','-e',commit+':data'],cwd=root,capture_output=True)
    if result.returncode:
        raise RuntimeError('Pinned migration source commit unavailable: '+commit+
                           '. Fetch full history (checkout fetch-depth: 0) or explicitly fetch this commit; preservation checks cannot be skipped.')


def original(path):
    return json.loads(subprocess.check_output(['git','show',SOURCE+':'+path],cwd=ROOT))


def reverse(record, day):
    if record['releaseStatus']=='verified' and day<record['releasedAt']:return None
    state=copy.deepcopy(record['current']);state.pop('art',None)
    matching=[r for r in record['history'] if r.get('from','0001-01-01')<=day<r.get('before','9999-12-31')]
    assert len(matching)<=1,('overlapping intervals',record['id'],day)
    for rev in matching:
        # Independent implementation of exact reverse operations.
        for field in rev['changes'].get('__remove',[]):state.pop(field,None)
        state.update({k:copy.deepcopy(v) for k,v in rev['changes'].items() if k!='__remove'})
    return state

def fixtures():
    states=[
        {'id':'TEST','type':'MINION','cost':1,'attack':0,'health':3,'text':'Taunt','mechanics':['TAUNT']},
        {'id':'TEST','type':'SPELL','cost':0,'text':'','mechanics':[]},
        {'id':'TEST','type':'WEAPON','cost':0,'attack':1,'durability':0,'text':''},
        {'id':'TEST','type':'HERO','cost':0,'armor':5,'text':''},
        {'id':'TEST','type':'LOCATION','cost':1,'durability':2,'text':''},
        {'id':'TEST','type':'HERO_POWER','cost':0,'text':''},
        {'id':'TEST','type':'ENCHANTMENT','text':'','effectData':{'amount':0},'explicitNull':None},
    ]
    timeline={};previous={}
    for i,state in enumerate(states,1):
        timeline[f'2020-01-0{i}']=delta(previous,state);previous=state
    validate_timeline(timeline)
    assert fold(timeline,'2019-12-31') is None
    for i,state in enumerate(states,1):assert fold(timeline,f'2020-01-0{i}')==state
    assert 'attack' not in fold(timeline,'2020-01-02')
    assert fold(timeline,'2020-01-01')['attack']==0
    assert fold(timeline,'2020-01-02')['text']==''
    assert fold(timeline,'2020-01-07')['explicitNull'] is None
    assert apply({'x':None},{})=={'x':None}
    assert apply({'x':None},{REMOVE:['x']})=={}
    for before,after in ((False,0),(True,1),({'nested':[False,{'x':True}]},{'nested':[0,{'x':1}]})):
        patch=delta({'effect':before},{'effect':after})
        assert patch=={'effect':after} and patch
        assert apply({'effect':before},patch,validate=True)=={'effect':after}
    assert project({'id':'BASE','type':'HERO','health':30,'attack':0,'armor':0},native_tags=[{'id':45,'value':30}])=={'id':'BASE','type':'HERO','health':30}
    assert project({'id':'EN','type':'ENCHANTMENT','attack':0,'text':''})['attack']==0
    effect={'id':'EN','type':'ENCHANTMENT','effectData':{'amount':0},'text':'','actualZero':0,'actualFalse':False,'nullableEffect':None}
    assert project(effect,gameplay_fields={'effectData','actualZero','actualFalse','nullableEffect'})==effect
    try:project(effect)
    except ValueError:pass
    else:raise AssertionError('Unclassified effect fields silently dropped or backdated')
    raw={'id':'RAW','type':'SPELL','cost':0,'nativeSetId':1635,'installed':True,
         'techLevel':0,'battlegroundsNormalDbfId':0,'isBattlegroundsBuddy':False,
         'nativeTags':[{'id':1720,'value':1}],'releasedAt':'2013-08-17','releaseStatus':'estimated'}
    assert project(raw)=={'id':'RAW','type':'SPELL','cost':0}
    for race in ('DEMON','BEAST'):
        spell={'id':'CHOICE','type':'SPELL','cost':0,'text':'','race':race,'races':[race]}
        assert project(spell)==spell
    assert project({'id':'NO','type':'SPELL','cost':0,'race':'','races':[],'spellSchool':''})=={'id':'NO','type':'SPELL','cost':0}
    # Attribute loss creates explicit removal, never a future empty placeholder.
    before=project({'id':'RACE','type':'MINION','race':'BEAST','races':['BEAST'],'cost':1,'attack':1,'health':1})
    after=project({'id':'RACE','type':'MINION','race':'','races':[],'cost':1,'attack':1,'health':1})
    assert delta(before,after)=={REMOVE:['race','races']}
    for bad in ({'2020-02-30':states[0]}, {'2020-01-01':states[0],'2020-01-02':{'attack':0}}, {'2020-01-01':states[0],'2020-01-02':{REMOVE:['missing']}}, {'2020-01-01':states[0],'2020-01-02':{REMOVE:['attack'],'attack':1}}):
        try:validate_timeline(bad)
        except ValueError:pass
        else:raise AssertionError('Invalid/redundant timeline accepted')
    for change in ({'id':'OTHER'}, {REMOVE:['id']}, {'dbfId':456}, {REMOVE:['dbfId']}):
        bad={'2020-01-01':dict(states[0],dbfId=123),'2020-01-02':change}
        try:validate_timeline(bad)
        except ValueError:pass
        else:raise AssertionError('Card identity mutation accepted')
    for field,value in (('nativeTags',[]),('installed',True),('nativeSetId',1635),('techLevel',0),('set','LEGACY')):
        try:validate_timeline({'2020-01-01':states[0],'2020-01-02':{field:value}})
        except ValueError:pass
        else:raise AssertionError('Current-only field dated directly: '+field)


def independent_expected(doc, day):
 raw=copy.deepcopy(doc['card'])
 if day is not None and day<raw['releasedAt']:return None
 for e in raw['patches']:
  if day is None or e['date']<=day:raw.update(copy.deepcopy(e['changes']))
 # Korean client 3.0 text remained a single line until the 8.0 build.
 if raw['id']=='BRM_015' and day is not None and '2015-08-19'<=day<'2017-04-05':
  raw['text']='<b>모든</b> 하수인에게 피해를 $1 줍니다. 내 생명력이 12 이하면, 피해를 $3 줍니다.'
 fields={'id','dbfId','name','type','cardClass','classes','rarity','collectible','cost','attack','health','durability','armor','text','races','race','spellSchool','chooseOne','heroPowerDbfId'}
 result={k:copy.deepcopy(v) for k,v in raw.items() if k in fields}
 keep={'MINION':{'cost','attack','health'},'SPELL':{'cost'},'HERO_POWER':{'cost'},'HERO':{'health'}}[raw['type']]
 for k in {'cost','attack','health','armor','durability'}-keep:result.pop(k,None)
 for k,empty in [('race',''),('races',[]),('spellSchool','')]:
  if result.get(k)==empty:result.pop(k,None)
 if not result.get('heroPowerDbfId'):result.pop('heroPowerDbfId',None)
 # Independent semantics from release text, rather than migration's ability map.
 battlecries={'BRM_004','BRM_008','BRM_014','BRM_018','BRM_024','BRM_026','BRM_029','BRM_030','BRM_033','BRM_034'}
 result['mechanics']=['BATTLECRY'] if raw['id'] in battlecries else []
 if raw['id']=='BRM_009':result['mechanics']=['TAUNT']
 if raw['id']=='BRM_010':result['mechanics']=['CHOOSE_ONE']
 if raw['id']=='BRM_012':result['mechanics']=['BATTLECRY','OVERLOAD']
 if raw['id']=='BRM_027':result['mechanics']=['DEATHRATTLE']
 # Preserve immutable original source but recognize the one approved display
 # spelling correction after BRM_014's 2015-08-19 recorded wording change.
 if raw['id']=='BRM_014' and '<b>전투의_함성:</b>' in result.get('text',''):
  result['text']=result['text'].replace('<b>전투의_함성:</b>','<b>전투의 함성:</b>')
 return result

def main():
 fixtures();require_source_commit(ROOT,SOURCE)
 current={c['id']:c for c in load(ROOT/'cards-date.json')['cards']}
 rendered={c['id']:c for c in load(ROOT/'render-date.json')['cards']}
 histories=load(ROOT/'history-date.json')['cards']
 source_catalog={c['id']:c for c in original('cards.json')['cards']}
 recheck=load(ROOT/'tools/brm-date-recheck.json')
 reward_dates={cid:w['date'] for w in recheck['collectibleWings'] for cid in w['bossAndWingRewards']+w['classRewards']}
 assert len(reward_dates)==31
 assert reward_dates=={cid:c['releasedAt'] for cid,c in source_catalog.items() if c['collectible']}
 for cid in recheck['secondaryRaceTiming']['originals']:
  assert 'No independent' in load(ROOT/'metadata'/(cid+'.json'))['historicalDateConfidence']['2022-11-30']
 files=sorted((ROOT/'data').glob('*.json'))
 assert {p.stem for p in files}==set(current)==set(rendered)==set(source_catalog)
 assert len(current)==len(histories)==len({c['dbfId'] for c in current.values()})==41
 assert {p.name for p in files}=={p.name for p in (ROOT/'metadata').glob('*.json')}
 originals={p.stem:original('data/'+p.name) for p in files}
 dates={'1900-01-01','2099-12-31','2026-11-09'}
 for doc in originals.values():
  for d in [doc['card']['releasedAt']]+[e['date'] for e in doc['card']['patches']]:
   dates.update((date.fromisoformat(d)+timedelta(days=n)).isoformat() for n in (-1,0,1))
 dates.update((date.fromisoformat('2017-04-05')+timedelta(days=n)).isoformat() for n in (-1,0,1))
 tree=subprocess.check_output(['git','ls-tree','-r','--name-only',SOURCE],cwd=ROOT,text=True).splitlines()
 preserved=[]
 for path in tree:
  if path.endswith('.json') and not path.startswith('data/') and path not in ('cards.json','render.json','history.json'):
   assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',SOURCE+':'+path],cwd=ROOT),('evidence changed',path)
   preserved.append(path)
 checks=0;patches=0;types=Counter();losses=[]
 for p in files:
  cid=p.stem;timeline,meta=read_card(ROOT,cid);doc=originals[cid]
  assert meta['sourceCommit']==SOURCE
  assert 'ordinary constructed-match' in meta['availabilityScope']
  assert json_equal(meta['originalSource'],doc),(cid,'original JSON loss')
  assert json_equal(meta['currentCatalog'],source_catalog[cid]),(cid,'current metadata loss')
  assert meta['baselineStatus']=='partially-verified'
  assert meta['abilityImplementationObservations']
  assert doc['card']['chooseOne'] is (cid=='BRM_010') and 'chooseOne' not in meta['currentCatalog']
  assert current[cid]['chooseOne'] is rendered[cid]['chooseOne'] is doc['card']['chooseOne']
  assert meta['chooseOneEvidence']['preservedOriginalValue'] is doc['card']['chooseOne']
  assert set(rendered[cid]['currentOnlyFields']).isdisjoint(set(meta['canonicalFields']))
  if cid in ('BRM_010a','BRM_010b','BRM_022t'):
   assert 'Provisional' in meta['fieldUncertainty']['rarity']['meaning']
  assert meta['release']=={'date':doc['card']['releasedAt'],'status':'verified'}
  assert list(timeline)==sorted(timeline)
  assert len(timeline)==1+len(doc['card']['patches'])+(1 if cid=='BRM_015' else 0)
  validate_timeline(timeline);patches+=len(timeline)-1
  for day in sorted(dates):
   expected=independent_expected(doc,day);actual=resolve(timeline,meta,day)
   assert json_equal(actual,expected),(cid,day,'source replay',actual,expected)
   assert json_equal(reverse(histories[str(current[cid]['dbfId'])],day),expected),(cid,day,'history-date')
   render_current={k:v for k,v in rendered[cid].items() if k in SPECS}
   record={**histories[str(current[cid]['dbfId'])],'current':render_current,'history':rendered[cid]['history']}
   assert json_equal(reverse(record,day),expected),(cid,day,'render-date');checks+=1
  assert json_equal({k:v for k,v in current[cid].items() if k in SPECS},independent_expected(doc,None)),(cid,'current')
  for field,value in source_catalog[cid].items():
   if field not in SPECS:assert json_equal(current[cid][field],value),(cid,field,'current-only loss')
  state={}
  for day,change in timeline.items():
   nxt=apply(state,change);assert json_equal(delta(state,nxt),change),(cid,day,'redundant delta')
   if nxt.get('spellSchool'):assert day>='2021-03-26'
   if cid=='BRM_012' and nxt.get('race')=='ELEMENTAL':assert day>='2017-04-05'
   if len(nxt.get('races',[]))==2:
    bound='2023-02-15' if cid=='OG_044b' else '2026-02-10' if cid=='BRM_014' else '2022-11-30'
    assert day>=bound and nxt['race']=='BEAST'
   state=nxt
  types[state['type']]+=1
  try:resolve(timeline,meta,'2026-11-09',strict=True)
  except UncertainHistory:pass
  else:raise AssertionError('Incomplete baseline promoted')
  losses.append({'id':cid,'sourcePlaceholdersExcludedFromCanonical':{k:v for k,v in doc['card'].items() if k in SPECS and k not in next(iter(timeline.values()))}})
 assert patches==36 and types=={'MINION':30,'SPELL':9,'HERO':1,'HERO_POWER':1}
 assert current['BRM_022']['attack']==0
 hero=current['BRM_027h'];assert hero['health']==8 and hero['heroPowerDbfId']==2319
 assert not {'cost','attack','armor','durability'} & hero.keys()
 assert not {'attack','health','armor','durability'} & current['BRM_027p'].keys()
 for cid in ('BRM_010a','BRM_010b'):
  tl,_=read_card(ROOT,cid)
  assert tl['2016-10-21']=={'__remove':['race','races']}
  assert fold(tl,'2018-11-29')['type']=='SPELL' and 'attack' not in fold(tl,'2018-11-29')
  assert fold(tl,'2018-11-30')['type']=='MINION' and fold(tl,'2018-11-30')['text']==''
 assert current['BRM_011']['mechanics']==[]
 assert sum(c['chooseOne'] is True for c in current.values())==1
 report={'result':'pass','sourceCommit':SOURCE,'cards':41,'sourceDocumentsPreserved':41,'events':patches,'baselineFullyVerified':0,'partialExactInitialTexts':14,'uncertainRarityHistories':3,'globalDateSamples':len(dates),'exactSourceAndTransportChecks':checks,'types':dict(types),'reconstructedKeywordLists':41,'keywordDeltasAddedToExistingEvents':0,'preservedChooseOneBooleans':{'true':1,'false':40},'preservedPriorEvidenceFiles':preserved,'projectionChanges':losses,'presenceFixturesPassed':True}
 put(ROOT/'tools/date-schema-validation.json',report)
 print(json.dumps({k:v for k,v in report.items() if k not in ('projectionChanges','preservedPriorEvidenceFiles')}))
if __name__=='__main__':main()
