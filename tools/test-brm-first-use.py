#!/usr/bin/env python3
"""Independent first availability by Korean wing and generated Blackrock Mountain child IDs."""
from __future__ import annotations
import json
from collections import Counter
from datetime import date,timedelta
from pathlib import Path
from date_schema import read_card,resolve
ROOT=Path(__file__).resolve().parents[1]

def load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

def main():
    a=load("tools/brm-first-use-verification-20261113.json")
    old=load("tools/brm-independent-review.json")
    policy=load("release-policy.json")
    catalog={x["id"]:x for x in load("cards-date.json")["cards"]}
    legacy={x["id"]:x for x in load("cards.json")["cards"]}
    manifest=load("manifest.json")
    assert a["schema"]==1 and a["timezone"]==policy["timezone"]=="Asia/Seoul"
    assert len(a["wings"])==len(old["wingReviews"])==5
    assert len(catalog)==len(legacy)==len(policy["cards"])==manifest["sourceRecords"]==41
    assert manifest["collectible"]==31 and manifest["uncollectible"]==10
    assert set(catalog)==set(legacy)==set(policy["cards"])
    assert {p.stem for p in (ROOT/"data").glob("*.json")}==set(catalog)
    assert {p.stem for p in (ROOT/"metadata").glob("*.json")}==set(catalog)
    counts=Counter()
    all_ids=set()
    for entry,previous in zip(a["wings"],old["wingReviews"]):
        date_kst=entry["openDateKst"]
        assert date_kst==previous["date"]
        assert entry["evidence"]["official"].startswith("https://")
        assert entry["evidence"]["local"].startswith("https://")
        assert set(c["id"] for c in entry["collectibles"])==set(
            previous["bossRewards"]+[previous["wingReward"]]+list(previous["classRewards"].values()))
        for card in entry["collectibles"]:
            cid=card["id"]
            assert cid not in all_ids and catalog[cid]["collectible"],cid
            assert card["name"]==catalog[cid]["name"] and card["dbfId"]==catalog[cid]["dbfId"]
            assert card["kind"] in ("boss","wingLegendary","classChallenge")
            if card["kind"]=="boss":
                assert cid in previous["bossRewards"]
            if card["kind"]=="wingLegendary":
                assert cid==previous["wingReward"] and catalog[cid]["rarity"]=="LEGENDARY"
            if card["kind"]=="classChallenge":
                assert previous["classRewards"][card["heroClass"]]==cid
            counts[card["kind"]]+=1
            all_ids.add(cid)
        for card in entry["generated"]:
            cid=card["id"]
            assert cid not in all_ids and not catalog[cid]["collectible"],cid
            assert card["date"]==date_kst
            assert card["dbfId"]==catalog[cid]["dbfId"]
            assert card["parentCardIds"] and all(pid in catalog for pid in card["parentCardIds"])
            for pid in card["parentCardIds"]:
                assert catalog[pid]["releasedAt"]==date_kst
                _,parent_meta=read_card(ROOT,pid)
                assert card["dbfId"] in parent_meta["originalSource"]["relatedIds"],(cid,pid)
            all_ids.add(cid)
            counts["inEraGenerated"]+=1
    later=a["laterGenerated"]
    assert len(later)==1 and later[0]["id"]=="OG_044b"
    special=later[0]
    assert special["firstPlayableKst"]=="2016-04-27"
    assert special["parents"]==["BRM_010","OG_044"]
    assert catalog["BRM_010"]["releasedAt"]=="2015-04-10"
    assert "OG_044" not in catalog
    assert all(s.startswith("https://") for s in special["sources"])
    assert special["dbfId"]==catalog["OG_044b"]["dbfId"]
    all_ids.add("OG_044b")
    counts["laterGenerated"]+=1
    assert counts==Counter({"boss":17,"wingLegendary":5,"classChallenge":9,
                             "inEraGenerated":9,"laterGenerated":1}),counts
    assert all_ids==set(catalog)
    for cid,card in catalog.items():
        timeline,meta=read_card(ROOT,cid)
        assert policy["cards"][cid]=={"date":card["releasedAt"],"status":"verified"},cid
        assert legacy[cid]["releasedAt"]==card["releasedAt"],cid
        assert meta["release"]=={"date":card["releasedAt"],"status":"verified"},cid
        assert meta["originalSource"]["card"]["id"]==cid
        assert card["releaseStatus"]=="verified"
        assert list(timeline)[0]==card["releasedAt"],cid
        d=date.fromisoformat(card["releasedAt"])
        assert resolve(timeline,meta,(d-timedelta(days=1)).isoformat()) is None,cid
        assert resolve(timeline,meta,d.isoformat())["id"]==cid
        assert meta["baselineStatus"]=="partially-verified"
    assert a["result"]["changesNeeded"]==0
    assert a["result"]["misdatedGeneratedIds"]==[]
    assert a["result"]["incorrectInitialDates"]==[]
    assert a["result"]["missingCatalogIds"]==[]
    print(json.dumps({"result":"pass","cards":len(catalog),"collectible":31,
        "generated":10,"bossRewards":17,"wingLegendary":5,"classRewards":9,
        "originalWingDates":[w["openDateKst"] for w in a["wings"]],
        "laterCombined":"2016-04-27","releaseDateChanges":0,
        "rawSourceMutation":False},ensure_ascii=False))

if __name__=="__main__":
    main()
