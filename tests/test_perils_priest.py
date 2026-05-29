"""Perils in Paradise — PRIEST collectible cards.

Tests assert the PRINTED card behaviour. One test (or cluster) per
collectible card: VAC_404 (Nightshade Tea, Drink), VAC_414 (Hot Coals),
VAC_417 (Sensory Deprivation), VAC_418 (Sauna Regular), VAC_419
(Acupuncture), VAC_420 (Narain Soothfancy), VAC_423 (Twilight Medium),
VAC_457 (Rest in Peace), VAC_512 (Brain Masseuse), VAC_957 (Chillin'
Vol'jin — Hunter Tourist).
"""

from utils import *

from fireplace import cards as _cards
from fireplace.utils import random_draft, tourist_class_of


# ---------------------------------------------------------------------------
# VAC_404 — Nightshade Tea (Drink): Deal $3 damage to a minion. Deal $2
# damage to your hero. (3 Drinks left!) -> VAC_404t1 -> VAC_404t2 (Last).
# ---------------------------------------------------------------------------
def test_nightshade_tea_damage_and_next_drink():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    target = game.player2.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    target.max_health = 50
    target.damage = 0
    p1.hero.max_health = 30
    p1.hero.damage = 0
    tea = p1.give("VAC_404")
    tea.play(target=target)
    # $3 to the minion, $2 to own hero.
    assert target.damage == 3
    assert p1.hero.damage == 2
    # The next Drink (2 left) is added to hand.
    nexts = [c for c in p1.hand if c.id == "VAC_404t1"]
    assert len(nexts) == 1


def test_nightshade_tea_second_drink_chains_to_last():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    target = game.player2.summon(GOLDSHIRE_FOOTMAN)
    target.max_health = 50
    target.damage = 0
    t1 = p1.give("VAC_404t1")  # "2 Drinks left"
    t1.play(target=target)
    assert target.damage == 3
    # 2-left drink chains into the Last drink (VAC_404t2).
    lasts = [c for c in p1.hand if c.id == "VAC_404t2"]
    assert len(lasts) == 1


def test_nightshade_tea_last_drink_returns_nothing():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    target = game.player2.summon(GOLDSHIRE_FOOTMAN)
    target.max_health = 50
    target.damage = 0
    p1.hero.max_health = 30
    p1.hero.damage = 0
    last = p1.give("VAC_404t2")  # "Last Drink!"
    last.play(target=target)
    assert target.damage == 3
    assert p1.hero.damage == 2
    # Last drink: no further Nightshade Tea added to hand.
    assert not any(c.id in ("VAC_404", "VAC_404t1", "VAC_404t2") for c in p1.hand)


# ---------------------------------------------------------------------------
# VAC_414 — Hot Coals: Deal $2 damage to all enemies. If your hero took
# damage this turn, deal $1 more.
# ---------------------------------------------------------------------------
def test_hot_coals_base_two_damage_all_enemies():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    enemy.max_health = 50
    enemy.damage = 0
    p2.hero.max_health = 50
    p2.hero.damage = 0
    # Hero has NOT taken damage this turn.
    assert p1.hero.damaged_this_turn == 0
    spell = p1.give("VAC_414")
    spell.play()
    # 2 damage to all enemies, no bonus tick.
    assert enemy.damage == 2
    assert p2.hero.damage == 2


def test_hot_coals_bonus_when_hero_damaged_this_turn():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    enemy.max_health = 50
    enemy.damage = 0
    p2.hero.max_health = 50
    p2.hero.damage = 0
    # Make own hero take damage this turn.
    p1.hero.max_health = 30
    game.queue_actions(p1.hero, [Hit(p1.hero, 3)])
    assert p1.hero.damaged_this_turn == 3
    spell = p1.give("VAC_414")
    spell.play()
    # 2 + 1 = 3 to all enemies.
    assert enemy.damage == 3
    assert p2.hero.damage == 3


# ---------------------------------------------------------------------------
# VAC_417 — Sensory Deprivation: Summon a copy of an enemy minion. If you
# have 20 or less Health, destroy the original.
# ---------------------------------------------------------------------------
def test_sensory_deprivation_copies_no_destroy_high_health():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p1.hero.max_health = 30
    p1.hero.damage = 0  # 30 health -> above 20
    enemy = p2.summon("CS2_172")  # Bloodfen Raptor 3/2
    spell = p1.give("VAC_417")
    spell.play(target=enemy)
    # A copy summoned on our side.
    copies = [m for m in p1.field if m.id == "CS2_172"]
    assert len(copies) == 1
    assert (copies[0].atk, copies[0].max_health) == (3, 2)
    # Original NOT destroyed (we have > 20 health).
    assert enemy in p2.field


def test_sensory_deprivation_destroys_original_at_low_health():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p1.hero.max_health = 30
    p1.hero.damage = 15  # 15 health -> 20 or less
    enemy = p2.summon("CS2_172")  # Bloodfen Raptor
    spell = p1.give("VAC_417")
    spell.play(target=enemy)
    copies = [m for m in p1.field if m.id == "CS2_172"]
    assert len(copies) == 1
    # Original destroyed.
    assert enemy not in p2.field
    assert enemy.zone == Zone.GRAVEYARD


# ---------------------------------------------------------------------------
# VAC_418 — Sauna Regular: Taunt. Costs (1) less for each time your hero
# has taken damage on your turn.
# ---------------------------------------------------------------------------
def test_sauna_regular_taunt():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    m = game.player1.summon("VAC_418")
    assert m.taunt


def test_sauna_regular_cost_reduction_per_hero_damage():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    card = p1.give("VAC_418")
    base = card.data.cost
    assert base == 5
    assert card.cost == 5  # no damage yet
    # Hero takes damage on our turn three times (1 each).
    p1.hero.max_health = 30
    for _ in range(3):
        game.queue_actions(p1.hero, [Hit(p1.hero, 1)])
    # "for each time your hero has taken damage" -> 3 instances -> -3.
    assert card.cost == base - 3


# ---------------------------------------------------------------------------
# VAC_419 — Acupuncture: Deal $4 damage to both heroes.
# ---------------------------------------------------------------------------
def test_acupuncture_hits_both_heroes():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p1.hero.max_health = 30
    p1.hero.damage = 0
    p2.hero.max_health = 30
    p2.hero.damage = 0
    spell = p1.give("VAC_419")
    spell.play()
    assert p1.hero.damage == 4
    assert p2.hero.damage == 4


# ---------------------------------------------------------------------------
# VAC_420 — Narain Soothfancy: Battlecry: Get two Fortunes that are copies
# of the top card of your deck.  VAC_420t — Fortune: when played, copies and
# plays the top card of your deck for free.
# ---------------------------------------------------------------------------
def test_narain_gives_two_fortunes():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    narain = p1.give("VAC_420")
    narain.play()
    fortunes = [c for c in p1.hand if c.id == "VAC_420t"]
    assert len(fortunes) == 2


def test_fortune_plays_copy_of_top_deck_card():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    # Top of deck = a known minion. Fortune copies and plays it for free.
    top = p1.card("CS2_172")  # Bloodfen Raptor 3/2
    top.zone = Zone.DECK  # only card -> it's the top
    pre_field = len(p1.field)
    fortune = p1.give("VAC_420t")
    fortune.play()
    # A Bloodfen Raptor was summoned (the copy played for free).
    raptors = [m for m in p1.field if m.id == "CS2_172"]
    assert len(raptors) == 1
    # The deck's original copy is untouched (still in deck).
    assert top.zone == Zone.DECK


def test_fortune_empty_deck_does_nothing():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    assert len(p1.deck) == 0
    fortune = p1.give("VAC_420t")
    fortune.play()
    assert len(p1.field) == 0


# ---------------------------------------------------------------------------
# VAC_423 — Twilight Medium: Taunt. Battlecry: Set the Cost of the top card
# of your deck to (1).
# ---------------------------------------------------------------------------
def test_twilight_medium_taunt():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    m = game.player1.summon("VAC_423")
    assert m.taunt


def test_twilight_medium_sets_top_deck_cost_to_one():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    top = p1.card("EX1_279")  # Pyroblast, base cost 10
    top.zone = Zone.DECK
    assert top.cost == 10
    medium = p1.give("VAC_423")
    medium.play()
    assert top.cost == 1


# ---------------------------------------------------------------------------
# VAC_457 — Rest in Peace: Each player summons their highest Cost minion
# that died this game.
# ---------------------------------------------------------------------------
def test_rest_in_peace_summons_highest_cost_dead_each_player():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    # p1: a cheap (1-cost) and an expensive (6-cost) minion both die. Only
    # the 6-cost should be resurrected.
    cheap = p1.summon("CS2_171")    # Stonetusk Boar, cost 1
    pricey = p1.summon("AT_008")    # Coldarra Drake, cost 6
    cheap.destroy()
    pricey.destroy()
    # p2: only a 2-cost dies.
    foe = p2.summon("CS2_172")      # Bloodfen Raptor, cost 2
    foe.destroy()
    game.process_deaths()
    spell = p1.give("VAC_457")
    spell.play()
    # p1 gets back the 6-cost Coldarra Drake (not the 1-cost boar).
    p1_ids = [m.id for m in p1.field]
    assert "AT_008" in p1_ids
    assert "CS2_171" not in p1_ids
    # p2 gets back its only dead minion.
    assert "CS2_172" in [m.id for m in p2.field]


# ---------------------------------------------------------------------------
# VAC_512 — Brain Masseuse: Whenever this minion takes damage, also deal
# that amount to your hero.
# ---------------------------------------------------------------------------
def test_brain_masseuse_mirrors_damage_to_own_hero():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0
    masseuse = p1.summon("VAC_512")  # 2/4
    masseuse.max_health = 40
    masseuse.damage = 0
    game.queue_actions(p1.hero, [Hit(masseuse, 3)])
    # Minion took 3 -> hero also takes 3.
    assert masseuse.damage == 3
    assert p1.hero.damage == 3


# ---------------------------------------------------------------------------
# VAC_957 — Chillin' Vol'jin: Hunter Tourist. Battlecry: Choose 2 minions.
# Swap their stats.
# ---------------------------------------------------------------------------
def test_voljin_swaps_two_minion_stats():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    a = p1.summon("CS2_172")  # Bloodfen Raptor 3/2
    b = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    assert (a.atk, a.max_health) == (3, 2)
    assert (b.atk, b.max_health) == (4, 5)
    voljin = p1.give("VAC_957")
    # Pre-stamp the second pick so the choice UI is skipped (per impl).
    voljin._voljinB = b
    voljin.play(target=a)
    # Stats swapped: a takes b's 4/5, b takes a's 3/2.
    assert (a.atk, a.max_health) == (4, 5)
    assert (b.atk, b.max_health) == (3, 2)


def test_voljin_unlocks_hunter_tourist_deck():
    # Deckbuilding: a Priest deck built with the Hunter Tourist may include
    # Hunter cards and contains a Tourist card.
    deck = random_draft(CardClass.PRIEST, tourist=CardClass.HUNTER)
    has_hunter = False
    for cid in deck:
        cdata = _cards.db[cid]
        classes = list(getattr(cdata, "classes", None) or [cdata.card_class])
        if CardClass.HUNTER in classes and CardClass.PRIEST not in classes:
            has_hunter = True
            break
    assert has_hunter
    # A matching Hunter-unlocking Tourist card is present in the deck
    # (for Priest, that is Chillin' Vol'jin, VAC_957).
    has_tourist = any(
        tourist_class_of(_cards.db[cid]) == CardClass.HUNTER for cid in deck
    )
    assert has_tourist


# VAC_418 Sauna Regular (Tier-2): costs (1) less per damage EVENT on your turn.
def test_sauna_regular_cost_per_damage_event():
    from fireplace.actions import Hit
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p = game.player1
    sauna = p.give("VAC_418")
    assert sauna.cost == 5
    # Two separate 1-damage events to our own hero on our turn -> -2 (not -1
    # per point; a single 2-damage hit would also be one event).
    game.queue_actions(p.hero, [Hit(p.hero, 1)])
    game.queue_actions(p.hero, [Hit(p.hero, 1)])
    assert sauna.cost == 3


# VAC_420t Fortune (Tier-2): playing a minion Fortune fires its battlecry.
def test_fortune_fires_minion_battlecry():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p = game.player1
    # Deck (bottom->top): a Wisp, then Novice Engineer on top.
    p.card("CS2_231").zone = Zone.DECK
    p.card("EX1_015").zone = Zone.DECK  # Novice Engineer = top (battlecry: draw)
    pre_deck = len(p.deck)
    fortune = p.give("VAC_420t")
    fortune.play()
    # Fortune copied + played the Novice Engineer; its battlecry drew a card.
    assert any(m.id == "EX1_015" for m in p.field)
    assert len(p.deck) == pre_deck - 1
