"""Across the Timeways — Hunter (TIME_) unit tests."""

from hearthstone.enums import CardClass, CardType, GameTag, Race, Zone
from utils import prepare_game


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def test_king_maluk_discards_hand_and_gives_banana():
    """TIME_042 King Maluk — Battlecry: Discard your hand. Get an Infinite
    Banana."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    # Stuff the hand with known cards so we can prove the discard.
    p.discard_hand()
    for _ in range(3):
        p.give("CS2_122")  # Raid Leader, vanilla-ish filler
    maluk = p.give("TIME_042")
    assert len(p.hand) == 4  # 3 filler + Maluk
    maluk.play()
    # Hand was discarded; only the freshly-given Infinite Banana remains.
    assert len(p.hand) == 1
    assert p.hand[0].id == "TIME_042t"


def test_infinite_banana_buffs_and_returns():
    """TIME_042t Infinite Banana — Give a minion +1/+1; stays in your hand."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    target = p.summon("CS2_182")  # Chillwind Yeti 4/5
    banana = p.give("TIME_042t")
    banana.play(target=target)
    assert target.atk == 5
    assert target.health == 6
    # A fresh copy returned to hand.
    assert len(p.hand) == 1
    assert p.hand[0].id == "TIME_042t"


def _precise_shot_setup(game):
    """Beefy enemy target so 3 vs 5 damage is unambiguous; empty caster hand."""
    p = game.player1
    p.discard_hand()
    target = game.player2.summon("CS2_182")  # Chillwind Yeti
    target.max_health = 20
    target.damage = 0
    return p, target


def _give_hand(p, *, center_at, size):
    """Fill p's hand with `size` cards, Precise Shot at index `center_at`.

    Returns the Precise Shot card. Order of give() determines hand index, so
    we give `center_at` filler, then the shot, then the rest.
    """
    for _ in range(center_at):
        p.give("CS2_122")  # Raid Leader filler
    shot = p.give("TIME_600")
    for _ in range(size - center_at - 1):
        p.give("CS2_122")
    assert len(p.hand) == size
    assert p.hand.index(shot) == center_at
    return shot


def test_precise_shot_five_card_dead_center():
    """TIME_600 — 5-card hand, shot at index 2 (dead center) → 5 damage.

    This is the case the old left/right-edge heuristic got wrong (it could
    only detect center for hand sizes 1 and 3).
    """
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p, target = _precise_shot_setup(game)
    shot = _give_hand(p, center_at=2, size=5)
    shot.play(target=target)
    assert target.damage == 5


def test_precise_shot_five_card_off_center_index0():
    """TIME_600 — 5-card hand, shot at index 0 (leftmost) → 3 damage."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p, target = _precise_shot_setup(game)
    shot = _give_hand(p, center_at=0, size=5)
    shot.play(target=target)
    assert target.damage == 3


def test_precise_shot_five_card_off_center_index1():
    """TIME_600 — 5-card hand, shot at index 1 (just left of center) → 3."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p, target = _precise_shot_setup(game)
    shot = _give_hand(p, center_at=1, size=5)
    shot.play(target=target)
    assert target.damage == 3


def test_precise_shot_three_card_center():
    """TIME_600 — 3-card hand, shot at index 1 (center) → 5 damage."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p, target = _precise_shot_setup(game)
    shot = _give_hand(p, center_at=1, size=3)
    shot.play(target=target)
    assert target.damage == 5


def test_precise_shot_single_card_is_center():
    """TIME_600 — sole card in hand (size 1) is its own center → 5 damage."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p, target = _precise_shot_setup(game)
    shot = _give_hand(p, center_at=0, size=1)
    shot.play(target=target)
    assert target.damage == 5


def test_precise_shot_even_hand_no_center():
    """TIME_600 — even hand (4 cards) has no exact center → 3 damage."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p, target = _precise_shot_setup(game)
    # index 2 of 4 is as close to center as any slot, but even hands never
    # have an exact center.
    shot = _give_hand(p, center_at=2, size=4)
    shot.play(target=target)
    assert target.damage == 3


def test_arrow_retriever_draws_until_three():
    """TIME_601 Arrow Retriever — Battlecry: Draw until you have 3 cards."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    p.give("CS2_122")  # 1 card in hand before battlecry
    retriever = p.give("TIME_601")  # 2 cards now
    assert len(p.hand) == 2
    retriever.play()  # leaves 1 card in hand, then draws up to 3
    assert len(p.hand) == 3


def test_ticking_timebomb_destroys_random_enemy():
    """TIME_603 Ticking Timebomb — Deathrattle: Destroy a random enemy
    minion."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    bomb = game.player1.summon("TIME_603")
    victim = game.player2.summon("CS2_182")  # only enemy minion
    bomb.destroy()
    assert victim.zone == Zone.GRAVEYARD


def test_ticking_timebomb_no_enemy_minions():
    """TIME_603 — Deathrattle is a no-op (no crash) with no enemy minions."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    bomb = game.player1.summon("TIME_603")
    bomb.destroy()
    assert bomb.zone == Zone.GRAVEYARD


def test_epoch_stalker_summons_copy():
    """TIME_605 Epoch Stalker — Battlecry: Summon a copy of this."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    stalker = p.give("TIME_605")
    stalker.play()
    stalkers = [m for m in p.field if m.id == "TIME_605"]
    assert len(stalkers) == 2
    assert all(m.rush for m in stalkers)


def test_queldorei_fletcher_zeroes_hero_power():
    """TIME_606 Quel'dorei Fletcher — Hero Power costs (0) while hand <= 3."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    p.summon("TIME_606")
    # Hand empty (<=3) → hero power cost 0.
    assert p.hero.power.cost == 0
    # Fill hand above 3 → cost reverts to 2.
    for _ in range(4):
        p.give("CS2_122")
    assert len(p.hand) == 4
    assert p.hero.power.cost == 2


def test_wormhole_summons_beast_and_attacks():
    """TIME_602 Wormhole — Summon a random 3-Cost Beast; it attacks a random
    enemy. Seeded so the rolled beast (TLC_469, 4/3) survives, lets us assert
    the summon AND that its full Attack landed on some enemy character."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    enemy = game.player2.summon("CS2_182")  # 4/5; beef up so it can't die
    enemy.max_health = 40
    enemy.damage = 0
    game.random.seed(1)
    wormhole = p.give("TIME_602")
    wormhole.play()
    # Choose Keep Timeline so the effect runs exactly once.
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    beasts = list(p.field)
    assert len(beasts) == 1
    beast = beasts[0]
    assert beast.cost == 3
    assert Race.BEAST in beast.races
    # Exactly the beast's Attack was dealt to a single random enemy character
    # (either the minion or the hero) — no more, no less.
    dealt = enemy.damage + (30 - game.player2.hero.health)
    assert dealt == beast.atk


def test_wormhole_rewind_runs_effect_twice():
    """TIME_602 Wormhole — picking Rewind Timeline re-runs the play effect once,
    summoning a SECOND 3-Cost Beast."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    enemy = game.player2.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    wormhole = p.give("TIME_602")
    wormhole.play()
    # The engine offers the Rewind choice: [Keep (TIME_000ta), Rewind (TIME_000tb)].
    assert p.choice is not None
    rewind_token = p.choice.cards[1]
    assert rewind_token.id == "TIME_000tb"
    p.choice.choose(rewind_token)
    # No further choices expected.
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    # Two 3-Cost Beasts now summoned (one per effect run); some may have died to
    # retaliation, so count beasts across board + graveyard.
    summoned = [
        c
        for c in list(p.field) + list(p.graveyard)
        if c.type == CardType.MINION and Race.BEAST in c.races and c.cost == 3
    ]
    assert len(summoned) == 2


def test_untimely_death_resummons_next_turn_death():
    """TIME_620 Untimely Death — Secret: a friendly minion that dies the turn
    after being played is resummoned."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    secret = p.give("TIME_620")
    secret.play()
    assert secret.zone == Zone.SECRET
    minion = p.give("CS2_182")  # Chillwind Yeti 4/5
    minion.play()
    # Advance to the next turn so the minion dies the turn AFTER it was played.
    game.end_turn()
    minion.destroy()
    # Secret fired: a fresh copy was resummoned, secret consumed.
    assert secret.zone == Zone.GRAVEYARD
    copies = [m for m in p.field if m.id == "CS2_182"]
    assert len(copies) == 1
    assert copies[0] is not minion


def test_untimely_death_same_turn_death_does_not_fire():
    """TIME_620 — a minion that dies the SAME turn it was played is NOT
    resummoned (secret stays armed)."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    secret = p.give("TIME_620")
    secret.play()
    minion = p.summon("CS2_182")
    minion.destroy()  # dies same turn it entered play
    assert secret.zone == Zone.SECRET
    assert not [m for m in p.field if m.id == "CS2_182"]


def test_sylvanas_solo_hits_all_enemies():
    """TIME_609 Ranger General Sylvanas — Battlecry: Deal 2 to all enemies
    (no sisters played → once)."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p2 = game.player2
    e1 = p2.summon("CS2_182")  # 4/5
    e2 = p2.summon("CS2_182")
    p.give("TIME_609").play()
    assert e1.damage == 2
    assert e2.damage == 2
    assert p2.hero.health == 28


def test_sylvanas_repeats_per_sister_played():
    """TIME_609 — if Alleria/Vereesa already played this game, repeat for
    each. Two sisters played → Sylvanas fires 3x = 6 damage."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p2 = game.player2
    # Play Alleria and Vereesa first (from hand so they enter the history).
    alleria = p.give("TIME_609t1")
    alleria.play()
    _resolve_choices(p)
    vereesa = p.give("TIME_609t2")
    vereesa.play()
    enemy = p2.summon("CS2_182")
    enemy.max_health = 40
    enemy.damage = 0
    p.give("TIME_609").play()
    # 1 base + 1 (Alleria) + 1 (Vereesa) = 3 casts of 2 damage = 6.
    assert enemy.damage == 6


def test_alleria_discovers_spell():
    """TIME_609t1 Ranger Captain Alleria — Battlecry: Discover a spell."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    p.give("TIME_609t1").play()
    assert p.choice is not None
    assert all(c.type == CardType.SPELL for c in p.choice.cards)
    p.choice.choose(p.choice.cards[0])
    assert len(p.hand) == 1
    assert p.hand[0].type == CardType.SPELL


def test_vereesa_buffs_deck_minions():
    """TIME_609t2 Ranger Initiate Vereesa — Battlecry: Give minions in your
    deck +1/+1."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    deck_minion = p.give("CS2_182")  # 4/5
    deck_minion.shuffle_into_deck()
    base_atk = deck_minion.atk
    base_health = deck_minion.health
    p.give("TIME_609t2").play()
    assert deck_minion.atk == base_atk + 1
    assert deck_minion.health == base_health + 1


def test_past_silvermoon_damages_and_advances():
    """TIME_810 Past Silvermoon — Deal 5 to a random enemy minion, then
    advance to Present Silvermoon."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    enemy = game.player2.summon("CS2_182")  # 4/5
    enemy.max_health = 20
    enemy.damage = 0
    loc = p.give("TIME_810")
    loc.play()
    game.end_turn(); game.end_turn()  # clear exhaustion
    loc.use()
    assert enemy.damage == 5
    # Advanced: the controller's location is now Present Silvermoon.
    assert p.location is not None
    assert p.location.id == "TIME_810t1"


def test_present_silvermoon_excess_to_face_and_advances():
    """TIME_810t1 Present Silvermoon — Deal 5 to a random enemy minion; excess
    hits the enemy hero; then advance to Future Silvermoon."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    enemy = game.player2.summon("CS2_182")  # 4/5 → 5 dmg kills, 0 excess
    weak = game.player2.summon("CS2_182")
    weak.max_health = 2  # if targeted, 3 excess to face
    # Force determinism: only one enemy minion.
    weak.destroy()
    loc = p.summon("TIME_810t1")
    game.end_turn(); game.end_turn()
    loc.use()
    # 5 damage to a 5-health minion → 0 excess to face.
    assert game.player2.hero.health == 30
    assert p.location.id == "TIME_810t2"


def test_present_silvermoon_overkill_splashes_face():
    """TIME_810t1 — excess over the minion's health hits the enemy hero."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    enemy = game.player2.summon("CS2_182")
    enemy.max_health = 2  # 5 - 2 = 3 excess to face
    enemy.damage = 0
    loc = p.summon("TIME_810t1")
    game.end_turn(); game.end_turn()
    loc.use()
    assert enemy.zone == Zone.GRAVEYARD
    assert game.player2.hero.health == 27


def test_future_silvermoon_hits_lowest_health():
    """TIME_810t2 Future Silvermoon — Deal 5 to the lowest-Health enemy
    minion; excess hits the enemy hero."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    big = game.player2.summon("CS2_182")  # 4/5
    big.max_health = 10
    big.damage = 0
    small = game.player2.summon("CS2_182")
    small.max_health = 2  # lowest health → targeted; 3 excess to face
    small.damage = 0
    loc = p.summon("TIME_810t2")
    game.end_turn(); game.end_turn()
    loc.use()
    assert small.zone == Zone.GRAVEYARD
    assert big.damage == 0  # the big minion was untouched
    assert game.player2.hero.health == 27


# ---------------------------------------------------------------------------
# END_ — Across the Timeways mini-set ("End Time")
# ---------------------------------------------------------------------------

BEAST = "CS2_172"  # Bloodfen Raptor (3/2 Beast)


def _arm_kindred_beast(game, p):
    """Play a Beast last turn so a Beast card's Kindred is active this turn."""
    p.give(BEAST).play()
    game.end_turn(); game.end_turn()
    assert Race.BEAST in p.races_played_last_turn
    for m in list(p.field):
        m.destroy()
    game.process_deaths()


def test_triennium_rex_deathrattle_gets_discounted_deathrattle_minion():
    """END_015 Triennium Rex — Deathrattle: Get a random Deathrattle minion,
    costing (2) less."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    game.random.seed(1)
    rex = p.summon("END_015")
    rex.destroy()
    assert len(p.hand) == 1
    got = p.hand[0]
    # The fetched minion is itself a Deathrattle minion.
    assert got.type == CardType.MINION
    assert got.data.deathrattle
    # It costs (2) less than its printed cost (floored at 0).
    assert got.cost == max(0, got.data.cost - 2)


def test_triennium_rex_kindred_play_gets_discounted_deathrattle_minion():
    """END_015 — Kindred (Beast played last turn): the play also fetches a
    discounted Deathrattle minion."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    _arm_kindred_beast(game, p)
    p.discard_hand()  # clear cards drawn during the turn-cycle
    game.random.seed(2)
    rex = p.give("END_015")
    rex.play()
    # Kindred active on play → exactly one fetched minion in hand.
    assert len(p.hand) == 1
    got = p.hand[0]
    assert got.type == CardType.MINION
    assert got.data.deathrattle
    assert got.cost == max(0, got.data.cost - 2)


def test_triennium_rex_no_kindred_play_fetches_nothing():
    """END_015 — without Kindred active, the play effect does nothing
    (Deathrattle still pending on the board)."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    assert Race.BEAST not in p.races_played_last_turn
    rex = p.give("END_015")
    rex.play()
    # No Kindred → nothing fetched on play.
    assert len(p.hand) == 0
    assert rex.zone == Zone.PLAY


def test_triennium_rex_discount_floors_at_zero():
    """END_015 — the (2)-less discount never drops a fetched minion's cost
    below 0."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    p.discard_hand()
    game.random.seed(1)
    rex = p.summon("END_015")
    rex.destroy()
    got = p.hand[0]
    assert got.cost >= 0
