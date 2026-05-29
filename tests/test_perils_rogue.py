"""Perils in Paradise — ROGUE collectible card tests.

Covers all 10 collectible Rogue cards (VAC_330, VAC_332, VAC_333, VAC_334,
VAC_335, VAC_336, VAC_460, VAC_464, VAC_700, VAC_701) plus a handful of the
reachable Eudora loot tokens whose scripts carry non-trivial logic.
"""

from utils import *

from fireplace import cards as _cards


# VAC_330 — Metal Detector (3/2/2 weapon):
# After your hero attacks and kills a minion, get a Coin.
def test_metal_detector_coin_on_kill():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    weapon = p1.give("VAC_330")
    weapon.play()
    assert p1.hero.atk == 2
    # Enemy 1-health minion the hero can kill outright.
    victim = p2.summon("CS2_231")  # Wisp 1/1
    pre_coins = len([c for c in p1.hand if c.id == "GAME_005"])
    p1.hero.attack(victim)
    game.process_deaths()
    assert victim.dead
    coins = [c for c in p1.hand if c.id == "GAME_005"]
    assert len(coins) == pre_coins + 1


def test_metal_detector_no_coin_when_minion_survives():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    weapon = p1.give("VAC_330")
    weapon.play()
    # Beefy minion that survives a 2-attack hit.
    victim = p2.summon("CS2_231")
    victim.max_health = 10
    victim._max_health = 10
    victim.damage = 0
    pre_coins = len([c for c in p1.hand if c.id == "GAME_005"])
    p1.hero.attack(victim)
    game.process_deaths()
    assert not victim.dead
    coins = [c for c in p1.hand if c.id == "GAME_005"]
    assert len(coins) == pre_coins


# VAC_332 — Sea Shill (3/3/2 Pirate):
# Battlecry: The next card you play from a non-Rogue class costs (2) less.
def test_sea_shill_discounts_next_nonrogue_card():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    shill = p1.give("VAC_332")
    shill.play()
    # A Mage card (Fireball, base cost 4) in hand should now cost 2 less.
    fireball = p1.give("CS2_029")  # Fireball, 4-cost Mage spell
    assert fireball.cost == 4 - 2


def test_sea_shill_does_not_discount_rogue_card():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    shill = p1.give("VAC_332")
    shill.play()
    # A Rogue card should NOT be discounted (non-Rogue class only).
    backstab = p1.give("CS2_072")  # Backstab, 0-cost Rogue spell
    assert backstab.cost == 0
    sinister = p1.give("EX1_581")  # Sap, 2-cost Rogue spell
    assert sinister.cost == 2


def test_sea_shill_discount_consumed_after_one_play():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    shill = p1.give("VAC_332")
    shill.play()
    first = p1.give("CS2_029")  # Fireball, 4 -> 2
    assert first.cost == 2
    first.play(target=game.player2.hero)
    game.process_deaths()
    # Discount consumed: a second non-Rogue card is full price.
    second = p1.give("CS2_029")
    assert second.cost == 4


# VAC_333 — Conniving Conman (4/4/4 Pirate):
# Battlecry: Replay the last card you've played from another class.
def test_conniving_conman_replays_last_other_class_card():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Play a Mage minion (other class). Use a minion so the replay is a
    # deterministic Summon (replaying a targeted spell would pick a random
    # target). Water Elemental is a 3/6 Mage minion.
    elemental = p1.give("CS2_033")  # Water Elemental (Mage)
    elemental.play()
    game.process_deaths()
    assert len([m for m in p1.field if m.id == "CS2_033"]) == 1
    # Now Conman replays the last other-class card: another Water Elemental.
    conman = p1.give("VAC_333")
    conman.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    game.process_deaths()
    assert len([m for m in p1.field if m.id == "CS2_033"]) == 2


# VAC_334 — Knickknack Shack (3-cost Location):
# Draw a card. If you play it this turn, reopen this.
def test_knickknack_shack_draws_and_reopens_on_play():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Seed the deck with exactly one drawable card (Wisp) so the draw is known.
    wisp = p1.give("CS2_231")
    wisp.zone = Zone.DECK
    loc = p1.give("VAC_334")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    pre_hand = len(p1.hand)
    loc.use()
    # Drew the Wisp; location now on cooldown 2.
    assert wisp.zone == Zone.HAND
    assert len(p1.hand) == pre_hand + 1
    assert loc.cooldown == 2
    # Playing the drawn card this turn reopens the location (cooldown -> 0).
    wisp.play()
    game.process_deaths()
    assert loc.cooldown == 0


def test_knickknack_shack_no_reopen_for_other_card():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    drawn = p1.give("CS2_231")  # Wisp gets drawn
    drawn.zone = Zone.DECK
    loc = p1.give("VAC_334")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    assert drawn.zone == Zone.HAND
    assert loc.cooldown == 2
    # Play a DIFFERENT card (one we held, not the drawn one) -> no reopen.
    other = p1.give("CS2_231")
    other.play()
    game.process_deaths()
    assert loc.cooldown == 2


# VAC_335 — Petty Theft (2-cost spell):
# Get two random 1-Cost spells from other classes.
def test_petty_theft_gives_two_other_class_one_cost_spells():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    spell = p1.give("VAC_335")
    pre = len(p1.hand)
    spell.play()
    gained = [c for c in p1.hand]
    # Two new cards in hand (the VAC_335 left hand when played).
    assert len(p1.hand) == pre - 1 + 2
    # The two newest are 1-cost spells from a non-Rogue class.
    new_cards = p1.hand[-2:]
    assert len(new_cards) == 2
    for c in new_cards:
        assert c.type == CardType.SPELL
        assert c.data.cost == 1
        # The card's primary class is not Rogue (it comes "from other
        # classes"). Multi-class cards may incidentally list Rogue too, but
        # the pooled class enum used to draw it is non-Rogue.
        assert c.data.card_class != CardClass.ROGUE


# VAC_336 — Maestra, Mask Merchant (6/6/5, Warlock Tourist):
# Battlecry: Discover a Hero card from the past (from another class).
def test_maestra_discovers_other_class_hero_card():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    maestra = p1.give("VAC_336")
    maestra.play()
    assert p1.choice is not None
    # Every offered card is a HERO card from a class other than Rogue.
    for cid in p1.choice.cards:
        cdata = _cards.db[cid]
        assert cdata.type == CardType.HERO
        classes = list(getattr(cdata, "classes", None) or [cdata.card_class])
        assert CardClass.ROGUE not in classes
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    assert any(c.id == chosen for c in p1.hand)


# VAC_460 — Oh, Manager! (2-cost spell):
# Deal $2 damage. Combo: Get a coin.
def test_oh_manager_deals_2_no_combo():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_231")
    victim.max_health = 10
    victim._max_health = 10
    victim.damage = 0
    # Clear hand so playing this is the first card (no combo).
    for c in list(p1.hand):
        c.discard()
    spell = p1.give("VAC_460")
    spell.play(target=victim)
    game.process_deaths()
    assert victim.damage == 2
    assert not any(c.id == "GAME_005" for c in p1.hand)


def test_oh_manager_combo_gives_coin():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_231")
    victim.max_health = 10
    victim._max_health = 10
    victim.damage = 0
    # Trigger combo: play a card first this turn.
    p1.give("CS2_231").play()
    spell = p1.give("VAC_460")
    spell.play(target=victim)
    game.process_deaths()
    # Combo line: deals 2 AND grants a coin.
    assert victim.damage == 2
    coins = [c for c in p1.hand if c.id == "GAME_005"]
    assert len(coins) == 1


# VAC_464 — Treasure Hunter Eudora (6/4/5 Pirate):
# Battlecry: Sidequest — play 3 cards from other classes -> Discover 2 loot.
def test_eudora_summons_sidequest():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    eudora = p1.give("VAC_464")
    eudora.play()
    quests = [c for c in p1.field if c.id == "VAC_464t"]
    # The sidequest enchantment/quest is attached.
    secrets = [s for s in p1.secrets if s.id == "VAC_464t"]
    assert quests or secrets or any(
        getattr(o, "id", None) == "VAC_464t" for o in p1.entities
    )


def test_eudora_sidequest_rewards_two_loot_after_three_other_class():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    eudora = p1.give("VAC_464")
    eudora.play()
    # Play 3 other-class minions to complete the sidequest. Use a cheap
    # Mage minion (Mana Wyrm, 1-cost) so total mana fits and no targeting.
    for _ in range(3):
        m = p1.give("NEW1_012")  # Mana Wyrm (Mage minion)
        m.play()
        game.process_deaths()
    # Reward: Discover two pieces of loot (two discover choices in sequence).
    discovered = 0
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
        discovered += 1
    assert discovered == 2
    loot_ids = {
        "VAC_464t2", "VAC_464t3", "VAC_464t4", "VAC_464t5", "VAC_464t6",
        "VAC_464t7", "VAC_464t8", "VAC_464t9", "VAC_464t10", "VAC_464t11",
        "VAC_464t12", "VAC_464t14", "VAC_464t15", "VAC_464t16", "VAC_464t17",
        "VAC_464t18", "VAC_464t19", "VAC_464t20", "VAC_464t21", "VAC_464t22",
        "VAC_464t23", "VAC_464t24", "VAC_464t25", "VAC_464t26", "VAC_464t27",
        "VAC_464t28", "VAC_464t29", "VAC_464t30", "VAC_464t31",
    }
    gained = [c for c in p1.hand if c.id in loot_ids]
    assert len(gained) == 2


# VAC_700 — Snatch and Grab (8-cost spell):
# Destroy two random enemy minions. Costs (1) less for each card you've
# played from another class.
def test_snatch_and_grab_destroys_two_enemy_minions():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    m1 = p2.summon("CS2_231")
    m2 = p2.summon("CS2_231")
    spell = p1.give("VAC_700")
    spell.play()
    game.process_deaths()
    assert m1.dead and m2.dead
    assert len(p2.field) == 0


def test_snatch_and_grab_cost_reduction_per_other_class_card():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    spell = p1.give("VAC_700")
    assert spell.cost == 8  # base
    # Play 2 other-class cards (Mage Fireballs) -> cost reduced by 2.
    for _ in range(2):
        fb = p1.give("CS2_029")
        fb.play(target=p2.hero)
        game.process_deaths()
    assert spell.cost == 8 - 2


# VAC_701 — Swarthy Swordshiner (3/3/3 Pirate):
# Battlecry: Set the Attack and Durability of your weapon to 3.
def test_swarthy_swordshiner_sets_weapon_to_3_3():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Equip a small weapon (Wicked Knife 1/2) then set it to 3/3.
    knife = p1.give("CS2_082")  # Wicked Knife 1/2
    knife.play()
    assert p1.weapon.atk == 1
    assert p1.weapon.durability == 2
    shiner = p1.give("VAC_701")
    shiner.play()
    assert p1.weapon.atk == 3
    assert p1.weapon.durability == 3


def test_swarthy_swordshiner_lowers_bigger_weapon_to_3_3():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Equip a bigger weapon (Arcanite Reaper 5/2) -> set DOWN to 3/3.
    reaper = p1.give("CS2_112")  # Arcanite Reaper 5/2
    reaper.play()
    assert p1.weapon.atk == 5
    assert p1.weapon.durability == 2
    shiner = p1.give("VAC_701")
    shiner.play()
    assert p1.weapon.atk == 3
    assert p1.weapon.durability == 3


# --- Selected Eudora loot tokens (reachable via the sidequest reward) ---


# VAC_464t2 — Necrotic Poison: Destroy a minion.
def test_loot_necrotic_poison_destroys_minion():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_231")
    spell = p1.give("VAC_464t2")
    spell.play(target=victim)
    game.process_deaths()
    assert victim.dead


# VAC_464t5 — Pure Cold: Deal $8 damage to the enemy hero, and Freeze it.
def test_loot_pure_cold_damages_and_freezes_enemy_hero():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    spell = p1.give("VAC_464t5")
    spell.play()
    game.process_deaths()
    assert p2.hero.health == 80 - 8
    assert p2.hero.frozen


# VAC_464t9 — Looming Presence: Draw 2 cards. Gain 4 Armor.
def test_loot_looming_presence_draws_two_and_armor():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    for _ in range(2):
        c = p1.give("CS2_231")
        c.zone = Zone.DECK
    pre_hand = len(p1.hand)  # 0 (deck cards excluded)
    assert p1.hero.armor == 0
    spell = p1.give("VAC_464t9")
    spell.play()
    # spell entered and left hand; net effect is +2 drawn cards.
    assert len(p1.hand) == pre_hand + 2
    assert p1.hero.armor == 4


# VAC_464t3 — Mutating Injection: Give a minion +4/+4 and Taunt.
def test_loot_mutating_injection_buffs_and_taunt():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    target = p1.summon("CS2_231")  # Wisp 1/1
    spell = p1.give("VAC_464t3")
    spell.play(target=target)
    game.process_deaths()
    assert target.atk == 1 + 4
    assert target.max_health == 1 + 4
    assert target.taunt


# VAC_464t30 — Hilt of Quel'Delar: Give a minion +3/+3.
def test_loot_hilt_of_queldelar_buffs():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    target = p1.summon("CS2_231")  # 1/1
    spell = p1.give("VAC_464t30")
    spell.play(target=target)
    game.process_deaths()
    assert target.atk == 1 + 3
    assert target.max_health == 1 + 3


# VAC_464t8 — Crusty the Crustacean: Destroy a minion. Gain its Attack/Health.
def test_loot_crusty_devours_minion_stats():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_172")  # Bloodfen Raptor 3/2
    crusty = p1.give("VAC_464t8")
    crusty.play(target=victim)
    game.process_deaths()
    assert victim.dead
    # Base 3/3 + devoured 3 atk / 2 health = 6/5.
    assert crusty.atk == 3 + 3
    assert crusty.max_health == 3 + 2


# VAC_464t12 Puzzle Box (Tier-2): transform all minions into ones costing +3.
def test_puzzle_box_transforms_to_cost_plus_three():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p = game.player1
    p.summon("CS2_172")  # Bloodfen Raptor, 2-cost
    p.give("VAC_464t12").play()
    # The (now morphed) minion costs 2 + 3 = 5.
    assert len(p.field) == 1
    assert p.field[0].data.cost == 5


# VAC_464t25 Annoy-o Horn (treasure): fill your board with random "annoying
# minions" from the card's pool (per the wiki).
def test_annoy_o_horn_fills_board_from_pool():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p = game.player1
    pool = {"ETC_109", "GVG_085", "BOT_911", "OG_145", "ETC_321"}
    p.give("VAC_464t25").play()
    assert len(p.field) == game.MAX_MINIONS_ON_FIELD
    assert all(m.id in pool for m in p.field)
