# Fireplace — Claude project guide

A Python Hearthstone engine + card scripts. Forked from `shinoi2/fireplace`
(itself forked from `jleclanche/fireplace`), now tracking modern HS patches
expansion by expansion at `felipe-main/fireplace`.

## Repo layout

```
fireplace/
  actions.py             # all TargetedAction / GameAction subclasses
  card.py                # Card / PlayableCard / Minion / Spell / Weapon / Hero
  player.py              # Player state + per-game/per-turn counters
  game.py                # turn flow, action_block, broadcast
  entity.py              # base Entity + event broadcast machinery
  events.py              # OWN_TURN_BEGIN / OWN_SPELL_PLAY / etc.
  managers.py            # GameTag ↔ attribute name mapping
  enums.py               # custom enums (PlayReq, BoardEnum, …)
  dsl/
    selector.py          # all selectors + EnumSelector / FuncSelector
    evaluator.py         # Evaluator + ChooseBoth + …
    lazynum.py           # LazyNum + Attr + Count + …
    random_picker.py     # RandomMinion / RandomSpell / RandomCardPicker
  cards/
    __init__.py          # CardDB, get_script_definition (handles CORE_ prefix)
    utils.py             # buff() helper, @custom_card, mixins
    <set_name>/          # one package per expansion
      __init__.py        # star-imports the class files
      demonhunter.py
      druid.py
      …
      neutral.py         # or neutral_common/rare/epic/legendary.py for big sets
tests/
  test_<set_name>.py     # one test file per expansion
  soak.py                # 1000-game harness
  utils.py               # prepare_game, BaseTestGame (max_mana=10 from start)
setup.cfg                # hearthstone_data pin lives here
```

## Working with this codebase

### Data layer

- `setup.cfg` pins `hearthstone_data==<build>.1`. Each expansion bumps it.
- The build number maps to a Hearthstone patch — check
  `https://hearthstone.wiki.gg/wiki/Patches` and pick the **lowest** build that
  fully contains the new set (older builds may have placeholder data).
- The shinoi2 fork of `python-hearthstone` is required — it parses extra
  CardXML attributes (questline, sigil, requirements, corrupt_card,
  entourage, choose_cards, is_standard) that upstream skips.

### Common dev commands

```sh
# Smoke import (catches syntax / @custom_card errors immediately)
python -c "import fireplace.cards; fireplace.cards.db.initialize(); print('OK')"

# Tests (fast, ~20s)
python -m pytest tests/ -q --tb=line

# 1000-game soak (3-4 min) — redirect to file, not pipe (SIGPIPE issue)
python tests/soak.py 1000 > /tmp/soak.log 2>&1 && grep SUMMARY /tmp/soak.log
```

### Code conventions

- Card scripts are **classes**, not instances. The merge code in
  `cards/__init__.py` reads class attributes (`play`, `events`, `tags`,
  `deathrattle`, `cost_mod`, `update`, `dormant_events`, `dormant_turns`,
  `requirements`, `choose`, `entourage`, `Hand.events`, `Deck.events`, …)
  and grafts them onto the data card. No `__init__`.
- Card classes' **docstrings must equal the printed card name exactly**,
  end with `)` (the regex exemption), or be `None`. `test_card_docstrings`
  enforces this.
- Enchantments that exist in data don't need `@custom_card` — just declare
  the class with `tags = {…}`. Check `cid in db` if unsure.
- For enchantments **not** in data (rare — usually engine-internal markers),
  decorate with `@custom_card` and supply `GameTag.CARDNAME` +
  `GameTag.CARDTYPE = CardType.ENCHANTMENT` in `tags`.

### Engine gotchas (learned the hard way)

- **Counter ordering in `Play.do`:** counter bumps (`spells_cast_while_holding`,
  per-minion spell-mana, etc.) must happen **before** the broadcast loop,
  otherwise OWN_SPELL_PLAY listeners see stale values.
- **Choice sequencing:** flat tuples of `Discover` / `GenericChoice` all set
  `player.choice` at once and only the last one survives. Nest via `.then()`
  callbacks or use a re-entrant action that re-queues itself.
- **Dormant minions** only fire `dormant_events`, never `events`. Awaken
  via the `Awaken(target)` action — `UnsetTags(target, (DORMANT,))` is
  insufficient because `card.dormant` is a Python attribute, not a tag.
- **Lambdas in `events` lists** get called **twice** by `trigger_event`
  (once for the truthy gate, again to extract iterable actions). Any
  side-effects belong in a custom `TargetedAction` subclass, never in a
  lambda body.
- **`int & Action` doesn't work.** `(LazyNumEvaluator) & Action` does.
  Comparisons on `Attr(...)`/`Count(...)`/`COST(...)` return evaluators
  because `LazyNum._cmp` is defined; literal ints don't, so write
  `Attr(...) >= 5` not `5 <= Attr(...)`.
- **`SET()` in a buff's `tags` dict crashes.** Use `GameTag.COST: -100`
  (engine clamps to 0) for "set cost to 0" effects.
- **Colossal hook lives in `Summon.do` AND `Play.do`** — `Play` moves a
  minion straight into PLAY without going through Summon, so a Colossal
  card played from hand needs the mirrored hook.
- **`destroy()` is the right way to kill a minion in tests** — never
  `game.queue_actions(player.hero, [Destroy(target)])` (skips the
  deathrattle pipeline).
- **`prepare_game()` sets `max_mana = 10` from turn 1** — any `while
  player.mana < N: end_turn()` loops are unnecessary and may even spin
  forever.
- **`game.player1` / `game.player2` track turn order, not name** — after
  `pick_first_player`, `game.player1` is whoever goes first. Use the
  `.name` attribute if you need to disambiguate.

### Per-state attributes — where to put what

| Lifetime | Location | Reset point |
|---|---|---|
| Per-game (player) | `Player.__init__` | game start |
| Per-turn (player) | `Player.__init__` | `game.py begin_turn` |
| Per-card-while-in-hand | `PlayableCard.__init__` | bump in `Play.do`; auto-reset on hand-leave |
| Per-minion-while-in-play | `Minion.__init__` | `card.py _set_zone` when entering PLAY |

## Adding a new expansion — playbook

The process below has been tested on Alterac → Onyxia's Lair → Sunken City.
Each new expansion should take a fraction of the time as the engine matures.

### Step 0 — Roadmap pick

Roadmap items are in chronological order. Pick the next one (mini-set or
full expansion). Find its patch on `hearthstone.wiki.gg/wiki/Patches`.

### Step 1 — Pin the data

```sh
# Find available builds
pip index versions hearthstone_data
# Try the lowest build that fully contains the new set
pip install "hearthstone_data==<build>.1"
python -c "
from hearthstone.cardxml import load
from hearthstone.enums import CardSet
import hearthstone_data
db,_ = load(path=hearthstone_data.get_carddefs_path(), locale='enUS')
new = [c for c in db.values() if c.card_set.name == '<SET_ENUM>' and c.collectible]
print(len(new))
"
```

Update `setup.cfg` to pin to the chosen build with a comment naming the patch.

### Step 2 — Dump the cards

```sh
python -c "
from hearthstone.cardxml import load
from hearthstone.enums import CardSet, CardType
import hearthstone_data
db,_ = load(path=hearthstone_data.get_carddefs_path(), locale='enUS')
new = sorted([(cid, c) for cid, c in db.items()
              if c.card_set.name == '<SET_ENUM>' and c.collectible])
for cid, c in new:
    cost = c.cost or 0
    stats = (f'{cost}/{c.atk}/{c.health}' if c.type == CardType.MINION
             else f'{cost}/{c.atk}/{c.durability}' if c.type == CardType.WEAPON
             else str(cost))
    cls = c.card_class.name if c.card_class else 'NEUTRAL'
    text = (c.description or '').replace(chr(10), ' ')
    print(f'{cid:12s} {c.type.name:6s} {stats:8s} {cls:13s} {c.name:35s} | {text}')
"
```

Save to `/tmp/<set>_cards.txt`. This is your working reference.

### Step 3 — Identify novel mechanics

Tally GameTags across the new set:

```python
all_tags = {}
for c in new:
    for t in c.tags:
        name = t.name if hasattr(t, 'name') else str(t)
        all_tags[name] = all_tags.get(name, 0) + 1
```

Anything that doesn't already have engine handling is a Phase 1 engine task.
Common patterns:

- New **keyword** → new `TargetedAction` in `actions.py` + maybe a hook in
  `Play.do` / `Summon.do`.
- New **tribe** → new `EnumSelector` in `dsl/selector.py`.
- New **per-card counter** → attribute on `PlayableCard.__init__`, bump in
  `Play.do` for hand cards, or on `Minion.__init__` reset in `_set_zone`.
- New **per-game counter** → attribute on `Player.__init__`, reset on game
  start or in `begin_turn` for per-turn counters.

### Step 4 — Phase 0 audit (no card work yet)

Bump `setup.cfg`, install, run the full test suite. Expected failures:

- `test_battlecry_scripts` / `test_deathrattle_scripts` complain about
  unimplemented cards — **expected**, will clear in Phase 1.
- Base-stat / cost balance changes — update the affected test to read
  from data (`card.cost` instead of a hardcoded literal).
- `CORE_`-aliased data cards — already handled in `get_script_definition`,
  but verify your card is actually scripted (under its bare id, not the
  `CORE_` id).

### Step 5 — Phase 1: engine extensions (one PR-equivalent per primitive)

For each novel mechanic identified in Step 3:

1. Add the action / selector / counter.
2. Wire it into the relevant hook (`Play.do`, `Summon.do`, `_set_zone`,
   `begin_turn`).
3. Write a smoke test that exercises just the primitive (not any card).
4. Run the suite — should be green except for the unimplemented cards.

Commit per primitive with `engine: add <Mechanic>` messages.

### Step 6 — Phase 1: scaffold the package

```sh
mkdir fireplace/cards/<set_name>
```

Create `__init__.py`:
```python
from .demonhunter import *
from .druid import *
from .hunter import *
from .mage import *
from .paladin import *
from .priest import *
from .rogue import *
from .shaman import *
from .warlock import *
from .warrior import *
from .neutral import *
```

Create empty per-class files. The package auto-discovers via
`utils.CARD_SETS = iter_modules([cards/])`.

### Step 7 — Phase 1: implement cards class-by-class

Per card:

1. Copy the printed text from `/tmp/<set>_cards.txt` into a `#` comment.
2. Class docstring = exact card name (or end with `)`).
3. Write the script using existing primitives. Lean on these helpers:
   - `HOLDING_DRAGON`, `EMPTY_BOARD`, `FULL_BOARD`, `COINFLIP`,
     `OVERLOADED`, `AT_MAX_MANA`
   - `DISCOVER(picker)` — wraps `Discover().then(Give)`
   - `RECRUIT`, `Recruit(selector)`
   - `MAGNETIC`, `INVOKE`, `JOUST`, `JOUST_SPELL`
   - `buff(atk=N, health=N, **kwargs)` — note keyword names lower-case
     match `GameTag` enum names
4. For each enchant ID referenced in your `Buff(target, "ID")` calls,
   check `cid in db`. If not, register via `@custom_card`.
5. For Choose One: `choose = ("subA", "subB")` on parent +
   `play = ChooseBoth(CONTROLLER) & (effectA, effectB)`, plus the two
   sub-cards as their own classes.

### Step 8 — Phase 1: write tests

`tests/test_<set_name>.py`. One test per card or per cluster. Patterns:

```python
def test_<card_name>():
    game = prepare_game(CardClass.X, CardClass.X)  # match the card's class
    card = game.player1.summon("<id>")             # bypass cost + battlecry
    # OR:
    card = game.player1.give("<id>")
    card.play()                                     # full play (battlecry fires)

    # Auto-resolve any Discover / Choice that pops up:
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])

    assert <expected_state>
```

### Step 9 — Phase 1: green the suite, run the soak

```sh
python -m pytest tests/ -q --tb=line   # twice in a row to confirm stability
python tests/soak.py 1000 > /tmp/soak.log 2>&1 && grep SUMMARY /tmp/soak.log
```

Until SUMMARY says `1000/1000 succeeded, 0 failed`, **don't ship**.
Each soak failure is a real bug from random card-pool interactions —
fix it, re-run.

### Step 10 — Phase 1: ship

Single commit `<Expansion>` containing all card files + engine commits +
the test file. Bump README patch line. Push to `felipe-main/master`.

### Step 11 — Audit pass

Write a self-audit listing every card whose implementation has known gaps,
and append it to `REVIEW.md` at the repo root (one `## <Expansion>` section
per set, with a sub-table per bucket). Group into:

- **Real bugs** — needs a fix
- **Significant approximations** — works, doesn't match the printed card
- **Cosmetic** — text rendering only
- **Once-overs** — probably correct, watch for edge cases

`Status` and `Fix` are separate columns. `Status` is `open` / `fixed` /
`watch`; `Fix` is empty until a tier-N pass closes the row, then it holds
`<short-sha> — <one-line how>`. Rows are never deleted — `REVIEW.md` is
also the history of what was changed and why.

Template:

```markdown
## <Expansion>

### Real bugs
| Card | Approximation | Real behaviour | Status | Fix |
|---|---|---|---|---|
| <Name> | <what we do today> | <what the printed card does> | open | |

### Significant approximations
| Card | Approximation | Real behaviour | Status | Fix |
|---|---|---|---|---|
| <Name> | <what we do today> | <what the printed card does> | open | |

### Cosmetic
| Card | Issue | Status | Fix |
|---|---|---|---|
| <Name> | <e.g. text shows "@" placeholder> | open | |

### Once-overs
| Card | Watch for | Status | Fix |
|---|---|---|---|
| <Name> | <edge case to revisit> | watch | |
```

Present the new section to the user and let them pick what to invest in.

### Step 12 — Tier-N fix passes

Take the highest-impact subset (5-7 cards). Fix each with a new test that
targets the exact bug. When a row is fixed, update its `REVIEW.md` entry
in place: flip `Status` to `fixed` and fill `Fix` with the short SHA and
a one-line description of the actual change (e.g.
`a1b2c3d — moved _devoured to player attr so reshuffle preserves it`).
Each tier ends with: full suite green + 1000-game soak. Commit
`[bugfix] Tier-N <Expansion> approximations`.

Repeat until the user calls it.

### Step 13 — Final cosmetic + once-over lap

- Fill any `@` / `{0}` progress placeholders via `custom_cardtext` +
  `cardtext_entity_0` (share a mixin for similar cards — see
  `ThreeSpellsProgressUtils` for the template).
- Write defensive tests for the once-over watchlist; either confirm
  correctness or escalate to a bug.

Final commit `<Expansion> cosmetic + once-over audit`.

### Step 14 — Close the expansion

- Every card has a script.
- Every approximation either fixed or accepted.
- README reflects the latest patch.
- Tests + soak both green.
- Mark roadmap item done in memory or notes.
- Move to the next expansion.

## Reference: cumulative engine extensions so far

(Things added by previous expansions that subsequent ones can rely on.)

**Actions:** `HonorableKill`, `TickObjective`, `IncreaseAttr`,
`Dredge`, `PutOnBottom`, `Awaken`, `_AbyssalCurseTick`,
`_NellieRememberCrew`, `_BootstrapToBottom`, `_FaelinPutOnBottom`,
`_BloodscentMark` / `_BloodscentPayHP`, `_SchoolTeacherTeachNagaling`.

**Selectors:** `NAGA`, `ARCANE_SPELL`, `FIRE_SPELL`, `FROST_SPELL`,
`NATURE_SPELL`, `HOLY_SPELL`, `SHADOW_SPELL`, `FEL_SPELL`,
`OTHER_CLASS`.

**Player attributes:** `num_hero_attacks_this_game`, `armor_gained_this_game`,
`damage_taken_on_opponents_turn`, `next_hero_power_costs_zero`,
`next_hero_power_freezes_target`, `next_choose_one_discount`,
`next_choose_one_combined`, `last_choose_one_parent_id`,
`last_choose_one_chosen_id`, `spells_cast_by_school`,
`mana_spent_on_spells_this_game`, `mana_spent_on_holy_spells_this_game`,
`spells_poisonous_this_turn`, `spell_mana_spent_this_turn`,
`abyssal_curses_drawn`.

**Card / Minion attributes:** `has_honorable_kill`,
`incoming_damage_divider`, `doesnt_lose_durability`, `buffs_doubled`,
`honorably_killed`, `spells_cast_while_holding`,
`nagas_played_while_holding`, `spells_history_while_holding`,
`spell_mana_spent_in_play`. Plus various per-card `_*` attrs for
specific cards (Gigafin's `_devoured`, Nellie's Ship `_nellie_crew`,
Nagaling's `_taught_spell`, Bloodscent's `_bloodscent_*`, Faelin's
`_faelin_choices_left`).

**Engine hooks:** Colossal limb-summon in `Summon.do` + `Play.do`;
spell-source poison destroy in `Damage.do`; counter bumps for
`spells_cast_while_holding` + `spell_mana_spent_in_play` in `Play.do`;
custom `_FaelinChoice` GenericChoice variant; CORE_-prefix stripping
in `get_script_definition`.

**Utility mixins in `cards/utils.py`:** `JadeGolemUtils`, `SchemeUtils`,
`GalakrondUtils`, `ThresholdUtils`, `QuestRewardProtect`,
`ThreeSpellsProgressUtils`.
