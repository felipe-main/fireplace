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
- 2026-05-31 | 3:Emerald Dream mini-set (FIR_) | P7 soak | run1 999/1000 (_played_cost crash -> default 0); run2 999/1000 (Emerald Portal casts-when-drawn generator -> list()); run3 1000/1000, 0 failed. SET #3 DONE. README->Patch 32.2.219846
- 2026-05-31 | MILESTONE | 3 of 8 sets DONE | #1 StarCraft, #2 Emerald Dream, #3 Firelands mini all green+audited+soaked.
- 2026-05-31 | 4:The Shrouded City / Lost City of Un'Goro (TLC_) | P0/P1 | bump 219846->223542.1 (Patch 33.0); 145 TLC_ cards; novel=Kindred (matching minion-type/spell-school played PREVIOUS turn). Fixed 2 data-bump regressions (Flickering Lightbot cost 3->5; King Plush rework). 4b5b01c0
- 2026-05-31 | 4:Lost City (TLC_) | P2 engine | Kindred: player.races/schools_played_{this,last}_turn + Play.do record + _begin_turn rollover; Kindred evaluator + kindred_active() + KindredCost LazyNum; test_tlc_engine.py 4 tests green
- 2026-05-31 | 4:Lost City (TLC_) | P3 cards+gate | wf_98003509: 145 TLC_ cards; gate caught EDR_950 (new collectible at 223542 -> implemented) + TLC_436 corpse cost 5->3 + Shokk set-cost-enchant/determinism; full suite 3572 passed; commit bd0b5317 (+ removed stray tmp_paladin_tlc.py)
- 2026-05-31 | 4:Lost City (TLC_) | P4 audit | wf_99317081 (3-vote) crashed on StructuredOutput overload; re-ran lean wf_cb0d4079 (1-vote): 35 rows = 3 real bugs/22 approx/6 once-over/4 cosmetic
- 2026-06-01 | 4:Lost City (TLC_) | P5 tierfix | 3 real bugs fixed (3f327269): High Cultist Herenn simultaneous fight, Cursed Catacombs deck-Discover, + per-spell SPELLPOWER engine fix (closes Volcanic Thrasher AND EDR_874 Stellar Balance watch). 32 watch. review.csv 0 open real bugs
- 2026-06-01 | 4:Lost City (TLC_) | P6+P7 soak | README->Patch 33.0; soak 1000/1000. SET #4 DONE
- 2026-06-01 | MILESTONE | 4 of 8 sets DONE
- 2026-06-01 | 5:Lost City mini-set (DINO_) | P0/P1 | bump 223542->226928.1 (Patch 33.2); 38 DINO_ Dinosaur cards, CardSet=THE_LOST_CITY; reuses Kindred/Corpses/Outcast/Combo + Masks (set-stats) + Egg counters; no new mechanic. Fixed 9 data-bump regressions (quest totals 7->6/8->7/6->5/15->12, Osk 7/7->6/6, Playhouse Giant 20->25)
- 2026-06-01 | 5:Lost City mini-set (DINO_) | P3 cards+gate | wf_8fcbd1a2: 38 DINO_ cards; gate caught TLC_EVENT_402 (EVENT card -> skip) + 3 stale quest totals (TLC_433/460/229) -> engine progress_total data fallback; full suite 3638 passed; commit 7bec019c
- 2026-06-01 | 5:Lost City mini-set (DINO_) | P4 audit | wf_060b46a3 (lean): 4 rows, 0 real bugs, all watch
- 2026-06-01 | 5:Lost City mini-set (DINO_) | P7 soak | 2 latent crash fixes (Swampqueen Hagatha method-play combine; Mirrex re-entrant morph guard); soak 2000/2000. SET #5 DONE. README->Patch 33.2
- 2026-06-01 | MILESTONE | 5 of 8 sets DONE | Next: #6 Across the Timeways (TIME_TRAVEL, build TBD ~234xxx+)
- 2026-06-01 | 6:Across the Timeways (TIME_) | P0/P1/P2 | bump 226928->229984.1 (Patch 34.0, lowest build w/ full 145; CATACLYSM=0/PET=0 clean). NOVEL=Rewind (after play effect, choose Keep Timeline TIME_000ta no-op vs Rewind Timeline TIME_000tb re-run effect once). Engine: _RewindChoice in Play.do gated on GameTag.REWIND+trigger_battlecry; 3 micro-tests green. Fabled=cosmetic legendary marker (no engine). Scaffolded across_the_timeways pkg + hand-impl TIME_004. Fixed 4 data-bump regressions (DINO_130 token 1/2->3/3, DINO_422 7/7->7/5, DINO_407 Mirrex 3/3->3/4, EDR_488 Dark-Gift test de-brittled). Commit 31253c0a
- 2026-06-01 | 6:Across the Timeways (TIME_) | P3 cards+gate | wf_2c40ba8e DONE: 145 TIME_ cards (across_the_timeways pkg) + tokens, 0 real verify mismatches; full suite 3891 passed/2 skipped (twice); commit 012530ff
- 2026-06-01 | 6:Across the Timeways (TIME_) | P7 soak | run1 999/1000 (baseline utils.py:66 remove race, no TIME_ frame); run2 1000/1000, 0 failed. Soak GREEN
- 2026-06-01 | 6:Across the Timeways (TIME_) | P4 audit | wf_69d220d7 DONE: 19 survivors = 4 real bugs / 11 approx / 3 once-over / 1 cosmetic -> review.csv
- 2026-06-01 | 6:Across the Timeways (TIME_) | P5 tierfix | 4 real bugs fixed (04d6f336): Aeon Rend distinct-targets, Cease to Exist same-minion silence+destroy, Untimely Death turn+1 bound, Well of Eternity per-spell _casts_twice_self engine flag. test_timeways_tierfix.py 6 tests. Full suite 3897 passed/2 skipped. review.csv 4 fixed/15 watch/0 open
- 2026-06-01 | 6:Across the Timeways (TIME_) | P6 docs | README -> Patch 34.0.229984 + Across the Timeways line
- 2026-06-01 | 6:Across the Timeways (TIME_) | P7 soak | final 1000/1000, 0 failed (after tier-fix). SET #6 DONE (6ec6811b)
- 2026-06-01 | MILESTONE | 6 of 8 sets DONE | Next: #7 Across the Timeways mini-set (TIME_TRAVEL, build TBD; full set arrived 229984, mini-set later build)
- 2026-06-01 | 7:Across the Timeways mini-set (END_) | P0/P1/P2 | bump 229984->233275.1 (Patch 34.2; TIME_TRAVEL 145->183, prefix END_ 38 "End Time"; CATACLYSM still 0). Reuses Imbue/Rewind/Kindred/Dark Gift/Corpses/Quest/INFINITY=SET(large)/multi-class. NOVEL=Morchie END_036 (Rewinds keep BOTH outcomes -> Play.do re-runs effect, no choice, when END_036 in field). Fixed 2 GDB data-bump regressions (GDB_100 lost Taunt + armor 6->4; starship test uses GDB_109 Lifesteal). Commit d504d687
- 2026-06-01 | 7:Across the Timeways mini-set (END_) | P3 cards | workflow wf_1d44568d running (12 class agents, neutral=27, folds into across_the_timeways pkg)
