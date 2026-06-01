"""Cataclysm (CATA_) — Warrior tests."""

from hearthstone.enums import CardClass, GameTag, Zone

from utils import prepare_empty_game, prepare_game


WISP = "CS2_231"          # 0/1/1 vanilla minion
CHILLWIND = "CS2_182"     # 4/4/5 Chillwind Yeti (vanilla)
FIREBALL = "CS2_029"      # 6 damage fire spell (SpellSchool.FIRE)


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# CATA_150 Ragnaros, the Great Fire (Colossal +2) + Hand of Ragnaros limbs
# ---------------------------------------------------------------------------

def test_ragnaros_colossal_summons_two_hands():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    rag = p1.summon("CATA_150")
    # Colossal +2: Ragnaros plus its two Hand of Ragnaros limbs.
    ids = [m.id for m in p1.field]
    assert ids.count("CATA_150") == 1
    assert ids.count("CATA_150t") + ids.count("CATA_150t1") == 2
    assert len(p1.field) == 3


def test_ragnaros_end_of_turn_triggers_friendly_deathrattles():
    # Hand of Ragnaros deathrattle (deal 2 to a random enemy) fires at end of
    # turn while Ragnaros lives, WITHOUT the limb dying.
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    p1.summon("CATA_150")
    p2.hero.set_current_health(30)
    # No enemy minions: all damage lands on the enemy hero.
    assert len(p2.field) == 0
    game.end_turn()  # p1's turn ends -> OWN_TURN_END trigger
    # Two Hand limbs each deal 2 -> 4 total to face.
    assert p2.hero.health == 26


# ---------------------------------------------------------------------------
# CATA_150t / CATA_580t deathrattle scaling with Herald
# ---------------------------------------------------------------------------

def test_hand_of_ragnaros_deathrattle_base_two_damage():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    p2.hero.set_current_health(30)
    hand = p1.summon("CATA_150t")
    assert p1.heralds_this_game == 0
    hand.destroy()
    game.process_deaths()
    assert p2.hero.health == 28  # exactly 2


def test_soldier_of_ragnaros_deathrattle_scales_to_four_at_two_heralds():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    p2.hero.set_current_health(30)
    p1.heralds_this_game = 2
    soldier = p1.summon("CATA_580t")
    soldier.destroy()
    game.process_deaths()
    assert p2.hero.health == 26  # 2 + min(2,2) = 4


def test_soldier_of_ragnaros_deathrattle_scales_to_three_at_one_herald():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    p2.hero.set_current_health(30)
    p1.heralds_this_game = 1
    soldier = p1.summon("CATA_580t")
    soldier.destroy()
    game.process_deaths()
    assert p2.hero.health == 27  # 2 + 1 = 3


# ---------------------------------------------------------------------------
# CATA_160 Scorching Ravager — Battlecry: Herald. Summon a Soldier with Rush.
# ---------------------------------------------------------------------------

def test_scorching_ravager_heralds_and_summons_rush_soldier():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    assert p1.heralds_this_game == 0
    p1.give("CATA_160").play()
    assert p1.heralds_this_game == 1
    soldiers = [m for m in p1.field if m.id == "CATA_580t"]
    assert len(soldiers) == 1
    assert soldiers[0].rush is True


# ---------------------------------------------------------------------------
# CATA_580 Cataclysmic War Axe — Battlecry: Herald.
# ---------------------------------------------------------------------------

def test_cataclysmic_war_axe_heralds_and_equips():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.give("CATA_580").play()
    assert p1.heralds_this_game == 1
    assert p1.weapon is not None
    assert p1.weapon.atk == 3


# ---------------------------------------------------------------------------
# CATA_581 Decimation — deal (1 + #minions) to all minions.
# ---------------------------------------------------------------------------

def test_decimation_scales_with_board_count():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # 3 minions total on board -> amount = 1 + 3 = 4.
    a = p1.summon(CHILLWIND)   # 4/5
    b = p2.summon(CHILLWIND)   # 4/5
    c = p2.summon(CHILLWIND)   # 4/5
    for m in (a, b, c):
        m.damage = 0
    p1.give("CATA_581").play()
    game.process_deaths()
    # Each Yeti (5 health) took 4; survivors at 1 health.
    assert a.health == 1
    assert b.health == 1
    assert c.health == 1


def test_decimation_one_minion_deals_two():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    a = p2.summon(CHILLWIND)
    a.damage = 0
    p1.give("CATA_581").play()
    game.process_deaths()
    assert a.health == 3  # 5 - (1+1) = 3


# ---------------------------------------------------------------------------
# CATA_582 Searing Fissure — 1 to all minions + hero +3 Attack this turn.
# ---------------------------------------------------------------------------

def test_searing_fissure_damages_all_minions_and_buffs_hero():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    a = p1.summon(CHILLWIND)
    b = p2.summon(CHILLWIND)
    for m in (a, b):
        m.damage = 0
    assert p1.hero.atk == 0
    p1.give("CATA_582").play()
    game.process_deaths()
    assert a.health == 4
    assert b.health == 4
    assert p1.hero.atk == 3


# ---------------------------------------------------------------------------
# CATA_584 Erupting Volcano — location: 3 split among enemies, +3 if fire spell
# ---------------------------------------------------------------------------

def test_erupting_volcano_base_three_to_face():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    p2.hero.set_current_health(30)
    assert len(p2.field) == 0  # all split damage hits the lone enemy hero
    p1.summon("CATA_584")
    p1.location.use()
    game.process_deaths()
    assert p2.hero.health == 27  # exactly 3


def test_erupting_volcano_extra_three_after_fire_spell():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    p2.hero.set_current_health(30)
    # Cast a Fire spell this turn first (Fireball at the enemy hero).
    fb = p1.give(FIREBALL)
    fb.play(target=p2.hero)
    game.process_deaths()
    from hearthstone.enums import SpellSchool
    assert SpellSchool.FIRE in p1.schools_played_this_turn
    health_after_fireball = p2.hero.health  # 30 - 6 = 24
    p1.summon("CATA_584")
    p1.location.use()
    game.process_deaths()
    assert p2.hero.health == health_after_fireball - 6  # 3 + 3


# ---------------------------------------------------------------------------
# CATA_585 Torch — deal 8 to a damaged minion; return with excess.
# ---------------------------------------------------------------------------

def test_torch_requires_no_return_without_excess():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    target = p2.summon(CHILLWIND)  # 4/5
    target.max_health = 20
    target.damage = 1  # damaged, big enough to absorb 8 with no excess
    pre_hand = len(p1.hand)
    p1.give("CATA_585").play(target=target)
    game.process_deaths()
    assert target.damage == 9  # 1 + 8
    # No excess -> no copy returned (hand unchanged net of the played card).
    assert len([c for c in p1.hand if c.id == "CATA_585"]) == 0


def test_torch_returns_copy_with_excess_damage():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    target = p2.summon(CHILLWIND)  # 4/5
    target.damage = 2  # damaged; current health 3
    p1.give("CATA_585").play(target=target)
    game.process_deaths()
    # 8 damage to a 3-health minion -> 5 excess; a Torch copy returns to hand.
    assert target.zone == Zone.GRAVEYARD
    copies = [c for c in p1.hand if c.id == "CATA_585"]
    assert len(copies) == 1
    assert getattr(copies[0], "_torch_damage", 8) == 5


# ---------------------------------------------------------------------------
# CATA_586 Destructive Blaze — survive damage -> summon copy; DR 2 to enemy.
# ---------------------------------------------------------------------------

def test_destructive_blaze_summons_copy_when_surviving_damage():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    blaze = p1.summon("CATA_586")  # 3/3
    # Damage it for 1 (survives) -> should summon a second Destructive Blaze.
    blaze.set_current_health(3)
    game.queue_actions(p1.hero, [__import__("fireplace.actions", fromlist=["Hit"]).Hit(blaze, 1)])
    game.process_deaths()
    assert blaze.health == 2
    assert len([m for m in p1.field if m.id == "CATA_586"]) == 2


def test_destructive_blaze_deathrattle_hits_enemy():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    p2.hero.set_current_health(30)
    assert len(p2.field) == 0
    blaze = p1.summon("CATA_586")
    blaze.destroy()
    game.process_deaths()
    assert p2.hero.health == 28  # exactly 2


# ---------------------------------------------------------------------------
# CATA_591 Commander Geddon — Battlecry: cant_draw + start-of-turn Discover.
# ---------------------------------------------------------------------------

def test_commander_geddon_suppresses_draw():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    assert p1.cant_draw is False
    p1.give("CATA_591").play()
    assert p1.cant_draw is True
    # Hero carries the Barren enchant.
    assert any(e.id == "CATA_591e" for e in p1.hero.buffs)


def test_geddon_start_of_turn_discovers_cost_reduced_from_deck():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    p1.give("CATA_591").play()
    # Advance to p1's next turn start; Barren surfaces a 3-card choice.
    game.end_turn()  # p1 -> p2
    game.end_turn()  # p2 -> p1 (OWN_TURN_BEGIN fires the choice)
    assert p1.choice is not None
    chosen = p1.choice.cards[0]
    pre_cost = chosen.cost
    p1.choice.choose(chosen)
    # The chosen card is now in hand carrying Overheat (-3 cost).
    in_hand = [c for c in p1.hand if any(b.id == "CATA_591e2" for b in c.buffs)]
    assert len(in_hand) == 1
    assert in_hand[0].cost == max(0, pre_cost - 3)


# ---------------------------------------------------------------------------
# CATA_610 Lo'Gosh's Last Stand — give a minion a summon-from-hand deathrattle.
# ---------------------------------------------------------------------------

def test_logosh_last_stand_grants_deathrattle_that_summons_from_hand():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    target = p1.summon(WISP)  # 0/1/1
    # Put exactly one minion in hand so the random summon is deterministic.
    for c in list(p1.hand):
        c.discard()
    handmin = p1.give(CHILLWIND)
    p1.give("CATA_610").play(target=target)
    assert target.has_deathrattle
    target.destroy()
    game.process_deaths()
    # The Chillwind Yeti from hand is now on the board.
    assert any(m.id == CHILLWIND for m in p1.field)
    assert handmin.zone == Zone.PLAY
