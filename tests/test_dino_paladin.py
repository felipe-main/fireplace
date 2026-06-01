"""The Lost City of Un'Goro mini-set (Dinosaurs, DINO_) — Paladin card tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, Rarity, Zone


def test_dino_404_firegill_kindred_active_gives_rush():
    # Kindred: Give your other minions Rush.
    # Firegill is Elemental + Murloc. Prime Kindred by playing a Murloc last
    # turn, then play Firegill — its other minions should gain Rush.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1

    p1.give(MURLOC).play()  # PRO_001at, a Murloc — primes Kindred
    game.end_turn(); game.end_turn()  # back to p1's next turn
    assert Race.MURLOC in p1.races_played_last_turn

    # Two bystanders that should receive Rush.
    other1 = p1.summon("CS2_172")  # Bloodfen Raptor
    other2 = p1.summon("CS2_186")  # War Golem
    assert not other1.rush and not other2.rush

    firegill = p1.give("DINO_404")
    firegill.play()

    # Kindred active -> other minions get Rush.
    assert other1.rush is True
    assert other2.rush is True
    # Firegill itself ("other minions") does NOT gain Rush.
    assert firegill.rush is False


def test_dino_404_firegill_kindred_inactive_no_rush():
    # Negative case: nothing matching played last turn -> Kindred inactive,
    # no Rush is granted.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Make sure nothing of Firegill's types was played last turn.
    assert Race.MURLOC not in p1.races_played_last_turn
    assert Race.ELEMENTAL not in p1.races_played_last_turn

    other = p1.summon("CS2_172")  # Bloodfen Raptor
    assert not other.rush

    firegill = p1.give("DINO_404")
    firegill.play()

    # Kindred inactive -> no Rush granted.
    assert other.rush is False
    assert firegill.rush is False


def test_dino_405_hatching_ceremony_buffs_at_end_of_next_turn():
    # At the end of your next turn, give your minions +2/+2.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1

    minion = p1.summon("CS2_172")  # Bloodfen Raptor 3/2
    assert minion.atk == 3 and minion.max_health == 2

    p1.give("DINO_405").play()

    # Still p1's turn (the turn the spell was cast): NOT yet buffed.
    assert minion.atk == 3 and minion.max_health == 2

    # End of THIS turn — first OWN_TURN_END is skipped (the spell counts the
    # *next* turn's end). Still no buff.
    game.end_turn()  # p1 -> p2
    assert minion.atk == 3 and minion.max_health == 2
    game.end_turn()  # p2 -> p1 (p1's next turn begins)
    assert minion.atk == 3 and minion.max_health == 2

    # A minion summoned during the next turn is also a "your minion" when the
    # buff fires at the end of that turn.
    late = p1.summon("CS2_186")  # War Golem 7/7
    assert late.atk == 7 and late.max_health == 7

    game.end_turn()  # end of p1's NEXT turn -> buff fires here
    assert minion.atk == 5 and minion.max_health == 4
    assert late.atk == 9 and late.max_health == 9


def test_dino_405_hatching_ceremony_fires_only_once():
    # The timer should resolve exactly once and then stop.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    minion = p1.summon("CS2_172")  # 3/2

    p1.give("DINO_405").play()
    game.end_turn(); game.end_turn()  # this turn end + into next turn
    game.end_turn()  # end of next turn -> fires (+2/+2)
    assert minion.atk == 5 and minion.max_health == 4

    # Cycle two more full turns; the buff must not re-apply.
    game.end_turn(); game.end_turn()
    game.end_turn(); game.end_turn()
    assert minion.atk == 5 and minion.max_health == 4


def test_dino_424_heros_welcome_summons_legendary_at_10_10():
    # Discover a Legendary minion to summon. Set its stats to 10/10.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    pre_field = len(p1.field)

    p1.give("DINO_424").play()

    # A Discover choice pops up; all candidates must be Legendary minions.
    assert p1.choice is not None
    candidates = p1.choice.cards
    assert len(candidates) == 3
    for c in candidates:
        assert c.rarity == Rarity.LEGENDARY
        assert c.type == CardType.MINION
    chosen = candidates[0]
    p1.choice.choose(chosen)

    # Exactly one minion summoned, and it is the chosen card.
    assert len(p1.field) == pre_field + 1
    summoned = p1.field[-1]
    assert summoned.id == chosen.id
    # Stats set to exactly 10/10 regardless of the card's printed stats.
    assert summoned.atk == 10
    assert summoned.max_health == 10
