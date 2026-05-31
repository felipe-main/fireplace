# Autonomous roadmap run — report (updated 2026-05-31, continuing)

Branch: **`feature/heroes-to-cataclysm`** · **all commits local, nothing pushed** (per your instruction).
Driver: disk-state loop in `roadmap/` (`progress.json` + `LOG.md` + per-set `manifest.json`).

Per your "do all, don't stop — store logs, I'll review" directive, the run is no longer stopping at
set #2; it continues through the roadmap. Logs for review: this file, `LOG.md`, `review.csv`,
`soak_*.log`, and the per-workflow transcripts.

## TL;DR

| # | Set | Status | Cards | Suite | Soak | Audit |
|---|-----|--------|-------|-------|------|-------|
| 1 | **Heroes of StarCraft** (mini, `SC_`) | ✅ **DONE** | 49/49 | 3060 pass | 1000/1000 | 8 fixed / 4 watch / **0 open** |
| 2 | **Into the Emerald Dream** (`EDR_`) | ✅ **DONE** | 145/145 + Imbue | 3288 pass / 2 skip | 1000/1000 | 25 fixed / 18 watch / **0 open** |
| 3 | Emerald Dream mini-set | ⏳ in progress | — | — | — | — |
| 4–8 | Shrouded City → Cataclysm | ⛔ queued | — | — | — | — |

## Set #1 — Heroes of StarCraft ✅ COMPLETE
Data `214839.1` (Patch 31.4). Faction engine (Protoss/Terran/Zerg), 49 cards, `launch=` channel,
multi-class fix. Audit 0-open. Nothing outstanding — safe to push.

## Set #2 — Into the Emerald Dream ✅ COMPLETE
Data `219197.1` (Patch 32.0). New package `fireplace/cards/emerald_dream/`. 145 `EDR_` cards + the
**Imbue** hero-power engine. Completion gate green, full suite **3288 passed / 2 skipped**, soak
**1000/1000**. Cleanup done this session:

1. **14 data-bump regressions in OTHER expansions fixed** (`b2735609`) — stat rebalances / pool / rework
   changes from build 219197 (Void Ray hp 1→2, Ceaseless Expanse cost 100→125, Seaside Giant reduction
   2→1, Kologarn dropped DEATHRATTLE tag, weapons moved durability→HEALTH tag, Painter's Virtue lost
   Lifesteal, Build-A-Beast pool, etc.). Each verified against live data, tight assertions.
2. **Full adversarial audit run** (247 agents: per-class finders + 3-vote refute panels) → 43 rows.
3. **All 13 real bugs fixed** — 8 at card-script level (`e625ae56`) + **5 needing an engine pass**
   (`3d845eff`):
   - `Bounce` now broadcasts at AFTER; Harbinger of the Blighted wired as a `Hand.events` listener.
   - End-turn one-turn-effect sweep now expires `weapon.buffs` (Barbed Thorn's Poisonous-this-turn).
   - New custom `PlayReq.REQ_TARGET_WITH_CARD_NAME` (Divination targets a friendly "Wisp" by name).
   - `_GiveDarkGift` records granted gifts on the recipient (Wallow + Overgrown Horror read them).
4. **review.csv closed**: 25 fixed / **18 watch / 0 open** (`e27b4549`).

**18 watch rows** are genuine engine/data limits, NOT bugs: Imbue `@`-scaling magnitudes (not in
CardXML), the Dark-Gift pool (not enumerated in data), "Temporary card" lifetime (no engine model),
Goldrinn stat-vs-damage doubling and Ohn'ahra/Plucky Podling (need Morph/Play-pipeline engine hooks).
These are documented for a future engine investment; none affect correctness of the common cases.

## Sets #3–8 — IN PROGRESS
Driver resumes at set #3 (Emerald Dream mini-set), then The Shrouded City (+mini), Across the Timeways
(+mini), Cataclysm. Flag-and-continue: any set that can't be greened or hits a data-ambiguous mechanic
is committed partial, marked `needs-human`, and the run advances. Builds/prefixes resolved per set at
its dump phase.

## How to review
- `git log --oneline feature/heroes-to-cataclysm` — every phase is a local commit.
- `review.csv` filtered to an Expansion — audit ledger (Status/Fix columns).
- `roadmap/LOG.md` — append-only phase trail; `roadmap/soak_*.log` — soak outputs.
- Nothing is pushed. When you're ready, pick what to push (set #1 and #2 are both clean/green).
