"""Date-first card state, explicit presence, and lossless migration helpers.

__remove is an operation, never a card attribute. Null, zero, false, empty
strings and arrays remain real values. No implicit coercions or deep merge.
"""
from __future__ import annotations
import copy
import json
import re
from datetime import date
from pathlib import Path

REMOVE = "__remove"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SPECS = ("id", "dbfId", "name", "type", "cardClass", "classes", "rarity",
         "collectible", "cost", "attack", "health", "durability", "armor",
         "text", "races", "race", "spellSchool", "mechanics", "legacyArt",
         "heroPowerDbfId", "runes", "chooseOne")
STATS = {"cost", "attack", "health", "durability", "armor"}
CURRENT_ONLY = ("nativeTags", "nativeRawText", "nativeTextBuilder", "portrait",
                "flavor", "artist", "watermark", "set", "relatedDbfIds")
# These installed/exporter attributes have no verified historical effective
# date. Unclassified fields require explicit gameplay classification rather
# than silently disappearing or being backdated. All excluded fields live in
# the sidecar. Callers may pass evidence-backed extra gameplay fields.
SIDECAR_FIELDS = set(CURRENT_ONLY) | {
    "art", "patches", "history", "releasedAt", "releaseStatus", "nativeSetId",
    "installed", "techLevel", "battlegroundsNormalDbfId",
    "battlegroundsPremiumDbfId", "battlegroundsRelatedCard",
    "battlegroundsBuddyDbfId", "battlegroundsSkinParentId",
    "isBattlegroundsDuosExclusive", "battlegroundsAssociatedRaces",
    "isBattlegroundsPoolMinion", "isBattlegroundsPoolSpell",
    "battlegroundsHero", "isBattlegroundsBuddy", "initialSpecStatus", "patchSources",
}
BREAK = re.compile(r'<br\s*/?>\s*(?:</br>)?|\\r\\n|\\n|\\r|\r\n?|\n|/n', re.I)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def put(path, value):
    path = Path(path)
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def valid_day(day):
    if not isinstance(day, str) or not DATE_RE.fullmatch(day):
        raise ValueError(f"Invalid KST calendar date: {day!r}")
    date.fromisoformat(day)
    return day


def json_equal(a, b):
    """JSON value equality: booleans are not numbers, including nested data."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(json_equal(x,y) for x,y in zip(a,b))
    if isinstance(a, (int,float)) and isinstance(b, (int,float)):
        return a == b
    return type(a) is type(b) and a == b


def apply(state, changes, *, validate=False):
    if not isinstance(changes, dict):
        raise ValueError("A date record must be an object")
    removed = changes.get(REMOVE, [])
    if (not isinstance(removed, list) or any(not isinstance(k, str) for k in removed)
            or len(set(removed)) != len(removed) or REMOVE in removed
            or any(k in changes for k in removed)):
        raise ValueError("Invalid or conflicting explicit removals")
    result = copy.deepcopy(state)
    for key in removed:
        if validate and key not in result:
            raise ValueError(f"Redundant removal: {key}")
        result.pop(key, None)
    for key, value in changes.items():
        if key == REMOVE:
            continue
        if validate and key in result and json_equal(result[key], value):
            raise ValueError(f"Redundant value: {key}")
        result[key] = copy.deepcopy(value)
    return result


def delta(before, after):
    result = {k: copy.deepcopy(v) for k, v in after.items()
              if k not in before or not json_equal(before[k], v)}
    removed = sorted(set(before) - set(after))
    if removed:
        result[REMOVE] = removed
    return result


def validate_timeline(timeline):
    if not isinstance(timeline, dict):
        raise ValueError("Timeline must be a date-keyed object")
    if list(timeline) != sorted(timeline):
        raise ValueError("Dates must be stored in ascending order")
    state = {}
    identity = None
    for index, (day, changes) in enumerate(timeline.items()):
        valid_day(day)
        json.dumps(changes, allow_nan=False)
        if not changes or (index == 0 and REMOVE in changes):
            raise ValueError("Empty record or removal in initial baseline")
        state = apply(state, changes, validate=True)
        if set(state) & SIDECAR_FIELDS:
            raise ValueError("Current-only/exporter metadata cannot be dated: " + ", ".join(sorted(set(state) & SIDECAR_FIELDS)))
        if not isinstance(state.get("id"), str) or not isinstance(state.get("type"), str):
            raise ValueError("Every reconstructable state requires id and type")
        current_identity = {k: state[k] for k in ("id", "dbfId") if k in state}
        if state.get("dbfId") is not None and (type(state["dbfId"]) is not int or state["dbfId"] <= 0):
            raise ValueError("DBF identity must be a positive integer or explicitly unknown")
        if identity is None:
            identity = current_identity
        elif not json_equal(current_identity, identity):
            raise ValueError("Card ID/DBF identity and presence are immutable")
        forbidden = {
            "MINION": {"durability", "armor"},
            "SPELL": {"attack", "health", "durability", "armor"},
            "WEAPON": {"health", "armor"},
            "LOCATION": {"attack", "health", "armor"},
            "HERO_POWER": {"attack", "health", "durability", "armor"},
        }.get(state["type"], set())
        if forbidden & state.keys():
            raise ValueError("Type change must explicitly remove inapplicable stats")
    return state


def fold(timeline, day=None):
    """Exact date-key folding. Before the first key, the card does not exist."""
    validate_timeline(timeline)
    if day is not None:
        valid_day(day)
    state = None
    for when, changes in timeline.items():
        if day is not None and when > day:
            break
        state = apply(state or {}, changes)
    return state


class UncertainHistory(ValueError):
    pass


def resolve(timeline, metadata, day=None, *, strict=False):
    """Compatibility is default. Strict refuses uncertainty, never verifies it.

    Estimated releases retain the earlier API's visibility before the estimate.
    Unknown releases use an explicitly undated baseline, without inventing keys.
    """
    status = metadata["release"]["status"]
    if day is not None:
        valid_day(day)
        if strict and (status != "verified" or metadata.get("baselineStatus") != "verified"):
            raise UncertainHistory("Release/baseline is not fully verified")
    if timeline:
        result = fold(timeline, day)
        if result is None and status != "verified" and not strict:
            return copy.deepcopy(next(iter(timeline.values())))
        return result
    unresolved = metadata.get("undated", {})
    state = copy.deepcopy(unresolved.get("baseline"))
    if state is None:
        return None
    for event in unresolved.get("patches", []):
        if day is None or event["date"] <= day:
            state = apply(state, event["changes"])
    return state


def project(state, *, hero_role=None, native_tags=None, gameplay_fields=()):
    """Drop exporter placeholders, not genuine zeroes. Never add a stat."""
    allowed_fields = set(SPECS) | set(gameplay_fields)
    unknown = set(state) - allowed_fields - SIDECAR_FIELDS
    if unknown:
        raise ValueError("Unclassified source fields require evidence-backed classification: " + ", ".join(sorted(unknown)))
    result = {k: copy.deepcopy(v) for k, v in state.items() if k in allowed_fields}
    kind = result.get("type")
    allowed = {"MINION": {"cost", "attack", "health"},
               "SPELL": {"cost"}, "WEAPON": {"cost", "attack", "durability"},
               "LOCATION": {"cost", "durability"}, "HERO_POWER": {"cost"}}
    if kind == "HERO":
        # Playable replacement cards grant armor. Base/skin/transformed hero
        # entities can have actual health; preserve it and only sourced stats.
        allowed[kind] = {"cost", "armor"} if hero_role == "playable-card" else {"health"}
        if hero_role != "playable-card":
            tag_ids = {t.get("id") for t in (native_tags or [])}
            for field, tag in (("attack",47),("cost",48),("armor",292)):
                if tag in tag_ids:
                    allowed[kind].add(field)
    if kind == "ENCHANTMENT":
        # Generic input already represents actual source fields; never add
        # defaults and never delete real enchantment effect/stat attributes.
        allowed[kind] = STATS
    if kind in allowed:
        for field in STATS - allowed[kind]:
            result.pop(field, None)
    # Empty exporter placeholders mean the attribute was not possessed. A
    # genuine race on a spell/choice card remains valid source data; type alone
    # cannot justify deleting it (e.g. Demon spells or Beast choice cards).
    for field, empty in (("race", ""), ("races", []), ("spellSchool", "")):
        if field in result and result[field] == empty:
            result.pop(field)
    if result.get("heroPowerDbfId") in (None, 0):
        result.pop("heroPowerDbfId", None)
    for field in ("text",):
        if isinstance(result.get(field), str):
            result[field] = BREAK.sub("<br></br>", result[field])
    return result


def original_states(document):
    card = copy.deepcopy(document["card"])
    patches = card.pop("patches", [])
    card.pop("history", None)
    states = [(card.get("releasedAt"), copy.deepcopy(card))]
    for event in patches:
        card.update(copy.deepcopy(event["changes"]))
        states.append((event["date"], copy.deepcopy(card)))
    return states


def projected_states(document):
    abilities = load(Path(__file__).with_name("brm-keyword-abilities.json"))
    cid = document["card"]["id"]
    result = []
    for day, state in original_states(document):
        state["mechanics"] = copy.deepcopy(abilities["baseline"][cid])
        for when, value in abilities["events"].get(cid, {}).items():
            if day is None or when <= day:
                state["mechanics"] = copy.deepcopy(value)
        role = "playable-card" if state.get("type") == "HERO" and state.get("collectible") else None
        result.append((day, project(state, hero_role=role, native_tags=state.get("nativeTags"))))
    return result


def abilities_vocabulary():
    return load(Path(__file__).with_name("brm-keyword-abilities.json"))["vocabulary"]


def migrate_document(document, current, source_commit):
    card = document["card"]
    release = {"date": card.get("releasedAt"), "status": card.get("releaseStatus", "pending")}
    states = projected_states(document)
    timeline = {}
    patches = []
    prior = states[0][1]
    if release["date"]:
        timeline[release["date"]] = prior
    for day, state in states[1:]:
        changes = delta(prior, state)
        if changes:
            if release["date"]:
                timeline[day] = changes
            else:
                patches.append({"date": day, "changes": changes})
        prior = state
    metadata = {
        "schema": "hscard-date-metadata-1", "id": card["id"],
        "timezone": "Asia/Seoul", "release": release,
        "baselineStatus": "partially-verified",
        "confidenceNote": "Existing dates and baseline values are preserved, not independently promoted to verified. Strict historical lookup remains unavailable while baseline verification is incomplete.",
        "sourceCommit": source_commit,
        "originalSource": copy.deepcopy(document),
        "currentCatalog": copy.deepcopy(current),
        "currentOnlyFields": list(CURRENT_ONLY),
        "canonicalFields": sorted({k for _, state in states for k in state}),
        "keywordAbilityEvidence": {"source": "tools/brm-keyword-abilities.json", "vocabulary": abilities_vocabulary()},
        "legacyMechanicsConvention": {"present": "mechanics" in card, "original": card.get("mechanics", []), "canonicalBaseline": states[0][1]["mechanics"]},
    }
    if not release["date"]:
        metadata["undated"] = {"baseline": states[0][1], "patches": patches,
            "reason": "No verified or previously adopted release date; no synthetic date key is created."}
    if card["type"] == "HERO":
        metadata["heroRole"] = "playable-card" if card.get("collectible") else "transformed-hero-entity"
    metadata["chooseOneEvidence"] = {
        "meaning": "Original parent ability boolean, not generated-option membership.",
        "preservedOriginalValue": copy.deepcopy(card["chooseOne"]),
        "baselineBasis": "BRM_010 release text explicitly has Choose One; the other40 original false booleans are retained. Current tags are corroboration, not release proof.",
        "oldCurrentCatalogPresence": "Absent; root preserves endpoint-specific omission.",
        "source": "tools/brm-keyword-abilities.json"}
    validate_timeline(timeline)
    return timeline, metadata


def read_card(root, cid):
    return load(Path(root)/"data"/(cid+".json")), load(Path(root)/"metadata"/(cid+".json"))


def compatibility_card(root, cid):
    """Read-only old audit view of canonical data, never another source."""
    from legacy_projection import project_legacy
    timeline, metadata = read_card(root, cid)
    card = copy.deepcopy(metadata["originalSource"]["card"])
    points = list(timeline.items())
    baseline = project_legacy(points[0][1], metadata)
    for field in SPECS:
        if field in ("id", "dbfId"):
            continue
        card.pop(field, None)
    card.update(baseline)
    card["patches"] = []
    state = points[0][1]
    prior = baseline
    for day, change in points[1:]:
        state = apply(state, change)
        nxt = project_legacy(state, metadata)
        change = delta(prior, nxt)
        if change:
            if REMOVE in change:
                raise ValueError("Old audit view cannot express this future removal")
            card["patches"].append({"date": day, "changes": change})
        prior = nxt
    for correction in metadata.get("historyDateCorrections", []):
        card.setdefault("patchSources", {})[correction["correctedDate"]] = correction["sources"]
    card["releasedAt"] = metadata["release"]["date"]
    card["releaseStatus"] = metadata["release"]["status"]
    return card
