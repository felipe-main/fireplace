"""The Lost City of Un'Goro — Rogue cards (TLC_513..TLC_522)."""

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Race, SpellSchool, Zone

from fireplace.actions import Buff, Summon


COIN = "GAME_005"
BEAST = "CS2_172"   # Bloodfen Raptor (3/2 Beast)
WISP = "CS2_231"    # 0/1, no race


def _clear_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# TLC_514 Merchant of Legend — Discover a Legendary minion, shuffle other two.
# ---------------------------------------------------------------------------
def test_merchant_of_legend():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    deck_before = len(p1.deck)
    merchant = p1.give("TLC_514")
    merchant.play()
    # A Discover window opened with 3 legendary minions.
    assert p1.choice is not None
    offered = list(p1.choice.cards)
    assert len(offered) == 3
    for c in offered:
        assert c.type == CardType.MINION
    chosen = offered[0]
    p1.choice.choose(chosen)
    assert p1.choice is None
    # Chosen legendary is in hand.
    assert any(c.id == chosen.id for c in p1.hand)
    # The OTHER TWO were shuffled into the deck.
    assert len(p1.deck) == deck_before + 2


# ---------------------------------------------------------------------------
# TLC_516 Neferset Weaponsmith — random weapon from another class; Combo +2 atk.
# ---------------------------------------------------------------------------
def test_neferset_weaponsmith_no_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    smith = p1.give("TLC_516")
    smith.play()
    weapons = [c for c in p1.hand if c.type == CardType.WEAPON]
    assert len(weapons) == 1
    w = weapons[0]
    # From another class (not Rogue, not Neutral weapons collide rarely; just
    # assert it isn't Rogue's own class).
    assert w.card_class != CardClass.ROGUE
    # No combo: attack is the weapon's printed base.
    assert w.atk == w.data.atk


def test_neferset_weaponsmith_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    p1.give(COIN).play()  # warm-up card → combo active
    smith = p1.give("TLC_516")
    smith.play()
    weapons = [c for c in p1.hand if c.type == CardType.WEAPON]
    assert len(weapons) == 1
    w = weapons[0]
    # Combo: +2 Attack on top of base.
    assert w.atk == w.data.atk + 2


# ---------------------------------------------------------------------------
# TLC_517 Knockback — deal damage equal to times shuffled into deck.
# ---------------------------------------------------------------------------
def test_knockback_scales_with_shuffles():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Shuffle exactly 3 cards into our own deck.
    p1.give("TLC_518").play()  # shuffles three 3/3 Ninjas
    assert getattr(p1, "_tlc_times_shuffled", 0) == 3
    # Beefy target so we can read the exact damage.
    target = p1.opponent.summon("CS2_182")  # Chillwind Yeti 4/5
    target.max_health = 80
    target.damage = 0
    kb = p1.give("TLC_517")
    kb.play(target=target)
    assert target.damage == 3


def test_knockback_zero_when_no_shuffles():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    assert getattr(p1, "_tlc_times_shuffled", 0) == 0
    target = p1.opponent.summon("CS2_182")
    target.max_health = 80
    target.damage = 0
    kb = p1.give("TLC_517")
    kb.play(target=target)
    assert target.damage == 0


# ---------------------------------------------------------------------------
# TLC_518 Interrogation — shuffle three 3/3 Stealth Ninjas (Summoned When Drawn)
# ---------------------------------------------------------------------------
def test_interrogation_shuffles_three_ninjas():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    deck_before = len(p1.deck)
    p1.give("TLC_518").play()
    assert len(p1.deck) == deck_before + 3
    ninjas = [c for c in p1.deck if c.id == "TLC_513t2"]
    assert len(ninjas) == 3
    n = ninjas[0]
    assert n.atk == 3 and n.max_health == 3
    assert n.stealthed
    # "Summoned When Drawn" is driven by the token's `draw` script
    # (Summon(CONTROLLER, SELF)), not the data CASTS_WHEN_DRAWN tag (which the
    # 226928.1 rebalance removed). Assert the real mechanism is present.
    assert n.get_actions("draw")


def test_interrogation_ninja_summoned_when_drawn():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Clear deck so we can draw the ninja deterministically.
    for c in list(p1.deck):
        c.zone = Zone.REMOVEDFROMGAME
    p1.give("TLC_518").play()
    field_before = len(p1.field)
    p1.draw()  # only Ninjas in deck → draw one
    # Summoned When Drawn: it enters PLAY, not hand.
    assert len(p1.field) == field_before + 1
    assert p1.field[-1].id == "TLC_513t2"


# ---------------------------------------------------------------------------
# TLC_519 Ambush Predators — summon 1/1 Spitter; Kindred: do it again.
# ---------------------------------------------------------------------------
def test_ambush_predators_no_kindred():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Nothing played last turn → Kindred inactive.
    assert Race.BEAST not in p1.races_played_last_turn
    p1.give("TLC_519").play()
    spitters = [c for c in p1.field if c.id == "TLC_519t"]
    assert len(spitters) == 1
    s = spitters[0]
    assert s.atk == 1 and s.max_health == 1
    assert s.stealthed and s.poisonous and Race.BEAST in s.races


def test_ambush_predators_kindred_doubles():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Ambush Predators is a SHADOW spell — Kindred matches a Shadow card played
    # last turn. Mind Vision (CS2_003) is a 1-cost Shadow spell, no target.
    p1.give("CS2_003").play()
    game.end_turn(); game.end_turn()
    from hearthstone.enums import SpellSchool
    assert SpellSchool.SHADOW in p1.schools_played_last_turn
    field_before = len(p1.field)
    p1.give("TLC_519").play()
    spitters = [c for c in p1.field if c.id == "TLC_519t"]
    assert len(spitters) == 2
    assert len(p1.field) == field_before + 2


# ---------------------------------------------------------------------------
# TLC_520 Underbrush Tracker — costs (1) less per shuffle; has Rush.
# ---------------------------------------------------------------------------
def test_underbrush_tracker_cost_reduction():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    tracker = p1.give("TLC_520")
    base = tracker.data.cost
    assert tracker.cost == base
    # Shuffle 3 cards → costs 3 less.
    p1.give("TLC_518").play()
    assert getattr(p1, "_tlc_times_shuffled", 0) == 3
    assert tracker.cost == base - 3
    # Confirm it has Rush in data.
    assert tracker.rush


# ---------------------------------------------------------------------------
# TLC_521 Eyes in the Sky — look at top 3 of enemy deck, put one on top.
# ---------------------------------------------------------------------------
def test_eyes_in_the_sky_puts_enemy_card_on_top():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p2 = game.player2
    # Rebuild p2's deck with known, distinct ids on top.
    for c in list(p2.deck):
        c.zone = Zone.REMOVEDFROMGAME
    bottom = p2.give(WISP); bottom.zone = Zone.DECK
    a = p2.card("CS2_171"); a.controller = p2; a.zone = Zone.DECK  # Stonetusk
    b = p2.card("CS2_172"); b.controller = p2; b.zone = Zone.DECK  # Bloodfen
    c = p2.card("CS2_173"); c.controller = p2; c.zone = Zone.DECK  # Bluegill (top)
    # deck order now [wisp, a, b, c]; top three = a,b,c.
    eyes = p1.give("TLC_521")
    eyes.play()
    assert p1.choice is not None
    offered = list(p1.choice.cards)
    assert len(offered) == 3
    # Choose a specific card to move to the top (next draw).
    pick = a
    assert pick in offered
    p1.choice.choose(pick)
    assert p1.choice is None
    assert p2.deck[-1] is pick


# ---------------------------------------------------------------------------
# TLC_522 Opu the Unseen — Battlecry/Combo/Deathrattle cast Fan of Knives.
# ---------------------------------------------------------------------------
def test_opu_battlecry_casts_fan_of_knives():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    # Three 1-health enemy minions to be cleared by Fan of Knives (1 dmg AoE).
    enemies = [p1.opponent.summon(WISP) for _ in range(3)]
    hand_before = len(p1.hand)
    p1.give("TLC_522").play()
    # Fan of Knives: 1 damage to all enemy minions (kills the 0/1 Wisps),
    # and draws a card.
    assert all(e.dead for e in enemies)
    assert len(p1.hand) == hand_before + 1  # battlecry cast drew 1


def test_opu_deathrattle_casts_fan_of_knives():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    opu = p1.summon("TLC_522")  # summon: no battlecry
    enemies = [p1.opponent.summon(WISP) for _ in range(2)]
    hand_before = len(p1.hand)
    opu.destroy()
    assert all(e.dead for e in enemies)
    assert len(p1.hand) == hand_before + 1


# ---------------------------------------------------------------------------
# TLC_513 Lie in Wait — Quest (shuffle 5 times) → reward Master Dusk hero.
# ---------------------------------------------------------------------------
def test_lie_in_wait_quest_progresses_and_rewards():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    quest = p1.give("TLC_513")
    quest.play()
    assert p1.secrets  # quest sits in the secret zone
    assert quest.progress == 0
    # Shuffle 5 cards (one Interrogation = 3, plus two more via a second).
    p1.give("TLC_518").play()  # +3
    assert quest.progress == 3
    p1.give("TLC_518").play()  # +3 → 6, clamps the 5-progress quest as done
    # Quest completes → reward summons Master Dusk (a Hero) and replaces hero.
    _clear_choices(p1)
    assert p1.hero.id == "TLC_513t"
    # Master Dusk battlecry summoned two 3/3 Stealth Ninjas.
    ninjas = [c for c in p1.field if c.id == "TLC_513t2"]
    assert len(ninjas) == 2
    for n in ninjas:
        assert n.atk == 3 and n.max_health == 3 and n.stealthed


def test_master_dusk_reshuffles_dead_ninjas():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    # Apply Master Dusk's ongoing enchant + put a Tortollan Ninja on board.
    game.queue_actions(p1.hero, [Buff(p1, "TLC_513e2")])
    ninja = p1.summon("TLC_513t2")
    assert ninja.id == "TLC_513t2"
    deck_before = len(p1.deck)
    ninja.destroy()
    # The reshuffle enchant shuffles a copy of the dead Ninja back into deck.
    assert len(p1.deck) == deck_before + 1
    assert any(c.id == "TLC_513t2" for c in p1.deck)


# ---------------------------------------------------------------------------
# TLC_515 Cultist Map — Discover a card from your deck (drawn out for real).
# ---------------------------------------------------------------------------
def test_cultist_map_discovers_from_own_deck():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Known deck: clear and seed three distinct cards.
    for c in list(p1.deck):
        c.zone = Zone.REMOVEDFROMGAME
    seeded = []
    for cid in ("CS2_171", "CS2_172", "CS2_173"):
        card = p1.card(cid); card.controller = p1; card.zone = Zone.DECK
        seeded.append(card)
    deck_before = len(p1.deck)
    hand_before = len(p1.hand)
    p1.give("TLC_515").play()
    assert p1.choice is not None
    offered_ids = {c.id for c in p1.choice.cards}
    assert offered_ids <= {"CS2_171", "CS2_172", "CS2_173"}
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    assert p1.choice is None
    # The real deck copy is now in hand; deck shrank by exactly one.
    assert len(p1.deck) == deck_before - 1
    assert len(p1.hand) == hand_before + 1
    assert any(c.id == chosen.id for c in p1.hand)
