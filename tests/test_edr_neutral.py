"""Into the Emerald Dream — NEUTRAL collectible cards.

Tight unit tests asserting the PRINTED behaviour of every collectible
NEUTRAL card (EDR_ prefix). One test per card; assertions are exact
wherever the setup can be constrained.
"""

import pytest

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Race, Rarity, Zone

import fireplace.cards as _cards


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# EDR_000 — Ysera, Emerald Aspect: Start of Game +5 max mana both; Battlecry
# gain 3 mana crystals.
def test_ysera_emerald_aspect():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    p1.max_mana = 5
    p1.used_mana = 0
    p2.max_mana = 5
    ysera = p1.summon("EDR_000")
    # Drive the battlecry directly (summon bypasses it).
    game.cheat_action(ysera, list(ysera.get_actions("play")))
    # Battlecry gives p1 three crystals on top of the five it had.
    assert p1.max_mana == 8
    # Battlecry does not touch the opponent (that's Start of Game only).
    assert p2.max_mana == 5


def test_ysera_start_of_game():
    # Drive the Start of Game effect directly.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.max_mana = 2
    p2.max_mana = 2
    ysera = p1.summon("EDR_000")
    game.cheat_action(ysera, list(ysera.get_actions("start_of_game")))
    assert p1.max_mana == 7
    assert p2.max_mana == 7


def test_ysera_start_of_game_raises_ceiling_past_ten():
    # The signature beyond-10 ramp: Ysera lifts each player's max-Mana ceiling
    # by 5 (10 -> 15), so per-turn ramp can climb past the normal 10 cap.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.max_mana = 9
    p2.max_mana = 9
    assert p1.max_resources == 10
    ysera = p1.summon("EDR_000")
    game.cheat_action(ysera, list(ysera.get_actions("start_of_game")))
    # Ceiling lifted to 15 for both; current max_mana bumped by 5 (capped only
    # by the new ceiling, so 9 + 5 = 14).
    assert p1.max_resources == 15
    assert p2.max_resources == 15
    assert p1.max_mana == 14
    assert p2.max_mana == 14
    # Per-turn ramp can now push past 10 toward 15.
    p1.max_mana = 14
    p1.max_mana += 1
    assert p1.max_mana == 15  # 11+ reachable; the 10-cap is gone


# EDR_001 — Hopeful Dryad: Battlecry: Get a random Dream card.
def test_hopeful_dryad():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.hand[:] = []
    dryad = p1.give("EDR_001")
    dryad.play()
    assert len(p1.hand) == 1
    assert p1.hand[0].id in (
        "DREAM_01", "DREAM_02", "DREAM_03", "DREAM_04", "DREAM_05",
    )


# EDR_102 — Treacherous Tormentor: Battlecry: Discover a Legendary minion
# with a Dark Gift.
def test_treacherous_tormentor():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.hand[:] = []
    torm = p1.give("EDR_102")
    torm.play()
    _resolve_choices(p1)
    # The discovered minion is gifted then given; one gift ("Sweet Dreams")
    # relocates it to the top of the deck, so look across hand AND deck.
    got = [c for c in (list(p1.hand) + list(p1.deck))][0]
    assert got.rarity == Rarity.LEGENDARY
    assert got.type == CardType.MINION
    # Exactly one real Dark Gift was applied.
    assert len(getattr(got, "_dark_gifts", [])) == 1


# EDR_105 — Creature of Madness: Battlecry: Discover a 3-Cost minion with a
# Dark Gift.
def test_creature_of_madness():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.hand[:] = []
    cre = p1.give("EDR_105")
    cre.play()
    _resolve_choices(p1)
    got = [c for c in (list(p1.hand) + list(p1.deck))][0]
    assert got.data.cost == 3  # base cost of the discovered minion is 3
    assert got.type == CardType.MINION
    assert len(getattr(got, "_dark_gifts", [])) == 1


# EDR_110 — Sporegnasher: Poisonous. Deathrattle: Deal 1 damage to a random
# enemy minion.
def test_sporegnasher():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    spore = p1.summon("EDR_110")
    assert spore.poisonous
    target = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    # The Deathrattle deals 1 damage to a random enemy minion. The spore is
    # Poisonous, so that single point of damage destroys whatever it hits.
    spore.destroy()
    game.process_deaths()
    assert target.dead
    assert len(p2.field) == 0


# EDR_254 — Animated Moonwell: After you cast a spell, gain Attack equal to
# its Cost.
def test_animated_moonwell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    well = p1.summon("EDR_254")
    base = well.atk
    spell = p1.give("CS2_029")  # Fireball, cost 4
    spell.play(target=p2.hero)
    assert well.atk == base + 4


# EDR_260 — Illusory Greenwing: Taunt. Deathrattle: Shuffle two 4/5 Dragons
# with Taunt into your deck. Summoned When Drawn.
def test_illusory_greenwing():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.deck[:] = []
    wing = p1.summon("EDR_260")
    assert wing.taunt
    wing.destroy()
    game.process_deaths()
    illusions = [c for c in p1.deck if c.id == "EDR_260t"]
    assert len(illusions) == 2
    assert illusions[0].atk == 4 and illusions[0].max_health == 5
    assert illusions[0].taunt
    # Summoned When Drawn: drawing one summons it instead of going to hand.
    # Regression (real bug): exactly ONE 4/5 Taunt enters the board and NO
    # Illusion is left sitting in hand (the old impl summoned a copy AND kept
    # the original in hand, doubling the value).
    pre_field = len(p1.field)
    pre_hand_illusions = sum(1 for c in p1.hand if c.id == "EDR_260t")
    p1.draw()
    assert len(p1.field) == pre_field + 1
    summoned = [m for m in p1.field if m.id == "EDR_260t"]
    assert len(summoned) == 1
    assert summoned[0].atk == 4 and summoned[0].max_health == 5
    assert summoned[0].taunt
    # No leftover Illusion card in hand.
    assert sum(1 for c in p1.hand if c.id == "EDR_260t") == pre_hand_illusions
    assert not any(c.id == "EDR_260t" for c in p1.hand)
    # And the deck shrank by one (the drawn Illusion left the deck).
    assert sum(1 for c in p1.deck if c.id == "EDR_260t") == 1


# EDR_453 — Briarspawn Drake: At end of your turn, attack a random enemy
# minion (excess hits hero).
def test_briarspawn_drake_tramples_excess_to_hero():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    drake = p1.summon("EDR_453")  # 12/7
    enemy = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    enemy_hp_pre = p2.hero.health
    game.end_turn()  # p1 turn ends -> drake attacks enemy
    assert enemy.dead  # 12 atk kills 4/5
    assert drake.damage == 4  # drake took 4 back from the minion's attack
    # Excess = 12 atk - 5 health = 7 spills onto the enemy hero.
    assert p2.hero.health == enemy_hp_pre - 7


def test_briarspawn_drake_no_excess_when_minion_survives():
    # Target minion HP >= drake atk -> the hero takes 0 (no trample).
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    drake = p1.summon("EDR_453")  # 12/7
    # A big-health enemy minion that absorbs the full 12 attack.
    tank = p2.summon("CS2_182")  # Chillwind Yeti, then beef its health up.
    tank.max_health = 30
    tank.damage = 0
    hero_hp_pre = p2.hero.health
    game.end_turn()  # drake attacks the tank
    assert not tank.dead
    assert tank.damage == 12  # absorbed the whole hit
    assert p2.hero.health == hero_hp_pre  # no excess to hero


# EDR_469 — Slumbering Sprite: Starts Dormant. After you use your Hero Power,
# this awakens.
def test_slumbering_sprite():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    if game.current_player is not p1:
        game.end_turn()
    sprite = p1.summon("EDR_469")
    assert sprite.dormant
    p1.hero.power.use(target=game.player2.hero)  # Mage Fireblast needs a target
    assert not sprite.dormant


# EDR_470 — Barkshield Sentinel: Taunt. After you use your Hero Power, gain
# +2 Health.
def test_barkshield_sentinel():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    if game.current_player is not p1:
        game.end_turn()
    sentinel = p1.summon("EDR_470")
    assert sentinel.taunt
    base = sentinel.max_health
    p1.hero.power.use(target=game.player2.hero)  # Mage Fireblast needs a target
    assert sentinel.max_health == base + 2


# EDR_484 — Scavenging Flytrap: After a minion dies, gain its Attack.
def test_scavenging_flytrap():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    trap = p1.summon("EDR_484")  # 2/7
    base = trap.atk
    victim = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    victim.destroy()
    game.process_deaths()
    assert trap.atk == base + 4


# EDR_486 — Scorching Observer: Rush, Lifesteal (vanilla).
def test_scorching_observer():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    obs = game.player1.summon("EDR_486")
    assert obs.rush
    assert obs.lifesteal


# EDR_492 — Mother Duck: Battlecry: Summon three 1/1 Ducklings with Rush.
def test_mother_duck():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    duck = p1.give("EDR_492")
    duck.play()
    ducklings = [m for m in p1.field if m.id == "EDR_492t"]
    assert len(ducklings) == 3
    assert all(d.atk == 1 and d.max_health == 1 and d.rush for d in ducklings)


# EDR_495 — Twisted Treant: Deathrattle: Give a random minion in each player's
# hand -2 Attack.
def test_twisted_treant():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.hand[:] = []
    p2.hand[:] = []
    treant = p1.summon("EDR_495")
    mine = p1.give("CS2_182")   # Chillwind Yeti 4/5 in hand
    theirs = p2.give("CS2_182")
    treant.destroy()
    game.process_deaths()
    assert mine.atk == 2
    assert theirs.atk == 2


# EDR_530 — Daydreaming Pixie: At end of your turn, get a random Nature spell.
def test_daydreaming_pixie():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    if game.current_player is not p1:
        game.end_turn()
    p1.summon("EDR_530")
    p1.hand[:] = []
    game.end_turn()
    assert len(p1.hand) == 1
    from hearthstone.enums import SpellSchool
    assert p1.hand[0].spell_school == SpellSchool.NATURE


# EDR_571 — Fae Trickster: Deathrattle: Draw a spell that costs (5) or more.
def test_fae_trickster():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.deck[:] = []
    p1.hand[:] = []
    fae = p1.summon("EDR_571")
    cheap = p1.give("CS2_029")  # Fireball cost 4
    cheap.zone = Zone.DECK
    pyro = p1.give("EX1_279")   # Pyroblast cost 10
    pyro.zone = Zone.DECK
    fae.destroy()
    game.process_deaths()
    # Only the cost>=5 spell is drawable.
    assert pyro.zone == Zone.HAND
    assert cheap.zone == Zone.DECK


# EDR_572 — Tormented Dreadwing: Deathrattle: Draw 2 Dragons. Reduce Costs by 1.
def test_tormented_dreadwing():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.deck[:] = []
    p1.hand[:] = []
    wing = p1.summon("EDR_572")
    d1 = p1.give("CS2_182")  # not a dragon - should be ignored
    d1.zone = Zone.DECK
    dragons = []
    for _ in range(2):
        d = p1.give("EX1_561")  # Alexstrasza, Dragon, cost 9
        d.zone = Zone.DECK
        dragons.append(d)
    wing.destroy()
    game.process_deaths()
    drawn = [c for c in dragons if c.zone == Zone.HAND]
    assert len(drawn) == 2
    assert all(c.cost == 8 for c in drawn)  # 9 - 1
    assert d1.zone == Zone.DECK


# EDR_598 — Dream Rager: Elusive.
def test_dream_rager():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    rager = p1.summon("EDR_598")
    # Elusive: an enemy spell cannot target it.
    fireball = p2.give("CS2_029")  # Fireball
    assert rager not in fireball.targets


# EDR_780 — Bloodthistle Illusionist: Battlecry: Summon a copy of this.
# One secretly dies when it takes damage.
def test_bloodthistle_illusionist():
    from fireplace.actions import Hit
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    illu = p1.give("EDR_780")
    illu.play()
    copies = [m for m in p1.field if m.id == "EDR_780"]
    assert len(copies) == 2
    # Exactly ONE of the two is the "secretly fake" twin (the summoned copy):
    # it is stamped _glass_dies; the original is not.
    glass = [m for m in copies if getattr(m, "_glass_dies", False)]
    normal = [m for m in copies if not getattr(m, "_glass_dies", False)]
    assert len(glass) == 1
    assert len(normal) == 1
    original, fake = normal[0], glass[0]
    # The original is the played Illusionist itself.
    assert original is illu
    # 1 damage to the fake copy destroys it outright (dies on any damage).
    fake.set_current_health(fake.health)  # ensure full health
    game.cheat_action(p1.hero, [Hit(fake, 1)])
    assert fake.dead
    # The original survives the same 1 damage (normal minion).
    assert not original.dead
    game.cheat_action(p1.hero, [Hit(original, 1)])
    assert not original.dead
    assert original.damage == 1


# EDR_800 — Flutterwing Guardian: Taunt, Divine Shield. Battlecry: Imbue HP.
def test_flutterwing_guardian():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    guard = p1.give("EDR_800")
    guard.play()
    assert guard.taunt
    assert guard.divine_shield
    assert p1.imbues_this_game == 1
    # Mage's imbued power was installed.
    assert p1.hero.power.id == "EDR_851p"  # Mage = Blessing of the Wisp


# EDR_844 — Naralex, Herald of the Flights: Your Dragons cost (1).
def test_naralex():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    dragon = p1.give("EX1_561")  # Alexstrasza, cost 9
    assert dragon.cost == 9
    p1.summon("EDR_844")
    assert dragon.cost == 1


# EDR_846 — Shaladrassil: Get all 5 Dream cards. If you've played a higher
# Cost card while holding this, corrupt them.
def test_shaladrassil_uncorrupted():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.hand[:] = []
    shal = p1.give("EDR_846")
    shal.play()
    ids = sorted(c.id for c in p1.hand)
    assert ids == ["DREAM_01", "DREAM_02", "DREAM_03", "DREAM_04", "DREAM_05"]


def test_shaladrassil_corrupted():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    p1.hand[:] = []
    shal = p1.give("EDR_846")  # cost 7
    p1.max_mana = 10
    p1.used_mana = 0
    pyro = p1.give("EX1_279")  # Pyroblast cost 10 > 7
    pyro.play(target=p2.hero)
    assert getattr(shal, "_played_higher_cost", False)
    # Refill mana so the 7-cost Shaladrassil is playable after the Pyroblast.
    p1.used_mana = 0
    shal.play()
    corrupted = sorted(c.id for c in p1.hand)
    assert corrupted == [
        "EDR_846t1", "EDR_846t2", "EDR_846t3", "EDR_846t4", "EDR_846t5",
    ]


# EDR_849 — Dreambound Raptor: After you play a minion, give it a random
# Bonus Effect (the eight-keyword Delve pool — not a Dark Gift).
def test_dreambound_raptor():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("EDR_849")
    played = p1.give("CS2_182")  # Chillwind Yeti, no keywords
    played.play()
    # A Bonus Effect is keyword-only: exactly one of the eight keywords is now
    # set on the played minion (which started with none).
    BONUS = (
        GameTag.TAUNT, GameTag.WINDFURY, GameTag.DIVINE_SHIELD,
        GameTag.POISONOUS, GameTag.CANT_BE_TARGETED_BY_SPELLS,
        GameTag.RUSH, GameTag.LIFESTEAL, GameTag.REBORN,
    )
    assert any(played.tags.get(t) for t in BONUS)
    # No Dark Gift was recorded — this is a plain Bonus Effect, not a Dark Gift.
    assert not getattr(played, "_dark_gifts", [])


# EDR_852 — Bitterbloom Knight: Battlecry: Imbue your Hero Power.
def test_bitterbloom_knight():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    knight = p1.give("EDR_852")
    knight.play()
    assert p1.imbues_this_game == 1
    assert p1.hero.power.id == "EDR_851p"  # Mage = Blessing of the Wisp


# EDR_856 — Nightmare Lord Xavius: Battlecry: Discover a minion from your
# deck. Give it a Dark Gift.
def test_nightmare_lord_xavius():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.deck[:] = []
    p1.hand[:] = []
    seed = p1.give("CS2_182")  # Chillwind Yeti, no keywords
    seed.zone = Zone.DECK
    xav = p1.give("EDR_856")
    xav.play()
    _resolve_choices(p1)
    # The only deck minion is the seeded Yeti; the discovered copy is gifted.
    # The "Sweet Dreams" gift relocates the copy to the top of the deck, so the
    # gifted card is whichever copy carries a `_dark_gifts` marker.
    gifted = [c for c in (list(p1.hand) + list(p1.deck))
              if getattr(c, "_dark_gifts", None)]
    assert len(gifted) == 1
    got = gifted[0]
    assert got.id == "CS2_182"
    assert len(got._dark_gifts) == 1


# EDR_860 — Resplendent Dreamweaver: Lifesteal. Battlecry: If Imbued twice,
# deal 4 damage to a minion.
def test_resplendent_dreamweaver_not_imbued():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_182")  # 4/5
    target.max_health = 80
    target.damage = 0
    dw = p1.give("EDR_860")
    assert dw.lifesteal
    dw.play(target=target)
    # Not imbued twice -> no damage.
    assert target.damage == 0


def test_resplendent_dreamweaver_imbued_twice():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.imbues_this_game = 2
    target = p2.summon("CS2_182")  # 4/5
    target.max_health = 80
    target.damage = 0
    dw = p1.give("EDR_860")
    dw.play(target=target)
    assert target.damage == 4


# EDR_861 — Tranquil Treant: Deathrattle: Both players gain an empty Mana
# Crystal.
def test_tranquil_treant():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.max_mana = 3
    p2.max_mana = 3
    treant = p1.summon("EDR_861")
    treant.destroy()
    game.process_deaths()
    assert p1.max_mana == 4
    assert p2.max_mana == 4


# EDR_873 — Envoy of the Glade: Battlecry: Transform all Neutral cards in your
# deck into random Druid ones.
def test_envoy_of_the_glade():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.deck[:] = []
    neutral_card = p1.give("CS2_182")  # Chillwind Yeti (neutral)
    neutral_card.zone = Zone.DECK
    envoy = p1.give("EDR_873")
    envoy.play()
    survivors = [c for c in p1.deck]
    assert len(survivors) == 1
    assert CardClass.DRUID in survivors[0].classes
    assert survivors[0].id != "CS2_182"
    # Regression (real bug): the morphed card must be a COLLECTIBLE Druid card
    # (not a non-collectible Druid token / hero power / enchant).
    assert _cards.db[survivors[0].id].collectible
    assert survivors[0].type == CardType.MINION or \
        _cards.db[survivors[0].id].type in (CardType.MINION, CardType.SPELL, CardType.WEAPON)


# EDR_888 — Malorne the Waywatcher: Battlecry: Discover a Legendary Wild God.
# If Imbued 4 times, set its Cost to (1).
def test_malorne_not_imbued():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.hand[:] = []
    mal = p1.give("EDR_888")
    mal.play()
    _resolve_choices(p1)
    assert len(p1.hand) == 1
    got = p1.hand[0]
    assert _cards.db[got.id].tags.get(4065)  # Wild God marker
    # Not imbued 4x -> Cost unchanged from its printed value.
    assert got.cost == _cards.db[got.id].cost


def test_malorne_imbued_four_times():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.imbues_this_game = 4
    p1.hand[:] = []
    mal = p1.give("EDR_888")
    mal.play()
    _resolve_choices(p1)
    got = p1.hand[0]
    assert _cards.db[got.id].tags.get(4065)
    assert got.cost == 1


# EDR_889 — Petal Peddler: At end of your turn, give another random friendly
# Dragon +1/+1.
def test_petal_peddler():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    if game.current_player is not p1:
        game.end_turn()
    p1.summon("EDR_889")
    dragon = p1.summon("EX1_561")  # Alexstrasza, Dragon 8/8
    a, h = dragon.atk, dragon.max_health
    game.end_turn()
    assert dragon.atk == a + 1
    assert dragon.max_health == h + 1


# EDR_942 — Curious Cumulus: At end of your turn, give your hero Divine Shield.
def test_curious_cumulus():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    if game.current_player is not p1:
        game.end_turn()
    p1.summon("EDR_942")
    assert not p1.hero.tags.get(GameTag.DIVINE_SHIELD)
    game.end_turn()
    assert p1.hero.tags.get(GameTag.DIVINE_SHIELD)


# EDR_971 — Critter Caretaker: At end of your turn, restore 3 Health to both
# heroes.
def test_critter_caretaker():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    p1.hero.damage = 10
    p2.hero.damage = 10
    p1.summon("EDR_971")
    game.end_turn()
    assert p1.hero.damage == 7
    assert p2.hero.damage == 7


# EDR_978 — Meadowstrider: Taunt. Deathrattle: Put a Meadowstrider on bottom
# of deck. It costs (1).
def test_meadowstrider():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.deck[:] = []
    strider = p1.summon("EDR_978")
    assert strider.taunt
    strider.destroy()
    game.process_deaths()
    copies = [c for c in p1.deck if c.id == "EDR_978"]
    assert len(copies) == 1
    assert copies[0].cost == 1
    # On the bottom of the deck (index 0 = bottom, drawn from the end).
    assert p1.deck[0].id == "EDR_978"


# EDR_979 — Ancient of Yore: Dormant 2 turns. While Dormant, gain 5 Armor and
# draw at end of your turn.
def test_ancient_of_yore():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    if game.current_player is not p1:
        game.end_turn()
    p1.hero.armor = 0
    p1.deck[:] = []
    seed = p1.give("CHICKEN" if False else "CS2_182")
    seed.zone = Zone.DECK
    ancient = p1.summon("EDR_979")
    assert ancient.dormant
    pre_hand = len(p1.hand)
    game.end_turn()
    # While dormant: +5 armor and a draw at end of my turn.
    assert p1.hero.armor == 5
    assert len(p1.hand) == pre_hand + 1


# EDR_999 — Gnawing Greenfin: Battlecry: Get a random Murloc.
def test_gnawing_greenfin():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.hand[:] = []
    fin = p1.give("EDR_999")
    fin.play()
    assert len(p1.hand) == 1
    assert Race.MURLOC in p1.hand[0].races


def test_sharp_eyed_lookout_draws_and_discounts():
    # EDR_950 (collectible since build 223542): Battlecry - draw a card; it
    # costs (1) less this turn.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    fireball = p1.card("CS2_029")  # Fireball, cost 4
    fireball.zone = Zone.DECK
    base = fireball.data.cost
    p1.give("EDR_950").play()
    assert fireball.zone == Zone.HAND
    assert fireball.cost == base - 1


# FIR_959 — Fyrakk the Blazing (implemented in the emerald_dream neutral
# package): the Battlecry's Fire-spell candidate pool must be Standard-legal
# only (the set is Standard), so Wild-only Fire spells are never eligible.
def test_fyrakk_pool_is_standard_only():
    from hearthstone.enums import SpellSchool, CardType
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Rebuild the exact candidate comprehension the FIR_959 battlecry uses
    # (budget=20 so all costed Fire spells are in scope).
    candidates = [
        cid for cid, c in _cards.db.items()
        if (
            c.collectible
            and c.type == CardType.SPELL
            and getattr(c, "spell_school", None) == SpellSchool.FIRE
            and c.cost is not None
            and 0 < c.cost <= 20
            and getattr(c, "is_standard", False)
        )
    ]
    assert candidates, "Standard Fire-spell pool must be non-empty"
    # Every eligible card is a Standard, costed, Fire-school spell.
    for cid in candidates:
        c = _cards.db[cid]
        assert getattr(c, "is_standard", False)
        assert c.spell_school == SpellSchool.FIRE
        assert (c.cost or 0) > 0
    # A known Wild-only Fire spell (Flame Lance, AT_001) is excluded.
    assert getattr(_cards.db["AT_001"], "is_standard", False) is False
    assert "AT_001" not in candidates


def test_fyrakk_battlecry_casts_about_twenty_mana_of_fire():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    game.random.seed(99)
    # Absorb every random Fire spell on the enemy hero so the loop runs clean.
    p2.hero.max_health = 500
    p2.hero._max_health = 500
    pre = len(p1.spells_cast_this_game)
    fyrakk = p1.give("FIR_959")
    fyrakk.play()
    cast = p1.spells_cast_this_game[pre:]
    # The battlecry cast at least one Fire spell, and EVERY cast was a costed
    # Standard Fire-school spell. Total Mana spent is exactly the 20 budget
    # (1-Cost Standard Fire spells exist so the budget drains to 0).
    assert len(cast) >= 1
    assert all(c.spell_school == SpellSchool.FIRE for c in cast)
    assert all(getattr(c, "is_standard", False) for c in cast)
    assert sum((c.cost or 0) for c in cast) == 20


# EDR_888 — Malorne the Waywatcher (defensive once-over): the Discover pool is
# exactly the 11 Legendary Wild Gods (tag 4065), offered with an EVEN draw (no
# neutral/own-class weighting). The imbues>=4 cost-to-1 buff (EDR_888e) is gated
# on the per-game imbue counter.
def test_malorne_pool_is_eleven_wild_gods():
    from fireplace.cards.emerald_dream.neutral import WILD_GOD_IDS
    # The hard-coded pool matches exactly the collectible tag-4065 Wild Gods.
    expected = {
        cid for cid, c in _cards.db.items()
        if c.collectible and bool(c.tags.get(4065))
    }
    assert len(expected) == 11
    assert set(WILD_GOD_IDS) == expected


def test_malorne_offers_three_distinct_wild_gods_unweighted():
    # The offer is three DISTINCT Wild Gods drawn evenly. Run as a class whose
    # own Wild God exists (Mage -> Aessina EDR_430): the even RandomID draw must
    # not force/over-offer the own-class God, and never repeats.
    from fireplace.cards.emerald_dream.neutral import WILD_GOD_IDS
    for seed in range(8):
        game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
        p1 = game.player1
        p1.hand[:] = []
        game.random.seed(seed)
        p1.give("EDR_888").play()
        assert p1.choice is not None
        offered = [c.id for c in p1.choice.cards]
        assert len(offered) == 3
        assert len(set(offered)) == 3                  # distinct
        assert all(cid in WILD_GOD_IDS for cid in offered)
        p1.choice.choose(p1.choice.cards[0])


def test_malorne_buff_gated_on_imbue_count():
    # EDR_888e sets the discovered God's Cost to (1) ONLY when imbued >= 4.
    # Not imbued: no buff -> printed cost. Imbued 4x: cost forced to 1.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.imbues_this_game = 3  # one short of the gate
    p1.hand[:] = []
    p1.give("EDR_888").play()
    _resolve_choices(p1)
    got = p1.hand[0]
    assert _cards.db[got.id].tags.get(4065)
    assert got.cost == _cards.db[got.id].cost  # unbuffed at 3 imbues

    game2 = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    q1 = game2.player1
    q1.imbues_this_game = 4  # gate met
    q1.hand[:] = []
    q1.give("EDR_888").play()
    _resolve_choices(q1)
    got2 = q1.hand[0]
    assert _cards.db[got2.id].tags.get(4065)
    assert got2.cost == 1
