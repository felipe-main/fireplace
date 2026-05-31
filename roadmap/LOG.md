# Autonomous roadmap run — log

Self-scheduling driver implementing all remaining sets (Heroes of StarCraft → Cataclysm).
Policy: flag-and-continue · local commits only (no push) · full-adversarial audit.
Each line: `tick | set#:name | phase | result`.

- 2026-05-31 | init | seed | progress.json + LOG.md created on branch feature/heroes-to-cataclysm
- 2026-05-31 | 1:Heroes of StarCraft | P0 data + P1 dump | bumped 213852->214839; pinned 49 SC_ cards, faction=GameTag PROTOSS/TERRAN/ZERG; manifest written
- 2026-05-31 | 1:Heroes of StarCraft | P2 engine | faction selectors+cost attrs+launch discount+protoss-spell counter; fixed Card.classes for MULTIPLE_CLASSES bitmask; 14 engine tests green
- 2026-05-31 | 1:Heroes of StarCraft | P3 launch | card workflow wf_0ca370a1-c5f launched (token-broker -> neutral/zerg/protoss/terran impl -> verify); 49 collectibles + ~20 token minions/hero-powers; partition race-free (factions split classes disjointly)
- 2026-05-31 | 1:Heroes of StarCraft | P3 cards+gate | all 49 SC_ cards implemented (workflow); fixed 3 base docstrings (data renames); full suite 3057 passed/2 skipped
- 2026-05-31 | 1:Heroes of StarCraft | engine-fix | launch effects fire at launch (new launch channel) + Thor _sc_starships_launched counter
- 2026-05-31 | 1:Heroes of StarCraft | P4+soak launch | audit workflow wf_bccbf6b0 + 1000-game soak (background)
- 2026-05-31 | 1:Heroes of StarCraft | soak | 1000/1000 succeeded, 0 failed (SC_ cards clean in random pools)
- 2026-05-31 | 1:Heroes of StarCraft | P5 tierfix | 8 fixed (654056da: Spawning Pool one-turn rush, launch-channel x3, Larva re-roll, Hallucination ExactCopy, Dark Templar req, Thor) + 4 watch; 0 open
- 2026-05-31 | 1:Heroes of StarCraft | P6 docs + re-soak | README->31.4, memory bumped, soak 1000/1000; SET #1 DONE
- 2026-05-31 | 2:Into the Emerald Dream | P0+P1 | bump 214839->219197.1; 145 EDR_ cards; novel mechanic=Imbue (hero-power upgrade, 6 Imbued HPs); manifest written
- 2026-05-31 | 2:Into the Emerald Dream | cards+engine | 145 EDR_ + Imbue (workflow wf_79cf7ebb + 2 hand-added); gate GREEN; weapon engine bug fixed; soak Give-crash fixed
- 2026-05-31 | 2:Into the Emerald Dream | needs-human | 14 non-EDR data-bump test regressions + Imbue scaling/Dark Gift approximations + audit pending; STOPPED before sets #3-8 (see REPORT.md)
- 2026-05-31 | 2:Into the Emerald Dream | soak | 600/600 succeeded, 0 failed (after Give-crash fix); engine stable
- 2026-05-31 | RESUME | user override "do all, don't stop" | resuming autonomous run: finish set#2 cleanup (14 regressions + audit) then drive sets #3-8. Local commits only.
- 2026-05-31 | 2:Into the Emerald Dream | databump-fix | wf_933351f9 worktrees branched STALE (1af5c0ee, no merge-back); re-applied via wf_96deef4d (no isolation, direct writes); 14 fixed; full suite 3266 passed/0 failed; commit b2735609
- 2026-05-31 | 2:Into the Emerald Dream | P4 audit | wf_8dc8a391 finders+3-vote refute (247 agents); 43 rows survived -> review.csv (13 real bugs, 24 approx, 6 once-overs)
- 2026-05-31 | 2:Into the Emerald Dream | P5 tierfix | wf_20ecc2f2 (12 agents): 20 cards fixed (e625ae56) + engine pass (3d845eff) closed 5 real bugs needing engine: Bounce-broadcasts-AFTER+Hand.events (Harbinger), weapon one-turn sweep (Barbed Thorn), REQ_TARGET_WITH_CARD_NAME (Divination), _GiveDarkGift records gifts (Wallow/Overgrown). Suite 3288 passed
- 2026-05-31 | 2:Into the Emerald Dream | P5 ledger | review.csv EDR closed: 25 fixed, 18 watch, 0 open (e27b4549). All 13 real bugs fixed; 18 watch = genuine @-scaling/Dark-Gift-pool/Temporary/Morph-Play-pipeline engine limits
- 2026-05-31 | 2:Into the Emerald Dream | P7 soak | 1000/1000 succeeded, 0 failed. SET #2 DONE (7df40d77)
- 2026-05-31 | 3:Emerald Dream mini-set (FIR_) | P0/P1 | bump 219197->219846.1 (Patch 32.2); 38 FIR_ Firelands cards, CardSet=EMERALD_DREAM; no data-bump regressions (small bump); novel=Smoldering; 039fff
- 2026-05-31 | 3:Emerald Dream mini-set (FIR_) | P2 engine | _smolder.py helper (_SmolderTick + smolder_level); reuses Dark Gift/Imbue/Corpses
- 2026-05-31 | 3:Emerald Dream mini-set (FIR_) | P3 cards+gate | wf_d7df8ca2: 38 FIR_ cards + Smoldering; gate GREEN; full suite 3364 passed; commit e398ef1b
- 2026-05-31 | 3:Emerald Dream mini-set (FIR_) | P4 audit | wf_09b1bd88 (finders+refute): 7 rows survived = 6 approx + 1 once-over, 0 REAL BUGS -> all watch; review.csv 25 fixed/25 watch/0 open
- 2026-05-31 | 3:Emerald Dream mini-set (FIR_) | P7 soak | first run 999/1000: latent GDB bug (Attr SELF _played_cost crash on indirect cast) -> default _played_cost=0 in PlayableCard.__init__; re-soak running
