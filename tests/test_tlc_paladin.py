"""The Lost City of Un'Goro - Paladin card tests.

Tight per-card coverage for the TLC paladin class (review.csv row 544).
Each test asserts exact post-state so a wrong-but-non-crashing script fails.
"""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, SpellSchool, Zone


# Tokens / helper cards
MURLOC = "CS2_168"       # Murloc Raider 1/2/1 (Race.MURLOC)
BEAST = "CS2_172"        # Bloodfen Raptor 2/3/2 (Race.BEAST)
WISP = "CS2_231"         # Wisp 0/1/1 (Race.UNDEAD)
YETI = "CS2_182"         # Chillwind Yeti 4/4/5 (no tribe)
HOLY_SMITE = "CS1_130"   # 1-cost Holy spell, 3 dmg to a minion


# The eight Bonus Effect keyword groups (mirrors _bonus.BONUS_EFFECTS).
BONUS_TAGS = (
    GameTag.TAUNT,
    GameTag.WINDFURY,
    GameTag.DIVINE_SHIELD,
    GameTag.POISONOUS,
    GameTag.CANT_BE_TARGETED_BY_SPELLS,  # Elusive marker
    GameTag.RUSH,
    GameTag.LIFESTEAL,
    GameTag.REBORN,
)


def _count_bonus_effects(minion):
    """How many distinct bonus-effect keywords are live on this minion."""
    return sum(1 for tag in BONUS_TAGS if minion.tags.get(tag))


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def _clear_board(game, player):
    for m in list(player.field):
        m.destroy()
    game.process_deaths()


# ---------------------------------------------------------------------------
# TLC_240 Tyrannogill - Rush. Deathrattle: Summon three 2/1 Murlocs (Dinoloc),
# give them each a random Bonus Effect.
# ---------------------------------------------------------------------------

def test_tyrannogill_deathrattle():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    _clear_board(game, p1)
    tyr = p1.summon("TLC_240")
    assert tyr.rush
    tyr.destroy()
    game.process_deaths()

    dinolocs = [m for m in p1.field if m.id == "TLC_240t"]
    assert len(dinolocs) == 3
    for d in dinolocs:
        assert d.atk == 2 and d.health == 1
        # Each gets exactly one random Bonus Effect keyword.
        assert _count_bonus_effects(d) == 1


# ---------------------------------------------------------------------------
# TLC_241 Ido of the Threshfleet - While alive you get a 2-Cost Holy spell
# (Call the Threshfleet!) that gives a minion +2/+2 and Divine Shield.
# Modeled: battlecry gives the token; deathrattle removes it from hand.
# ---------------------------------------------------------------------------

def test_ido_gives_token_on_play():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    pre = len(p1.hand)
    ido = p1.give("TLC_241")
    ido.play()
    tokens = [c for c in p1.hand if c.id == "TLC_241t"]
    assert len(tokens) == 1
    assert tokens[0].cost == 2
    assert tokens[0].spell_school == SpellSchool.HOLY


def test_call_the_threshfleet_buffs_and_shields():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    target = p1.summon(YETI)  # 4/5
    token = p1.give("TLC_241t")
    token.play(target=target)
    assert target.atk == 6 and target.health == 7
    assert target.divine_shield


def test_ido_deathrattle_removes_token_in_hand():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    ido = p1.give("TLC_241")
    ido.play()
    assert any(c.id == "TLC_241t" for c in p1.hand)
    ido.destroy()
    game.process_deaths()
    # Token discarded from hand when Ido leaves play.
    assert not any(c.id == "TLC_241t" for c in p1.hand)


# ---------------------------------------------------------------------------
# TLC_426 Dive the Golakka Depths - Repeatable Quest: Summon 6 Murlocs.
# Reward: Murlocs you summon gain +1/+1 (stacks per completion).
# ---------------------------------------------------------------------------

def _summon_murloc_clean(game, p1):
    """Summon a Murloc, snapshot its stats, then clear it so the 7-minion
    board cap never blocks the next summon. Returns (atk, health)."""
    m = p1.summon(MURLOC)
    stats = (m.atk, m.health)
    m.destroy()
    game.process_deaths()
    return stats


def test_golakka_buffs_only_after_six_murlocs():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    _clear_board(game, p1)
    quest = p1.give("TLC_426")
    quest.play()
    assert quest.zone == Zone.SECRET

    # Summon 6 murlocs to complete one cycle. None of these is buffed
    # (bonus is still 0 while the batch is being counted).
    for _ in range(6):
        assert _summon_murloc_clean(game, p1) == (2, 1)

    # The 7th murloc (first after completion) gets +1/+1.
    assert _summon_murloc_clean(game, p1) == (3, 2)


def test_golakka_stacks_two_cycles():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    _clear_board(game, p1)
    p1.give("TLC_426").play()

    # First cycle: 6 murlocs -> bonus becomes 1.
    for _ in range(6):
        _summon_murloc_clean(game, p1)
    # Second cycle: 6 more murlocs, each carrying +1/+1; the 6th completes
    # the cycle bumping bonus to 2 (the +1/+1 is applied before the count).
    for _ in range(6):
        assert _summon_murloc_clean(game, p1) == (3, 2)
    # Next murloc gets +2/+2.
    assert _summon_murloc_clean(game, p1) == (4, 3)


# ---------------------------------------------------------------------------
# TLC_428 Hot Spring Glider - Battlecry: Your next Murloc costs (1) less.
# Kindred: And gains Divine Shield.
# ---------------------------------------------------------------------------

def test_hot_spring_glider_discount_no_kindred():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # No murloc played last turn -> Kindred inactive.
    p1.races_played_last_turn = set()
    glider = p1.give("TLC_428")
    glider.play()
    murloc = p1.give(MURLOC)  # base cost 1
    assert murloc.cost == 0  # 1 - 1 discount
    assert not murloc.divine_shield


def test_hot_spring_glider_kindred_divine_shield():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Murloc played last turn -> Kindred active for the (Murloc) Glider.
    p1.races_played_last_turn = {Race.MURLOC}
    glider = p1.give("TLC_428")
    glider.play()
    murloc = p1.give(MURLOC)
    assert murloc.cost == 0
    murloc.play()
    assert murloc.divine_shield


# ---------------------------------------------------------------------------
# TLC_430 Creature of the Sacred Cave - At end of your turn, recast a random
# Holy spell you cast this turn (targets this if possible).
# ---------------------------------------------------------------------------

def test_creature_recasts_holy_spell_on_self():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    _clear_board(game, p1)
    _clear_board(game, p2)
    creature = p1.summon("TLC_430")  # 2/5
    creature.max_health = 50
    creature.damage = 0
    # Cast a Holy spell this turn at an enemy so it is NOT targeting creature.
    enemy = p2.summon(YETI)
    enemy.max_health = 50
    enemy.damage = 0
    p1.give(HOLY_SMITE).play(target=enemy)
    assert enemy.damage == 3
    # End turn -> recast Holy Smite, this time targeting the creature itself.
    game.end_turn()
    assert creature.damage == 3
    # The original target took no additional damage from the recast.
    assert enemy.damage == 3


# ---------------------------------------------------------------------------
# TLC_438 Violet Treasuregill - Battlecry: Cast a random spell from your deck
# that costs (2) or less (targets this if possible).
# ---------------------------------------------------------------------------

def test_violet_treasuregill_casts_deck_spell_on_self():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Empty the deck so the only eligible (<=2 cost) spell is the one we seed:
    # Holy Smite (3 dmg). Otherwise prepare_game's deck contributes other
    # cheap spells and the random pick becomes non-deterministic.
    for c in list(p1.deck):
        c.zone = Zone.SETASIDE
    spell = p1.give(HOLY_SMITE)
    spell.zone = Zone.DECK
    fish = p1.give("TLC_438")  # 2/1/2
    fish.max_health = 50
    fish.damage = 0
    fish.play()
    # The only <=2 spell in deck was cast targeting the battlecry minion.
    assert fish.damage == 3
    # The spell left the deck (was cast).
    assert spell.zone != Zone.DECK


# ---------------------------------------------------------------------------
# TLC_441 Ready the Fleet - Give +1/+2 to a friendly minion and your other
# minions that share a type with it.
# ---------------------------------------------------------------------------

def test_ready_the_fleet_buffs_shared_type_only():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    _clear_board(game, p1)
    target = p1.summon(MURLOC)   # 2/1 Murloc
    same = p1.summon(MURLOC)     # 2/1 Murloc (shares type)
    other = p1.summon(BEAST)     # 3/2 Beast (different type)
    p1.give("TLC_441").play(target=target)
    # Target and the other Murloc get +1/+2.
    assert target.atk == 3 and target.health == 3
    assert same.atk == 3 and same.health == 3
    # The Beast is untouched.
    assert other.atk == 3 and other.health == 2


# ---------------------------------------------------------------------------
# TLC_442 Submerged Map - Discover a Murloc. If you play it this turn, also
# pick one of the others.
# ---------------------------------------------------------------------------

def test_submerged_map_discover_then_second_pick():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    _clear_board(game, p1)
    for c in list(p1.hand):
        c.discard()
    p1.give("TLC_442").play()
    # Discover offers 3 Murlocs; choose the first, remember the other two.
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    chosen = p1.choice.cards[0]
    assert Race.MURLOC in (chosen.races or [])
    others = [c.id for c in p1.choice.cards if c is not chosen]
    assert len(others) == 2
    p1.choice.choose(chosen)
    # The chosen Murloc is now the only card in hand (Map consumed on play).
    assert [c.id for c in p1.hand] == [chosen.id]
    discovered = p1.hand[0]
    # Playing the discovered Murloc this turn triggers a second pick offering
    # exactly the two unchosen Murlocs.
    discovered.play()
    assert p1.choice is not None
    assert sorted(c.id for c in p1.choice.cards) == sorted(others)
    pick = p1.choice.cards[0]
    p1.choice.choose(pick)
    assert p1.choice is None
    # The second pick is now in hand and is one of the original "others".
    assert [c.id for c in p1.hand] == [pick.id]
    assert pick.id in others


def test_submerged_map_no_second_pick_without_play():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.give("TLC_442").play()
    assert p1.choice is not None
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    # Did NOT play the discovered murloc -> no further choice queued.
    assert p1.choice is None
    # Exactly one Murloc was added to hand (the discovered one).
    assert sum(1 for c in p1.hand if c.id == chosen.id) == 1


# ---------------------------------------------------------------------------
# TLC_444 Story of Galvadon - Give a minion three random Bonus Effects.
# ---------------------------------------------------------------------------

def test_story_of_galvadon_three_bonus_effects():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    target = p1.summon(YETI)
    assert _count_bonus_effects(target) == 0
    p1.give("TLC_444").play(target=target)
    # Exactly three distinct bonus-effect keywords applied.
    assert _count_bonus_effects(target) == 3


# ---------------------------------------------------------------------------
# TLC_477 Threshrider's Blessing - Give +4/+4 and "Deathrattle: Summon a
# random 4-Cost minion."
# ---------------------------------------------------------------------------

def test_threshriders_blessing_buff_and_deathrattle():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    _clear_board(game, p1)
    target = p1.summon(WISP)  # 1/1
    p1.give("TLC_477").play(target=target)
    assert target.atk == 5 and target.health == 5
    assert target.has_deathrattle
    pre = len(p1.field)
    target.destroy()
    game.process_deaths()
    # Deathrattle summoned a random 4-cost minion (Wisp left, 1 new minion).
    new = [m for m in p1.field if m.id != WISP]
    assert len(new) == 1
    assert new[0].cost == 4
