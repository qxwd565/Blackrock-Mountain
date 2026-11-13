#!/usr/bin/env python3
"""Validate the bounded Blackrock Mountain audit without conflating client observations and live dates."""
from pathlib import Path
from datetime import date,timedelta
import copy,hashlib,importlib.util,json,re,subprocess,sys
R=Path(__file__).resolve().parents[1]
def load(p):return json.loads((R/p).read_text())
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
spec=importlib.util.spec_from_file_location('builder',R/'tools/wrapper_api_reference.py');B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
fixtures=load('tools/brm-current-fixtures.json')['cards'];obs=load('tools/brm-client-numeric.json')['cards']
current={c['id']:c for c in load('cards.json')['cards']};render={c['id']:c for c in load('render.json')['cards']};legacy=load('history.json')['cards']
from date_schema import compatibility_card
docs={p.stem:dict(json.loads((R/'metadata'/p.name).read_text())['originalSource'],card=compatibility_card(R,p.stem)) for p in (R/'data').glob('*.json')};audit=load('tools/brm-release-audit.json');policy=load('release-policy.json')
assert len(docs)==41 and set(docs)==set(current)==set(render)==set(fixtures)==set(obs)
assert sum(c['collectible'] for c in current.values())==31
for p in R.rglob('*.json'):json.loads(p.read_text())
def norm(s):return re.sub(r'<br\s*/?>\s*(?:</br\s*>)?|</br\s*>|\\r\\n|\\n|/n|\r\n|[\r\n]','<br></br>',s,flags=re.I)
def display(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ('nativeTags','nativeRawText'):continue
   if k in ('name','text','flavor') and isinstance(v,str):assert norm(v)==v,(k,v)
   else:display(v)
 elif isinstance(x,list):
  for v in x:display(v)
def forward(c,day):
 if day<c['releasedAt']:return None
 s={k:copy.deepcopy(c[k]) for k in B.SPEC_FIELDS if k in c};s['legacyArt']=c.get('legacyArt',False)
 for p in c['patches']:
  if p['date']<=day:s.update(p['changes'])
 return s
def reverse(c,day):
 if day<c['releasedAt']:return None
 s={k:copy.deepcopy(c[k]) for k in B.SPEC_FIELDS if k in c};s['legacyArt']=c.get('legacyArt',False)
 found=[h for h in c.get('history',[]) if ('from' not in h or h['from']<=day) and ('before' not in h or day<h['before'])]
 assert len(found)<=1,(c['id'],day)
 for h in found:s.update(h['changes'])
 return s
checks=0
tribes={14:'MURLOC',15:'DEMON',17:'MECHANICAL',18:'ELEMENTAL',20:'BEAST',21:'TOTEM',23:'PIRATE',24:'DRAGON'}
classes={0:'NEUTRAL',12:'NEUTRAL',2:'DRUID',3:'HUNTER',4:'MAGE',5:'PALADIN',6:'PRIEST',7:'ROGUE',8:'SHAMAN',9:'WARLOCK',10:'WARRIOR'}
types={3:'HERO',4:'MINION',5:'SPELL',10:'HERO_POWER'}
schools={0:'',2:'FIRE',5:'HOLY',7:'FEL'}
for cid,doc in docs.items():
 c=doc['card'];f=fixtures[cid]
 assert doc['schemaVersion']==2 and 'history' not in c
 assert c['initialSpecStatus']=='partially_verified'
 assert c['releasedAt']==current[cid]['releasedAt']==policy['cards'][cid]['date']
 assert c['releaseStatus']==current[cid]['releaseStatus']=='verified'
 assert c['dbfId']==current[cid]['dbfId']==f['dbfId']
 assert digest({k:c.get(k) for k in ('nativeTags','nativeRawText')})==f['nativeSourceHash'],cid
 assert digest(current[cid].get('nativeTags'))==f['currentNativeTagsHash'],cid
 assert digest(doc['historicalTextObservations'])==f['historicalTextObservationsHash'],cid
 actual=copy.deepcopy(current[cid]);actual.pop('history',None)
 # A previous one-time approved Korean spacing correction in BRM_014
 # changed only its current displayed text. The frozen fixture predates it.
 semantic_fixture=copy.deepcopy(actual)
 if cid=='BRM_014':
  assert '<b>전투의 함성:</b>' in semantic_fixture['text']
  semantic_fixture['text']=semantic_fixture['text'].replace('<b>전투의 함성:</b>','<b>전투의_함성:</b>')
 assert digest(semantic_fixture)==f['expectedNormalizedCurrentHash'],('unexpected current semantic change',cid)
 for card in (c,current[cid],render[cid]):display(card)
 # Latest raw names and text agree after established client-control formatting.
 latest=doc['historicalTextObservations'][-1]
 assert latest.get('lastObservedBuild',latest['build'])=='37.0.2.256589'
 def comparable(t):return re.sub(r'\s+','',norm(t).replace('<br></br>','').replace('[x]','').replace('$','').replace('_','').replace('#','').replace('&','').replace('{0}','1/1'))
 assert latest['name']==current[cid]['name']
 assert comparable(latest['rawText'])==comparable(current[cid]['text']),cid
 B.read_patches(c,cid)
 for p in c['patches']:
  assert p['date'] in c['patchSources'] or (cid=='BRM_015' and p['date']=='2017-04-05')
 dates={c['releasedAt'],'2026-11-09','2099-12-31'}|{p['date'] for p in c['patches']}
 for d in dates:
  for offset in (-1,0,1):
   day=(date.fromisoformat(d)+timedelta(days=offset)).isoformat();assert forward(c,day)==reverse(render[cid],day),(cid,day);checks+=1
 assert legacy.get(str(c['dbfId']),{}).get('history',[])==render[cid].get('history',[])
 assert forward(c,'2099-12-31')==reverse(current[cid],'2099-12-31')
 first=obs[cid][0];assert first[0]==('5.0.0.12574' if cid=='OG_044b' else '2.4.0.8311')
 assert [c[k] for k in ('cost','attack','health','durability')]==first[1:5],cid
 assert c['type']==types[first[6]]
 assert c['collectible']==bool(first[9]) and c['cardClass']==classes[first[8]]
 assert c['races']==([tribes[first[5]]] if first[5] else [])
 for o in obs[cid]:
  build=tuple(map(int,o[0].split('.')));state={k:c[k] for k in ('cost','attack','health','durability')}
  typ=c['type'];races=c['races'][:];school=''
  if cid in ['BRM_010a','BRM_010b']:
   if build>=(6,2):races=[]
   if build>=(13,0):
    typ='MINION';races=['BEAST'];state.update(cost=3,attack=2 if cid.endswith('a') else 5,health=5 if cid.endswith('a') else 2)
   if build>=(13,2):state.update(attack=5 if cid.endswith('a') else 2,health=2 if cid.endswith('a') else 5)
  if cid=='BRM_012' and build>=(8,0):races=['ELEMENTAL']
  if cid in ['BRM_010a','BRM_010b','BRM_010t','BRM_010t2'] and build>=(25,0):races=['BEAST','ELEMENTAL']
  if cid=='OG_044b' and build>=(25,4):races=['BEAST','ELEMENTAL']
  if cid=='BRM_014' and build>=(34,6):races=['BEAST','ELEMENTAL']
  if build>=(27,2):
   if cid=='BRM_008':state['cost']=4
   if cid=='BRM_016':state['health']=6
   if cid=='BRM_028':state.update(cost=5,attack=4,health=4)
  if build>=(20,0):school=current[cid].get('spellSchool','')
  observedRaces=([tribes[o[5]]] if o[5] else [])+(['ELEMENTAL'] if o[10] else [])
  assert list(state.values())==o[1:5],(cid,o[0],state,o[1:5])
  assert typ==types[o[6]],(cid,o[0],typ,o[6])
  assert races==observedRaces,(cid,o[0],races,observedRaces)
  assert school==schools[o[11]],(cid,o[0],school,o[11])
  assert c['cardClass']==classes[o[8]] and c['collectible']==bool(o[9])
  if cid not in ['BRM_010a','BRM_010b','BRM_022t']:
   assert c['rarity']=={0:'FREE',1:'COMMON',3:'RARE',4:'EPIC',5:'LEGENDARY'}[o[7]],(cid,o[0])
def at(cid,d):return forward(docs[cid]['card'],d)
assert '<br></br>' not in at('BRM_015','2017-04-04')['text']
assert at('BRM_015','2017-04-05')['text']=='<b>모든</b> 하수인에게 피해를 $1 줍니다.<br></br>내 생명력이 12 이하면, 피해를 $3 줍니다.'
assert at('BRM_028','2023-08-22')['cost']==6 and at('BRM_028','2023-08-22')['attack']==5
assert at('BRM_028','2023-08-23')['cost']==5 and at('BRM_028','2023-08-23')['attack']==4
assert at('BRM_016','2023-08-22')['health']==5 and at('BRM_016','2023-08-23')['health']==6
assert '3' in at('BRM_034','2023-08-22')['text'] and '5' in at('BRM_034','2023-08-23')['text']
assert at('BRM_010a','2018-11-29')['type']=='SPELL' and at('BRM_010a','2018-11-30')['type']=='MINION'
assert at('BRM_010a','2019-02-05')['attack']==2 and at('BRM_010a','2019-02-06')['attack']==5
assert at('BRM_010b','2019-02-05')['attack']==5 and at('BRM_010b','2019-02-06')['attack']==2
assert at('BRM_010t','2018-11-30')['attack']==5 and at('BRM_010t2','2018-11-30')['attack']==2
assert at('BRM_010a','2016-10-20')['races']==['BEAST'] and at('BRM_010a','2016-10-21')['races']==[]
assert at('BRM_010t','2022-11-29')['races']==['BEAST'] and at('BRM_010t','2022-11-30')['races']==['BEAST','ELEMENTAL']
assert at('OG_044b','2023-02-14')['races']==['BEAST'] and at('OG_044b','2023-02-15')['races']==['BEAST','ELEMENTAL']
assert at('BRM_014','2026-02-09')['races']==['BEAST'] and at('BRM_014','2026-02-10')['races']==['BEAST','ELEMENTAL']
assert at('BRM_013','2019-04-04')['name']=='속사' and at('BRM_013','2019-04-05')['name']=='신속 사격'
assert at('BRM_020','2016-11-29')['name']=='용혈족 마술사' and at('BRM_020','2016-11-30')['name']=='용족 마술사'
assert '생존할 때마다' in at('BRM_019','2018-02-06')['text'] and '생존한 후에' in at('BRM_019','2018-02-07')['text']
assert '영웅 능력' in at('BRM_027p','2022-11-29')['text'] and '영웅 능력' not in at('BRM_027p','2022-11-30')['text']
assert at('OG_044b','2016-04-26') is None and at('OG_044b','2016-04-27')['attack']==5
for day,ids in [('2015-04-03',['BRM_003','BRM_013','BRM_019','BRM_028']),('2015-04-10',['BRM_010a','BRM_010t','BRM_027h','BRM_027p','BRM_006t']),('2015-04-17',['BRM_022t','BRM_009']),('2015-04-24',['BRM_008','BRM_005']),('2015-05-01',['BRM_001','BRM_030','BRM_030t'])]:
 for cid in ids:
  assert at(cid,(date.fromisoformat(day)-timedelta(days=1)).isoformat()) is None
  assert at(cid,day) is not None
assert sum(not c['initialDisplayMatchesRelease'] for c in audit['cards'])==load('manifest.json')['partialInitialDisplayCardCount']
paths=[R/p for p in ('cards.json','render.json','history.json')]+list((R/'data').glob('*.json'))
before={p:p.read_bytes() for p in paths}
for _ in range(2):
 subprocess.run([sys.executable,str(R/'tools/build-api.py')],check=True,capture_output=True)
 assert all(p.read_bytes()==b for p,b in before.items()),'non-idempotent builder'
print(json.dumps({'cards':41,'collectible':31,'tokensAndOptions':10,'datedEvents':sum(len(d['card']['patches']) for d in docs.values()),'forwardReverseBoundaryChecks':checks,'clientNumericObservations':sum(map(len,obs.values())),'partialInitialDisplays':load('manifest.json')['partialInitialDisplayCardCount'],'currentGameplaySpecChanges':0,'currentReleaseMetadataChanges':0,'rawEvidencePreserved':True,'twoBuildsIdempotent':True}))
