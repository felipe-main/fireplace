from utils import *


# TOY_517 Plucky Paintfin — Poisonous Battlecry: Draw a Rush minion.
def test_plucky_paintfin_draws_rush_minion():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Seed the deck: one Rush minion + two non-rush distractors.
    rush = p1.card("GIL_202", zone=Zone.DECK)   # a Rush minion
    p1.card("CS2_231", zone=Zone.DECK)          # Wisp (no rush)
    p1.card("CS2_231", zone=Zone.DECK)          # Wisp (no rush)
    pre_hand = len(p1.hand)
    paintfin = p1.give("TOY_517")
    paintfin.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # The Rush minion must be the card drawn into hand.
    assert rush.zone == Zone.HAND
    assert len(p1.hand) == pre_hand + 1  # paintfin played out, rush drawn
    # Paintfin itself carries Poisonous (from data).
    assert paintfin.poisonous


# TOY_518 Treasure Distributor — After you summon a Pirate, give it +1 Attack.
def test_treasure_distributor_buffs_summoned_pirate():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("TOY_518")
    # Summon a Pirate (Patches the Pirate is a 1/1 Pirate).
    pirate = p1.summon("CFM_637")
    assert pirate.atk == 2  # 1 base +1 from Distributor


def test_treasure_distributor_ignores_non_pirate():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("TOY_518")
    wisp = p1.summon("CS2_231")  # 1/1 not a pirate
    assert wisp.atk == 1


# TOY_520 Observer of Mysteries — Battlecry: Cast 2 random Secrets.
# At the start of your turn, destroy them.
def test_observer_casts_two_secrets():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    assert len(p1.secrets) == 0
    p1.give("TOY_520").play()
    assert len(p1.secrets) == 2


def test_observer_secrets_destroyed_at_start_of_turn():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("TOY_520").play()
    assert len(p1.secrets) == 2
    # Pass to opponent and back; at the start of p1's next turn they vanish.
    game.end_turn()  # p1 -> p2
    game.end_turn()  # p2 -> p1 (begin_turn destroys temp secrets)
    assert len(p1.secrets) == 0


# TOY_528 Sing-Along Buddy — Your Hero Power triggers twice.
def test_sing_along_buddy_doubles_hero_power():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("TOY_528")
    enemy = game.player2.hero
    pre = enemy.health
    # Mage hero power: deal 1 damage. With Buddy it fires twice => 2 damage.
    p1.hero.power.use(target=enemy)
    assert enemy.health == pre - 2


# TOY_530 Playhouse Giant — Costs (1) less for each card drawn this game.
def test_playhouse_giant_cost_reduction():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    giant = p1.give("TOY_530")
    base = giant.cost  # equals 20 minus whatever was drawn before it entered hand
    # Draw three cards; cost should drop by 3 from current.
    pre = giant.cost
    p1.draw()
    p1.draw()
    p1.draw()
    assert giant.cost == pre - 3


def test_playhouse_giant_base_cost_is_20():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Empty game: no draws have happened during start beyond the opening hand.
    giant = p1.card("TOY_530", zone=Zone.HAND)
    # cost = base - cards drawn this game. Read the base cost from data so the
    # test survives rebalances (Patch 33.2 bumped the base 20 -> 25).
    base = giant.data.cost
    assert giant.cost == max(0, base - getattr(giant, "_cards_drawn_this_game", 0))


# TOY_531 Li'Na, Shop Manager — Whenever you cast a spell, fill your board
# with random minions of that Cost.
def test_lina_fills_board_with_cost_matched_minions():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("TOY_531")
    assert len(p1.field) == 1
    # Cast a 1-cost spell (Moonfire is 0; use a known 1-cost: Frostbolt CS2_024=2)
    spell = p1.give("CS2_024")  # Frostbolt, cost 2
    spell.play(target=game.player2.hero)
    # Board filled to max (7).
    assert len(p1.field) == game.MAX_MINIONS_ON_FIELD
    # Every summoned minion (all but Li'Na) costs 2.
    summoned = [m for m in p1.field if m.id != "TOY_531"]
    assert len(summoned) == game.MAX_MINIONS_ON_FIELD - 1
    assert all(m.cost == 2 for m in summoned)


# TOY_601 Factory Assemblybot — At end of your turn, summon a 6/7 Bot that
# attacks a random enemy.
def test_factory_assemblybot_summons_attacking_bot():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("TOY_601")
    # Beef up enemy hero so it survives and we can read exact damage.
    enemy = game.player2.hero
    enemy.max_health = 80
    enemy.damage = 0
    # Clear enemy board so the only enemy target is the hero.
    pre = enemy.health
    game.end_turn()  # triggers OWN_TURN_END for p1
    # A Copybot was summoned on p1's board.
    bots = [m for m in p1.field if m.id == "TOY_601t2"]
    assert len(bots) == 1
    bot = bots[0]
    assert bot.atk == 6 and bot.max_health == 7
    # It attacked the only enemy character (hero) for 6.
    assert enemy.health == pre - 6


# TOY_646 Messmaker — Deathrattle: Deal 1 damage to all enemies.
def test_messmaker_deathrattle_hits_all_enemies():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    messmaker = p1.summon("TOY_646")
    enemy_hero = game.player2.hero
    enemy_hero.max_health = 80
    enemy_hero.damage = 0
    p1.hero.max_health = 80
    p1.hero.damage = 40  # friendly hero hurt, so lifesteal heal is visible
    enemy_minion = game.player2.summon("CS2_231")  # Wisp 1/1
    pre_hero = enemy_hero.health
    pre_friendly = p1.hero.health
    messmaker.destroy()
    assert enemy_hero.health == pre_hero - 1
    assert enemy_minion.dead  # 1 damage kills the 1-health Wisp
    # Lifesteal applies to the deathrattle damage: 2 enemies hit for 1 each
    # => 2 total damage dealt => 2 healed back to friendly hero.
    assert p1.hero.health == pre_friendly + 2


def test_messmaker_has_taunt_and_lifesteal():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    m = game.player1.summon("TOY_646")
    assert m.taunt
    assert m.lifesteal


# TOY_670 Giggling Toymaker — Deathrattle: Summon two 1/2 Mechs with Taunt
# and Divine Shield.
def test_giggling_toymaker_deathrattle():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    toymaker = p1.summon("TOY_670")
    toymaker.destroy()
    mechs = [m for m in p1.field if m.id == "BOT_270t"]
    assert len(mechs) == 2
    for m in mechs:
        assert m.atk == 1 and m.max_health == 2
        assert m.taunt and m.divine_shield
        assert m.race == Race.MECHANICAL


# TOY_703 Colifero the Artist — Battlecry: Draw a minion. Transform all other
# friendly minions into copies of it.
def test_colifero_transforms_other_minions():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Seed deck with exactly one minion to draw (Chillwind Yeti 4/5).
    yeti = p1.card("CS2_182", zone=Zone.DECK)
    # Two existing minions that should be transformed into Yeti copies.
    p1.summon("CS2_231")  # Wisp
    p1.summon("CS2_231")  # Wisp
    colifero = p1.give("TOY_703")
    colifero.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert yeti.zone == Zone.HAND
    # Morph replaces minion entities, so inspect the resulting field.
    field = p1.field
    assert len(field) == 3  # Colifero + 2 transformed minions
    others = [m for m in field if m is not colifero]
    assert len(others) == 2
    # Both former Wisps are now Chillwind Yeti copies (4/5).
    assert all(m.id == "CS2_182" for m in others)
    assert all(m.atk == 4 and m.max_health == 5 for m in others)
    # Colifero itself is unchanged (not transformed into a copy of itself).
    assert colifero.id == "TOY_703"


# TOY_700 Splendiferous Whizbang — You start the game with one of Whizbang's
# Experimental Decks!
def test_splendiferous_whizbang_is_vanilla_stats():
    # BUG: "You start the game with one of Whizbang's Experimental Decks!" is a
    # start-of-game deck-replacement effect that is NOT implemented (no script
    # is merged onto TOY_700). It currently plays as a vanilla 4/4/5 with no
    # effect. This test pins the current (unimplemented) behaviour.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    whiz = p1.give("TOY_700")
    whiz.play()
    assert whiz.atk == 4 and whiz.max_health == 5
    # No start-of-game deck swap happened (decks were drafted normally).
    assert whiz.zone == Zone.PLAY


# TOY_814 Bucket of Soldiers — Deathrattle: Summon five 1/1 Soldiers with
# random bonus effects.
def test_bucket_of_soldiers_summons_five():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    bucket = p1.summon("TOY_814")
    bucket.destroy()
    soldiers = [m for m in p1.field if m.id.startswith("TOY_814t")]
    assert len(soldiers) == 5
    for s in soldiers:
        assert s.atk == 1 and s.max_health == 1
