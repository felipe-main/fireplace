from utils import *


# ---------------------------------------------------------------------------
# TOY_716 — Flash Sale (4 mana spell)
# Summon a 1/2 Mech with Divine Shield and Taunt. Give your minions +1/+2.
# ---------------------------------------------------------------------------
def test_flash_sale():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    yeti = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    assert (yeti.atk, yeti.health) == (4, 5)
    p1.give("TOY_716").play()
    # The summoned mech is GVG_085 Annoy-o-Tron (1/2 base, DS + Taunt)
    mech = [c for c in p1.field if c.id == "GVG_085"][0]
    assert mech.divine_shield
    assert mech.taunt
    assert Race.MECHANICAL in mech.races
    # Both friendly minions get +1/+2 (the mech is on board when buff resolves).
    assert (mech.atk, mech.health) == (2, 4)
    assert (yeti.atk, yeti.health) == (5, 7)


# ---------------------------------------------------------------------------
# TOY_808 — Crafter's Aura (7 mana HOLY spell)
# At the end of your turn, summon a random 6-Cost minion. Lasts 3 turns.
# ---------------------------------------------------------------------------
def test_crafters_aura_summons_each_turn_end():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.give("TOY_808").play()
    pre = len(p1.field)
    game.end_turn()  # OWN_TURN_END fires -> summon one 6-cost minion
    assert len(p1.field) == pre + 1
    # Verify the summoned minion costs 6.
    summoned = p1.field[-1]
    assert summoned.data.cost == 6


def test_crafters_aura_lasts_three_turns():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.give("TOY_808").play()
    # Three of our own turn-ends should summon 3 minions, then the aura expires.
    for _ in range(3):
        game.end_turn()           # our turn end -> summon
        game.end_turn()           # opponent turn end (no effect)
    assert len(p1.field) == 3
    # 4th own turn-end: aura already expired, no new summon.
    game.end_turn()
    game.end_turn()
    assert len(p1.field) == 3


# ---------------------------------------------------------------------------
# TOY_809 — Cardboard Golem (4/4/4)
# Battlecry: Increase the duration of Auras in hand, deck, and battlefield by 1.
# ---------------------------------------------------------------------------
def test_cardboard_golem_extends_active_aura():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.give("TOY_808").play()
    enchant = [b for b in p1.buffs if hasattr(b, "_aura_turns_left")][0]
    assert enchant._aura_turns_left == 3
    p1.used_mana = 0  # refresh so the golem is affordable
    p1.give("TOY_809").play()  # battlecry: +1 duration
    assert enchant._aura_turns_left == 4


def test_cardboard_golem_extends_aura_card_in_hand():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    aura_card = p1.give("TOY_808")  # in hand, not yet played
    p1.give("TOY_809").play()
    assert getattr(aura_card, "_aura_duration_bonus", 0) == 1
    # When played, the aura now lasts 3 + 1 = 4 turns.
    p1.used_mana = 0  # refresh so the 7-cost aura is affordable
    aura_card.play()
    enchant = [b for b in p1.buffs if hasattr(b, "_aura_turns_left")][0]
    assert enchant._aura_turns_left == 4


# ---------------------------------------------------------------------------
# TOY_810 — Painter's Virtue (4 mana 2/3 weapon, Lifesteal)
# After your hero attacks, give minions in your hand +1/+1.
# ---------------------------------------------------------------------------
def test_painters_virtue_lifesteal_and_hand_buff():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    p1.hero.set_current_health(20)
    p1.give("TOY_810").play()
    assert p1.weapon.lifesteal
    # A minion sitting in hand that should get +1/+1 after the hero attacks.
    in_hand = p1.give("CS2_182")  # Chillwind Yeti 4/5 in hand
    assert (in_hand.atk, in_hand.health) == (4, 5)
    game.end_turn(); game.end_turn()  # fresh turn so the hero can attack
    p1.hero.attack(p2.hero)
    # Lifesteal: 2 weapon attack heals the hero by 2.
    assert p1.hero.health == 22
    # Hand minion buffed +1/+1.
    assert (in_hand.atk, in_hand.health) == (5, 6)


# ---------------------------------------------------------------------------
# TOY_811 — Tigress Plushy (3/3/2, Miniaturize; Rush/Lifesteal/Divine Shield)
# ---------------------------------------------------------------------------
def test_tigress_plushy_keywords_and_miniaturize():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    card = p1.give("TOY_811")
    card.play()
    minion = [c for c in p1.field if c.id == "TOY_811"][0]
    assert minion.rush and minion.lifesteal and minion.divine_shield
    assert Race.BEAST in minion.races
    # Miniaturize: playing it adds the 1/1 Mini token (TOY_811t) to hand.
    mini = [c for c in p1.hand if c.id == "TOY_811t"]
    assert len(mini) == 1
    assert (mini[0].atk, mini[0].health) == (1, 1)


def test_tigress_plushy_mini_token_keywords():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.summon("TOY_811t")
    m = p1.field[0]
    assert (m.atk, m.health) == (1, 1)
    assert m.rush and m.lifesteal and m.divine_shield
    assert Race.BEAST in m.races


# ---------------------------------------------------------------------------
# TOY_812 — Pipsi Painthoof (7/4/4)
# Deathrattle: Summon a random Divine Shield, Rush, and Taunt minion from deck.
# ---------------------------------------------------------------------------
def test_pipsi_deathrattle_summons_from_deck():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.discard_hand()
    for c in list(p1.deck):
        c.discard()
    # Seed deck with exactly one minion that is DS + Rush + Taunt.
    # We craft one via buffs is hard; instead pick a card that has all three.
    # Use a minion and give it the three keywords by tags via summon-to-deck.
    target = p1.give("GVG_085")  # Annoy-o-Tron: DS + Taunt (no Rush) -> shouldn't qualify
    target.zone = Zone.DECK
    pipsi = p1.summon("TOY_812")
    pipsi.destroy()
    # Annoy-o-Tron lacks Rush, so it must NOT be summoned.
    assert "GVG_085" not in [c.id for c in p1.field]


def test_pipsi_deathrattle_summons_qualifying_minion():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.discard_hand()
    for c in list(p1.deck):
        c.discard()
    # Brass Elemental has Divine Shield + Rush + Taunt -> the only valid pick.
    qualifier = p1.give("ETC_357")
    qualifier.zone = Zone.DECK
    pipsi = p1.summon("TOY_812")
    pipsi.destroy()
    assert "ETC_357" in [c.id for c in p1.field]
    # It left the deck.
    assert "ETC_357" not in [c.id for c in p1.deck]


# ---------------------------------------------------------------------------
# TOY_813 — Toy Captain Tarim (5/3/7, Miniaturize, Taunt)
# Battlecry: Set a minion's Attack and Health to this minion's.
# ---------------------------------------------------------------------------
def test_tarim_sets_stats():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    big = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    tarim = p1.give("TOY_813")
    tarim.play(target=big)
    # Tarim base 3/7 -> target set to 3/7.
    assert (big.atk, big.health) == (3, 7)
    assert tarim.taunt
    # Miniaturize gives the 1/1 mini token.
    assert any(c.id == "TOY_813t" for c in p1.hand)


def test_tarim_mini_token_sets_stats():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    ogre = p1.summon("CS2_200")  # 6/7
    mini = p1.give("TOY_813t")   # 1/1 Mini token, same battlecry
    mini.play(target=ogre)
    assert (ogre.atk, ogre.health) == (1, 1)
    assert mini.taunt


def test_tarim_sets_stats_down():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Boulderfist Ogre 6/7 -> set to 3/7
    ogre = p1.summon("CS2_200")
    assert (ogre.atk, ogre.health) == (6, 7)
    tarim = p1.give("TOY_813")
    tarim.play(target=ogre)
    assert (ogre.atk, ogre.health) == (3, 7)


# ---------------------------------------------------------------------------
# TOY_880 — Wind-Up Enforcer (6/3/5, Tradeable)
# Battlecry: Summon @ copies of this minion. (Trade to upgrade!)
# ---------------------------------------------------------------------------
def test_windup_enforcer_base_summons_one_copy():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.give("TOY_880").play()
    copies = [c for c in p1.field if c.id == "TOY_880"]
    # The played minion itself + 1 summoned copy = 2.
    assert len(copies) == 2


def test_windup_enforcer_trade_upgrades_copies():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.current_player  # trade requires the active player
    # Ensure a deck card exists to trade into.
    p1.give("CS2_182").zone = Zone.DECK
    card = p1.give("TOY_880")
    p1.used_mana = p1.max_mana  # drain to 0 mana so the card is tradeable
    card.trade()  # one trade -> copies should become 2
    assert card._windup_copies == 2
    # The traded card went back to the deck; draw it and verify the upgrade persists.
    drawn = [c for c in p1.deck if c.id == "TOY_880"][0]
    assert drawn._windup_copies == 2
    drawn.zone = Zone.HAND
    p1.used_mana = 0
    drawn.play()
    copies = [c for c in p1.field if c.id == "TOY_880"]
    # played minion + 2 summoned copies = 3.
    assert len(copies) == 3


# ---------------------------------------------------------------------------
# TOY_881 — Fancy Packaging (1 mana spell)
# Give a minion with Divine Shield +2/+3.
# ---------------------------------------------------------------------------
def test_fancy_packaging_buffs_divine_shield_minion():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    ds = p1.summon("GVG_085")  # Annoy-o-Tron 1/2 with Divine Shield
    p1.give("TOY_881").play(target=ds)
    assert (ds.atk, ds.health) == (3, 5)


# ---------------------------------------------------------------------------
# TOY_882 — Trinket Artist (3/2/3)
# Battlecry: Draw a Divine Shield minion and an Aura.
# ---------------------------------------------------------------------------
def test_trinket_artist_draws_ds_minion_and_aura():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.discard_hand()
    for c in list(p1.deck):
        c.discard()
    ds_minion = p1.give("GVG_085")
    ds_minion.zone = Zone.DECK
    aura = p1.give("TOY_808")  # Crafter's Aura — an Aura card
    aura.zone = Zone.DECK
    p1.give("TOY_882").play()
    drawn_ids = [c.id for c in p1.hand]
    assert "GVG_085" in drawn_ids
    assert "TOY_808" in drawn_ids
