# Per-expansion implementation audit

A running ledger of known gaps and approximations in the card scripts,
broken down by expansion. `Status` tracks lifecycle (`open` / `fixed` /
`watch`); `Fix` holds the short SHA + one-line description when a row is
closed. Rows are never deleted — this file doubles as the change history
of what was approximated, refined, or accepted.

## Murder at Castle Nathria

### Real bugs
| Card | Approximation | Real behaviour | Status | Fix |
|---|---|---|---|---|

(none flagged yet — engine extensions and per-card scripts ship green
through tests and the 1000-game soak. Anything that surfaces in
gameplay or future soaks lands here first.)

### Significant approximations
| Card | Approximation | Real behaviour | Status | Fix |
|---|---|---|---|---|
| Prince Renathal | Plays as a vanilla 3/3/4; start-of-game deck-size/HP swap is unimplemented | "Start of Game: Your deck size and starting Health are 40." Doubles deck size and grants +10 starting HP. | fixed | 801398ba — detect "REV_018" in starting_deck during prepare_for_game; bump hero.max_health and player.max_deck_size to 40 |
| Sire Denathrius | Deals 1 damage to random enemies for `friendly_minions_died_this_game + 5` ticks; randomly distributed | "Battlecry: Deal 5 damage amongst enemies. Endlessly Infuse (1): Deal 1 more." Damage is split smartly across enemies; Endlessly Infuse means each friendly death adds +1 to the final battlecry damage rather than to a hand counter. | open | |
| Murloc Holmes | Copies 3 random cards from opponent's hand | "Solve 3 Clues about your opponent's cards to get copies of them." Clues are interactive Discover-style guess prompts. | open | |
| Artificer Xy'mox | Casts a single random DH spell (or, infused, casts the 3 Relic spells statically) | "Discover and cast a Relic." Relic pool isn't engine-aware; we don't track per-game Relic progression either. | open | |
| Relic of Dimensions / Extinction / Phantasms | Use fixed numbers (cost-by-2, 2 damage, 2/2 spirits) | The three Relic spells each grow stronger each time a Relic is cast that game. Counter isn't tracked. | open | |
| Imp King Rafaam (and all Imp synergies) | Treats "Imp" as any Demon (no IMP race in engine selectors) | Imp is a true sub-race; flagged minions like Mischievous Imp are imps but Voidwalker etc. are NOT imps. | fixed | 801398ba — IMP FuncSelector matches Demons whose name contains the whole word "Imp" (so Imprisoned * / Impcaster / Impulsive * are excluded); removed warlock.py IMP=DEMON alias |
| Sinstone Graveyard | Summons a vanilla 1/1 Stealthed token | "Has +1/+1 for each other card you played this turn." | open | |
| Necrolord Draka | Equips a vanilla 3/3 dagger | "Equip an X/3 Dagger; +1 Attack for each other card you played this turn." | open | |
| Halkias | Resurrects itself immediately if a Secret is controlled | Should "store its soul inside the secret" and resurrect when the secret triggers (sequencing approximated as immediate). | open | |
| Topior the Shrubbagazzor | Summons random Beasts as Whelp tokens; trigger is real Nature-spell event | Token (Nightmare Whelp) has Rush and is a Dragon, not a generic Beast — but the trigger and rate are correct. | watch | |
| Stonebound Gargon (infused) | Hit-based cleave on attack via REV_352t | Real card applies cleave during attack resolution; ours approximates with an after-attack Hit. | watch | |
| Insatiable Devourer | Devours target + (infused) its neighbors; consumed stats are buffed onto self via a single empty enchantment | Real card devours and *replaces* its own stats; ours stacks via Buff which interacts oddly with later buffs/silences. | open | |
| Sinfueled Golem (infused) | Static +6/+6 buff on the infused twin | Should gain stats equal to the sum of Attacks of the minions that infused it. We don't remember which minions infused. | open | |
| Pelagos | Buffs target +1/+1 per cast on it | Should set target's Attack and Health to the higher of the two; we don't have MAX() over two LazyNums. | fixed | 801398ba — REV_250e snapshots max(atk, max_health) in apply() and uses Inner-Fire-style override lambdas; clears damage when health is being raised |
| Kael'thas Sinstrider | Aura that drops minion costs to 0 when `minions_played_this_turn % 3 == 2` | Real card makes every 3rd minion this turn cost (0); ours triggers correctly but only for the *next* minion in hand. | open | |
| Convoke the Spirits | Casts 8 random Druid spells regardless of cost or playability | Real cast picks from castable spells; ours can cast Galakrond-type cards that don't make sense for our deck. | watch | |
| Lady Darkvein | Summons two 2/1 Shades without the cast-last-Shadow-spell deathrattle | Each Shade has "Deathrattle: cast your last Shadow spell." We don't track last-Shadow-spell. | open | |
| Steamcleaner | Destroys one random card from each deck instead of all post-start additions | Should destroy every card in both decks that wasn't there at game start (requires per-card origin tracking). | open | |
| Shadowborn | Reduces cost of a random Shadow spell in hand by 3 | Real card reduces the *highest-cost* Shadow spell. | open | |
| Vengeful Visage | Summons a copy of the attacker and triggers a forced attack on enemy hero | Real card uses the attacking copy with full targeting; sequencing approximated. | watch | |
| Sticky Situation / Double Cross | Fire on opponent's spell / turn end instead of "spends all mana" | Trigger condition simplified. | watch | |
| Conqueror's Banner | Draws 3 random cards from your deck | Should reveal a card from each deck three times and draw the bigger-cost ones. | open | |
| Riot! | Force-attacks random enemy minions but skips the "can't be reduced below 1 HP this turn" rider | Friendly minions should be immune to lethal damage this turn. | open | |
| Remornia, Living Blade | Approximated as a minion with a deathrattle that equips a 7/3 weapon | Real card transforms into the weapon on each attack (rush-into-weapon hybrid). | open | |
| Baroness Vashj | Plays as vanilla 4/3/6 Naga | "If this would transform into a minion, summon that minion instead." Engine has no transform-redirect hook. | open | |
| Famished Fool / Stoneborn Accuser / Murlocula / Priest of the Deceased / Mischievous Imp / Plot of Sin / Frenzied Fangs / Frozen Touch / Clean the Scene / Convincing Disguise / Door of Shadows / Imbued Axe / Party Favor Totem / Insatiable Devourer / Sinfueled Golem | Use full-text Infuse twin morph; base and infused effects scripted on the two separate data card IDs. | All Infuse cards rely on the engine's `infuse_threshold` + `morph_to_infused_card_id` machinery, which is correct, but individual twins make per-card approximations (see entries above for the non-trivial ones). | watch | |

### Cosmetic
| Card | Issue | Status | Fix |
|---|---|---|---|
| Several Infuse cards | Card text contains literal `@` (e.g. "Infuse (@):"); no `custom_cardtext` rewriter applied. | open | |
| Several Relic spells | Card text contains `@` for the per-Relic counter. | open | |

### Once-overs
| Card | Watch for | Status | Fix |
|---|---|---|---|
| Sire Denathrius scaling | Sire's damage counter is read at battlecry time; ensure the post-battlecry counter doesn't double-count if Sire itself dies in the same chain. | watch | |
| Location cooldown ticking | Cooldown decrements on the controller's begin_turn, not the opponent's. Verify two-turn cadence still matches the printed "use, skip a turn, reuse" pattern in real games. | watch | |
| Infuse + Resurrect | If an Infuse hand card is morphed mid-loop while another Infuse card morphs in the same death batch, ensure no skipped bumps (snapshot via `list(hand)` should handle it). | watch | |
| Imp synergies firing on Voidwalker / Felstalker / other non-imp Demons | Until a proper IMP race is added, these will overtrigger. | watch | |
| `is_playable` requirement-strip on Locations | Mutating `self.requirements` in-place inside a `try/finally` is safe sequentially, but if `is_playable` is ever called re-entrantly (e.g. via an aura that introspects), the strip could leak. | watch | |
