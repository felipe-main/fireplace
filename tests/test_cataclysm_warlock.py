"""Cataclysm — Warlock tests."""

from hearthstone.enums import GameTag, Race, Zone
from utils import prepare_game, CardClass


def _resolve_choices(game):
    for p in (game.player1, game.player2):
        while p.choice:
            p.choice.choose(p.choice.cards[0])


##
# CATA_490 — Ocular Occultist: Taunt + battlecry discard a card.


def test_ocular_occultist_taunt_and_discards():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    # Give exactly one other card so the random discard is deterministic.
    victim = game.player1.give("CS2_029")  # Fireball
    occultist = game.player1.give("CATA_490")
    occultist.play()
    assert occultist.taunt
    # The one other hand card was discarded (Occultist excludes itself).
    assert victim.zone == Zone.REMOVEDFROMGAME
    assert occultist in game.player1.field


def test_ocular_occultist_empty_hand_no_crash():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    occultist = game.player1.give("CATA_490")
    occultist.play()
    # No other card -> nothing discarded, no crash.
    assert occultist in game.player1.field


def test_ocular_occultist_chooses_which_card_to_discard():
    # With two cards in hand the player CHOOSES which to discard (not random).
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.discard_hand()
    keep = p1.give("CS2_029")    # Fireball
    toss = p1.give("CS2_062")    # Hellfire
    occultist = p1.give("CATA_490")
    occultist.play()
    assert p1.choice is not None
    assert set(p1.choice.cards) == {keep, toss}
    p1.choice.choose(toss)       # discard the chosen one only
    assert toss.zone == Zone.REMOVEDFROMGAME
    assert keep.zone == Zone.HAND


##
# CATA_493 — Duke of Below: Rush, +2/+2 per card discarded this game.


def _discard_count(player):
    from fireplace.dsl.selector import FRIENDLY, DISCARDED

    return len((FRIENDLY + DISCARDED).eval(player.game, player.hero))


def test_duke_of_below_scales_with_discards():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    base_discards = _discard_count(game.player1)
    # Discard two more known cards.
    a = game.player1.give("CS2_029")
    b = game.player1.give("CS2_029")
    from fireplace.actions import Discard

    game.queue_actions(game.player1.hero, [Discard([a, b])])
    n = _discard_count(game.player1)
    assert n == base_discards + 2
    duke = game.player1.give("CATA_493")
    duke.play()
    assert duke.rush
    # Base 2/2 + 2/2 per discarded card this game.
    assert duke.atk == 2 + 2 * n
    assert duke.health == 2 + 2 * n


def test_duke_of_below_no_discards_base_stats():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Fresh game: no discards yet -> base 2/2.
    assert _discard_count(game.player1) == 0
    duke = game.player1.give("CATA_493")
    duke.play()
    assert duke.atk == 2
    assert duke.health == 2


##
# CATA_494 — Maloriak: after you discard a minion, summon a copy.


def test_maloriak_summons_copy_of_discarded_minion():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    game.player1.summon("CATA_494")
    minion = game.player1.give("CS2_182")  # 4/5 Chillwind Yeti
    from fireplace.actions import Discard

    game.queue_actions(game.player1.hero, [Discard(minion)])
    copies = [m for m in game.player1.field if m.id == "CS2_182"]
    assert len(copies) == 1
    assert copies[0].atk == 4 and copies[0].health == 5


def test_maloriak_ignores_discarded_spell():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    game.player1.summon("CATA_494")
    spell = game.player1.give("CS2_029")  # Fireball (spell)
    from fireplace.actions import Discard

    game.queue_actions(game.player1.hero, [Discard(spell)])
    # No minion summoned from a discarded spell.
    assert not [m for m in game.player1.field if m.id == "CS2_029"]


##
# CATA_725 — Shadowsworn Disciple: Battlecry Herald; Deathrattle heal 3.


def test_shadowsworn_disciple_herald_and_deathrattle():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    pre_heralds = game.player1.heralds_this_game
    disciple = game.player1.give("CATA_725")
    disciple.play()
    assert game.player1.heralds_this_game == pre_heralds + 1
    game.player1.hero.damage = 10
    disciple.destroy()
    game.process_deaths()
    # Restored 3 -> 30 - 10 + 3 = 23.
    assert game.player1.hero.health == 23


##
# CATA_491 — Eldritch Tentacles: 3/2/1 damage waves to all minions.


def test_eldritch_tentacles_repeats_with_less_damage():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # A tanky minion absorbs all three waves: 3 + 2 + 1 = 6.
    tank = game.player2.summon("CS2_182")  # 4/5
    tank.max_health = 50
    tank.damage = 0
    game.player1.give("CATA_491").play()
    assert tank.damage == 6


def test_eldritch_tentacles_kills_small_minions_each_wave():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # 3-health minion dies to first wave; 1-health to first wave too.
    a = game.player2.summon("CS2_182")  # 4/5 -> 5 hp, survives 3+2+1=6? dies on wave2 (5)
    a.max_health = 5
    a.damage = 0
    game.player1.give("CATA_491").play()
    # 5 health: wave1 -3 -> 2 left, wave2 -2 -> dead.
    assert a.dead


##
# CATA_496 — Cursed Chains: steal until end of their turn, can't attack.


def test_cursed_chains_takes_control_and_cant_attack():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    enemy = game.player2.summon("CS2_182")  # 4/5
    chains = game.player1.give("CATA_496")
    chains.play(target=enemy)
    # Now controlled by player1, can't attack this turn.
    assert enemy in game.player1.field
    assert enemy not in game.player2.field
    assert bool(enemy.tags.get(GameTag.CANT_ATTACK))


def test_cursed_chains_returns_at_end_of_their_turn():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    enemy = game.player2.summon("CS2_182")
    chains = game.player1.give("CATA_496")
    chains.play(target=enemy)
    assert enemy in game.player1.field
    # End player1's turn — keep it (their/opponent's turn hasn't ended).
    game.end_turn()
    assert enemy in game.player1.field
    # End the opponent's (player2's) turn — control reverts.
    game.end_turn()
    assert enemy in game.player2.field
    assert enemy not in game.player1.field


##
# CATA_498 — Rafaams' Last Stand: deal $@ to two random enemy minions, upgrades.


def test_rafaams_last_stand_base_damage():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    a = game.player2.summon("CS2_182")  # 4/5
    b = game.player2.summon("CS2_182")
    a.max_health = 20; a.damage = 0
    b.max_health = 20; b.damage = 0
    game.player1.give("CATA_498").play()
    # Base damage 2 to each of the two enemy minions.
    assert a.damage == 2
    assert b.damage == 2


def test_rafaams_last_stand_upgrades_in_hand():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    card = game.player1.give("CATA_498")
    # Held across two of the controller's turn-starts -> +2 damage (progress 2).
    game.end_turn(); game.end_turn()
    game.end_turn(); game.end_turn()
    a = game.player2.summon("CS2_182")
    b = game.player2.summon("CS2_182")
    a.max_health = 20; a.damage = 0
    b.max_health = 20; b.damage = 0
    card.play()
    # 2 base + 2 progress = 4 each.
    assert a.damage == 4
    assert b.damage == 4


##
# CATA_499 — Disposable Acolytes: play OR discard summons two 1-Cost minions.


def test_disposable_acolytes_on_play():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    pre = len(game.player1.field)
    game.player1.give("CATA_499").play()
    summoned = [m for m in game.player1.field]
    assert len(summoned) == pre + 2
    for m in summoned[pre:]:
        assert m.data.cost == 1


def test_disposable_acolytes_on_discard():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    card = game.player1.give("CATA_499")
    pre = len(game.player1.field)
    from fireplace.actions import Discard

    game.queue_actions(game.player1.hero, [Discard(card)])
    summoned = game.player1.field[pre:]
    assert len(summoned) == 2
    for m in summoned:
        assert m.data.cost == 1


##
# CATA_492 — Shrine of Twilight (Location): Herald, draw a card.


def test_shrine_of_twilight_heralds_and_draws():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    pre_heralds = game.player1.heralds_this_game
    pre_hand = len(game.player1.hand)
    location = game.player1.summon("CATA_492")
    location.use()
    _resolve_choices(game)
    assert game.player1.heralds_this_game == pre_heralds + 1
    assert len(game.player1.hand) == pre_hand + 1


##
# CATA_726 — Cho'gall, Mastermind: Colossal +2 (two Arm limbs).


def test_chogall_colossal_summons_two_arms():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.summon("CATA_726")
    ids = [m.id for m in game.player1.field]
    assert ids.count("CATA_726") == 1
    assert "CATA_726t" in ids
    assert "CATA_726t1" in ids


def test_chogall_arm_consumes_minion_to_right_at_end_of_turn():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    arm = game.player1.summon("CATA_726t")  # 1/1 Cho's Arm
    victim = game.player1.summon("CS2_182")  # 4/5 to the right
    pre_atk, pre_health = arm.atk, arm.health
    game.end_turn()
    # Right neighbour destroyed; Arm gained +2/+2 (base, 0 heralds).
    assert victim.dead
    assert arm.atk == pre_atk + 2
    assert arm.health == pre_health + 2


def test_chogall_arm_gain_scales_with_heralds():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    game.player1.heralds_this_game = 2
    arm = game.player1.summon("CATA_726t1")  # Gall's Arm
    victim = game.player1.summon("CS2_182")
    pre_atk, pre_health = arm.atk, arm.health
    game.end_turn()
    assert victim.dead
    # +2/+2 base + 2 heralds = +4/+4.
    assert arm.atk == pre_atk + 4
    assert arm.health == pre_health + 4


def test_chogall_arm_gain_caps_at_two_heralds():
    # Regression: the gain used base + heralds with NO cap, so 3 heralds gave
    # +5/+5. The printed card upgrades only twice ("Herald twice to upgrade"
    # then "once"), so it caps at base 2 + min(heralds, 2) = +4/+4.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    game.player1.heralds_this_game = 3
    arm = game.player1.summon("CATA_726t1")
    victim = game.player1.summon("CS2_182")
    pre_atk, pre_health = arm.atk, arm.health
    game.end_turn()
    assert victim.dead
    assert arm.atk == pre_atk + 4  # capped, not +5
    assert arm.health == pre_health + 4


##
# CATA_725t — Soldier of Cho'gall: same end-of-turn consume effect.


def test_chogall_arm_no_right_minion_no_gain():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    # Arm is rightmost -> nothing to consume -> no stat gain.
    arm = game.player1.summon("CATA_726t")
    pre_atk, pre_health = arm.atk, arm.health
    game.end_turn()
    assert arm.atk == pre_atk
    assert arm.health == pre_health


def test_soldier_of_chogall_consumes_right():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    soldier = game.player1.summon("CATA_725t")
    victim = game.player1.summon("CS2_182")
    pre_atk, pre_health = soldier.atk, soldier.health
    game.end_turn()
    assert victim.dead
    assert soldier.atk == pre_atk + 2
    assert soldier.health == pre_health + 2
