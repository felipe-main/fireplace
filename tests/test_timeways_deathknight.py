"""Across the Timeways - Death Knight (TIME_) card tests.

One test per collectible card (plus effect-bearing tokens). Assertions are
tight: targets are beefed up so random/AoE effects land deterministically, and
RNG-driven pools are constrained where possible.
"""
from utils import *

from hearthstone.enums import CardClass, GameTag, Race, Zone
from fireplace.actions import Hit


YETI = "CS2_182"  # Chillwind Yeti 4/5, no text - inert target


def _dk_game():
    return prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)


def _beef(minion, hp=80):
    minion.max_health = hp
    minion.damage = 0
    return minion


def _resolve_rewind_keep(player):
    """If a Rewind timeline choice is pending, pick Keep Timeline (no re-run)."""
    if player.choice:
        keep = next(c for c in player.choice.cards if c.id == "TIME_000ta")
        player.choice.choose(keep)


# ---------------------------------------------------------------------------
# TIME_610 Shadows of Yesterday - Rewind. Summon four 3/2 Shades, each gains
# two random Bonus Effects.
# ---------------------------------------------------------------------------

_BONUS_TAGS = (
    GameTag.TAUNT, GameTag.WINDFURY, GameTag.DIVINE_SHIELD, GameTag.POISONOUS,
    GameTag.CANT_BE_TARGETED_BY_SPELLS, GameTag.RUSH, GameTag.LIFESTEAL,
    GameTag.REBORN,
)


def _bonus_count(minion):
    return sum(1 for t in _BONUS_TAGS if minion.tags.get(t))


def test_shadows_of_yesterday_base():
    game = _dk_game()
    card = game.player1.give("TIME_610")
    ctrl = card.controller
    card.play()
    _resolve_rewind_keep(ctrl)
    shades = [m for m in ctrl.field if m.id == "TIME_610t2"]
    assert len(shades) == 4
    for m in shades:
        assert (m.atk, m.health) == (3, 2)
        assert _bonus_count(m) == 2


def test_shadows_of_yesterday_rewind_reruns():
    game = _dk_game()
    card = game.player1.give("TIME_610")
    ctrl = card.controller
    card.play()
    assert ctrl.choice is not None
    rewind = next(c for c in ctrl.choice.cards if c.id == "TIME_000tb")
    ctrl.choice.choose(rewind)
    # Re-run summons four more shades (board caps at 7).
    shades = [m for m in ctrl.field if m.id == "TIME_610t2"]
    assert len(shades) == 7


# ---------------------------------------------------------------------------
# TIME_611 Timestop - Deal 3 damage to a random enemy minion; Freeze two
# random enemy minions.
# ---------------------------------------------------------------------------

def test_timestop():
    game = _dk_game()
    caster = game.player1
    opp = caster.opponent
    minions = [_beef(opp.summon(YETI)) for _ in range(3)]
    card = caster.give("TIME_611")
    card.play()
    assert sum(m.damage for m in minions) == 3
    assert sum(1 for m in minions if m.frozen) == 2


# ---------------------------------------------------------------------------
# TIME_612 Blood Draw - Discover a spell. Costs Health instead of Mana.
# ---------------------------------------------------------------------------

def test_blood_draw():
    game = _dk_game()
    caster = game.player1
    hp0 = caster.hero.health
    card = caster.give("TIME_612")
    assert card.card_costs_health is True
    card.play()
    assert caster.choice is not None
    assert all(c.type == CardType.SPELL for c in caster.choice.cards)
    assert len(caster.choice.cards) == 3
    caster.choice.choose(caster.choice.cards[0])
    # Cost 3 paid in Health, not Mana.
    assert hp0 - caster.hero.health == 3


# ---------------------------------------------------------------------------
# TIME_613 Cryofrozen Champion - Deathrattle: Get a random Legendary minion.
# Reduce its Cost by (1).
# ---------------------------------------------------------------------------

def test_cryofrozen_champion():
    game = _dk_game()
    caster = game.player1
    before = len(caster.hand)
    m = caster.summon("TIME_613")
    m.destroy()
    game.process_deaths()
    assert len(caster.hand) == before + 1
    got = caster.hand[-1]
    assert got.rarity == Rarity.LEGENDARY
    assert got.type == CardType.MINION
    # Cost reduced by exactly 1 from base (engine floors at 0).
    assert got.cost == max(0, (got.data.cost or 0) - 1)


# ---------------------------------------------------------------------------
# TIME_614 Liferender - Battlecry: If your hero's Health changed this turn,
# deal 6 damage to an enemy minion.
# ---------------------------------------------------------------------------

def test_liferender_health_changed():
    game = _dk_game()
    caster = game.player1
    opp = caster.opponent
    tgt = _beef(opp.summon(YETI))
    game.queue_actions(caster.hero, [Hit(caster.hero, 2)])
    assert caster.hero_health_changed_this_turn >= 1
    card = caster.give("TIME_614")
    card.play(target=tgt)
    assert tgt.damage == 6


def test_liferender_no_health_change():
    game = _dk_game()
    caster = game.player1
    opp = caster.opponent
    tgt = _beef(opp.summon(YETI))
    assert caster.hero_health_changed_this_turn == 0
    card = caster.give("TIME_614")
    card.play(target=tgt)
    assert tgt.damage == 0


# ---------------------------------------------------------------------------
# TIME_615 Forgotten Millennium - Fill your hand with random Undead. They cost
# Health instead of Mana this turn.
# ---------------------------------------------------------------------------

def test_forgotten_millennium():
    game = _dk_game()
    caster = game.player1
    caster.discard_hand()
    card = caster.give("TIME_615")
    card.play()
    hand = list(caster.hand)
    assert len(hand) == caster.max_hand_size
    for c in hand:
        is_undead = c.race == Race.UNDEAD or Race.UNDEAD in getattr(c, "races", [])
        assert is_undead
        assert c.card_costs_health is True


# ---------------------------------------------------------------------------
# TIME_616 Memoriam Manifest - Summon the highest Cost friendly Undead that
# died this game.
# ---------------------------------------------------------------------------

def test_memoriam_manifest():
    game = _dk_game()
    caster = game.player1
    low = caster.summon("TIME_610t2")    # 3/2 Undead, cost 2
    high = caster.summon("TIME_617")     # Chronochiller, Undead, cost 4
    low.destroy()
    high.destroy()
    game.process_deaths()
    field_before = len(caster.field)
    card = caster.give("TIME_616")
    card.play()
    assert len(caster.field) == field_before + 1
    summoned = caster.field[-1]
    assert summoned.id == "TIME_617"  # the cost-4, not the cost-2


# ---------------------------------------------------------------------------
# TIME_617 Chronochiller - You no longer draw a card at the start of your turn.
# ---------------------------------------------------------------------------

def test_chronochiller_skips_start_draw():
    game = _dk_game()
    caster = game.player1
    caster.summon("TIME_617")
    if game.current_player is caster:
        game.end_turn()
        game.end_turn()
    else:
        game.end_turn()
    assert game.current_player is caster
    hand_before = len(caster.hand)
    game.end_turn()  # opp turn
    game.end_turn()  # back to caster: start-of-turn draw should be skipped
    assert game.current_player is caster
    assert len(caster.hand) == hand_before


def test_chronochiller_opponent_draws_normally():
    game = _dk_game()
    caster = game.player1
    opp = caster.opponent
    caster.summon("TIME_617")
    if game.current_player is not opp:
        game.end_turn()
    assert game.current_player is opp
    ob = len(opp.hand)
    game.end_turn()  # opp ends, caster begins
    game.end_turn()  # caster ends, opp begins -> opp draws
    assert game.current_player is opp
    assert len(opp.hand) == ob + 1


# ---------------------------------------------------------------------------
# TIME_618 Husk, Eternal Reaper - Battlecry: Give your hero "Deathrattle: Spend
# up to 20 Corpses to resurrect with that much Health."
# ---------------------------------------------------------------------------

def test_husk_grants_hero_deathrattle():
    game = _dk_game()
    caster = game.player1
    card = caster.give("TIME_618")
    card.play()
    enchants = [e for e in caster.hero.buffs if e.id == "TIME_618e"]
    assert len(enchants) == 1
    ench = enchants[0]
    # The granted deathrattle spends up to 20 Corpses when triggered.
    caster.corpses = 25
    game.queue_actions(caster.hero, list(ench.get_actions("deathrattle")))
    assert caster.corpses == 5  # spent exactly 20 (capped)


def test_husk_deathrattle_caps_at_available_corpses():
    game = _dk_game()
    caster = game.player1
    card = caster.give("TIME_618")
    card.play()
    ench = [e for e in caster.hero.buffs if e.id == "TIME_618e"][0]
    caster.corpses = 7
    game.queue_actions(caster.hero, list(ench.get_actions("deathrattle")))
    assert caster.corpses == 0  # spent all 7 (< 20)


# ---------------------------------------------------------------------------
# TIME_619 Talanji of the Graves - Battlecry: Draw Bwonsamdi (or resurrect him
# if he has died). Choose a Boon to give him.
# ---------------------------------------------------------------------------

def test_talanji_draws_bwonsamdi_and_applies_boon():
    game = _dk_game()
    caster = game.player1
    bw = caster.card("TIME_619t")
    bw.zone = Zone.DECK
    card = caster.give("TIME_619")
    card.play()
    assert caster.choice is not None
    assert sorted(c.id for c in caster.choice.cards) == [
        "TIME_619t3", "TIME_619t4", "TIME_619t5"
    ]
    power = next(c for c in caster.choice.cards if c.id == "TIME_619t3")
    caster.choice.choose(power)
    in_hand = [c for c in caster.hand if c.id == "TIME_619t"]
    assert len(in_hand) == 1
    drawn = in_hand[0]
    assert drawn.taunt is True
    assert getattr(drawn, "_bwonsamdi_boon_cost", 0) == 2


def test_talanji_creates_bwonsamdi_if_not_in_deck():
    game = _dk_game()
    caster = game.player1
    assert not any(c.id == "TIME_619t" for c in caster.deck)
    card = caster.give("TIME_619")
    card.play()
    longevity = next(c for c in caster.choice.cards if c.id == "TIME_619t4")
    caster.choice.choose(longevity)
    in_hand = [c for c in caster.hand if c.id == "TIME_619t"]
    assert len(in_hand) == 1
    assert in_hand[0].lifesteal is True


# ---------------------------------------------------------------------------
# TIME_619t Bwonsamdi - Deathrattle: Summon a random 4-Cost minion.
# ---------------------------------------------------------------------------

def test_bwonsamdi_deathrattle_summons_four_cost():
    game = _dk_game()
    caster = game.player1
    bw = caster.summon("TIME_619t")
    bw.destroy()
    game.process_deaths()
    summoned = caster.field[-1]
    assert summoned.data.cost == 4
    assert summoned.type == CardType.MINION


# ---------------------------------------------------------------------------
# TIME_619t2 What Befell Zandalar - Deal 2 damage to all enemies. Choose a Boon
# to give to Bwonsamdi.
# ---------------------------------------------------------------------------

def test_what_befell_zandalar():
    game = _dk_game()
    caster = game.player1
    opp = caster.opponent
    bw = caster.summon("TIME_619t")
    m1 = _beef(opp.summon(YETI))
    m2 = _beef(opp.summon(YETI))
    hp0 = opp.hero.health
    card = caster.give("TIME_619t2")
    card.play()
    assert m1.damage == 2
    assert m2.damage == 2
    assert hp0 - opp.hero.health == 2
    assert caster.choice is not None
    speed = next(c for c in caster.choice.cards if c.id == "TIME_619t5")
    caster.choice.choose(speed)
    assert bw.rush is True


# ---------------------------------------------------------------------------
# Boon tokens cast directly (TIME_619t3 / t5).
# ---------------------------------------------------------------------------

def test_boon_of_power_token_direct():
    game = _dk_game()
    caster = game.player1
    bw = caster.summon("TIME_619t")
    token = caster.give("TIME_619t3")
    token.play()
    assert bw.taunt is True


def test_boon_of_speed_token_direct():
    game = _dk_game()
    caster = game.player1
    bw = caster.summon("TIME_619t")
    token = caster.give("TIME_619t5")
    token.play()
    assert bw.rush is True


# ---------------------------------------------------------------------------
# TIME_610t2 Anomalous Shade - vanilla 3/2 Undead token.
# ---------------------------------------------------------------------------

def test_anomalous_shade_vanilla():
    game = _dk_game()
    caster = game.player1
    m = caster.summon("TIME_610t2")
    assert (m.atk, m.health) == (3, 2)
    assert m.race == Race.UNDEAD or Race.UNDEAD in getattr(m, "races", [])
