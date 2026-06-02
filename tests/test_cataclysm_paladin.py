"""Cataclysm — Paladin tests."""

from hearthstone.enums import GameTag, Race, SpellSchool, Zone
from utils import prepare_game, CardClass


def _resolve_choices(game):
    for p in (game.player1, game.player2):
        while p.choice:
            p.choice.choose(p.choice.cards[0])


##
# CATA_432 — Chromatus (Colossal +4) + heads' deathrattles


def test_chromatus_colossal_and_keywords():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    body = game.player1.summon("CATA_432")
    field_ids = [m.id for m in game.player1.field]
    # Body + 4 heads on board.
    assert field_ids.count("CATA_432") == 1
    for head in ("CATA_432t1", "CATA_432t2", "CATA_432t3", "CATA_432t4"):
        assert head in field_ids
    # Body carries all four keywords from data.
    assert body.taunt
    assert body.lifesteal
    assert body.divine_shield
    # Elusive lives on the static card data (consolidated GameTag.ELUSIVE).
    assert bool(body.data.tags.get(GameTag.ELUSIVE))


def test_chromatus_head_deathrattles_remove_keywords():
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    body = game.player1.summon("CATA_432")
    heads = {m.id: m for m in game.player1.field if m.id != "CATA_432"}
    # Green head removes Taunt.
    assert body.taunt
    heads["CATA_432t1"].destroy()
    game.process_deaths()
    assert not body.taunt
    # Red head removes Lifesteal.
    assert body.lifesteal
    heads["CATA_432t2"].destroy()
    game.process_deaths()
    assert not body.lifesteal
    # Bronze head removes Divine Shield.
    assert body.divine_shield
    heads["CATA_432t4"].destroy()
    game.process_deaths()
    assert not body.divine_shield
    # Blue head removes Elusive — the body becomes targetable by enemy spells.
    fb = game.player2.give("CS2_029")  # Fireball
    assert body.elusive and body not in fb.targets
    heads["CATA_432t3"].destroy()
    game.process_deaths()
    assert not body.elusive
    assert body in fb.targets


##
# CATA_473 — Nozdormu, Bronze Aspect


def test_nozdormu_gives_divine_shield_then_buffs():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    nozdormu = game.player1.summon("CATA_473")
    other = game.player1.summon("CS2_182")  # 4/5 Chillwind Yeti, no DS
    assert not other.divine_shield
    game.end_turn()
    # Both got Divine Shield (neither had one), no +3/+3.
    assert other.divine_shield
    assert nozdormu.divine_shield
    assert other.atk == 4 and other.health == 5
    assert nozdormu.atk == 4 and nozdormu.health == 4


def test_nozdormu_buffs_minions_that_already_had_shield():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.summon("CATA_473")
    shielded = game.player1.summon("CS2_182")
    shielded.tags[GameTag.DIVINE_SHIELD] = True
    assert shielded.divine_shield
    game.end_turn()
    # Already had a shield -> +3/+3 instead, keeps shield.
    assert shielded.atk == 7 and shielded.health == 8
    assert shielded.divine_shield


##
# CATA_474 — Spearheart Sentry


def test_spearheart_sentry_gives_discounted_holy_spell():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.discard_hand()
    game.player1.summon("CATA_474")
    game.end_turn()
    assert len(game.player1.hand) == 1
    spell = game.player1.hand[0]
    assert spell.spell_school == SpellSchool.HOLY
    # Cost reduced by 3 (clamped at 0).
    base = spell.data.cost
    assert spell.cost == max(0, base - 3)


##
# CATA_475 — Scalebreaker Bulwark


def test_scalebreaker_bulwark_damages_all_enemies():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.summon("CATA_475")
    enemy = game.player2.summon("CS2_182")  # 4/5
    enemy_hero = game.player2.hero
    game.end_turn()
    assert enemy.health == 3  # 5 - 2
    assert enemy_hero.health == 28  # 30 - 2


##
# CATA_477 — Chamber of Aspects (Location)


def test_chamber_of_aspects_buffs_hand_minion():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.discard_hand()
    minion = game.player1.give("CS2_182")  # 4/5 in hand
    location = game.player1.summon("CATA_477")
    location.use()
    _resolve_choices(game)
    # The (only) hand minion got +2/+2.
    assert minion.atk == 6
    assert minion.health == 7


def test_chamber_of_aspects_lets_you_choose_which_hand_minion():
    # With two minions in hand the player CHOOSES which one gets +2/+2 (real
    # in-hand targeting, not a random pick).
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.discard_hand()
    a = p1.give("CS2_182")  # 4/5
    b = p1.give("CS2_182")  # 4/5
    location = p1.summon("CATA_477")
    location.use()
    assert p1.choice is not None
    assert set(p1.choice.cards) == {a, b}
    p1.choice.choose(b)        # pick the second one
    assert b.atk == 6 and b.health == 7
    assert a.atk == 4 and a.health == 5  # the unchosen minion is untouched


##
# CATA_478 — Bronze Redeemer


def test_bronze_redeemer_summons_matching_dragon():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    redeemer = game.player1.summon("CATA_478")  # 3/3
    game.end_turn()
    brutes = [m for m in game.player1.field if m.id == "CATA_478t"]
    assert len(brutes) == 1
    brute = brutes[0]
    assert Race.DRAGON in brute.races
    assert brute.atk == 3
    assert brute.health == 3


def test_bronze_redeemer_copies_buffed_stats():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    redeemer = game.player1.summon("CATA_478")  # 3/3
    redeemer.atk = 7
    redeemer.max_health = 9
    redeemer.damage = 0
    game.end_turn()
    brute = [m for m in game.player1.field if m.id == "CATA_478t"][-1]
    assert brute.atk == 7
    assert brute.health == 9


##
# CATA_479 — Flight Maneuvers (Shatter halves)


def test_flight_maneuvers_summon_half():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.give("CATA_479t").play()
    drakes = [m for m in game.player1.field if m.id == "CATA_479t3"]
    assert len(drakes) == 2
    for d in drakes:
        assert d.atk == 4 and d.health == 2
        assert Race.DRAGON in d.races


def test_flight_maneuvers_buff_half():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    a = game.player1.summon("CS2_182")  # 4/5
    b = game.player1.summon("CS2_182")
    game.player1.give("CATA_479t2").play()
    for m in (a, b):
        assert m.atk == 5 and m.health == 6
        assert m.divine_shield


def test_flight_maneuvers_shatters_on_draw():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.discard_hand()
    # Shatter splits the parent into its two halves when DRAWN.
    card = game.player1.card("CATA_479", zone=Zone.DECK)
    game.player1.draw()
    ids = sorted(c.id for c in game.player1.hand)
    assert ids == ["CATA_479t", "CATA_479t2"]
    assert card.zone != Zone.HAND


##
# CATA_480 — Sandfury Aura: end-of-turn effects trigger twice


def test_sandfury_aura_doubles_eot_effect():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    # Scalebreaker deals 2 to all enemies at EOT; doubled -> 4.
    game.player1.summon("CATA_475")
    enemy = game.player2.summon("CS2_182")  # 4/5
    enemy.max_health = 40
    enemy.damage = 0
    game.player1.give("CATA_480").play()
    game.end_turn()
    # Triggered twice: 2 + 2 = 4 damage.
    assert enemy.damage == 4


def test_sandfury_aura_lasts_three_turns():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.summon("CATA_475")
    enemy = game.player2.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    game.player1.give("CATA_480").play()
    # Turn 1 end (doubled = 4), turn 2 end (4), turn 3 end (4) = 12, then gone.
    for _ in range(3):
        game.end_turn()
        game.end_turn()  # skip opponent turn back to player1
    # 3 doubled ticks = 12; a 4th (single, aura expired) would add 2 more.
    assert enemy.damage == 12


##
# CATA_472 — Inspiring Maul: deathrattle triggers a friendly EOT effect


def test_inspiring_maul_triggers_eot_effect():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.summon("CATA_475")  # Scalebreaker: 2 dmg to all enemies
    enemy = game.player2.summon("CS2_182")
    enemy.max_health = 40
    enemy.damage = 0
    maul = game.player1.give("CATA_472")
    maul.play()
    assert game.player1.weapon is maul
    maul.destroy()
    game.process_deaths()
    # Scalebreaker's EOT effect fired once outside end of turn -> 2 damage.
    assert enemy.damage == 2


##
# CATA_621 — Gelbin's Triumph: get a random Paladin Aura, +1 turn


def test_gelbins_triumph_gives_aura():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.discard_hand()
    game.player1.give("CATA_621").play()
    assert len(game.player1.hand) == 1
    aura = game.player1.hand[0]
    assert bool(aura.data.tags.get(3429))  # PALADIN_AURA


def test_gelbins_triumph_extends_sandfury_to_four_turns():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.discard_hand()
    # Mark the bonus directly (Gelbin can give any aura; pin to Sandfury).
    game.player1._next_aura_bonus_turns = 1
    game.player1.summon("CATA_475")
    enemy = game.player2.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    game.player1.give("CATA_480").play()
    # With +1 turn the aura lasts 4 turns -> 4 doubled ticks = 16.
    for _ in range(4):
        game.end_turn()
        game.end_turn()
    assert enemy.damage == 16
