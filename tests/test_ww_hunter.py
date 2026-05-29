from utils import *

import fireplace.cards
from hearthstone.enums import GameTag, Race, Zone, CardType, Rarity


# ---------------------------------------------------------------------------
# TOY_350 Painted Canvasaur
#   Battlecry: Give each other friendly Beast a random bonus effect.
# ---------------------------------------------------------------------------
def test_painted_canvasaur_buffs_other_beasts_not_self():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    # Two friendly beasts already on board + a non-beast.
    beast1 = game.player1.summon("TOY_356")  # Toyrannosaurus (Beast)
    beast2 = game.player1.summon("NEW1_034")  # Huffer (Beast)
    nonbeast = game.player1.summon("CS1_042")  # Goldshire Footman (no race)

    BONUS_TAGS = (
        GameTag.TAUNT, GameTag.WINDFURY, GameTag.DIVINE_SHIELD,
        GameTag.POISONOUS, GameTag.CANT_BE_TARGETED_BY_SPELLS,
        GameTag.RUSH, GameTag.LIFESTEAL, GameTag.REBORN,
    )

    def bonus_count(m):
        return sum(1 for t in BONUS_TAGS if m.tags.get(t))

    pre1, pre2, pren = bonus_count(beast1), bonus_count(beast2), bonus_count(nonbeast)

    canvasaur = game.player1.give("TOY_350")
    canvasaur.play()

    # Each OTHER friendly beast gains exactly one bonus effect.
    assert bonus_count(beast1) == pre1 + 1
    assert bonus_count(beast2) == pre2 + 1
    # Non-beast untouched.
    assert bonus_count(nonbeast) == pren
    # Canvasaur itself ("each other") gains nothing.
    assert bonus_count(canvasaur) == 0
    # No stat changes from a bonus effect.
    assert canvasaur.atk == 3 and canvasaur.health == 2


# ---------------------------------------------------------------------------
# TOY_351 / TOY_351t Mystery Egg
#   Deathrattle: Get a copy of a random Beast in your deck. It costs (5) less.
# ---------------------------------------------------------------------------
def test_mystery_egg_deathrattle_copies_deck_beast_cost5less():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    # Empty the deck then seed exactly one beast to remove RNG.
    game.player1.discard_hand()
    for c in list(game.player1.deck):
        c.discard()
    beast = game.player1.give("TOY_356")  # Toyrannosaurus, base cost 7
    beast.zone = Zone.DECK

    egg = game.player1.summon("TOY_351")
    pre_hand = len(game.player1.hand)
    egg.destroy()

    assert len(game.player1.hand) == pre_hand + 1
    copy = game.player1.hand[-1]
    assert copy.id == "TOY_356"
    # base cost 7, -5 enchant => 2
    assert copy.cost == 2


def test_mystery_egg_mini_token_same_deathrattle():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.discard_hand()
    for c in list(game.player1.deck):
        c.discard()
    beast = game.player1.give("NEW1_034")  # Huffer, base cost 3
    beast.zone = Zone.DECK

    egg = game.player1.summon("TOY_351t")
    pre_hand = len(game.player1.hand)
    egg.destroy()

    assert len(game.player1.hand) == pre_hand + 1
    copy = game.player1.hand[-1]
    assert copy.id == "NEW1_034"
    # base cost 3, -5 => clamped to 0
    assert copy.cost == 0


# ---------------------------------------------------------------------------
# TOY_352 Fetch!
#   Draw a minion. If it's a Beast, draw a spell.
# ---------------------------------------------------------------------------
def test_fetch_draws_beast_then_spell():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.discard_hand()
    for c in list(game.player1.deck):
        c.discard()
    # Deck: exactly one beast minion + one spell.
    beast = game.player1.give("NEW1_034")  # Huffer (Beast)
    beast.zone = Zone.DECK
    spell = game.player1.give("CS2_029")  # Fireball
    spell.zone = Zone.DECK

    fetch = game.player1.give("TOY_352")
    fetch.play()

    ids = {c.id for c in game.player1.hand}
    # Drew the beast, then because it's a Beast, drew the spell too.
    assert "NEW1_034" in ids
    assert "CS2_029" in ids
    assert len(game.player1.deck) == 0


def test_fetch_nonbeast_minion_no_spell_draw():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.discard_hand()
    for c in list(game.player1.deck):
        c.discard()
    # Deck: one NON-beast minion + one spell.
    minion = game.player1.give("CS1_042")  # Goldshire Footman (no race)
    minion.zone = Zone.DECK
    spell = game.player1.give("CS2_029")  # Fireball
    spell.zone = Zone.DECK

    fetch = game.player1.give("TOY_352")
    fetch.play()

    ids = {c.id for c in game.player1.hand}
    assert "CS1_042" in ids
    # Spell must NOT be drawn (minion wasn't a beast).
    assert "CS2_029" not in ids
    assert len(game.player1.deck) == 1


# ---------------------------------------------------------------------------
# TOY_353 Patchwork Pals
#   Get all 3 Animal Companions. They cost (1) less.
# ---------------------------------------------------------------------------
def test_patchwork_pals_gives_three_companions_cost1less():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.discard_hand()

    spell = game.player1.give("TOY_353")
    spell.play()

    ids = sorted(c.id for c in game.player1.hand)
    assert ids == ["NEW1_032", "NEW1_033", "NEW1_034"]
    # Each base cost 3, -1 enchant => 2.
    for c in game.player1.hand:
        assert c.cost == 2


# ---------------------------------------------------------------------------
# TOY_354 R.C. Rampage
#   Summon six 1/1 Hounds. Any that can't fit give the others +1/+1.
# ---------------------------------------------------------------------------
def test_rc_rampage_empty_board_six_hounds():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    spell = game.player1.give("TOY_354")
    spell.play()

    hounds = [m for m in game.player1.field if m.id == "TOY_358t"]
    assert len(hounds) == 6
    for h in hounds:
        assert h.atk == 1 and h.health == 1


def test_rc_rampage_overflow_buffs():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    # Fill 4 slots; only 3 of the 6 hounds can fit, 3 overflow into +1/+1.
    for _ in range(4):
        game.player1.summon("CS2_231")  # Wisp (1/1, not a hound)
    spell = game.player1.give("TOY_354")
    spell.play()

    hounds = [m for m in game.player1.field if m.id == "TOY_358t"]
    assert len(hounds) == 3
    # 3 overflow distributed +1/+1 across the 3 summoned hounds (one each).
    total_atk = sum(h.atk for h in hounds)
    total_health = sum(h.health for h in hounds)
    # base 3 hounds = 3 atk / 3 health; +3 overflow buffs = +3/+3
    assert total_atk == 6
    assert total_health == 6


# ---------------------------------------------------------------------------
# TOY_355 Hemet, Foam Marksman
#   After a friendly Beast dies, get a random Legendary Beast from the past.
#   It costs (2) less.
# ---------------------------------------------------------------------------
def test_hemet_friendly_beast_death_adds_discounted_legendary_beast():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.discard_hand()
    hemet = game.player1.summon("TOY_355")
    beast = game.player1.summon("NEW1_034")  # Huffer (Beast)

    pre_hand = len(game.player1.hand)
    beast.destroy()

    assert len(game.player1.hand) == pre_hand + 1
    got = game.player1.hand[-1]
    base = fireplace.cards.db[got.id]
    assert Race.BEAST in base.races
    assert base.rarity == Rarity.LEGENDARY
    # 2-mana discount applied.
    assert got.cost == max(0, base.cost - 2)


def test_hemet_enemy_beast_death_does_nothing():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.discard_hand()
    game.player1.summon("TOY_355")
    enemy_beast = game.player2.summon("NEW1_034")

    pre_hand = len(game.player1.hand)
    enemy_beast.destroy()

    assert len(game.player1.hand) == pre_hand


# ---------------------------------------------------------------------------
# TOY_356 Toyrannosaurus
#   Rush. Deathrattle: Deal 5 damage to a random enemy.
# ---------------------------------------------------------------------------
def test_toyrannosaurus_deathrattle_5_to_random_enemy():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    # Only one possible enemy target: enemy hero (clear enemy board).
    rex = game.player1.summon("TOY_356")
    # Beef up enemy hero so it survives and we read exact damage.
    game.player2.hero.max_health = 80
    game.player2.hero.damage = 0
    rex.destroy()
    assert game.player2.hero.damage == 5


def test_toyrannosaurus_has_rush():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    rex = game.player1.summon("TOY_356")
    assert rex.rush


# ---------------------------------------------------------------------------
# TOY_357 King Plush
#   Charge. Battlecry: Return all minions with less Attack than this to
#   their owner's decks.
# ---------------------------------------------------------------------------
def test_king_plush_returns_lower_attack_minions_both_sides():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    # King Plush has 6 atk. Set up:
    low_friend = game.player1.summon("CS2_231")  # Wisp 0... actually 1/1
    high_friend = game.player1.summon("TOY_356")  # Toyrannosaurus 7 atk (>=6, stays)
    low_enemy = game.player2.summon("NEW1_034")  # Huffer 4 atk (<6, returns)
    eq_enemy = game.player2.summon("TOY_356")  # 7 atk enemy (stays)

    p1_deck_pre = len(game.player1.deck)
    p2_deck_pre = len(game.player2.deck)

    plush = game.player1.give("TOY_357")
    plush.play()

    # Plush atk is 6. Minions with atk < 6 get returned.
    field_ids_p1 = [m.id for m in game.player1.field]
    field_ids_p2 = [m.id for m in game.player2.field]

    assert "CS2_231" not in field_ids_p1  # 1 atk returned
    assert "TOY_356" in field_ids_p1       # 7 atk stays
    assert "NEW1_034" not in field_ids_p2  # 4 atk returned
    assert "TOY_356" in field_ids_p2       # 7 atk stays

    assert len(game.player1.deck) == p1_deck_pre + 1
    assert len(game.player2.deck) == p2_deck_pre + 1
    # King Plush itself stays on board.
    assert plush in game.player1.field


def test_king_plush_has_charge():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    plush = game.player1.summon("TOY_357")
    assert plush.charge


# ---------------------------------------------------------------------------
# TOY_358 / TOY_358t Remote Control
#   After your hero attacks, summon a 1/1 Hound.
# ---------------------------------------------------------------------------
def test_remote_control_summons_hound_on_hero_attack():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    weapon = game.player1.give("TOY_358")
    weapon.play()
    game.player2.hero.max_health = 80
    game.player2.hero.damage = 0

    pre = len([m for m in game.player1.field if m.id == "TOY_358t"])
    game.player1.hero.attack(game.player2.hero)
    post = len([m for m in game.player1.field if m.id == "TOY_358t"])
    assert post == pre + 1
    hound = [m for m in game.player1.field if m.id == "TOY_358t"][-1]
    assert hound.atk == 1 and hound.health == 1
    assert Race.BEAST in hound.races and Race.MECHANICAL in hound.races


# ---------------------------------------------------------------------------
# TOY_359 Jungle Gym
#   Deal 1 damage to a random enemy. Repeat for each friendly Beast.
# ---------------------------------------------------------------------------
def test_jungle_gym_one_plus_per_beast():
    # Empty decks/hands so the only friendly beasts are the two we summon.
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.summon("NEW1_034")  # Beast
    game.player1.summon("TOY_356")   # Beast
    # Only enemy target = hero; beef it up to absorb all hits.
    game.player2.hero.max_health = 80
    game.player2.hero.damage = 0

    gym = game.player1.give("TOY_359")
    gym.play()

    # Printed: 1 base + one per friendly Beast on the BOARD = 3.
    assert game.player2.hero.damage == 3


def test_jungle_gym_no_beasts_one_hit():
    # Empty decks/hands: zero friendly beasts anywhere.
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player2.hero.max_health = 80
    game.player2.hero.damage = 0

    gym = game.player1.give("TOY_359")
    gym.play()

    assert game.player2.hero.damage == 1


def test_jungle_gym_counts_beasts_in_hand_and_deck_BUG():
    # BUG (real_bug): Jungle Gym's "for each friendly Beast" counts beasts in
    # HAND and DECK, not just on the battlefield. Printed text means beasts
    # in play only. Here: 0 board beasts but 1 beast in hand + 1 in deck =>
    # impl deals 1 (base) + 2 (hand/deck beasts) = 3 instead of the correct 1.
    # Also BUG: the effect fires on PLAY as a battlecry; the printed card is a
    # Location whose effect should fire on USE/activate. The data `activate`
    # script is empty, so using the location does nothing.
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    beast_hand = game.player1.give("NEW1_034")  # Beast in hand
    beast_deck = game.player1.give("TOY_356")
    beast_deck.zone = Zone.DECK                  # Beast in deck
    game.player2.hero.max_health = 80
    game.player2.hero.damage = 0

    gym = game.player1.give("TOY_359")
    gym.play()

    # Current (buggy) behaviour: counts the hand + deck beasts.
    assert game.player2.hero.damage == 3
