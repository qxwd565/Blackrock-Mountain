# Date-first Blackrock Mountain data

Scope: `qxwd565/Blackrock-Mountain`, all 41 existing IDs (31 collectible cards and 10 generated forms, choices, hero and power entities). Pinned source: `0773e288056208e120d64f8fd11bf0834fa47b4a`. No other expansion or plugin is modified.

## Canonical dates and presence

`data/<CARD_ID>.json` retains every filename and ID, with ascending KST date keys. The first date contains the known initial gameplay specification, later dates contain only sparse changes. All 35 prior events on 25 IDs remain on their existing dates. Missing later fields inherit. `__remove: ["field"]` explicitly removes attributes. Zero, false, null, empty strings and lists are genuine values when supported, not deletion instructions.

The 41 current exact states include 30 MINION, 9 SPELL, one HERO and one HERO_POWER. Genuine zero attack on Dragon Egg stays zero. Spells have no fabricated combat stats. Druid of the Flame choices BRM_010a/b begin as SPELL with a sourced Beast affiliation, lose race/races explicitly on 2016-10-21, and become MINION previews on 2018-11-30; their actual stat swap follows on 2019-02-06. Their generated playable forms are distinct IDs and retain their own chronology. Empty description after the type change is a real empty string.

BRM_027h is the transformed Ragnaros hero entity, not a collectible replacement hero card. It retains genuine health 8 and heroPowerDbfId 2319. Its generic source zero cost/attack/armor/durability fields have no actual release/current tags and are treated as exporter placeholders, not retrospectively verified stats. Source and root projection keep those zeroes. BRM_027p is a two-cost HERO_POWER with no invented attack/health/armor/durability. This is field-specific evidence filtering, never a rule that zero is absent.

The original chooseOne boolean is true only on BRM_010 and false on the other 40 source documents. All values remain canonical; the old current catalog omits that field and retains its original endpoint-specific presence convention. Full parent/child and asset relationships remain in sidecars and current bundles; hero-power linkage is also canonical.

Display text uses exactly `<br></br>`; raw evidence is retained verbatim. Empty race/races/school exporter placeholders are filtered only in precise states. Existing `race` is the primary tribe label while `races` can contain both tribes: Beast/Elemental records do not invent a joined label. Spell schools begin on 2021-03-26, Fireguard Destroyer gains Elemental on 2017-04-05, original Druid forms retain their 25.0 date (2022-11-30), OG_044b retains its 25.4 date (2023-02-15), and Core Rager retains 34.6 (2026-02-10).

## Availability and evidence boundaries

The user selected ordinary constructed-match availability in Korea, not client preload, demos, Arena previews or earlier adventure challenges. Existing collectible wing/reward dates remain April 3, 10, 17, 24 and May 1, 2015. Related generated entities follow their producer. OG_044b first becomes available with Fandral Staghelm on April 27, 2016; it is not backdated to BRM's release.

The separate date recheck documents Korean wing/reward sources and later patch checks. Actual 25.0 archives contain secondary Elemental tag 2540 on the four original Druid choices/forms, while OG_044b lacks it until 25.4. A contemporary 25.4 list groups these forms loosely and is not enough to move their original 25.0 dates. The exact Korean server-live day for the four originals is inferred from the identified 25.0 client change and patch schedule, not independently confirmed by a card-specific live gameplay record. This qualification is retained; a client snapshot alone is not universal proof of server timing.

All 41 baselines remain partially verified. Fourteen initial Korean name/text timelines and three rarity timelines are explicitly provisional. Unknown intermediate wording and rarity transitions are retained as observed ranges, without fabricated dates. The rarity sidecars for BRM_010a, BRM_010b and BRM_022t distinguish inherited display values from archive tag observations. The current migration does not claim every-build, exact cosmetic, engine-bug, or format-legality completeness.

## Bounded intrinsic keyword lists

`tools/brm-keyword-abilities.json` defines the scope: recognized intrinsic keywords and targeting restrictions, not every free-text effect or engine flag. An empty list does not mean the card has no effect. All 41 lists are stable over the 36 selected archives, after a release-text exception: BRM_010 has Choose One in its initial text before the dedicated 443 tag appears in sampled 5.0. No new gameplay date is inferred from that implementation change.

Actual XML `Tag` and `ReferencedTag` children are extracted separately in `tools/brm-mechanics-evidence.json` with pinned source URLs and full-file SHA256 hashes. Own text matters as well; tag child type is not an infallible semantic oracle. Lava Shock references unlocking Overload but does not itself cause Overload. Its original `mechanics: ["OVERLOAD"]` is therefore retained only in raw evidence and the old transport, while the precise intrinsic list is empty. Eight `TRIGGER_VISUAL` annotations are retained as implementation evidence, not intrinsic keywords. No dated gameplay change is inferred from fluctuating AURA/TRIGGER_VISUAL flags.

The old root mechanics convention remains present on 23 records and absent on 18. It preserves order, implementation markers and Lava Shock's reference annotation. This is a narrow compatibility overlay: independently tested future canonical keyword additions/removals and cost changes still propagate; the whole current state is not frozen.

## Lossless sidecars and dual transports

Every `metadata/<ID>.json` retains the complete immutable originalSource, pinned sourceCommit, unchanged currentCatalog, relationships, raw text/tags, installed/current-only attributes, evidence and confidence. Every existing non-output JSON evidence file is byte-identical. No native/current-only field is dated as a release fact. Exact full-state replay is `fold`; a date before release returns no card. Strict historical resolution rejects partial baselines rather than silently promoting them.

Six root siblings preserve `art/<ID>` URL bases:

- `cards.json`, `render.json`, `history.json`: schema1 for unchanged existing clients; no removal operations. Current cards.json remains byte-for-byte equal to the pinned source. Before-release fallback and global visibility remain unchanged.
- `cards-date.json`, `render-date.json`, `history-date.json`: precise current type-specific state and historySchema2. Reverse intervals are disjoint, with explicit attribute-removal operations and authoritative current gameplay state.

The postponed plugin must not be pointed to the precise endpoints. Its old whitelist, native-tag handling, zero fallback, and unsupported HERO/HERO_POWER frames remain unchanged. Schema compatibility does not establish correct live rendering or import. `tools/legacy-compatibility-losses.json` describes these limits.

## Rebuild and verification

Run from the repository root:

1. `python3 tools/migrate-date-schema.py`
2. `python3 tools/build-api.py`
3. `python3 tools/test-brm-history.py`
4. `python3 tools/test-date-schema.py`
5. `python3 tools/test-brm-mechanics.py`
6. `python3 tools/test-legacy-compatibility.py`
7. `python3 tools/test-future-canonical.py`
8. `python3 tools/test-build-idempotence.py`
9. `python3 tools/test-clean-migration.py`
10. `git diff --check`

CI uses the committed local builder and checkout `fetch-depth: 0`. The old wrapper writer is disabled and retained as read-only reference for the prior audit's validation helpers. Missing pinned-source history fails explicitly. Clean pinned-source migration reproduces all 88 canonical/sidecar/bundle files byte-for-byte.

Coverage includes all 41 source documents, all 35 events, 474 old audit boundary checks, 2,583 all-card/global-date precise cases, 2,583 unchanged old-consumer cases, 1,470 retained numeric observations and a fresh 1,470 keyword observations from the same 36 builds. These are overlapping checks, not 2,940 independent snapshots. All 239 art/golden files and 246 sibling-relative art URL checks remain intact. Presence fixtures cover real zero, false, null, empty, explicit removal, immutable identity, unclassified fields and all supported card-type transitions.

For the unchanged PHP parser, create a fixture with `python3 tools/test-legacy-compatibility.py --fixture /tmp/brm-compatibility.json`, then run `php tools/test-legacy-plugin.php /path/to/unmodified/plugin /tmp/brm-compatibility.json`. The pinned unmodified plugin commit is `78ce6fdc4e70f689880a70d6f22aa77a6c75e337`. This harness tests imports and historical resolution offline, not WordPress, browser rendering, deployment or database migration.

The exact two PHP source blobs were re-fetched by their pinned Git hashes and verified locally before running the harness. PHP WASM 8.5.12 passes 2,584 checks: 41-card original/current import equality plus 2,583 historical cases. The blob identities and scope are saved in `tools/unmodified-php-validation.json`; no plugin source was modified.
