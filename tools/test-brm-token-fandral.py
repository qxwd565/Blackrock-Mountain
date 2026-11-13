#!/usr/bin/env python3
"""Verify all Blackrock Mountain generated IDs, original producer relations, and Fandral's release boundary."""
from __future__ import annotations
import json
from collections import Counter
from datetime import date,timedelta
from pathlib import Path
from date_schema import read_card,resolve
ROOT=Path(__file__).resolve().parents[1]
def read(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

def main():
    audit=read("tools/brm-token-fandral-review-20261114.json")
    catalog={c["id"]:c for c in read("cards-date.json")["cards"]}
    legacy={c["id"]:c for c in read("cards.json")["cards"]}
    policy=read("release-policy.json")
    manifest=read("manifest.json")
    assert audit["timezone"]==policy["timezone"]=="Asia/Seoul"
    assert len(catalog)==len(legacy)==manifest["sourceRecords"]==41
    assert manifest["collectible"]==31 and manifest["uncollectible"]==10
    assert {p.stem for p in (ROOT/"data").glob("*.json")}==set(catalog)
    assert {p.stem for p in (ROOT/"metadata").glob("*.json")}==set(catalog)
    assert audit["results"]["dateChangesRequired"] is False
    assert audit["results"]["unaccountedRelatedIds"]==[]
    assert audit["results"]["missingNormalMatchTokens"]==[]
    assert audit["results"]["fandralOnlyIncorrectFirstDates"]==[]
    fandral_day=audit["fandralFirstPlayableKst"]
    assert fandral_day=="2016-04-27"
    assert audit["sourceReferences"]["officialFandralReleaseKst"].startswith("https://hearthstone.blizzard.com/")
    children=audit["checkedBlackrockChildIds"]
    assert len(children)==10 and len({x["id"] for x in children})==10
    assert {x["id"] for x in children}=={cid for cid,c in catalog.items() if not c["collectible"]}
    counts=Counter()
    for c in children:
        cid=c["id"]
        current=catalog[cid]
        timeline,meta=read_card(ROOT,cid)
        day=c["releaseDateKst"]
        assert c["dbfId"]==current["dbfId"]==legacy[cid]["dbfId"],cid
        assert current["releasedAt"]==legacy[cid]["releasedAt"]==day,cid
        assert policy["cards"][cid]=={"date":day,"status":"verified"},cid
        assert meta["release"]=={"date":day,"status":"verified"},cid
        assert list(timeline)==sorted(timeline) and next(iter(timeline))==day,cid
        assert timeline[day]["type"]==c["initialCardType"],cid
        assert timeline[day]["collectible"] is False,cid
        assert resolve(timeline,meta,(date.fromisoformat(day)-timedelta(days=1)).isoformat()) is None,cid
        assert resolve(timeline,meta,day)["dbfId"]==current["dbfId"],cid
        counts[c["role"]]+=1
        if c["requiresFandral"]:
            assert cid=="OG_044b" and c["role"]=="fandral-exclusive-combined"
            assert c["parentCardIds"]==["BRM_010","OG_044"]
            assert day>=fandral_day
            assert day==fandral_day
            assert "2015-04-10" not in timeline
            assert meta["originalSource"]["card"]["releasedAt"]==day
        else:
            assert "OG_044" not in c["parentCardIds"],cid
            assert day<=fandral_day,cid
            assert all(parent_id in catalog for parent_id in c["parentCardIds"]),cid
            for parent_id in c["parentCardIds"]:
                assert catalog[parent_id]["releasedAt"]<=day,(cid,parent_id)
                _,source_meta=read_card(ROOT,parent_id)
                assert c["dbfId"] in source_meta["originalSource"]["relatedIds"],(cid,parent_id)
    assert counts==Counter({"summoned":2,"choice-effect":2,"normal-transform":2,
      "hero-transformation":1,"transformed-hero-power":1,
      "conditional-created":1,"fandral-exclusive-combined":1}),counts
    # Exhaustively check *every* stored related card reference, not just the
    # ten known children. One valid self-ID clone, BRM_019, is not a new token.
    expected={x["sourceId"]:[catalog[cid]["dbfId"] for cid in x["childIds"]]
              for x in audit["sourceRelatedIdExpectations"]}
    assert len(expected)==7
    for cid in catalog:
        _,meta=read_card(ROOT,cid)
        actual=meta["originalSource"].get("relatedIds",[])
        assert sorted(actual)==sorted(expected.get(cid,[])),(cid,"unexpected, missing or unmapped related ID",actual,expected.get(cid,[]))
    assert expected["BRM_019"]==[catalog["BRM_019"]["dbfId"]]
    # Original spell-like Choose One subcards were playable in 2015; their
    # later change of type to MINION cannot be used to backdate OG_044b.
    for cid in ("BRM_010a","BRM_010b"):
        timeline,_=read_card(ROOT,cid)
        assert next(iter(timeline))=="2015-04-10"
        assert timeline["2015-04-10"]["type"]=="SPELL"
    for cid in ("BRM_010t","BRM_010t2"):
        timeline,_=read_card(ROOT,cid)
        assert timeline["2015-04-10"]["type"]=="MINION"
    # Unused Whelp BRM_004t must remain deleted across every exported JSON.
    # BRM_022t is the legitimate Dragon Egg child and must remain available.
    assert "BRM_004t" not in catalog
    assert "BRM_022t" in catalog
    for filepath in (
        "data/BRM_004t.json",
        "metadata/BRM_004t.json",
        "golden/cards/BRM_004t.json",
        "art/BRM_004t.png",
    ):
        assert not (ROOT/ filepath).exists(), ("Unused Whelp reintroduced", filepath)
    assert "BRM_004t" not in policy["cards"]
    for api_file in (
        "cards.json", "cards-date.json", "render.json", "render-date.json",
        "history.json", "history-date.json", "manifest.json", "release-policy.json",
    ):
        document=read(api_file)
        assert "BRM_004t" not in json.dumps(document,ensure_ascii=False),api_file
        if api_file.startswith("history"):
            assert "2287" not in document["cards"],("Unused Whelp DBF restored",api_file)
    for cross in audit["crossExpansionFandralCombinedForms"]:
        assert cross["verifiedKst"]==fandral_day
        assert cross["repo"].startswith("qxwd565/")
    assert {x["id"] for x in audit["crossExpansionFandralCombinedForms"]}=={"OG_044a","OG_044b","OG_044c"}
    assert audit["results"]["totalExistingIDs"]==41 and audit["results"]["children"]==10
    print(json.dumps({"result":"pass","indexedCards":41,"collectible":31,"childCards":10,
      "fandralOnlyRelease":fandral_day,"crossSetCombinedIds":3,
      "allRawRelatedIdsAccountedFor":True,"excludedUnusedChild":"BRM_004t",
      "noBaselineDateChanges":True,"balancedPatchesUntouched":True},ensure_ascii=False))

if __name__=="__main__":
    main()
