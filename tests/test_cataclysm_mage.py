"""Cataclysm (CATA_) — Mage tests."""

from hearthstone.enums import CardClass, CardType, GameTag, SpellSchool, Zone

from utils import prepare_empty_game, prepare_game


WISP = "CS2_231"          # 0/1/1 vanilla minion
CHILLWIND = "CS2_182"     # 4/4/5 Chillwind Yeti (vanilla)
BOULDERFIST = "CS2_200"   # 6/6/7 Boulderfist Ogre (vanilla)
FIREBALL = "CS2_029"      # 6 damage Fire spell


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# CATA_452 Spellweaver's Brilliance — summon 6/6 Dragon; cost -1 per spell dmg
# ---------------------------------------------------------------------------

def test_spellweavers_brilliance_summons_azure_warden():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    card = p1.give("CATA_452")
    card.play()
    warden = p1.field[0]
    assert warden.id == "CATA_452t"
    assert warden.atk == 6 and warden.max_health == 6


def test_spellweavers_brilliance_cost_drops_per_spell_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    brilliance = p1.give("CATA_452")
    assert brilliance.cost == 10
    # Deal 6 spell damage with Fireball to the enemy hero.
    fb = p1.give(FIREBALL)
    fb.play(target=p2.hero)
    # 6 damage dealt with a spell this turn -> 10 - 6 = 4.
    assert brilliance.cost == 4


def test_spellweavers_brilliance_no_double_count_with_two_trackers():
    # Both Spellweaver's Brilliance and Unstable Spellcaster install the spell
    # damage tracker while in hand; a single damage event must be counted once.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    brilliance = p1.give("CATA_452")
    p1.give("CATA_483")  # second tracker in hand
    p1.give(FIREBALL).play(target=p2.hero)
    assert p1._cata_spell_dmg_this_turn == 6
    assert brilliance.cost == 4


def test_spellweavers_brilliance_cost_resets_next_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    brilliance = p1.give("CATA_452")
    p1.give(FIREBALL).play(target=p2.hero)
    assert brilliance.cost == 4
    game.end_turn(); game.end_turn()  # back to p1's next turn
    assert brilliance.cost == 10


# ---------------------------------------------------------------------------
# CATA_485 Sleet Storm — deal 2, then 1 to a random enemy minion
# ---------------------------------------------------------------------------

def test_sleet_storm_total_damage_is_three():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # One enemy minion with plenty of health to absorb both bolts; full-health
    # hero. Total enemy damage dealt is exactly 2 + 1 = 3, however the random
    # 2-bolt splits between hero and minion.
    target = p2.summon(BOULDERFIST)   # 6/6/7
    target.max_health = 80
    target.damage = 0
    p2.hero.set_current_health(30)
    p1.give("CATA_485").play()
    total = target.damage + (30 - p2.hero.health)
    assert total == 3
    # The 1-damage bolt always lands on the lone enemy minion.
    assert target.damage >= 1


def test_sleet_storm_minion_gets_guaranteed_bolt():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # No enemy hero damage possible to confuse: only an enemy minion. The
    # 1-damage random-enemy-minion bolt is guaranteed to hit it; the 2-damage
    # random-enemy-character bolt may hit hero or minion. Lower bound is 1.
    target = p2.summon(BOULDERFIST)
    target.max_health = 80
    target.damage = 0
    p1.give("CATA_485").play()
    assert target.damage >= 1


# ---------------------------------------------------------------------------
# CATA_489 Arcane Flow (SHATTER) — halves implemented
# ---------------------------------------------------------------------------

def test_arcane_flow_shatters_on_draw_into_halves():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    card = p1.give("CATA_489")
    card.zone = Zone.DECK
    p1.draw()
    ids = [c.id for c in p1.hand]
    assert "CATA_489t" in ids
    assert "CATA_489t2" in ids
    assert "CATA_489" not in ids


def test_arcane_flow_half1_deals_4_to_target():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(BOULDERFIST)  # 6/6/7
    half = p1.give("CATA_489t")
    half.play(target=target)
    assert target.damage == 4


def test_arcane_flow_half2_deals_2_to_all_enemies():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    m1 = p2.summon(BOULDERFIST)
    m2 = p2.summon(CHILLWIND)
    p2.hero.set_current_health(30)
    p1.give("CATA_489t2").play()
    assert m1.damage == 2
    assert m2.damage == 2
    assert p2.hero.health == 28


# ---------------------------------------------------------------------------
# CATA_978 Sindragosa's Triumph — 8 to minion; excess reduces a hand card cost
# ---------------------------------------------------------------------------

def test_sindragosa_triumph_deals_8_and_reduces_cost_by_excess():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(CHILLWIND)  # 4/4/5 health
    # Only one card in hand to receive the reduction.
    spell = p1.give(FIREBALL)      # cost 4
    assert spell.cost == 4
    p1.give("CATA_978").play(target=target)
    # 8 damage to a 5-health minion -> 3 excess.
    assert target.dead
    assert spell.cost == 1  # 4 - 3


def test_sindragosa_triumph_no_excess_no_reduction():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(BOULDERFIST)  # 7 health, so 8 dmg -> only 1 excess
    bigminion = p2.summon("GVG_113")  # not relevant
    spell = p1.give(FIREBALL)
    p1.give("CATA_978").play(target=target)
    assert target.dead
    assert spell.cost == 3  # 4 - 1 excess


# ---------------------------------------------------------------------------
# CATA_458 Archmage Kalec — give all spells in hand & deck Spell Damage +1
# ---------------------------------------------------------------------------

def test_archmage_kalec_buffs_hand_and_deck_spells():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    fb_hand = p1.give(FIREBALL)
    # A spell in deck.
    fb_deck = p1.give(FIREBALL)
    fb_deck.zone = Zone.DECK
    p1.summon("CATA_458")  # summon to avoid cost; play battlecry manually
    # battlecry didn't fire on summon -> play one from hand instead.
    kalec = p1.give("CATA_458")
    kalec.play()
    assert fb_hand._getattr("spellpower", 0) == 1
    assert fb_deck._getattr("spellpower", 0) == 1
    # The buffed Fireball now deals 7 instead of 6.
    fb_hand.play(target=p2.hero)
    assert p2.hero.health == 30 - 7


def test_archmage_kalec_does_not_buff_minions():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    minion_in_hand = p1.give(CHILLWIND)
    p1.give("CATA_458").play()
    assert minion_in_hand._getattr("spellpower", 0) == 0


# ---------------------------------------------------------------------------
# CATA_483 Unstable Spellcaster — Spell Damage +1; BC copy if dealt spell dmg
# ---------------------------------------------------------------------------

def test_unstable_spellcaster_has_spell_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    m = p1.summon("CATA_483")
    assert p1.spellpower == 1


def test_unstable_spellcaster_summons_copy_after_spell_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    caster = p1.give("CATA_483")   # tracker installed while in hand
    # Deal spell damage this turn first.
    p1.give(FIREBALL).play(target=p2.hero)
    pre = len([m for m in p1.field if m.id == "CATA_483"])
    caster.play()
    copies = len([m for m in p1.field if m.id == "CATA_483"])
    # The played Spellcaster plus its battlecry copy.
    assert copies == pre + 2


def test_unstable_spellcaster_no_copy_without_spell_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    caster = p1.give("CATA_483")
    caster.play()
    copies = len([m for m in p1.field if m.id == "CATA_483"])
    assert copies == 1


# ---------------------------------------------------------------------------
# CATA_484 Winterspring Whelp — Discover a 1-Cost spell
# ---------------------------------------------------------------------------

def test_winterspring_whelp_discovers_1cost_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    pre = len(p1.hand)
    whelp = p1.give("CATA_484")
    whelp.play()
    assert p1.choice is not None
    for c in p1.choice.cards:
        assert c.type == CardType.SPELL
        assert c.cost == 1
    p1.choice.choose(p1.choice.cards[0])
    # Whelp left hand to the board; one discovered spell entered hand.
    assert len(p1.hand) == pre + 1


# ---------------------------------------------------------------------------
# CATA_487 Raincaller — first spell damage each turn -> +2 Attack
# ---------------------------------------------------------------------------

def test_raincaller_gains_attack_on_first_spell_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    rain = p1.summon("CATA_487")  # 1/4
    assert rain.atk == 1
    p1.give(FIREBALL).play(target=p2.hero)
    assert rain.atk == 3  # +2


def test_raincaller_only_triggers_once_per_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    rain = p1.summon("CATA_487")
    p1.give(FIREBALL).play(target=p2.hero)
    p1.give(FIREBALL).play(target=p2.hero)
    assert rain.atk == 3  # still only +2 from the first


def test_raincaller_triggers_again_next_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    rain = p1.summon("CATA_487")
    p1.give(FIREBALL).play(target=p2.hero)
    assert rain.atk == 3
    game.end_turn(); game.end_turn()
    p1.give(FIREBALL).play(target=p2.hero)
    assert rain.atk == 5  # +2 again


# ---------------------------------------------------------------------------
# CATA_488 Vulcanos (Colossal +2) + Plume limbs
# ---------------------------------------------------------------------------

def test_vulcanos_colossal_summons_two_plumes():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("CATA_488")
    ids = [m.id for m in p1.field]
    assert ids.count("CATA_488") == 1
    assert ids.count("CATA_488t") + ids.count("CATA_488t2") == 2
    assert len(p1.field) == 3


def test_vulcanos_end_of_turn_damages_all_other_minions():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Isolate Vulcanos with no limbs by summoning the parent only is not
    # possible (Colossal forces limbs). Beef up an enemy minion to absorb.
    vulc = p1.summon("CATA_488")
    enemy = p2.summon(BOULDERFIST)  # 6/6/7
    enemy.max_health = 80
    enemy.damage = 0
    # Two friendly Plumes (4 health each) also exist; they'll take 2 too.
    game.end_turn()  # p1 turn ends -> Vulcanos end-of-turn fires
    # Enemy minion takes 2 from Vulcanos's end-of-turn AoE.
    assert enemy.damage == 2


def test_plume_gets_fire_spell_when_damaged():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    plume = p1.summon("CATA_488t")
    pre = len(p1.hand)
    plume.hit(1)
    new = [c for c in p1.hand]
    assert len(new) == pre + 1
    got = new[-1]
    assert got.type == CardType.SPELL
    assert got.spell_school == SpellSchool.FIRE
    # Costs (3) less than its printed cost.
    assert got.cost == max(0, got.data.cost - 3)


# ---------------------------------------------------------------------------
# CATA_979 Conjuration Specialist — split a hand spell into two same-cost spells
# ---------------------------------------------------------------------------

def test_conjuration_specialist_splits_a_hand_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    fb = p1.give(FIREBALL)  # the only spell in hand -> deterministically chosen
    fb_cost = fb.cost
    pre_ids = [c.id for c in p1.hand]
    p1.give("CATA_979").play()
    ids = [c.id for c in p1.hand]
    # The original Fireball was consumed.
    assert "CS2_029" not in ids
    # Two new spells of the same cost were created.
    new = [c for c in p1.hand if c.type == CardType.SPELL]
    assert len(new) == 2
    for c in new:
        assert c.cost == fb_cost
