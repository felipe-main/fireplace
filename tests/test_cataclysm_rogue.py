"""Cataclysm — Rogue (CATA_) unit tests."""

from utils import prepare_game
from hearthstone.enums import CardClass, CardType, Zone, GameTag
from fireplace.actions import Awaken


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# CATA_201 Twilight Mistress — Battlecry: return all enemy minions to hand
# ---------------------------------------------------------------------------
def test_twilight_mistress_bounces_all_enemy_minions():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    o.summon("CS2_172")
    o.summon("CS2_172")
    o.summon("CS2_172")
    hand_before = len(o.hand)
    p.give("CATA_201").play()
    # All three enemy minions left the board and returned to the owner's hand.
    assert len(o.field) == 0
    assert len(o.hand) == hand_before + 3
    # Friendly minions are untouched (only the Mistress is on our board).
    assert [m.id for m in p.field] == ["CATA_201"]


# ---------------------------------------------------------------------------
# CATA_203 Garona's Last Stand — destroy a Legendary minion
# ---------------------------------------------------------------------------
def test_garonas_last_stand_destroys_legendary():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    leg = o.summon("EX1_116")  # Leeroy Jenkins (Legendary)
    spell = p.give("CATA_203")
    # Only legendaries are valid targets.
    assert leg in spell.targets
    spell.play(target=leg)
    assert leg.zone == Zone.GRAVEYARD


def test_garonas_last_stand_cannot_target_nonlegendary():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    plain = o.summon("CS2_172")  # Bloodfen Raptor (not legendary)
    spell = p.give("CATA_203")
    assert plain not in spell.targets


# ---------------------------------------------------------------------------
# CATA_215 Daze — return an enemy minion to hand + Dazed enchant
# ---------------------------------------------------------------------------
def test_daze_bounces_and_marks():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    em = o.summon("CS2_172")
    hand_before = len(o.hand)
    p.give("CATA_215").play(target=em)
    assert em.zone == Zone.HAND
    assert len(o.hand) == hand_before + 1
    # The bounced card carries the Dazed enchant (CANT_PLAY marker).
    assert any(b.id == "CATA_215e" for b in em.buffs)


# ---------------------------------------------------------------------------
# CATA_200 Agent of the Old Ones — Battlecry: transform a hand card into a Coin
# ---------------------------------------------------------------------------
def test_agent_of_the_old_ones_makes_coin():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    p.discard_hand()
    p.give("CS2_172")  # the sole other card in hand
    agent = p.give("CATA_200")
    agent.play()
    # The other hand card was transformed into the Coin (the Agent itself is
    # now on the board, so the only hand card is the Coin).
    assert [c.id for c in p.hand] == ["CATA_COIN1"]


# ---------------------------------------------------------------------------
# CATA_785 Rite of Twilight — Herald; Combo: deal 3 damage
# ---------------------------------------------------------------------------
def test_rite_of_twilight_no_combo_only_heralds():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    assert p.heralds_this_game == 0
    p.give("CATA_785").play()
    assert p.heralds_this_game == 1
    # No combo -> no damage anywhere.
    assert o.hero.damage == 0 and p.hero.damage == 0


def test_rite_of_twilight_combo_deals_damage():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    p.give("CS2_172").play()  # establish Combo
    assert p.combo
    o.hero.max_health = 40
    o.hero.damage = 0
    p.give("CATA_785").play()
    # Combo bumps Herald AND deals 3 to a random enemy (only the enemy hero).
    assert p.heralds_this_game == 1
    assert o.hero.damage == 3


# ---------------------------------------------------------------------------
# CATA_158 Maniacal Follower — Stealth; Deathrattle: Herald
# ---------------------------------------------------------------------------
def test_maniacal_follower_heralds_on_death():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    mf = p.summon("CATA_158")
    assert mf.stealthed
    assert p.heralds_this_game == 0
    mf.destroy()
    assert p.heralds_this_game == 1


# ---------------------------------------------------------------------------
# CATA_481 Iso'rath — devour 2, go dormant, deathrattle returns them
# ---------------------------------------------------------------------------
def test_isorath_devours_and_returns():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    o.discard_hand()
    o.give("CS2_172")
    o.give("CS2_172")
    o.give("CS2_172")
    iso = p.give("CATA_481")
    iso.play()
    # Two cards devoured (opponent hand 3 -> 1); Iso'rath dormant for 2 turns.
    assert len(o.hand) == 1
    assert iso.dormant
    assert iso.dormant_turns == 2
    assert len(iso._devoured) == 2
    # Awaken so it can die, then the deathrattle returns the devoured cards.
    game.queue_actions(p.hero, [Awaken(iso)])
    assert not iso.dormant
    iso.destroy()
    assert len(o.hand) == 3


def test_isorath_dormant_cannot_be_destroyed_early():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    o.discard_hand()
    o.give("CS2_172")
    o.give("CS2_172")
    iso = p.give("CATA_481")
    iso.play()
    # While dormant it cannot be destroyed; the devoured cards stay set aside.
    iso.destroy()
    assert iso.zone == Zone.PLAY
    assert len(o.hand) == 0


# ---------------------------------------------------------------------------
# CATA_202 Stolen Power — get a random Shatter card from another class
# ---------------------------------------------------------------------------
def test_stolen_power_gets_other_class_shatter():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    p.discard_hand()
    p.give("CATA_202").play()
    assert len(p.hand) == 1
    got = p.hand[0]
    # It is a Shatter card and from another class (not Rogue, not Neutral).
    assert got.data.tags.get(GameTag.SHATTER, 0)
    assert got.card_class not in (CardClass.ROGUE, CardClass.NEUTRAL)


# ---------------------------------------------------------------------------
# CATA_786 Chaos Supplicant — after a spell, cast a same-Cost other-class spell
# ---------------------------------------------------------------------------
def test_chaos_supplicant_casts_extra_spell():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    p.summon("CATA_786")
    casts_before = len(p.spells_cast_this_game)
    prep = p.give("EX1_145")  # Preparation — 0-cost Rogue spell, no target
    prep.play()
    # The played spell plus the bonus other-class same-cost spell were cast.
    assert len(p.spells_cast_this_game) == casts_before + 2
    extra = p.spells_cast_this_game[-1] if p.spells_cast_this_game[-1].id != "EX1_145" else p.spells_cast_this_game[-2]
    assert extra.cost == 0
    assert extra.card_class not in (CardClass.ROGUE, CardClass.NEUTRAL)


# ---------------------------------------------------------------------------
# CATA_154 Sinestra — Colossal +2; other-class spells cast twice; wings give spells
# ---------------------------------------------------------------------------
def test_sinestra_colossal_and_wing_spells():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    p.discard_hand()
    sin = p.give("CATA_154")
    sin.play()
    # Colossal +2 — Sinestra plus two Wings on the board.
    assert [m.id for m in p.field] == ["CATA_154", "CATA_154t", "CATA_154t1"]
    # One discounted other-class spell per Wing (2 cards added to hand).
    assert len(p.hand) == 2
    for c in p.hand:
        assert c.type == CardType.SPELL
        assert c.card_class not in (CardClass.ROGUE, CardClass.NEUTRAL)


def test_sinestra_wing_spells_discounted_by_heralds():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    p.discard_hand()
    p.heralds_this_game = 2  # max discount of 2
    p.give("CATA_154").play()
    assert len(p.hand) == 2
    for c in p.hand:
        # Each gifted spell costs 2 less than its printed cost (clamped at 0).
        assert c.cost == max(0, (c.data.cost or 0) - 2)


def test_sinestra_doubles_other_class_spell():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    p.discard_hand()
    p.summon("CATA_154")
    game.refresh_auras()
    o.hero.max_health = 60
    o.hero.damage = 0
    fb = p.give("CS2_029")  # Fireball — Mage spell, 6 damage
    game.refresh_auras()
    assert fb._casts_twice_self is True
    fb.play(target=o.hero)
    # Other-class spell cast twice -> 12 damage.
    assert o.hero.damage == 12


def test_sinestra_does_not_double_own_class_spell():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p, o = game.player1, game.player2
    p.discard_hand()
    p.summon("CATA_154")
    game.refresh_auras()
    o.hero.max_health = 60
    o.hero.damage = 0
    # Sinister Strike (EX1_278 is Backstab; use a no-combo rogue damage spell):
    # Eviscerate (EX1_124) deals 2 (4 with combo). No combo here -> 2 once.
    ev = p.give("EX1_124")
    game.refresh_auras()
    assert getattr(ev, "_casts_twice_self", False) is False
    ev.play(target=o.hero)
    # Own-class spell is NOT doubled by Sinestra: exactly 2 damage.
    assert o.hero.damage == 2
