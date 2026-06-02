"""The Lost City of Un'Goro — Priest unit tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, SpellSchool, Zone


WISP = "CS2_231"            # 1/1 vanilla minion
BLOODFEN = "CS2_172"        # Bloodfen Raptor, Beast (Kindred type match)
CONSECRATION = "CS2_093"    # Holy spell, no target (2 dmg to all enemies)
THOUGHTSTEAL = "EX1_339"    # Shadow spell, no target


def test_archaios_sets_attacker_health():
    # Archaios is a 3/1/6. When another friendly minion attacks, its Health
    # is set equal to Archaios's Health (6) — both max and current.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    archaios = game.player1.summon("TLC_811")
    assert archaios.health == 6
    wisp = game.player1.summon(WISP)
    assert wisp.max_health == 1
    game.end_turn()
    game.end_turn()
    # Wisp attacks the enemy hero (survives the trade).
    wisp.attack(game.player2.hero)
    assert wisp.max_health == 6
    assert wisp.health == 6
    assert wisp.damage == 0


def test_twilight_mender_deathrattle_gets_holy_and_shadow():
    # Deathrattle: get a random Holy and a random Shadow spell (two cards).
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    mender = p1.summon("TLC_814")
    pre = len(p1.hand)
    mender.destroy()
    game.process_deaths()
    added = list(p1.hand)[pre:]
    assert len(added) == 2
    schools = {c.spell_school for c in added}
    assert schools == {SpellSchool.HOLY, SpellSchool.SHADOW}
    assert all(c.type == CardType.SPELL for c in added)


def test_gravedawn_voidbulb_no_kindred_summons_one():
    # Without Kindred active, summon a single 4-Cost minion with Taunt.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    assert len(p1.field) == 0
    p1.give("TLC_815").play()
    assert len(p1.field) == 1
    assert p1.field[0].taunt
    assert p1.field[0].cost == 4


def test_gravedawn_voidbulb_kindred_summons_two():
    # Voidbulb is a Shadow spell; playing a Shadow spell last turn activates
    # Kindred (do it again -> two 4-Cost Taunts).
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.give(THOUGHTSTEAL).play()
    game.end_turn()
    game.end_turn()
    assert SpellSchool.SHADOW in p1.schools_played_last_turn
    assert len(p1.field) == 0
    p1.give("TLC_815").play()
    assert len(p1.field) == 2
    assert all(m.taunt and m.cost == 4 for m in p1.field)


def test_gravedawn_sunbloom_draws_two():
    # Base effect: draw 2 cards.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    sunbloom = p1.give("TLC_816")
    pre_hand = len(p1.hand)
    pre_deck = len(p1.deck)
    sunbloom.play()
    # Sunbloom leaves hand (-1) and draws 2 (+1 net hand); deck loses 2.
    assert len(p1.hand) == pre_hand + 1
    assert len(p1.deck) == pre_deck - 2


def test_gravedawn_sunbloom_kindred_cost_reduction():
    # Sunbloom is a Holy spell; a Holy card played last turn makes it cost (2)
    # less. Base cost 4 -> 2.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    sunbloom_neg = p1.give("TLC_816")
    assert sunbloom_neg.cost == 4
    p1.give(CONSECRATION).play()
    game.end_turn()
    game.end_turn()
    assert SpellSchool.HOLY in p1.schools_played_last_turn
    sunbloom = p1.give("TLC_816")
    assert sunbloom.cost == 2


def test_gladesong_siren_cost_drops_after_holy_and_shadow():
    # 6/4/7 Lifesteal. Costs (1) once you've played a Holy AND a Shadow spell
    # this turn.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    siren = p1.give("TLC_819")
    assert siren.cost == 6
    assert siren.lifesteal
    p1.give(CONSECRATION).play()
    assert siren.cost == 6  # only Holy so far
    p1.give(THOUGHTSTEAL).play()
    assert SpellSchool.HOLY in p1.schools_played_this_turn
    assert SpellSchool.SHADOW in p1.schools_played_this_turn
    assert siren.cost == 1


def test_glade_ecologist_deathrattle_gives_purifying_vines():
    # Deathrattle: get Purifying Vines (a 1-Cost Holy spell).
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    eco = p1.summon("TLC_820")
    pre = len(p1.hand)
    eco.destroy()
    game.process_deaths()
    added = list(p1.hand)[pre:]
    assert len(added) == 1
    assert added[0].id == "TLC_813"
    assert added[0].cost == 1
    assert added[0].spell_school == SpellSchool.HOLY


def test_purifying_vines_friendly_buffs_enemy_debuffs():
    # Friendly minion: +2 Health. Enemy minion: -2 Health.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    friendly = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    assert friendly.health == 5
    p1.give("TLC_813").play(target=friendly)
    assert friendly.max_health == 7
    assert friendly.health == 7
    game.end_turn()
    enemy = p2.summon("CS2_182")
    game.end_turn()
    p1.give("TLC_813").play(target=enemy)
    assert enemy.max_health == 3
    assert enemy.health == 3


def test_resuscitate_resurrects_by_cost_with_reborn():
    # Resurrect a 1-, 2- and 3-Cost minion that died this game, each with Reborn.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    m1 = p1.summon("CS2_171")  # Stonetusk Boar, 1-cost
    m2 = p1.summon("CS2_172")  # Bloodfen Raptor, 2-cost
    m3 = p1.summon("CS2_182")  # Chillwind Yeti, 4... need 3-cost
    # use a known 3-cost minion instead of yeti
    m3.destroy()
    m3 = p1.summon("CS2_127")  # Silverback Patriarch, 3-cost
    for m in (m1, m2, m3):
        m.destroy()
    game.process_deaths()
    assert len(p1.field) == 0
    p1.give("TLC_818").play()
    game.process_deaths()
    field = p1.field
    assert len(field) == 3
    costs = sorted(m.cost for m in field)
    assert costs == [1, 2, 3]
    assert all(m.reborn for m in field)


def test_wilted_shadow_attacks_healed_enemy():
    # 7/7 Lifesteal. Whenever you heal an enemy, Wilted Shadow attacks it.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    shadow = p1.summon("TLC_821")
    assert shadow.lifesteal
    game.end_turn()
    enemy = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    enemy.damage = 3  # current health 2
    game.end_turn()
    # Heal the damaged enemy: triggers Wilted Shadow's attack on it.
    game.queue_actions(p1.hero, [Heal(enemy, 1)])
    game.process_deaths()
    # Enemy (back to 3 health after heal) takes 7 -> dies.
    assert enemy.dead
    # Wilted Shadow took 4 from the Yeti but lifesteal healed the hero.
    assert shadow.damage == 4


def test_wilted_shadow_ignores_friendly_heal():
    # Healing a friendly character must NOT trigger an attack.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    shadow = p1.summon("TLC_821")
    friendly = p1.summon("CS2_182")
    friendly.damage = 2
    game.queue_actions(p1.hero, [Heal(friendly, 1)])
    game.process_deaths()
    assert not friendly.dead
    assert shadow.damage == 0
    assert not shadow.attacked_this_turn if hasattr(shadow, "attacked_this_turn") else True


def test_story_of_amara_sets_hero_health_to_40():
    # Set your hero's Health to 40 (above the normal 30 cap).
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.hero.damage = 10  # current health 20
    p1.give("TLC_835").play()
    assert p1.hero.max_health == 40
    assert p1.hero.health == 40
    assert p1.hero.damage == 0


def test_reach_equilibrium_holy_quest_rewards_lifes_breath():
    # Cast 5 Holy spells -> Sol'etos, Life's Breath (TLC_817t3) joins your hand.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.discard_hand()
    p1.give("TLC_817").play()
    quest = next(c for c in p1.secrets if c.id == "TLC_817")
    for i in range(5):
        p1.used_mana = 0  # refund so we can chain 5 casts in one turn
        p1.give(CONSECRATION).play()
    assert any(c.id == "TLC_817t3" for c in p1.hand)
    # Shadow reward not yet earned; quest still in the secret zone.
    assert not any(c.id == "TLC_817t4" for c in p1.hand)
    assert quest.zone == Zone.SECRET


def test_reach_equilibrium_both_quests_complete():
    # Casting 4 Holy and 4 Shadow spells completes both halves and removes the
    # quest from the secret zone. With both halves landing in hand together they
    # immediately combine into Sol'etos, Cycle's Rebirth (TLC_817t5).
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.discard_hand()
    p1.give("TLC_817").play()
    quest = next(c for c in p1.secrets if c.id == "TLC_817")
    # Complete the Holy half first (its reward, Life's Breath, lands in hand);
    # keep it there so completing the Shadow half triggers the combine.
    for i in range(5):
        p1.used_mana = 0
        p1.give(CONSECRATION).play()
    assert any(c.id == "TLC_817t3" for c in p1.hand)
    # Now finish the Shadow half — Death's Touch is delivered into a hand that
    # already holds Life's Breath, so the two fuse on arrival.
    for i in range(5):
        p1.used_mana = 0
        p1.give(THOUGHTSTEAL).play()
        # Thoughtsteal adds 2 cards per cast; trim everything except the
        # Sol'etos pieces so the hand never overflows.
        for c in list(p1.hand):
            if c.id not in ("TLC_817t3", "TLC_817t4", "TLC_817t5"):
                c.discard()
    assert quest.zone != Zone.SECRET
    # Combined: neither half remains; the fused body is in hand instead.
    ids = {c.id for c in p1.hand}
    assert "TLC_817t5" in ids
    assert "TLC_817t3" not in ids
    assert "TLC_817t4" not in ids


def test_soletos_lifes_breath_battlecry_copies_itself():
    # Taunt. Battlecry: Summon a copy of this.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.give("TLC_817t3").play()
    assert len(p1.field) == 2
    assert all(m.id == "TLC_817t3" and m.taunt for m in p1.field)


def test_soletos_deaths_touch_deathrattle_deals_5():
    # Reborn. Deathrattle: deal 5 damage to a random enemy.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    touch = p1.summon("TLC_817t4")
    assert touch.reborn
    enemy_hp = p2.hero.health
    touch.destroy()
    game.process_deaths()
    # Reborn brings it back; the deathrattle 5 damage hit the only enemy (hero).
    assert p2.hero.health == enemy_hp - 5


def test_soletos_combines_when_holding_both_halves():
    # "If you're holding both halves of Sol'etos, combine!" — the moment the
    # second half enters hand, the pair fuses into Sol'etos, Cycle's Rebirth.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.discard_hand()
    p1.give("TLC_817t3")          # Life's Breath — no second half yet, no combine
    assert {c.id for c in p1.hand} == {"TLC_817t3"}
    p1.give("TLC_817t4")          # Death's Touch arrives -> combine fires
    ids = [c.id for c in p1.hand]
    assert ids == ["TLC_817t5"]   # exactly one card: the fused body
    assert "TLC_817t3" not in ids and "TLC_817t4" not in ids


def test_soletos_single_half_does_not_combine():
    # Holding only one half must never combine.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.discard_hand()
    p1.give("TLC_817t3")
    # Draw/generate other unrelated cards; still no partner half -> no combine.
    p1.give(WISP)
    p1.give(CONSECRATION)
    ids = {c.id for c in p1.hand}
    assert "TLC_817t3" in ids
    assert "TLC_817t5" not in ids


def test_soletos_combined_body_taunt_reborn_battlecry_deathrattle():
    # The fused TLC_817t5 keeps both halves' effects: Taunt + Reborn, the
    # Battlecry copy, and the 5-damage Deathrattle.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    p1.give("TLC_817t3")
    combined = p1.give("TLC_817t4")  # not necessarily the surviving object
    fused = next(c for c in p1.hand if c.id == "TLC_817t5")
    fused.play()                     # Battlecry: summon a copy of this
    assert len(p1.field) == 2
    body = p1.field[0]
    assert body.taunt and body.reborn
    assert all(m.id == "TLC_817t5" for m in p1.field)
    # Deathrattle: 5 damage to a random enemy (only the enemy hero is present).
    enemy_hp = p2.hero.health
    body.destroy()
    game.process_deaths()
    assert p2.hero.health == enemy_hp - 5
