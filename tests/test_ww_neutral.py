from utils import *


# TOY_000 Tar Slime — 1/0/3 Taunt; Has +2 Attack during your opponent's turn.
def test_tar_slime():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    slime = game.player1.summon("TOY_000")
    assert slime.taunt
    # player1's (own) turn -> base attack 0
    assert game.current_player is game.player1
    assert slime.atk == 0
    game.end_turn()  # now player2's (opponent's) turn
    assert game.current_player is game.player2
    assert slime.atk == 2
    game.end_turn()  # back to player1's turn
    assert slime.atk == 0


# TOY_006 Scarab Keychain — Battlecry: Discover a 2-Cost card.
def test_scarab_keychain():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    pre_hand = len(game.player1.hand)
    card = game.player1.give("TOY_006")
    card.play()
    assert game.player1.choice
    # All discover options must be 2-cost cards.
    for option in game.player1.choice.cards:
        assert option.cost == 2
    chosen = game.player1.choice.cards[0]
    game.player1.choice.choose(chosen)
    # Keychain on board + chosen card in hand. Hand: started pre_hand, gave +1,
    # played -1, discovered +1 = pre_hand + 1.
    assert len(game.player1.hand) == pre_hand + 1
    assert chosen.id in [c.id for c in game.player1.hand]


# TOY_054 Card Grader — Battlecry: If you've cast a spell while holding this,
# Discover a card from your deck.
def test_card_grader_no_spell_no_discover():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    card = game.player1.give("TOY_054")
    card.play()
    # No spell cast while holding -> no Discover window opens.
    assert not game.player1.choice


def test_card_grader_after_spell_discovers_from_deck():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    grader = game.player1.give("TOY_054")
    # Empty the deck, then seed it with a single known card so the Discover
    # window is deterministic.
    for c in list(game.player1.deck):
        c.zone = Zone.SETASIDE
    deck_card = game.player1.give("CS2_172")  # Bloodfen Raptor
    deck_card.zone = Zone.DECK
    # Cast a spell while holding the Grader.
    spell = game.player1.give(MOONFIRE)
    spell.play(target=game.player1.hero)
    assert grader.spells_cast_while_holding == 1
    grader.play()
    assert game.player1.choice
    # Only card-id in the deck is CS2_172.
    assert [c.id for c in game.player1.choice.cards] == ["CS2_172"]
    chosen = game.player1.choice.cards[0]
    game.player1.choice.choose(chosen)
    # The real card leaves the deck and enters hand.
    assert "CS2_172" in [c.id for c in game.player1.hand]
    assert "CS2_172" not in [c.id for c in game.player1.deck]


# TOY_307 Sweetened Snowflurry — 3/3/3 Miniaturize; Battlecry: Get 2 random
# temporary Frost spells.
def test_sweetened_snowflurry():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    # Seed RNG so the two random Frost spells are vanilla (don't auto-generate
    # extra cards on arrival), keeping the hand state exactly predictable.
    game.random.seed(0)
    for c in list(game.player1.hand):
        c.discard()
    card = game.player1.give("TOY_307")
    card.play()
    # Miniaturize adds the paired 1/1 Mini token (TOY_307t) to hand on play,
    # plus the battlecry grants exactly 2 temporary Frost spells.
    mini = [c for c in game.player1.hand if c.id == "TOY_307t"]
    assert len(mini) == 1
    assert not mini[0].temporary
    temp_spells = [c for c in game.player1.hand if c.temporary]
    assert len(temp_spells) == 2
    for c in temp_spells:
        assert c.spell_school == SpellSchool.FROST
    # End of turn: BOTH temporary Frost spells are discarded (one-turn cards).
    # The non-temporary Mini token (TOY_307t) survives.
    game.end_turn()
    assert temp_spells[0] not in game.player1.hand
    assert temp_spells[1] not in game.player1.hand
    assert [c for c in game.player1.hand if c.temporary] == []
    assert len([c for c in game.player1.hand if c.id == "TOY_307t"]) == 1
    # The non-temporary Mini token survives.
    assert len([c for c in game.player1.hand if c.id == "TOY_307t"]) == 1


# TOY_312 Nostalgic Gnome — 4/4 Rush; After this deals exact lethal damage on
# your turn, draw a card. (Honorable Kill)
def test_nostalgic_gnome_honorable_kill_draws():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    gnome = game.player1.give("TOY_312").play()  # 4/4
    game.end_turn()
    target = game.player2.summon(WISP)  # 1/1
    target.max_health = 4
    target.damage = 0  # exactly 4 health -> 4 dmg is exact lethal
    game.end_turn()  # back to player1; gnome no longer sick
    pre_hand = len(game.player1.hand)
    gnome.attack(target)
    assert target.dead
    assert len(game.player1.hand) == pre_hand + 1


def test_nostalgic_gnome_non_lethal_no_draw():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    gnome = game.player1.give("TOY_312").play()  # 4/4
    game.end_turn()
    target = game.player2.summon(WISP)
    target.max_health = 10
    target.damage = 0  # 4 dmg is not lethal
    game.end_turn()
    pre_hand = len(game.player1.hand)
    gnome.attack(target)
    assert not target.dead
    assert len(game.player1.hand) == pre_hand


# TOY_340 Nostalgic Initiate — 2/3 Miniaturize; The first time you cast a
# spell, gain +2/+2.
def test_nostalgic_initiate_first_spell_buffs_once():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    init = game.player1.summon("TOY_340")  # 2/3
    assert init.atk == 2 and init.health == 3
    spell1 = game.player1.give(MOONFIRE)
    spell1.play(target=game.player2.hero)
    assert init.atk == 4 and init.health == 5
    # Second spell should NOT buff again.
    spell2 = game.player1.give(MOONFIRE)
    spell2.play(target=game.player2.hero)
    assert init.atk == 4 and init.health == 5


# TOY_341 Nostalgic Clown — 6/5 Miniaturize; Battlecry: If you've played a
# higher Cost card while holding this, deal 4 damage.
def test_nostalgic_clown_no_higher_cost_no_damage():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    clown = game.player1.give("TOY_341")  # cost 5
    target = game.player2.summon(WISP)
    target.max_health = 20
    target.damage = 0
    clown.play(target=target)
    # No higher-cost card played while holding -> no damage.
    assert target.damage == 0


def test_nostalgic_clown_higher_cost_deals_4():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    clown = game.player1.give("TOY_341")  # cost 5
    # Play a higher-cost card (Pyroblast = cost 10) while holding the Clown.
    big = game.player1.give(PYROBLAST)  # cost 10 > 5
    big.play(target=game.player2.hero)
    assert clown._higher_cost_played == 1
    game.player1.used_mana = 0  # refund so the Clown is affordable
    target = game.player2.summon(WISP)
    target.max_health = 20
    target.damage = 0
    clown.play(target=target)
    assert target.damage == 4


def test_nostalgic_clown_lower_cost_no_trigger():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    clown = game.player1.give("TOY_341")  # cost 5
    small = game.player1.give(MOONFIRE)  # cost 0 < 5
    small.play(target=game.player2.hero)
    assert getattr(clown, "_higher_cost_played", 0) == 0
    target = game.player2.summon(WISP)
    target.max_health = 20
    target.damage = 0
    clown.play(target=target)
    assert target.damage == 0


# TOY_386 Giftwrapped Whelp — 2/1 Battlecry: If you're holding a Dragon, give
# it and this minion +1/+1.
def test_giftwrapped_whelp_with_dragon():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    for c in list(game.player1.hand):
        c.discard()
    whelp = game.player1.give("TOY_386")  # 2/1
    dragon = game.player1.give(WHELP)  # ds1_whelptoken is a Dragon 1/1
    assert dragon.race == Race.DRAGON
    whelp.play()
    # Whelp gains +1/+1 -> 3/2
    assert whelp.atk == 3 and whelp.health == 2
    # The held dragon gains +1/+1 -> 2/2
    assert dragon.atk == 2 and dragon.health == 2


def test_giftwrapped_whelp_no_dragon():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    for c in list(game.player1.hand):
        c.discard()
    whelp = game.player1.give("TOY_386")  # 2/1
    whelp.play()
    # No dragon held -> no buff (stays 2/1).
    assert whelp.atk == 2 and whelp.health == 1


# TOY_390 Clearance Promoter — 3/2 Deathrattle: Reduce the Cost of two spells
# in your hand by (1).
def test_clearance_promoter_reduces_two_spells():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    for c in list(game.player1.hand):
        c.discard()
    promoter = game.player1.summon("TOY_390")
    s1 = game.player1.give(FIREBALL)  # cost 4
    s2 = game.player1.give(PYROBLAST)  # cost 10
    assert s1.cost == 4 and s2.cost == 10
    promoter.destroy()
    game.process_deaths()
    assert s1.cost == 3 and s2.cost == 9


# TOY_391 Caricature Artist — 3/4 Battlecry: Draw a minion that costs (5) or
# more. Give it a funny mustache (cosmetic).
def test_caricature_artist_draws_costly_minion():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    # Empty the deck, then seed it with a single 5+ minion plus low-cost noise
    # so the only valid draw target is the costly minion.
    for c in list(game.player1.deck):
        c.zone = Zone.SETASIDE
    noise = game.player1.give(WISP)  # 0-cost minion (not a 5+ target)
    noise.zone = Zone.DECK
    target_minion = game.player1.give("CS2_186")  # War Golem 7/7/7 cost 7
    target_minion.zone = Zone.DECK
    art = game.player1.give("TOY_391")
    pre_hand = len(game.player1.hand)
    art.play()
    # The 5+ minion is drawn into hand; the 0-cost Wisp stays in the deck.
    assert "CS2_186" in [c.id for c in game.player1.hand]
    assert "CS2_186" not in [c.id for c in game.player1.deck]
    assert "CS2_231" in [c.id for c in game.player1.deck]
    drawn = next(c for c in game.player1.hand if c.id == "CS2_186")
    assert drawn.cost >= 5 and drawn.type == CardType.MINION
    # Caricature leaves hand (-1) and draws the War Golem (+1) -> net unchanged.
    assert len(game.player1.hand) == pre_hand
    # "Give it a funny mustache!" is purely cosmetic in HS: the TOY_391e
    # enchant attaches but carries no stats, so the drawn minion keeps its
    # natural 7/7/7 (and its cost).
    assert any(b.id == "TOY_391e" for b in drawn.buffs)
    assert drawn.atk == 7 and drawn.max_health == 7 and drawn.cost == 7


# TOY_509 Wind-Up Musician — 5/5 Tradeable; Battlecry: Deal @ damage (starts
# at 1) to all enemy minions. Trade to upgrade (+1 damage).
def test_windup_musician_base_damage():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    m1 = game.player2.summon(WISP)
    m1.max_health = 10
    m1.damage = 0
    m2 = game.player2.summon(GOLDSHIRE_FOOTMAN)
    m2.max_health = 10
    m2.damage = 0
    card = game.player1.give("TOY_509")
    card.play()
    assert m1.damage == 1
    assert m2.damage == 1
    # Hero (not a minion) is untouched.
    assert game.player2.hero.damage == 0


def test_windup_musician_upgrades_on_trade():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.current_player  # trade requires the active player
    card = p1.give("TOY_509")
    p1.used_mana = p1.max_mana  # drain to 0 mana so the card is tradeable
    assert card.is_tradeable()
    card.trade()
    # The traded card went back into the deck; the stored damage is now 2.
    upgraded = next(c for c in p1.deck if c.id == "TOY_509")
    assert upgraded._windup_damage == 2
    # Replay it and verify it now deals 2 to all enemy minions.
    upgraded.zone = Zone.HAND
    p1.used_mana = 0
    enemy = p1.opponent.summon(WISP)
    enemy.max_health = 10
    enemy.damage = 0
    upgraded.play()
    assert enemy.damage == 2
