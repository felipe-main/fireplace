"""Perils in Paradise — HUNTER collectible cards.

Tight unit tests asserting the PRINTED card behaviour. One test (or cluster)
per collectible card:
  VAC_407 Chatty Macaw, VAC_408 Birdwatching, VAC_409 Parrot Sanctuary,
  VAC_410 Furious Fowls, VAC_412 Catch of the Day, VAC_413 Ranger Gilly,
  VAC_415 Sasquawk, VAC_416 Death Roll, VAC_960 Trusty Fishing Rod,
  VAC_961 Pet Parrot.
"""

from utils import *

from fireplace import cards as _cards


# VAC_407 — Chatty Macaw: Battlecry: Repeat the last spell you cast at an
# enemy (at a random enemy if possible).
def test_chatty_macaw_repeats_last_spell_at_enemy():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    # Beef up the enemy hero so the repeated Moonfire (1 damage) lands on it
    # in full and is exactly measurable. No enemy minions exist, so the only
    # legal enemy target for the repeated spell is the enemy hero.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    # Cast Moonfire (1 damage) at the enemy hero so it is the "last spell".
    moonfire = p1.give(MOONFIRE)
    moonfire.play(target=p2.hero)
    assert p2.hero.health == 80 - 1
    # Now Chatty Macaw repeats that spell at an enemy: another 1 damage.
    macaw = p1.give("VAC_407")
    macaw.play()
    assert p2.hero.health == 80 - 2


def test_chatty_macaw_no_spell_cast_is_noop():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    macaw = p1.give("VAC_407")
    macaw.play()
    # No prior spell -> nothing repeated.
    assert p2.hero.health == 80
    assert macaw in p1.field


# VAC_408 — Birdwatching: Discover a minion from your deck. Give all copies
# of it +2/+1 (wherever they are).
def test_birdwatching_buffs_all_copies():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    # Put two copies of Wisp in the deck and one copy in hand.
    deck1 = p1.give(WISP); deck1.zone = Zone.DECK
    deck2 = p1.give(WISP); deck2.zone = Zone.DECK
    in_hand = p1.give(WISP)
    spell = p1.give("VAC_408")
    spell.play()
    # Discover must offer a minion from the deck (only Wisp present).
    assert p1.choice is not None
    for cid in p1.choice.cards:
        assert _cards.db[cid].type == CardType.MINION
    p1.choice.choose(p1.choice.cards[0])
    # All copies of Wisp (both in deck + the one in hand) get +2/+1.
    for c in (deck1, deck2, in_hand):
        assert c.buffs, "expected a buff on copy %r" % (c,)
        assert c.atk == 1 + 2
        assert c.health == 1 + 1


def test_birdwatching_discover_is_minion_only():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    minion = p1.give(WISP); minion.zone = Zone.DECK
    spell_in_deck = p1.give(MOONFIRE); spell_in_deck.zone = Zone.DECK
    spell = p1.give("VAC_408")
    spell.play()
    # Discover only offers minions from the deck — never the spell.
    assert p1.choice is not None
    assert all(_cards.db[cid].type == CardType.MINION for cid in p1.choice.cards)
    assert MOONFIRE not in p1.choice.cards


# VAC_409 — Parrot Sanctuary (Location): Your next Battlecry minion costs (1)
# less. After you play a Battlecry minion, reopen this.
def test_parrot_sanctuary_discounts_next_battlecry_minion():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    loc = p1.give("VAC_409")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    assert loc.cooldown == 2
    # A Battlecry minion in hand now costs (1) less. Elven Archer (CS2_189)
    # is a 1-cost Battlecry minion -> 1-1 = 0.
    bc = p1.give("CS2_189")  # Elven Archer, 1-cost Battlecry
    assert bc.data.cost == 1
    assert bc.cost == 0


def test_parrot_sanctuary_no_discount_on_nonbattlecry():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    loc = p1.give("VAC_409")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    # Wisp has no battlecry -> no discount.
    wisp = p1.give(WISP)
    assert wisp.cost == wisp.data.cost


def test_parrot_sanctuary_reopens_after_battlecry_minion():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    loc = p1.give("VAC_409")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    assert loc.cooldown == 2
    # Playing a Battlecry minion reopens the location (cooldown -> 0) and
    # consumes the discount enchant.
    bc = p1.give("CS2_189")  # Elven Archer (Battlecry)
    bc.play(target=p1.hero)
    assert loc.cooldown == 0
    # The discount enchant (VAC_409e) is consumed: a fresh Battlecry minion
    # is back at full cost.
    bc2 = p1.give("CS2_189")
    assert bc2.cost == bc2.data.cost


# VAC_410 — Furious Fowls: Choose an enemy. Summon two 3/2 Birds with Immune
# while attacking to attack it.
def test_furious_fowls_summons_two_birds_that_attack_target():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    # An enemy minion with enough health to absorb both 3-damage attacks and
    # survive (so it stays as the assertion subject).
    target = p2.summon(GOLDSHIRE_FOOTMAN)  # 1/2 Taunt
    target.max_health = 80
    target._max_health = 80
    target.damage = 0
    spell = p1.give("VAC_410")
    spell.play(target=target)
    # Two 3/2 Angry Birds summoned, each attacked the chosen target for 3.
    birds = [m for m in p1.field if m.id == "VAC_410t"]
    assert len(birds) == 2
    for b in birds:
        assert (b.atk, b.max_health) == (3, 2)
    # Both birds attacked -> 6 damage total; Immune-while-attacking means
    # they took no return damage and are at full health.
    assert target.damage == 6
    for b in birds:
        assert b.damage == 0


# VAC_412 — Catch of the Day: Rush. Battlecry: Summon a 2/1 Worm for your
# opponent.
def test_catch_of_the_day_summons_worm_for_opponent():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    pre = len(p2.field)
    fish = p1.give("VAC_412")
    fish.play()
    assert fish.rush
    # The 2/1 Worm token belongs to the OPPONENT.
    worms = [m for m in p2.field if m.id == "VAC_412t"]
    assert len(worms) == 1
    assert (worms[0].atk, worms[0].max_health) == (2, 1)
    assert worms[0].controller is p2
    assert not any(m.id == "VAC_412t" for m in p1.field)


# VAC_413 — Ranger Gilly: Warrior Tourist. At the end of your turn, get a 2/3
# Crocolisk. Deathrattle: Give all minions in your hand +2/+3.
def test_ranger_gilly_end_of_turn_crocolisk():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    gilly = p1.summon("VAC_413")
    pre = len([c for c in p1.hand if c.id == "VAC_413t"])
    game.end_turn()
    crocs = [c for c in p1.hand if c.id == "VAC_413t"]
    assert len(crocs) == pre + 1
    assert crocs[0].type == CardType.MINION
    assert (crocs[0].atk, crocs[0].health) == (2, 3)


def test_ranger_gilly_deathrattle_buffs_hand_minions():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    # Clear hand, then plant exactly one minion + one spell in hand.
    for c in list(p1.hand):
        c.discard()
    hand_minion = p1.give(WISP)  # 1/1
    hand_spell = p1.give(MOONFIRE)  # spell, must NOT be buffed
    gilly = p1.summon("VAC_413")
    gilly.destroy()
    game.process_deaths()
    # Hand minion gains +2/+3; the spell is untouched.
    assert hand_minion.atk == 1 + 2
    assert hand_minion.health == 1 + 3
    assert not hand_spell.buffs


def test_ranger_gilly_tourist_unlocks_warrior():
    # Tourist is deckbuilding-only: a Hunter deck with a Warrior Tourist may
    # include Warrior cards. random_draft with tourist=WARRIOR should produce
    # a legal deck containing Warrior cards and a Tourist card.
    from fireplace.utils import random_draft
    deck = random_draft(CardClass.HUNTER, tourist=CardClass.WARRIOR)
    has_warrior = any(
        CardClass.WARRIOR in (list(getattr(_cards.db[cid], "classes", None) or
                                    [_cards.db[cid].card_class]))
        for cid in deck
    )
    assert has_warrior
    has_tourist = any(
        GameTag.TOURIST in _cards.db[cid].tags for cid in deck
    )
    assert has_tourist


# VAC_415 — Sasquawk: Battlecry: Repeat each card you played last turn.
def test_sasquawk_repeats_cards_played_last_turn():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    # Turn N (p1): play a Wisp from hand (recorded with turn_played == turn).
    for c in list(p1.hand):
        c.discard()
    wisp = p1.give(WISP)
    wisp.play()
    assert len([m for m in p1.field if m.id == WISP]) == 1
    # Advance two game-turns so it's p1's next turn (the played turn becomes
    # game.turn - 2).
    game.end_turn()  # p2's turn
    game.end_turn()  # back to p1
    sasquawk = p1.give("VAC_415")
    sasquawk.play()
    # Sasquawk repeats each card played last turn (the Wisp) -> a second Wisp
    # is summoned. Board: original Wisp + repeated Wisp + Sasquawk.
    assert len([m for m in p1.field if m.id == WISP]) == 2


# VAC_416 — Death Roll: Destroy an enemy minion. Deal damage equal to its
# Attack randomly split among all enemies.
def test_death_roll_destroys_and_splits_attack():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    # The only enemy is the hero, so all split damage piles onto it. Use a
    # 5-attack minion as the destroy target -> exactly 5 damage to the hero.
    victim = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    victim.atk = 5
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    spell = p1.give("VAC_416")
    spell.play(target=victim)
    # Victim destroyed.
    assert victim.zone == Zone.GRAVEYARD
    # 5 damage split among all enemies; only the hero remains -> 5 to face.
    assert p2.hero.health == 80 - 5


# VAC_960 — Trusty Fishing Rod (Weapon): After your hero attacks, summon a
# 1-Cost minion from your deck.
def test_trusty_fishing_rod_summons_1cost_after_hero_attack():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    # Deck contains exactly one 1-cost minion (Stonetusk Boar) so the summon
    # is deterministic.
    boar_in_deck = p1.give("DS1_175")  # Stonetusk Boar, cost 1
    boar_in_deck.zone = Zone.DECK
    weapon = p1.give("VAC_960")
    weapon.play()
    assert p1.hero.atk == 1
    pre_field = len(p1.field)
    p1.hero.attack(p2.hero)
    # Hero dealt 1 to face; the rod summoned the 1-cost Boar from the deck.
    assert p2.hero.health == 80 - 1
    assert len([m for m in p1.field if m.id == "DS1_175"]) == 1
    assert boar_in_deck.zone == Zone.PLAY


# VAC_961 — Pet Parrot: Battlecry: Repeat the last 1-Cost card you played.
def test_pet_parrot_repeats_last_1cost_card():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    # Play a 1-cost minion (Stonetusk Boar), then a 2-cost minion; Pet Parrot
    # should repeat the 1-cost one, not the 2-cost.
    boar = p1.give("DS1_175")  # Stonetusk Boar, cost 1
    boar.play()
    raptor = p1.give("CS2_172")  # Bloodfen Raptor, cost 2
    raptor.play()
    assert len([m for m in p1.field if m.id == "DS1_175"]) == 1
    parrot = p1.give("VAC_961")
    parrot.play()
    # Repeated the last 1-cost card (Boar) -> a second Boar summoned.
    assert len([m for m in p1.field if m.id == "DS1_175"]) == 2
    # The 2-cost raptor was not repeated.
    assert len([m for m in p1.field if m.id == "CS2_172"]) == 1


# Tokens — verify base stats / keyword sit in data.
def test_angry_bird_token_stats():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    bird = game.player1.summon("VAC_410t")
    assert (bird.atk, bird.max_health) == (3, 2)
    assert Race.BEAST in bird.races


def test_delicious_worm_token_stats():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    worm = game.player1.summon("VAC_412t")
    assert (worm.atk, worm.max_health) == (2, 1)
    assert Race.BEAST in worm.races


def test_island_crocolisk_token_stats():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    croc = game.player1.summon("VAC_413t")
    assert (croc.atk, croc.max_health) == (2, 3)
    assert Race.BEAST in croc.races
