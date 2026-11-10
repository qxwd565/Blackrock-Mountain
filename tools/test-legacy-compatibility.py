#!/usr/bin/env python3
"""Byte-stable current catalog and unchanged-consumer historical behavior."""
import argparse, copy, hashlib, json, subprocess, sys
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urljoin
from date_schema import load,put,json_equal
from legacy_projection import PHP_FIELDS
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1]
SOURCE='0773e288056208e120d64f8fd11bf0834fa47b4a'
BASE_URL='https://raw.githubusercontent.com/qxwd565/Blackrock-Mountain/main/'


def source_bytes(path):
    return subprocess.check_output(['git','show',SOURCE+':'+path],cwd=ROOT)


def old_resolve(current,history,day):
    result=copy.deepcopy(current);done=set()
    for revision in history:
        if revision.get('from','0001-01-01')<=day<revision.get('before','9999-12-31'):
            for key,value in revision['changes'].items():
                if key in PHP_FIELDS and key not in done:
                    result[key]=copy.deepcopy(value);done.add(key)
    return result


def main(fixture=None):
    catalog=load(ROOT/'cards.json');render=load(ROOT/'render.json');history=load(ROOT/'history.json')
    precise=load(ROOT/'cards-date.json');precise_history=load(ROOT/'history-date.json')
    assert len(catalog['cards'])==len(precise['cards'])==41
    assert all(x.get('schema')==1 and 'historySchema' not in x for x in [catalog,render,history])
    assert precise_history['historySchema']==2
    for name in ['cards.json','render.json','history.json']:
        assert '__remove' not in (ROOT/name).read_text(encoding='utf-8')
    by_id={c['id']:c for c in catalog['cards']};render_by_id={c['id']:c for c in render['cards']}
    assert all('chooseOne' not in c for c in catalog['cards'])
    assert sum(c['chooseOne'] is True for c in precise['cards'])==1
    assert sum(c['chooseOne'] is False for c in precise['cards'])==40
    assert len(by_id)==41 and len({c['dbfId'] for c in catalog['cards']})==41
    original=json.loads(source_bytes('cards.json'))
    original_history=json.loads(source_bytes('history.json'))['cards']
    assert (ROOT/'cards.json').read_bytes()==source_bytes('cards.json'),'Current catalog byte drift'
    assert json_equal(catalog,original)
    original_by_id={c['id']:c for c in original['cards']}
    assets=set(subprocess.check_output(['git','ls-tree','-r','--name-only',SOURCE,'--','art','golden'],cwd=ROOT,text=True).splitlines())
    for asset in assets:assert (ROOT/asset).read_bytes()==source_bytes(asset),asset
    dates={'1900-01-01','2026-11-09','2099-12-31'}
    for cid in by_id:
        raw=load(ROOT/'metadata'/(cid+'.json'))['originalSource']['card']
        for d in [raw['releasedAt']]+[p['date'] for p in raw['patches']]:
            dates.update((date.fromisoformat(d)+timedelta(days=n)).isoformat() for n in [-1,0,1])
    dates.update((date.fromisoformat('2023-02-15')+timedelta(days=n)).isoformat() for n in (-1,0,1))
    dates.update((date.fromisoformat('2017-04-05')+timedelta(days=n)).isoformat() for n in (-1,0,1))
    corrections={}
    cases=[];art_checks=0;corrected_cases=0
    for current in catalog['cards']:
        cid=current['id'];dbf=str(current['dbfId'])
        for field in ('cost','attack','health','durability','armor'):
            assert type(current[field]) is int and 0<=current[field]<=32767
        assert current['art'] in assets
        for bundle in ('cards.json','render.json','history.json','cards-date.json','render-date.json','history-date.json'):
            assert urljoin(BASE_URL+bundle,current['art'])==BASE_URL+current['art'];art_checks+=1
        rows=history['cards'].get(dbf,{}).get('history',[])
        assert rows==render_by_id[cid].get('history',[])
        for day in sorted(dates):
            actual=old_resolve(current,rows,day)
            before=old_resolve(original_by_id[cid],original_history.get(dbf,{}).get('history',[]),day)
            if cid=='BRM_015' and '2015-08-19'<=day<'2017-04-05':
                # Reviewed client 3.0-7.1 Korean text had no line break.
                before['text']='<b>모든</b> 하수인에게 피해를 $1 줍니다. 내 생명력이 12 이하면, 피해를 $3 줍니다.'
            # Presence too, not just values; no unrelated exceptions.
            assert json_equal(actual,before),(cid,day,'old behavior drift',actual,before)
            assert actual['id']==cid and actual['dbfId']==current['dbfId']
            cases.append({'id':cid,'dbfId':current['dbfId'],'date':day,
                          'expected':{k:v for k,v in before.items() if k in PHP_FIELDS}})
    assert (ROOT/'history.json').stat().st_size<=524288
    assert 'fetch-depth: 0' in (ROOT/'.github/workflows/normalize-card-history.yml').read_text()
    report={'result':'pass','sourceCommit':SOURCE,'oldPluginBase':'78ce6fdc4e70f689880a70d6f22aa77a6c75e337',
            'currentCards':41,'currentCatalogueByteIdentical':True,
            'legacyDateCases':len(cases),'artURLChecks':art_checks,'preservedAssetFiles':len(assets),
            'missingAssets':0,'rootHistoryBytes':(ROOT/'history.json').stat().st_size,
            'preciseHistoryBytes':(ROOT/'history-date.json').stat().st_size,
            'visibility':'unchanged; no new release/strict gating','reviewedHistoryCorrections':corrections,'correctedLegacyDateCases':corrected_cases}
    put(ROOT/'tools/legacy-compatibility-validation.json',report)
    if fixture:put(fixture,{'catalog':catalog,'history':history,'cases':cases,'allowed':list(PHP_FIELDS),
                           'originalCatalog':original,'baseUrl':BASE_URL,'expectedCards':41})
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);main(p.parse_args().fixture)
