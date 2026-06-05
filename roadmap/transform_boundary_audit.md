# Transform-boundary enchant/cost audit

**Date:** 2026-06-04
**Scope:** Modern sets — Across the Timeways (TIME_), End Time (END_), Into the Emerald Dream (EDR_), Firelands (FIR_), Lost City of Un'Goro (TLC_), Dinosaurs (DINO_), Cataclysm (CATA_).
**Bug class:** enchantments (buffs) and cost-modifiers being **lost, doubled, or applied to the wrong entity** when a card changes identity (Shatter split/recombine, transform/Morph, copy/summon-a-copy, Colossal, Magnetic, Choose One combine, and `Give/Draw/Discover(...).then(Buff(...CARD))` chains where a generation hook intervenes).
**Origin:** found while investigating Archmage Kalec + Arcane Flow and Horn of Plenty + Wildwood Circle. The seed bug is Shatter recombine summing a cost discount twice.
**Method:** 4 parallel agents (one per set-group + one on shared engine primitives). Findings marked **Repro** were confirmed by running a Python repro; **Suspected** = code looks wrong but not run; **Latent** = unreachable with today's card pool but unsafe pattern.

> All findings are read-only analysis. No files were modified. Nothing here is fixed yet.

---

## Summary

| Severity | Count | Where |
|---|---|---|
| High | 6 | Shatter runtime-buff-value loss (A3, engine), Shatter-on-generate discount-loss (B1–B4, 4 cards), Divergence (C1) |
| Medium | 3 | Shatter split parent-enchant loss (A4), recombined parent unplayable (A6), Zin-Azshari doubling math (C2) |
| Low / Latent | 1 | Volcanic Thrasher (B5, latent) |
| Accepted (by design) | 2 | A1 cost conservation, A2 buff conservation — see ruling below |

> A1/A2 reclassified from bug → accepted per owner ruling 2026-06-04 (Shatter recombine should **conserve** independently-applied buffs/discounts, not de-duplicate). The seed Horn-of-Plenty problem is A5/B1 (discount **lost**), which is unaffected and still a bug.

**Key conclusion:** at the engine level the bug class is **concentrated entirely in the Shatter split/recombine path**. Every *other* identity-transform primitive — Morph, Copy/ExactCopy, Magnetic, Colossal + `summoned`, Choose One combine, Rewind, Imbue — was independently verified **clean** (see Coverage). The two non-Shatter card bugs (Divergence, Zin-Azshari) are hand-rolled card scripts that re-implement a "copy + adjust" by computing a delta from the *buffed* original and applying it to a *fresh base* copy.

---

## A. Engine root-cause bugs — Shatter split/recombine

All in `fireplace/actions.py`. Confirmed independently by both the Cataclysm agent and the engine-primitives agent.

> **Accepted / by-design (NOT bugs) — owner ruling 2026-06-04:** A1 (cost discount summed across both halves) and A2 (buffs summed across both halves) are **correct**. When an effect like Archmage Kalec buffs each half independently while the card is split, the two halves are genuinely two separate cards that each received a real buff/discount; recombine should **conserve both** (Kalec → Spell Damage +2; two −2 discounts → −4). The earlier "should appear once" framing was wrong. Caveat to watch: this conserves correctly for one-time buffs; a *continuous aura* ("−1 to cards in hand") applied to each half then baked into a permanent `_cost` on recombine would let the split→recombine route out-discount the whole card — edge case, accepted for now. Optional: confirm against the wiki ruling.

| # | Issue | Sev | Confirmed | Location | What happens | Correct behaviour | Suggested fix |
|---|---|---|---|---|---|---|---|
| A1 | ~~Cost discount summed across both halves~~ — **ACCEPTED (by design)** | — | Repro | `_do_shatter_recombine` `actions.py:3936`, applied `:3954` | Each half independently carried the discount; summing conserves both. base-4 Wildwood Circle with −2 on each half → recombined **0** (two real −2s). | Conservation: both reductions persist. | None — keep as-is. |
| A2 | ~~Buffs duplicated across both halves~~ — **ACCEPTED (by design)** | — | Repro | `actions.py:3937` (collect) + re-apply loop `:~3947` | Each half independently received the buff (e.g. Kalec hit both); summing conserves both. → recombined Spell Damage **+2**. | Conservation: both buffs persist. | None — keep as-is. |
| A3 | **Runtime buff tag amounts lost on recombine** | High | Repro | `actions.py:~3947` (`for bid in buff_ids: parent.buff(parent, bid)`) | Buffs are re-applied **by id only**, discarding runtime amounts. A `Buff(half,"…e",atk=5)` recombines as **+0 atk**. (Cost survives only because `total_discount` reads live `.cost`.) **Reinforced by the A1/A2 ruling:** if buffs are conserved, they must be conserved *at their real value*, not zeroed. | Resolved tag values (atk/health/… passed at buff time) must survive. | Snapshot each enchant's effective tag dict and re-create with those values, not just the id. |
| A4 | **Parent enchants/cost lost on split** | Med | Repro | `_shatter_into_halves` `actions.py:3783` | `card.discard()` then fresh `Give` of halves; the whole card's own buffs + `_cost` edits are not migrated → 1 buff on parent → halves have 0. | Buffs/cost-mods on the full card should carry onto the halves. | Snapshot parent buff ids + cost delta before `discard()`, re-apply to (or split across) the halves. |
| A5 | **`Give/Draw(...).then(Buff(...CARD))` over a Shatter card strands the buff** | High | Repro | `Give.do` `actions.py:~2743`; shatter-on-generate runs at end of `Give.do`/`Draw.do`; `.CARD` resolves to the input via `_trigger` `:~1475` | The split runs at the end of the action, discarding the original, but the action still exposes the discarded original as `.CARD`. The chained buff lands on the set-aside parent; the halves the player keeps get nothing → discount/buff **lost**. Drives all of section B. | The follow-up buff should land on the resulting halves. | After a card shatters inside Give/Draw, exclude it from `ret` / substitute the halves so chained `.CARD` actions target a live entity; or defer the split to the next action_end. |
| A6 | **Recombined Shatter parent has no `play` effect (unplayable)** | Med | Repro | rebuild at `actions.py:~3941`; parents are docstring-only (`mage.py:202` CATA_489, `druid.py:273` CATA_134, `paladin.py:374` CATA_479) | The rebuilt parent has no `play` script, so a recombined card does nothing when cast (Arcane Flow dealt 0 to enemy hero). Engine builds it correctly and marks `_no_reshatter`; the gap is the missing parent effect. | Recombined card should perform the **combined** effect of both halves. | Card-script task: give recombine parents a `play` that runs both halves' effects, or accept as a documented approximation. |

Affected Shatter cards (parents): Arcane Flow (CATA_489), Wildwood Circle (CATA_134), Schism (CATA_306), Flight Maneuvers (CATA_479), Supply Run (CATA_820).

---

## B. Card-specific instances of A5 (discount/buff stranded on shatter-on-generate)

Same root cause as A5; these are the live cards whose pool can actually contain a Shatter spell (all Shatter cards are spells costing ≤4). Fixing A5 closes all of these at once.

| Card (id) | Set | Sev | Confirmed | What happens | Location | Note |
|---|---|---|---|---|---|---|
| Horn of Plenty (EDR_270) | EDR | High | Repro | Discovers a Nature spell at (2) less; if it picks Wildwood Circle the −2 strands on the discarded original, halves stay full cost. | `emerald_dream/druid.py:184-186` | the original case |
| Sharp-Eyed Lookout (EDR_950) | EDR | High | Repro | Draws a card at (1) less; a drawn Shatter spell splits and the −1 strands. | `emerald_dream/neutral.py:677` | |
| Blessing of the Moon (EDR_449pe) | EDR | High | Repro | Discovered Priest card costs (@) less and is Temporary; if it picks Schism, **both** the cost cut and the Temporary self-destruct marker strand → halves never expire. | `emerald_dream/tokens.py:85-92` | loses a second effect too |
| Ashamane (EDR_527) | EDR | High | Repro | Copies opponent-deck cards at (3) less; a copied Shatter spell splits and the −3 strands. | `emerald_dream/rogue.py:113-115` | |
| Volcanic Thrasher (TLC_223) | TLC | Latent | Inspection | Kindred draws a Fire spell and gives it Spell Damage +2, gated on `card.zone==HAND` after draw; a shattered draw leaves the original in SETASIDE so the +2 silently drops. No Fire-school Shatter spell exists today → unreachable, but the pattern is unsafe. | `the_lost_city/shaman.py:100-104` | harmless now |

---

## C. Independent card bugs — same class, not Shatter (Timeways)

Hand-rolled "copy + adjust" scripts that compute a stat/cost delta from the **buffed** original and apply it to a **fresh base** copy. Correct only when the source is unbuffed.

| Card (id) | Sev | Confirmed | What happens | Correct behaviour | Location | Suggested fix |
|---|---|---|---|---|---|---|
| **Divergence (TIME_030)** | High | Repro | Splits a hand minion into two "halves." Reads the original's current (buffed) atk/health/cost, computes a halving delta, then applies it to two fresh **base** copies (zero enchants). Original buffed to 8/9 cost 2 → halves came out **0/1 cost 3** instead of ~4/5 cost 1. Unbuffed case is correct. | Each half ≈ half of the original's **current** stats/cost. | `across_the_timeways/warlock.py:227-261` (deltas `:246-248`, fresh copy `:253`, buff `:255-261`) | Set the copies' final stats relative to the copy's own base, or ExactCopy the original (carrying enchants) then add one halving buff. |
| **Zin-Azshari, empowered (`_SummonDoubledCopy`, TIME_211t2t)** | Med | Repro | "Summon a copy with stats doubled." Reads original's current stats, summons a fresh **base** copy, buffs by the current amount → copy ends at `base + current`, not `2 × current`. Chosen minion 14/15 (base 4/5) → copy **18/20**, expected **28/30**. Unbuffed case coincidentally correct. | Copy = double the chosen minion's **current** stats. | `across_the_timeways/druid.py:209-230` (reads `:221-222`, buff `:227-230`) | ExactCopy the chosen minion then add one `+current` buff, or buff the fresh copy by `2*current − base`. |

---

## D. Verified CLEAN (coverage)

Cross-validated by at least one agent, most via repro. These are *not* bugs — recorded so coverage is auditable.

- **Morph / Transform** (`Morph.do`, `actions.py:~2990`) — calls `clear_buffs()` before swapping; correctly wipes enchantments (matches Hearthstone). Timeways Alara'shi (EDR_493) and Lost City morph-chains re-target their pin buffs to the *new* card correctly.
- **Copy / ExactCopy** (`dsl/copy.py`) — base `Copy` drops buffs (correct for "summon a copy"); `ExactCopy` carries each buff exactly once via `copy_buffs`, copies only `silenceable_attributes` (excludes atk/max_health). Verified via Endangered Dodo (TIME_703), Unstable Spellcaster (CATA_483), Maloriak, Clutch egg.
- **Magnetic merge** (`cards/utils.py` `MAGNETIC`, `Play.do` hook) — host buffed once, magnet removed; no double/loss. (None present in EDR/FIR/TLC/DINO; verified on the engine primitive.)
- **Colossal limb summon + `summoned` self-effect** (`_summon_colossal_limbs`, hooks in both `Summon.do` and `Play.do`) — limbs fire their self-effect exactly once via both code paths; no double-fire despite the CLAUDE.md caution. Verified on CATA_151.
- **Choose One combine / discount** (`ChooseBoth`, `next_choose_one_combined`, `next_choose_one_discount`) — discount consumed once, combined flag decremented once.
- **Rewind** (`actions.py:~1089` + `_RewindChoice`) — re-runs the battlecry in place; the card never leaves its zone, so enchants/cost-mods cannot be lost or doubled. All Timeways Rewind cards clean by construction.
- **Imbue hero-power swaps** (`actions.py:~3717`) — `imbue_level` set/refreshed on the token correctly; level-scaling effects (Blessing of the Bronze cost-mod, Blessing of the Infinite +Atk) read it correctly through the real activation path.
- **Skip-turn** (Murozond `_skip_next_turn`), **Murozond INFINITY** (TIME_024), `_ResetCosts` (Wizened Truthseeker) — no copy/transform of an enchanted card involved.

---

## Recommended fix order

1. **A3 (Shatter recombine — preserve runtime buff values)** — in `_do_shatter_recombine`, snapshot each enchant's resolved tag dict and re-create with those values instead of by id. Keep A1/A2 conservation (sum) behaviour intact — A3 makes that conservation actually correct for valued buffs. Add a test: a `+5 atk` buff on a half recombines as +5 (or +10 if on both).
2. **A5 + all of section B** — one fix at the Give/Draw shatter-on-generate boundary closes Horn of Plenty, Sharp-Eyed Lookout, Blessing of the Moon, Ashamane, and the latent Volcanic Thrasher together.
3. **A4 (split parent-enchant loss)** — pairs naturally with #1; migrate the whole card's buffs/cost onto the halves on split.
4. **C: Divergence (TIME_030)** — High, but isolated to one card script.
5. **A6 (unplayable recombined parent)** and **C2: Zin-Azshari** — Medium; A6 is a card-script gap (give parents a combined `play`); Zin-Azshari is a one-card math fix.

> **Note:** A1/A2 are no longer in the fix list — accepted as by-design conservation. The only Shatter-recombine change left is A3 (value preservation).

Once confirmed bugs are fixed, fold them into `review.csv` (Section "Real bugs", one row each) per the CLAUDE.md audit playbook.
