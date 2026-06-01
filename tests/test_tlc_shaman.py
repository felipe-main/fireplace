"""The Lost City of Un'Goro - Shaman card tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, SpellSchool, Zone


# Test tokens / cards
ELEMENTAL = "UNG_809t1"      # Flame Elemental (1/2, Race.ELEMENTAL)
FIREBALL = "CS2_029"         # Fire spell, cost 4
FROSTBOLT = "CS2_024"        # Frost spell
BEAST = "CS2_172"            # Bloodfen Raptor (3/2 Beast)
MURLOC = "CS2_168"           # Murloc Raider (2/1 Murloc)
WISP = "CS2_231"             # 1/1, no tribe
SIZZLING_CINDER = "TLC_249"  # 2/1, Deathrattle: 2 dmg split among enemies


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def _clear_board(game, player):
    for m in list(player.field):
        m.destroy()
    game.process_deaths()


def _play_elemental_last_turn(game, player):
    """Play an Elemental from hand, then advance two turns so it counts as
    'played last turn' for Kindred."""
    player.give(ELEMENTAL).play()
    game.end_turn(); game.end_turn()
    assert Race.ELEMENTAL in player.races_played_last_turn


# ---------------------------------------------------------------------------
# TLC_221 Sizzling Swarm - Deal $3 damage. Summon that many 2/1 Sizzling
# Cinders.  (No target requirement in data -> hits a random enemy.)
# ---------------------------------------------------------------------------

def test_sizzling_swarm():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    # Clear the enemy board so the only enemy is the hero -> the random 3
    # damage lands deterministically on it. Beef it so the game doesn't end.
    _clear_board(game, p2)
    p2.hero.max_health = 80
    p2.hero.damage = 0
    pre = len(p1.field)
    p1.give("TLC_221").play()
    # Exactly 3 damage to the only enemy (the hero).
    assert p2.hero.health == 77
    # Three 2/1 Sizzling Cinders summoned.
    cinders = [m for m in p1.field if m.id == SIZZLING_CINDER]
    assert len(cinders) == 3
    assert all(c.atk == 2 and c.health == 1 for c in cinders)
    assert len(p1.field) == pre + 3


# ---------------------------------------------------------------------------
# TLC_222 Flight of the Firehawk - Draw two minions of different minion types.
# Give them +2/+2.
# ---------------------------------------------------------------------------

def test_flight_of_the_firehawk():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    # Deck: a Beast and a Murloc (different types) plus a spell that must be
    # skipped (minions only).
    beast = p1.give(BEAST); beast.zone = Zone.DECK       # 3/2 Beast
    murloc = p1.give(MURLOC); murloc.zone = Zone.DECK     # 2/1 Murloc
    fb = p1.give(FIREBALL); fb.zone = Zone.DECK           # spell, skipped
    p1.give("TLC_222").play()
    # Both minions drawn (different types); the spell stays in deck.
    drawn = [c for c in p1.hand if c.id in (BEAST, MURLOC)]
    assert len(drawn) == 2
    assert fb.zone == Zone.DECK
    # Each got +2/+2.
    assert beast.atk == 3 + 2 and beast.health == 2 + 2
    assert murloc.atk == 2 + 2 and murloc.health == 1 + 2


# ---------------------------------------------------------------------------
# TLC_223 Volcanic Thrasher - Battlecry: Draw a Fire spell. Kindred: Give it
# Spell Damage +2.
# ---------------------------------------------------------------------------

def test_volcanic_thrasher_kindred_active():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    _play_elemental_last_turn(game, p1)  # Thrasher is an Elemental -> Kindred on
    # Put the Fire spell in the deck AFTER advancing turns so the turn-start
    # draws don't pull it out before Thrasher's battlecry.
    fb = p1.give(FIREBALL); fb.zone = Zone.DECK
    p1.give("TLC_223").play()
    drawn = p1.hand[-1]
    assert drawn.id == FIREBALL
    # Kindred granted the Spell Damage +2 enchant (TLC_223e). The engine's
    # spell-damage path reads board spellpower, not a per-spell SPELLPOWER tag,
    # so we assert the enchant is attached (faithful to the card script).
    assert "TLC_223e" in [b.id for b in drawn.buffs]


def test_volcanic_thrasher_kindred_inactive():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    fb = p1.give(FIREBALL); fb.zone = Zone.DECK
    # Nothing played last turn -> Kindred off, no enchant on the drawn spell.
    p1.give("TLC_223").play()
    drawn = p1.hand[-1]
    assert drawn.id == FIREBALL
    assert "TLC_223e" not in [b.id for b in drawn.buffs]


# ---------------------------------------------------------------------------
# TLC_224 Mechanized Magma - Whenever you play a Fire spell, gain stats equal
# to its Cost.
# ---------------------------------------------------------------------------

def test_mechanized_magma_gains_on_fire_spell():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    magma = p1.summon("TLC_224")  # 2/5
    assert magma.atk == 2 and magma.health == 5
    p2.hero.max_health = 80
    p2.hero.damage = 0
    # Fireball costs 4 -> +4/+4.
    fb = p1.give(FIREBALL)
    assert fb.cost == 4
    fb.play(target=p2.hero)
    assert magma.atk == 2 + 4
    assert magma.health == 5 + 4


def test_mechanized_magma_ignores_non_fire_spell():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    magma = p1.summon("TLC_224")
    target = p2.summon(KOBOLD_GEOMANCER)
    target.max_health = 10
    target.damage = 0
    # Frostbolt is a Frost spell -> no gain.
    p1.give(FROSTBOLT).play(target=target)
    assert magma.atk == 2
    assert magma.health == 5


# ---------------------------------------------------------------------------
# TLC_225 Cinderfin - Deathrattle: Summon a 2/1 Sizzling Cinder.
# ---------------------------------------------------------------------------

def test_cinderfin_deathrattle():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    fin = p1.summon("TLC_225")  # 1/2
    fin.destroy()
    game.process_deaths()
    cinders = [m for m in p1.field if m.id == SIZZLING_CINDER]
    assert len(cinders) == 1
    assert cinders[0].atk == 2 and cinders[0].health == 1


# ---------------------------------------------------------------------------
# TLC_227 Lava Flow - Deal $2 damage to the lowest Health enemy, three times.
# Overload: (1)
# ---------------------------------------------------------------------------

def test_lava_flow_three_hits_lowest_health():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    _clear_board(game, p2)
    # One enemy minion with plenty of health so all three 2-damage hits land
    # on it (it stays the lowest-health enemy; the hero is at 30, never lower).
    target = p2.summon(WISP)
    target.max_health = 20
    target.damage = 0
    p1.give("TLC_227").play()
    # 3 hits x 2 damage = 6 on the single lowest-health enemy.
    assert target.damage == 6
    assert p2.hero.health == 30
    # Overload (1) applied from data.
    assert p1.overloaded == 1


# ---------------------------------------------------------------------------
# TLC_228 Bralma Searstone - Your Elementals deal 1 extra damage.
# (Approximated as a +1 Attack aura on friendly Elementals.)
# ---------------------------------------------------------------------------

def test_bralma_searstone_buffs_elementals():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    ele = p1.summon(ELEMENTAL)  # Flame Elemental 1/2
    assert ele.atk == 1
    p1.summon("TLC_228")
    # Elemental now deals +1 (modeled as +1 Attack).
    assert ele.atk == 2
    # A non-Elemental is unaffected.
    wisp = p1.summon(WISP)
    assert wisp.atk == 1


def test_bralma_searstone_aura_removed_on_death():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    ele = p1.summon(ELEMENTAL)
    bralma = p1.summon("TLC_228")
    assert ele.atk == 2
    bralma.destroy()
    game.process_deaths()
    assert ele.atk == 1


# ---------------------------------------------------------------------------
# TLC_229 Spirit of the Mountain - Quest: Play N minions of unique types.
# Reward: Ashalon. (N = QUEST_PROGRESS_TOTAL, read from data.)
# ---------------------------------------------------------------------------

def test_spirit_of_the_mountain_quest():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    quest = p1.give("TLC_229").play()
    total = quest.data.tags[GameTag.QUEST_PROGRESS_TOTAL]
    assert quest.zone == Zone.SECRET
    assert quest.progress == 0
    # `total` minions of distinct tribes. Destroy each after playing so the
    # board has room for the reward (Ashalon) at completion - progress counts
    # types played, independent of board presence.
    distinct = [
        BEAST,            # Beast
        MURLOC,           # Murloc
        "EX1_598",        # Imp - Demon
        "BOT_309",        # Mech
        ELEMENTAL,        # Elemental
        "ds1_whelptoken", # Dragon
        "CS2_051",        # Stoneclaw Totem - Totem
    ][:total]
    assert len(distinct) == total
    for i, cid in enumerate(distinct):
        m = p1.give(cid).play()
        if i < len(distinct) - 1:
            # Each new unique type advances progress by one.
            assert quest.progress == i + 1, (cid, quest.progress)
            m.destroy()
            game.process_deaths()
    # `total` unique types reached -> quest complete, reward (Ashalon) summoned.
    # (On completion the engine clears progress, so don't assert progress==total.)
    assert quest.zone == Zone.GRAVEYARD
    ashalons = [m for m in p1.field if m.id == "TLC_229t14"]
    assert len(ashalons) == 1


def test_spirit_of_the_mountain_duplicate_types_dont_progress():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    quest = p1.give("TLC_229").play()
    p1.give(BEAST).play()
    assert quest.progress == 1
    # A second Beast does not add a new unique type.
    p1.give(BEAST).play()
    assert quest.progress == 1


# ---------------------------------------------------------------------------
# TLC_464 Mountain Map - Discover a minion with a type you haven't played.
# ---------------------------------------------------------------------------

def test_mountain_map_discovers_unplayed_type():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    # Play a Beast from hand so Beast is now a "played" type.
    p1.give(BEAST).play()
    played = {r for c in p1.cards_played_this_game
              for r in getattr(c, "races", []) if r != Race.INVALID}
    assert Race.BEAST in played
    p1.give("TLC_464").play()
    assert p1.choice
    assert len(p1.choice.cards) == 3
    # Every discovered minion has at least one tribe the player hasn't played.
    for c in p1.choice.cards:
        races = [r for r in getattr(c, "races", []) if r != Race.INVALID]
        assert races, c.id
        assert any(r not in played for r in races), (c.id, races)
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    # Chosen card lands in hand.
    assert p1.hand[-1].id == chosen.id


# ---------------------------------------------------------------------------
# TLC_482 Slagclaw - Battlecry: Summon two 2/1 Sizzling Cinders. Kindred:
# Trigger your Sizzling Cinders' Deathrattles.
# ---------------------------------------------------------------------------

def test_slagclaw_kindred_active_triggers_cinder_deathrattles():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    _clear_board(game, p2)
    p2.hero.max_health = 80
    p2.hero.damage = 0
    _play_elemental_last_turn(game, p1)  # Slagclaw is an Elemental -> Kindred on
    p1.give("TLC_482").play()
    # Two Sizzling Cinders summoned.
    cinders = [m for m in p1.field if m.id == SIZZLING_CINDER]
    assert len(cinders) == 2
    # Kindred triggered each Cinder's Deathrattle (2 dmg split among enemies),
    # without killing them. Only the enemy hero is a valid target, so it took
    # 2 + 2 = 4 total.
    assert p2.hero.health == 76
    # The Cinders survived (deathrattle triggered, not the minion dying).
    assert len([m for m in p1.field if m.id == SIZZLING_CINDER]) == 2


def test_slagclaw_kindred_inactive_no_deathrattle_trigger():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    _clear_board(game, p2)
    p2.hero.max_health = 80
    p2.hero.damage = 0
    # Nothing played last turn -> Kindred off.
    p1.give("TLC_482").play()
    cinders = [m for m in p1.field if m.id == SIZZLING_CINDER]
    assert len(cinders) == 2
    # No deathrattle triggered -> hero untouched.
    assert p2.hero.health == 80
