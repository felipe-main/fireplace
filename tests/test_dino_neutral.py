"""The Lost City of Un'Goro MINI-SET — NEUTRAL Dinosaurs (DINO_ prefix)."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, Rarity, CardType, Zone


BEAST = "CS2_172"   # Bloodfen Raptor (3/2 Beast)


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# DINO_410 — The Egg of Khelos
# ---------------------------------------------------------------------------


def test_egg_of_khelos_chain_to_hatch():
    # Each egg's Deathrattle summons the next, more-cracked egg, until the
    # 20/20 Khelos hatches after the fifth break.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1

    chain = ["DINO_410", "DINO_410t2", "DINO_410t3", "DINO_410t4", "DINO_410t5"]
    for cur, nxt in zip(chain, chain[1:]):
        egg = p1.summon(cur)
        egg.destroy()
        game.process_deaths()
        field_ids = [m.id for m in p1.field]
        assert nxt in field_ids
        # The previous egg is gone, the new one is in play exactly once.
        assert field_ids.count(nxt) == 1
        # Clear board for the next isolated link.
        for m in list(p1.field):
            if m.id == nxt:
                continue
            m.destroy()
        game.process_deaths()

    # Final link: the most-cracked egg hatches into the 20/20 Khelos.
    last = [m for m in p1.field if m.id == "DINO_410t5"][0]
    last.destroy()
    game.process_deaths()
    khelos = [m for m in p1.field if m.id == "DINO_410t"]
    assert len(khelos) == 1
    assert khelos[0].atk == 20
    assert khelos[0].health == 20
    assert Race.BEAST in khelos[0].races


# ---------------------------------------------------------------------------
# DINO_411 — Holy Eggbearer
# ---------------------------------------------------------------------------


def test_holy_eggbearer_draws_zero_attack_minion():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.discard_hand()

    # Deck: one 0-Attack minion (the Egg of Khelos, 0/3) plus a non-zero-atk
    # minion. The battlecry must draw the 0-Attack one specifically.
    zero = p1.give("DINO_410")          # 0/3 minion (0 Attack)
    zero.zone = Zone.DECK
    nonzero = p1.give(BEAST)            # 3/2 minion (3 Attack)
    nonzero.zone = Zone.DECK

    eggbearer = p1.give("DINO_411")
    eggbearer.play()

    hand_ids = [c.id for c in p1.hand]
    assert "DINO_410" in hand_ids       # the 0-Attack minion was drawn
    assert BEAST not in hand_ids        # the 3-Attack minion stayed in deck


def test_holy_eggbearer_no_zero_attack_minion_draws_nothing():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.discard_hand()
    for c in list(p1.deck):
        c.discard()

    nonzero = p1.give(BEAST)
    nonzero.zone = Zone.DECK

    eggbearer = p1.give("DINO_411")
    eggbearer.play()

    # No 0-Attack minion in deck -> nothing drawn, the 3-Attack stays put.
    assert [c.id for c in p1.hand] == []
    assert [c.id for c in p1.deck] == [BEAST]


# ---------------------------------------------------------------------------
# DINO_419 — Herbivore Assistant
# ---------------------------------------------------------------------------


def test_herbivore_assistant_buffs_beast():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1

    beast = p1.summon(BEAST)            # 3/2 Bloodfen Raptor
    assert beast.atk == 3 and beast.health == 2
    assert not beast.rush

    assistant = p1.give("DINO_419")
    assistant.play(target=beast)

    assert beast.atk == 5              # 3 + 2
    assert beast.health == 4          # 2 + 2
    assert beast.rush is True


# ---------------------------------------------------------------------------
# DINO_430 — Beast Speaker Taka
# ---------------------------------------------------------------------------


def test_beast_speaker_taka_gains_then_summons():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1

    taka = p1.give("DINO_430")
    base_atk, base_health = taka.atk, taka.health  # 2/2 printed
    assert (base_atk, base_health) == (2, 2)

    taka.play()
    assert p1.choice is not None
    picked = p1.choice.cards[0]
    # The Discover pool must be Legendary Beasts only.
    assert picked.rarity == Rarity.LEGENDARY
    assert Race.BEAST in picked.races
    pick_atk, pick_health = picked.atk, picked.health
    p1.choice.choose(picked)

    # Gained the chosen Beast's stats on top of its own.
    assert taka.atk == base_atk + pick_atk
    assert taka.health == base_health + pick_health
    assert taka._taka_card_id == picked.id

    # Deathrattle summons a real copy of that Beast.
    taka.destroy()
    game.process_deaths()
    summoned = [m for m in p1.field if m.id == picked.id]
    assert len(summoned) == 1
    assert summoned[0].atk == pick_atk
    assert summoned[0].health == pick_health


# ---------------------------------------------------------------------------
# DINO_435 — Crater Experiment (Kindred)
# ---------------------------------------------------------------------------


def test_crater_experiment_kindred_summons_copy():
    # Crater Experiment is a Beast: play a Beast last turn to arm Kindred,
    # then playing Crater Experiment summons a second copy of it.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1

    p1.give(BEAST).play()
    game.end_turn(); game.end_turn()    # Beast is now "played last turn"
    assert Race.BEAST in p1.races_played_last_turn

    for m in list(p1.field):
        m.destroy()
    game.process_deaths()

    crater = p1.give("DINO_435")
    crater.play()

    craters = [m for m in p1.field if m.id == "DINO_435"]
    assert len(craters) == 2           # the played one + the Kindred copy
    assert all(m.atk == 3 and m.health == 4 for m in craters)


def test_crater_experiment_no_kindred_no_copy():
    # Without a matching type played last turn, Kindred is inactive: no copy.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    assert Race.BEAST not in p1.races_played_last_turn

    for m in list(p1.field):
        m.destroy()
    game.process_deaths()

    crater = p1.give("DINO_435")
    crater.play()

    craters = [m for m in p1.field if m.id == "DINO_435"]
    assert len(craters) == 1           # only the played one, no copy
