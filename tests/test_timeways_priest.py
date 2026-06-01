from hearthstone.enums import GameTag, Zone

from utils import prepare_game, CardClass


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# TIME_037 Disciple of the Dove — Battlecry: Draw a minion. Give minions in
# your hand +2 Health.
def test_disciple_of_the_dove():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.discard_hand()
    # Clear the deck, then seed exactly one minion so the draw is deterministic.
    for c in list(game.player1.deck):
        c.discard()
    deck_minion = game.player1.give("CS2_182")  # Chillwind Yeti (4/5)
    deck_minion.zone = Zone.DECK
    # A minion already in hand to receive the +2 Health buff.
    hand_minion = game.player1.give("CS2_182")  # 4/5
    base_health = hand_minion.health
    disciple = game.player1.give("TIME_037")
    disciple.play()
    # Drew the deck minion into hand.
    assert deck_minion.zone == Zone.HAND
    # Both minions in hand got +2 Health (including the freshly drawn one).
    assert hand_minion.health == base_health + 2
    assert deck_minion.health == deck_minion.data.health + 2


# TIME_427 Cleansing Lightspawn — Lifesteal. Battlecry: Deal damage to an enemy
# minion equal to this minion's Health (3).
def test_cleansing_lightspawn():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player2.field):
        m.destroy()
    # One beefy enemy minion to absorb the damage exactly.
    target = game.player2.summon("CS2_182")  # 4/5
    target.max_health = 20
    target.damage = 0
    # Damage our hero so we can observe the Lifesteal heal.
    game.player1.hero.max_health = 30
    game.player1.hero.damage = 10
    lightspawn = game.player1.give("TIME_427")
    lightspawn.play()
    # Deals damage equal to its Health (3).
    assert target.damage == 3
    # Lifesteal: hero healed by 3 (10 -> 7 damage).
    assert game.player1.hero.damage == 7


# TIME_429 Divine Augur — Battlecry: Set the Attack and Health of every minion
# in your hand to the higher of the two stats.
def test_divine_augur():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.discard_hand()
    # 4/5 Yeti: higher is 5 -> becomes 5/5.
    yeti = game.player1.give("CS2_182")
    # 6/7 War Golem: higher is 7 -> becomes 7/7.
    golem = game.player1.give("CS2_186")
    augur = game.player1.give("TIME_429")
    augur.play()
    assert yeti.atk == 5 and yeti.health == 5
    assert golem.atk == 7 and golem.health == 7


# TIME_431 Amber Priestess — Taunt. Battlecry: Restore Health to a character
# equal to this minion's Health (4).
def test_amber_priestess():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.hero.max_health = 30
    game.player1.hero.damage = 10
    priestess = game.player1.give("TIME_431")
    priestess.play()
    assert priestess.taunt
    # Heals the friendly hero by its Health (4): 10 -> 6 damage.
    assert game.player1.hero.damage == 6


# TIME_435 Eternus — Battlecry: Take control of an enemy minion with this
# minion's Health (2) or less.
def test_eternus_steals_eligible():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player2.field):
        m.destroy()
    # Only one enemy minion, with Health 1 (<= Eternus Health 2).
    victim = game.player2.summon("EX1_011")  # Voodoo Doctor 2/1 -> health 1
    pre = len(game.player1.field)
    eternus = game.player1.give("TIME_435")
    eternus.play()
    # Took control: victim is now on our board.
    assert victim.controller is game.player1
    assert victim in game.player1.field
    assert len(game.player1.field) == pre + 2  # Eternus + stolen minion


def test_eternus_ignores_too_healthy():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player2.field):
        m.destroy()
    # One enemy minion with Health 7 (> Eternus Health 2) -> not stolen.
    big = game.player2.summon("CS2_186")  # War Golem 7/7
    eternus = game.player1.give("TIME_435")
    eternus.play()
    assert big.controller is game.player2
    assert big in game.player2.field


# TIME_432 Intertwined Fate — Discover a copy of a card from your deck and one
# from your opponent's.
def test_intertwined_fate():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.discard_hand()
    # Stack each deck with a single known card so the Discover pools are
    # deterministic.
    for c in list(game.player1.deck):
        c.discard()
    for c in list(game.player2.deck):
        c.discard()
    mine = game.player1.give("CS2_182")
    mine.zone = Zone.DECK
    theirs = game.player2.give("CS2_186")
    theirs.zone = Zone.DECK
    pre_hand = len(game.player1.hand)
    spell = game.player1.give("TIME_432")
    spell.play()
    # First choice: a copy from our own deck.
    assert game.player1.choice
    first = game.player1.choice.cards[0]
    assert first.id == "CS2_182"
    game.player1.choice.choose(first)
    # Second choice: a copy from the opponent's deck.
    assert game.player1.choice
    second = game.player1.choice.cards[0]
    assert second.id == "CS2_186"
    game.player1.choice.choose(second)
    assert game.player1.choice is None
    assert len(game.player1.hand) == pre_hand + 2
    assert any(c.id == "CS2_182" for c in game.player1.hand)
    assert any(c.id == "CS2_186" for c in game.player1.hand)


# TIME_433 Cease to Exist — Rewind. Silence and destroy a random enemy minion.
def test_cease_to_exist_base():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player2.field):
        m.destroy()
    victim = game.player2.summon("CS2_182")
    spell = game.player1.give("TIME_433")
    spell.play()
    # Decline Rewind (Keep Timeline = first option).
    assert game.player1.choice
    game.player1.choice.choose(game.player1.choice.cards[0])
    assert game.player1.choice is None
    assert victim.zone == Zone.GRAVEYARD


def test_cease_to_exist_rewind():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player2.field):
        m.destroy()
    v1 = game.player2.summon("CS2_182")
    v2 = game.player2.summon("CS2_186")
    spell = game.player1.give("TIME_433")
    spell.play()
    # Pick Rewind (TIME_000tb = second token) to re-run the effect once.
    assert game.player1.choice
    rewind = game.player1.choice.cards[1]
    assert rewind.id == "TIME_000tb"
    game.player1.choice.choose(rewind)
    _resolve_choices(game.player1)
    # Both enemy minions destroyed (effect ran twice on a 2-minion board).
    assert v1.zone == Zone.GRAVEYARD
    assert v2.zone == Zone.GRAVEYARD


# TIME_447 Power Word: Barrier — Give a character Divine Shield. Give minions in
# your hand +2 Health.
def test_power_word_barrier():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.discard_hand()
    shielded = game.player1.summon("CS2_182")  # on board, receives Divine Shield
    hand_minion = game.player1.give("CS2_182")  # in hand, receives +2 Health
    base_health = hand_minion.health
    barrier = game.player1.give("TIME_447")
    barrier.play(target=shielded)
    assert shielded.divine_shield
    assert hand_minion.health == base_health + 2


# TIME_890 Medivh the Hallowed — Battlecry: Silence and destroy all other
# minions. Costs (0) if you control Karazhan.
def test_medivh_destroys_all_other():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player1.field):
        m.destroy()
    for m in list(game.player2.field):
        m.destroy()
    friendly = game.player1.summon("CS2_182")
    enemy = game.player2.summon("CS2_186")
    medivh = game.player1.give("TIME_890")
    medivh.play()
    assert friendly.zone == Zone.GRAVEYARD
    assert enemy.zone == Zone.GRAVEYARD
    # Medivh himself survives.
    assert medivh.zone == Zone.PLAY


def test_medivh_costs_zero_with_karazhan():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    medivh = game.player1.give("TIME_890")
    assert medivh.cost == 10
    # Drop Karazhan onto the board (location slot).
    karazhan = game.player1.summon("TIME_890t2")
    assert medivh.cost == 0


# TIME_890t Atiesh the Greatstaff — Double the damage and healing of your
# spells. Costs (0) if you control Medivh.
def test_atiesh_doubles_spells():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    atiesh = game.player1.give("TIME_890t")
    atiesh.play()
    assert game.player1.hero.weapon is atiesh
    game.player1.used_mana = 0  # refill mana after the (10-cost) equip
    for m in list(game.player2.field):
        m.destroy()
    target = game.player2.summon("CS2_186")  # War Golem 7/7
    target.max_health = 40
    target.damage = 0
    # Holy Smite deals 3 -> doubled to 6 with Atiesh equipped.
    smite = game.player1.give("CS1_130")
    smite.play(target=target)
    assert target.damage == 6


def test_atiesh_costs_zero_with_medivh():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    atiesh = game.player1.give("TIME_890t")
    assert atiesh.cost == 10
    game.player1.summon("TIME_890")
    assert atiesh.cost == 0


# TIME_890t2 Karazhan the Sanctum — Summon two random 8-Cost minions. Costs (0)
# if you're wielding Atiesh.
def test_karazhan_summons_two_eights():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player1.field):
        m.destroy()
    karazhan = game.player1.give("TIME_890t2")
    karazhan.play()
    pre = len(game.player1.field)
    karazhan.turn_played = -5  # bypass first-turn cooldown
    karazhan.cooldown = 0
    karazhan.use()
    summoned = game.player1.field[pre:]
    assert len(summoned) == 2
    assert all(m.cost == 8 for m in summoned)


def test_karazhan_costs_zero_with_atiesh():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    karazhan = game.player1.give("TIME_890t2")
    assert karazhan.cost == 10
    atiesh = game.player1.give("TIME_890t")
    atiesh.play()  # equip
    assert karazhan.cost == 0


# TIME_436 Past Conflux — Summon a random Dragon that costs (5) or more, then
# advance to Present Conflux.
def test_past_conflux_summons_dragon_and_advances():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player1.field):
        m.destroy()
    conflux = game.player1.give("TIME_436")
    conflux.play()
    pre = len(game.player1.field)
    conflux.turn_played = -5
    conflux.cooldown = 0
    conflux.use()
    summoned = game.player1.field[pre:]
    assert len(summoned) == 1
    dragon = summoned[0]
    assert dragon.race == dragon.race  # sanity
    from hearthstone.enums import Race

    assert Race.DRAGON in (dragon.races or [dragon.race])
    assert dragon.data.cost >= 5
    # Advanced to Present Conflux (the location morphed).
    assert game.player1.location is not None
    assert game.player1.location.id == "TIME_436t1"


# TIME_436t1 Present Conflux — Discover a Dragon that costs (5)+ and summon it,
# then advance to Future Conflux.
def test_present_conflux_discovers_and_summons():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player1.field):
        m.destroy()
    present = game.player1.summon("TIME_436t1")
    pre = len(game.player1.field)
    present.turn_played = -5
    present.cooldown = 0
    present.use()
    # Discover choice over big Dragons.
    assert game.player1.choice
    chosen = game.player1.choice.cards[0]
    assert chosen.data.cost >= 5
    game.player1.choice.choose(chosen)
    _resolve_choices(game.player1)
    summoned = game.player1.field[pre:]
    assert len(summoned) == 1
    assert summoned[0].id == chosen.id
    assert summoned[0].data.cost >= 5
    # Advanced to Future Conflux.
    assert game.player1.location is not None
    assert game.player1.location.id == "TIME_436t2"


# TIME_436t2 Future Conflux — Discover a Dragon that costs (5)+, summon it, and
# also get a copy of it.
def test_future_conflux_summons_and_copies():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    for m in list(game.player1.field):
        m.destroy()
    game.player1.discard_hand()
    future = game.player1.summon("TIME_436t2")
    pre_field = len(game.player1.field)
    pre_hand = len(game.player1.hand)
    future.turn_played = -5
    future.cooldown = 0
    future.use()
    assert game.player1.choice
    chosen = game.player1.choice.cards[0]
    game.player1.choice.choose(chosen)
    _resolve_choices(game.player1)
    summoned = game.player1.field[pre_field:]
    assert len(summoned) == 1
    assert summoned[0].id == chosen.id
    # Also got a copy of the Dragon in hand.
    assert len(game.player1.hand) == pre_hand + 1
    assert any(c.id == chosen.id for c in game.player1.hand)
