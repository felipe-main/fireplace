"""Perils in Paradise — PALADIN.

Tight unit tests asserting the printed behaviour of every collectible Paladin
card in the VAC_ set.
"""

from utils import *


# VAC_507 — Sunsapper Lynessa: Rogue Tourist. Your spells that cost (2) or
# less cast twice.  (TOURIST is deckbuilding only; only the spell-doubling
# is scripted.)  NOTE reference says TOURIST->7 (Priest), implementation
# docstring says "Rogue Tourist" — the keyword is cosmetic for scripting.
def test_sunsapper_lynessa_doubles_cheap_spell():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    game.player1.summon("VAC_507")
    # Beef up an enemy minion so it survives two Moonfires (1 dmg each).
    target = p2.summon("CS2_172")  # Bloodfen Raptor 3/2
    target.max_health = 20
    target.damage = 0
    moonfire = p1.give("CS2_008")  # Moonfire — 0 cost, deal 1 damage
    moonfire.play(target=target)
    # Cast twice -> 2 total damage on the target.
    assert target.damage == 2


def test_sunsapper_lynessa_no_double_for_expensive_spell():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    game.player1.summon("VAC_507")
    target = p2.summon("CS2_172")
    target.max_health = 20
    target.damage = 0
    fireball = p1.give("CS2_029")  # Fireball — 4 cost, deal 6 damage
    fireball.play(target=target)
    # Costs > 2 -> only cast once: 6 damage.
    assert target.damage == 6


def test_sunsapper_lynessa_tourist_deck_legality():
    # Lynessa is a Rogue Tourist (TOURIST->7 == CardClass.ROGUE). A draft with
    # tourist=ROGUE must include a matching Tourist card and admit Rogue cards.
    from fireplace.utils import random_draft, tourist_class_of
    from fireplace import cards as _cards

    deck = random_draft(CardClass.PALADIN, tourist=CardClass.ROGUE)
    # A matching Paladin Tourist card unlocking Rogue is force-included.
    tourist_cards = [
        cid for cid in deck
        if _cards.db[cid].card_class == CardClass.PALADIN
        and tourist_class_of(_cards.db[cid]) == CardClass.ROGUE
    ]
    assert len(tourist_cards) >= 1
    # The unlocked Rogue class's cards are present.
    rogue_cards = [cid for cid in deck if _cards.db[cid].card_class == CardClass.ROGUE]
    assert len(rogue_cards) >= 1


# VAC_558 — Sea Shanty: Summon three 5/5 Pirates. Costs (1) less for each
# spell you've cast on characters this game.
def test_sea_shanty_summons_three_pirates():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    card = p1.give("VAC_558")
    pre = len(p1.field)
    card.play()
    summoned = p1.field[pre:]
    assert len(summoned) == 3
    for m in summoned:
        assert m.id == "VAC_558t"
        assert (m.atk, m.health) == (5, 5)
        assert Race.PIRATE in m.races


def test_sea_shanty_cost_reduction_per_targeted_spell():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    card = p1.give("VAC_558")
    assert card.cost == 10  # base
    # Cast two spells on characters this game.
    target = p2.summon("CS2_172")
    target.max_health = 20
    target.damage = 0
    p1.give("CS2_008").play(target=target)  # Moonfire on a character
    p1.give("CS2_008").play(target=target)  # Moonfire on a character
    # Cost reduced by 2.
    assert card.cost == 8


# VAC_915 — Power Spike: Deal $4 damage. Give a random friendly minion +4/+4.
def test_power_spike_damage_and_buff():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    # Exactly one friendly minion so the random buff is deterministic.
    friendly = p1.summon("CS2_172")  # Bloodfen Raptor 3/2
    enemy = p2.summon("CS2_172")
    enemy.max_health = 10
    enemy.damage = 0
    spell = p1.give("VAC_915")
    spell.play(target=enemy)
    # Deal exactly 4 to the chosen target.
    assert enemy.damage == 4
    # Only friendly minion gets +4/+4 -> 3/2 becomes 7/6.
    assert friendly.atk == 7
    assert friendly.max_health == 6


# VAC_916 — Divine Brew: Give a character Divine Shield. If it already had
# one, give it +1 Attack this turn. (Drink: 3 -> 2 -> Last)
def test_divine_brew_gives_divine_shield_and_next_drink():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    minion = p1.summon("CS2_172")
    assert not minion.divine_shield
    brew = p1.give("VAC_916")
    brew.play(target=minion)
    assert minion.divine_shield
    # Next drink copy appears in hand ("2 Drinks left").
    nexts = [c for c in p1.hand if c.id == "VAC_916t2"]
    assert len(nexts) == 1


def test_divine_brew_already_shielded_gives_attack():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    minion = p1.summon("CS2_172")  # 3/2
    minion.divine_shield = True
    brew = p1.give("VAC_916")
    brew.play(target=minion)
    # Already had Divine Shield -> +1 Attack this turn instead.
    assert minion.atk == 4
    assert minion.divine_shield  # shield untouched


def test_divine_brew_drink_chain_last_returns_nothing():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    m = p1.summon("CS2_172")
    # Last drink — should give effect but NOT return another copy.
    last = p1.give("VAC_916t3")
    pre_count = len([c for c in p1.hand if c.id.startswith("VAC_916")])
    last.play(target=m)
    assert m.divine_shield
    remaining = [c for c in p1.hand if c.id.startswith("VAC_916")]
    assert len(remaining) == 0


def test_divine_brew_t2_chains_to_t3():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    m = p1.summon("CS2_172")
    drink = p1.give("VAC_916t2")
    drink.play(target=m)
    nexts = [c for c in p1.hand if c.id == "VAC_916t3"]
    assert len(nexts) == 1


# VAC_917 — Grillmaster: Battlecry: Draw your lowest Cost card. Deathrattle:
# Draw your highest Cost card.
def test_grillmaster_battlecry_draws_lowest_cost():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    low = p1.give("CS2_008")   # Moonfire, cost 0
    low.zone = Zone.DECK
    high = p1.give("CS2_029")  # Fireball, cost 4
    high.zone = Zone.DECK
    grill = p1.give("VAC_917")
    grill.play()
    # Battlecry draws lowest cost (Moonfire); Fireball stays in deck.
    assert low.zone == Zone.HAND
    assert high.zone == Zone.DECK


def test_grillmaster_deathrattle_draws_highest_cost():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    low = p1.give("CS2_008")   # Moonfire, cost 0
    low.zone = Zone.DECK
    high = p1.give("CS2_029")  # Fireball, cost 4
    high.zone = Zone.DECK
    grill = p1.summon("VAC_917")  # bypass battlecry so deck untouched
    grill.destroy()
    game.process_deaths()
    # Deathrattle draws highest cost (Fireball); Moonfire stays in deck.
    assert high.zone == Zone.HAND
    assert low.zone == Zone.DECK


# VAC_919 — Lifeguard: Taunt. Battlecry: The next spell you cast has Lifesteal.
def test_lifeguard_taunt():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    m = game.player1.summon("VAC_919")
    assert m.taunt


def test_lifeguard_next_spell_lifesteal():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    # Damage the hero so we can detect the lifesteal heal.
    p1.hero.max_health = 30
    p1.hero.damage = 10  # at 20 health
    lg = p1.give("VAC_919")
    lg.play()
    enemy = p2.summon("CS2_172")
    enemy.max_health = 20
    enemy.damage = 0
    # Moonfire deals 1 -> with lifesteal, hero heals 1 (20 -> 21).
    p1.give("CS2_008").play(target=enemy)
    assert enemy.damage == 1
    assert p1.hero.health == 21


def test_lifeguard_lifesteal_consumed_after_one_spell():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    p1.hero.max_health = 30
    p1.hero.damage = 12  # 18 health
    lg = p1.give("VAC_919")
    lg.play()
    enemy = p2.summon("CS2_172")
    enemy.max_health = 40
    enemy.damage = 0
    p1.give("CS2_008").play(target=enemy)  # lifesteal Moonfire: heal 1 -> 19
    assert p1.hero.health == 19
    # Second spell should NOT have lifesteal -> no heal.
    p1.give("CS2_008").play(target=enemy)
    assert p1.hero.health == 19  # no further heal


# VAC_920 — Service Ace: After this minion gains Attack, reduce the Cost of
# the highest Cost card in your hand by (1).
def test_service_ace_reduces_highest_cost_on_attack_gain():
    from fireplace.actions import Buff

    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Clear hand to control the highest-cost card precisely.
    for c in list(p1.hand):
        c.discard()
    ace = p1.summon("VAC_920")  # 3/3/3
    expensive = p1.give("CS2_029")  # Fireball, cost 4 (highest in hand)
    cheap = p1.give("CS2_008")      # Moonfire, cost 0
    assert expensive.cost == 4
    # Give the Ace +3 Attack through the action pipeline (the path a buff
    # spell takes) so the "after this minion gains Attack" trigger fires.
    game.queue_actions(p1.hero, [Buff(ace, "CS2_087e")])  # +3 Attack
    assert ace.atk == 6
    # Highest-cost card (Fireball) reduced by 1; the cheap card untouched.
    assert expensive.cost == 3
    assert cheap.cost == 0


# VAC_921 — Volley Maul (Weapon): After your hero attacks, get a 1-Cost
# Sunscreen that gives +1/+2.
def test_volley_maul_gives_sunscreen_on_hero_attack():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero.damage = 0
    weapon = p1.give("VAC_921")
    weapon.play()
    assert p1.hero.atk == 3
    pre = len([c for c in p1.hand if c.id == "VAC_917t"])
    p1.hero.attack(p2.hero)
    sunscreens = [c for c in p1.hand if c.id == "VAC_917t"]
    assert len(sunscreens) == pre + 1
    assert sunscreens[0].cost == 1


# VAC_917t — Sunscreen: Give a minion +1/+2.
def test_sunscreen_token_buffs_minion():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    m = p1.summon("CS2_172")  # 3/2
    screen = p1.give("VAC_917t")
    screen.play(target=m)
    assert m.atk == 4
    assert m.max_health == 4


# VAC_922 — Lifesaving Aura: At the end of your turn, get a 1-Cost Sunscreen
# that gives +1/+2. Lasts 3 turns.
def test_lifesaving_aura_grants_sunscreen_at_end_of_turn():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    spell = p1.give("VAC_922")
    spell.play()
    pre = len([c for c in p1.hand if c.id == "VAC_917t"])
    game.end_turn()
    got = len([c for c in p1.hand if c.id == "VAC_917t"])
    assert got == pre + 1


def test_lifesaving_aura_lasts_three_turns():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    spell = p1.give("VAC_922")
    spell.play()
    # Three of our own end-of-turn ticks -> three Sunscreens, then it expires.
    for _ in range(3):
        game.end_turn()  # our turn ends -> tick
        game.end_turn()  # opponent turn ends -> back to us
    count = len([c for c in p1.hand if c.id == "VAC_917t"])
    assert count == 3
    # Fourth turn: aura expired, no further grant.
    game.end_turn()
    game.end_turn()
    assert len([c for c in p1.hand if c.id == "VAC_917t"]) == 3


# VAC_923 — Sanc'Azel: Rush. After this attacks, turn into a location.
def test_sancazel_has_rush():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    m = game.player1.summon("VAC_923")
    assert m.rush
    assert (m.atk, m.max_health) == (3, 8)
    assert Race.ELEMENTAL in m.races


def test_sancazel_turns_into_location_after_attack():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    azel = p1.summon("VAC_923")
    enemy = p2.summon("CS2_172")  # 3/2
    enemy.max_health = 30
    enemy.damage = 0
    azel.attack(enemy)
    game.process_deaths()
    # The minion form is gone; a location (VAC_923t) is now the player's loc.
    assert p1.location is not None
    assert p1.location.id == "VAC_923t"
    # Health carried across (8 base minus 3 from the Raptor's retaliation = 5).
    assert p1.location.durability == 5


def test_sancazel_location_buffs_minion_and_turns_back():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    azel = p1.summon("VAC_923")
    enemy = p2.summon("CS2_172")
    enemy.max_health = 30
    enemy.damage = 0
    azel.attack(enemy)
    game.process_deaths()
    loc = p1.location
    assert loc is not None and loc.id == "VAC_923t"
    # Another friendly minion to receive the +3 Attack + Rush.
    buddy = p1.summon("CS2_231")  # Wisp 1/1
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use(target=buddy)
    assert buddy.atk == 1 + 3
    assert buddy.rush
    # Location turns back into the Sanc'Azel minion.
    minions = [m for m in p1.field if m.id == "VAC_923"]
    assert len(minions) == 1


# VAC_558 Sea Shanty (Tier-2): costs (1) less per spell cast ON A CHARACTER.
def test_sea_shanty_cost_per_spell_on_character():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p = game.player1
    shanty = p.give("VAC_558")
    assert shanty.cost == 10
    # Two spells cast on a character (Moonfire on the enemy hero).
    p.give("CS2_008").play(target=game.player2.hero)
    p.give("CS2_008").play(target=game.player2.hero)
    assert shanty.cost == 8
    # A spell NOT cast on a character (Arcane Intellect) does not count.
    p.give("CS2_023").play()
    assert shanty.cost == 8
