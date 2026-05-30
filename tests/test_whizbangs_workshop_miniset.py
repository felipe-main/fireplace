"""Whizbang's Workshop mini-set (Dr. Boom's Incredible Inventions, MIS_*).

One tight test per card plus standalone smoke tests for the engine primitives
this set added (Gigantify, the triggered-secrets ledger, the per-turn/per-game
Holy spell counters).
"""

from hearthstone.enums import CardClass, CardType, GameTag, Race, Rarity, Zone

import fireplace.cards as _cards
from utils import prepare_game, GOLDSHIRE_FOOTMAN, MOONFIRE, WISP


def _resolve(player, n=20):
    while player.choice and n:
        player.choice.choose(player.choice.cards[0])
        n -= 1


def _clear_hand(player):
    for c in list(player.hand):
        c.discard()


# ---------------------------------------------------------------------------
# Engine primitives
# ---------------------------------------------------------------------------


def test_gigantify_adds_8_8_giant_to_hand():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    p1.give("MIS_300").play()  # Snuggle Teddy (vanilla Gigantify minion)
    giants = [c for c in p1.hand if c.id == "MIS_300t"]
    assert len(giants) == 1
    g = giants[0]
    assert g.cost == 8 and g.atk == 8 and g.health == 8


def test_holy_spell_counters():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    assert p1.holy_spells_cast_this_game == 0
    assert p1.holy_spells_cast_this_turn == 0
    p1.give("CS2_089").play(target=p1.hero)  # Holy Light (Holy spell)
    assert p1.holy_spells_cast_this_game == 1
    assert p1.holy_spells_cast_this_turn == 1
    # Per-turn counter resets at the start of the controller's next turn.
    game.end_turn()
    game.end_turn()
    assert p1.holy_spells_cast_this_game == 1
    assert p1.holy_spells_cast_this_turn == 0


def test_secrets_triggered_ledger():
    game = prepare_game(CardClass.HUNTER, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    assert p1.secrets_triggered_cards_this_game == []
    p1.give("EX1_610").play()  # Explosive Trap
    game.end_turn()
    # Opponent attacks the hero -> Explosive Trap reveals.
    p2.give(GOLDSHIRE_FOOTMAN)
    foot = p2.summon(GOLDSHIRE_FOOTMAN)
    game.end_turn()
    game.end_turn()
    foot.attack(p1.hero)
    assert "EX1_610" in p1.secrets_triggered_cards_this_game


# ---------------------------------------------------------------------------
# Death Knight
# ---------------------------------------------------------------------------


def test_toysnatching_geist():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    geist = p1.give("MIS_006")  # 3/2/1, Attack 2
    geist.play()
    # Gigantic copy lands in hand.
    assert any(c.id == "MIS_006t" for c in p1.hand)
    assert p1.choice is not None
    chosen = p1.choice.cards[0]
    base = _cards.db[chosen].cost
    p1.choice.choose(chosen)
    discovered = [c for c in p1.hand if c.id == chosen]
    assert len(discovered) == 1
    assert Race.UNDEAD in discovered[0].races
    assert discovered[0].cost == max(0, base - 2)


def test_helm_of_humiliation():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    board = p1.summon("CS2_186")  # War Golem 7/7
    hand_minion = p1.give("CS2_186")  # another 7/7 in hand
    helm = p1.give("MIS_100")
    helm.play(target=board)
    _resolve(p1)
    assert board.atk == 2 and board.health == 2  # 7/7 -5/-5
    assert hand_minion.atk == 12 and hand_minion.health == 12  # 7/7 +5/+5


def test_foamrender_spends_corpses_for_durability():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.corpses = 3
    weapon = p1.give("MIS_101")  # 5/1 weapon
    weapon.play()
    assert p1.hero.atk == 5
    p1.hero.attack(p2.hero)
    # Durability: 1 - 1 (attack) + 1 (Foamrender) = 1; 3 corpses spent.
    assert p1.weapon.durability == 1
    assert p1.corpses == 0


def test_foamrender_no_corpses_breaks():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.corpses = 2  # not enough
    p1.give("MIS_101").play()
    p1.hero.attack(p2.hero)
    assert p1.weapon is None  # 1 - 1, no refund
    assert p1.corpses == 2


# ---------------------------------------------------------------------------
# Demon Hunter
# ---------------------------------------------------------------------------


def test_return_policy_triggers_deathrattle():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    leper = p1.give("EX1_029")  # Leper Gnome — Deathrattle: 2 dmg to enemy hero
    leper.play()
    leper.destroy()  # now it's a played deathrattle card this game
    enemy_hp = p2.hero.health
    rp = p1.give("MIS_102")
    rp.play()
    assert p1.choice is not None
    # Only EX1_029 was played this game with a deathrattle.
    assert all(c == "EX1_029" for c in p1.choice.cards)
    p1.choice.choose(p1.choice.cards[0])
    assert p2.hero.health == enemy_hp - 2
    assert any(c.id == "EX1_029" for c in p1.hand)


def test_sock_puppet_attack_tracks_hero():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.MAGE)
    p1 = game.player1
    puppet = p1.summon("MIS_710")  # base 1/3
    assert puppet.atk == 1
    p1.give("CS2_091").play()  # Light's Justice -> hero +1 Attack
    assert p1.hero.atk == 1
    assert puppet.atk == 2  # 1 base + 1 hero


def test_gibbering_reject_summons_on_hero_attack():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon("MIS_911")
    p1.give("CS2_091").play()  # weapon so hero can attack
    p1.hero.attack(p2.hero)
    assert len([m for m in p1.field if m.id == "MIS_911"]) == 2


# ---------------------------------------------------------------------------
# Druid
# ---------------------------------------------------------------------------


def test_overgrown_beanstalk():
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p1 = game.player1
    p1.summon("MIS_301t")  # one pre-existing Treant
    _clear_hand(p1)
    hand_before = len(p1.hand)
    p1.give("MIS_301").play()
    treants = [m for m in p1.field if m.id == "MIS_301t"]
    assert len(treants) == 2  # pre-existing + summoned
    # Drew one card per Treant (2); spell left hand on play.
    assert len(p1.hand) == hand_before + 2


def test_toyrantus_full_mana():
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p1 = game.player1
    p1.max_mana = 10
    t = p1.give("MIS_712")
    t.play()
    assert t.atk == 14 and t.health == 14  # 7/7 + 7/7


def test_toyrantus_below_full_mana():
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p1 = game.player1
    p1.max_mana = 9
    t = p1.give("MIS_712")
    t.play()
    assert t.atk == 7 and t.health == 7  # no buff


# ---------------------------------------------------------------------------
# Hunter
# ---------------------------------------------------------------------------


def test_wilderness_pack():
    game = prepare_game(CardClass.HUNTER, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    p1.give("MIS_104").play()
    assert len(p1.hand) == 5
    for c in p1.hand:
        assert Race.BEAST in c.races
        assert c.temporary


def test_bargain_bin_secret():
    game = prepare_game(CardClass.HUNTER, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.give("MIS_105").play()  # Secret
    assert len(p1.secrets) == 1
    # Empty p1's deck and seed exactly one spell so the draw is deterministic:
    # opponent plays a minion -> p1 draws a spell/weapon (the Fireball).
    for c in list(p1.deck):
        c.zone = Zone.REMOVEDFROMGAME
    p1.card("CS2_029").zone = Zone.DECK  # Fireball
    hand_before = len(p1.hand)
    game.end_turn()
    p2.give(GOLDSHIRE_FOOTMAN).play()
    assert len(p1.secrets) == 0  # secret revealed
    assert len(p1.hand) == hand_before + 1
    assert p1.hand[-1].id == "CS2_029"


def test_product_9_recasts_triggered_secrets():
    game = prepare_game(CardClass.HUNTER, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.give("EX1_610").play()  # Explosive Trap
    game.end_turn()
    foot = p2.summon(GOLDSHIRE_FOOTMAN)
    game.end_turn()
    game.end_turn()
    foot.attack(p1.hero)  # triggers + consumes Explosive Trap (p2's turn)
    assert len(p1.secrets) == 0
    game.end_turn()  # back to p1's turn so Product 9 is playable
    p1.give("MIS_914").play()  # Product 9 — recast triggered secrets
    assert any(s.id == "EX1_610" for s in p1.secrets)


# ---------------------------------------------------------------------------
# Mage
# ---------------------------------------------------------------------------


def test_malfunction_with_deck_minions():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    tank = p2.summon("CS2_186")  # Boulderfist Ogre 6/7
    tank.max_health = 80
    tank.damage = 0
    # Ensure p1 deck HAS a minion -> only 3 damage.
    p1.card("CS2_186").zone = Zone.DECK
    p1.give("MIS_107").play()
    assert tank.damage == 3


def test_malfunction_empty_deck_minions():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    tank = p2.summon("CS2_186")
    tank.max_health = 80
    tank.damage = 0
    # Remove every minion from p1's deck -> 3 + 3 = 6.
    for c in list(p1.deck):
        if c.type == CardType.MINION:
            c.zone = Zone.REMOVEDFROMGAME
    p1.give("MIS_107").play()
    assert tank.damage == 6


def test_buy_one_get_one_freeze():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_186")
    p1.give("MIS_302").play(target=target)
    assert target.frozen
    copies = [m for m in p1.field if m.id == "CS2_186"]
    assert len(copies) == 1
    assert copies[0].frozen


def test_darkmoon_magician_recasts_pricier_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 200
    p2.hero.damage = 5
    p1.hero.max_health = 200
    p1.hero.damage = 5
    # Minions on both boards + damaged heroes so the random (1)-cost recast
    # always has a legal target (otherwise CastSpell fizzles before counting).
    p1.summon(GOLDSHIRE_FOOTMAN)
    p2.summon(GOLDSHIRE_FOOTMAN)
    p1.summon("MIS_303")
    before = len(p1.spells_cast_this_game)
    p1.give(MOONFIRE).play(target=p2.hero)  # 0-cost spell
    # The Moonfire (hand-play) plus the triggered random (1)-cost recast.
    assert len(p1.spells_cast_this_game) == before + 2


# ---------------------------------------------------------------------------
# Paladin
# ---------------------------------------------------------------------------


def test_whack_a_gnoll():
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    p1.give("MIS_700").play()
    assert p1.choice is not None
    chosen = p1.choice.cards[0]
    data = _cards.db[chosen]
    assert data.type == CardType.WEAPON
    assert CardClass.PALADIN in data.classes
    p1.choice.choose(chosen)
    weapon = [c for c in p1.hand if c.id == chosen][0]
    assert weapon.atk == data.atk + 1
    assert weapon.durability == data.durability + 1


def test_holy_glowsticks_cost_and_lifesteal():
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    stick = p1.give("MIS_709")
    assert stick.cost == 4  # no Holy spell cast yet
    p1.give("CS2_089").play(target=p1.hero)  # cast a Holy spell this turn
    assert stick.cost == 1
    p1.hero.damage = 10
    target = p2.summon("CS2_186")  # 6/7
    stick.play(target=target)
    assert target.damage == 4
    assert p1.hero.damage == 6  # Lifesteal healed 4


def test_flickering_lightbot_cost_and_gigantify():
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    p1 = game.player1
    bot = p1.give("MIS_918")
    assert bot.cost == 3
    p1.give("CS2_089").play(target=p1.hero)
    p1.give("CS2_089").play(target=p1.hero)
    assert bot.cost == 1  # 3 - 2 Holy spells
    _clear_hand(p1)
    bot2 = p1.give("MIS_918")
    bot2.play()
    assert any(c.id == "MIS_918t" for c in p1.hand)


# ---------------------------------------------------------------------------
# Priest
# ---------------------------------------------------------------------------


def test_delayed_product():
    game = prepare_game(CardClass.PRIEST, CardClass.MAGE)
    p1 = game.player1
    p1.give("MIS_305").play()
    assert p1.choice is not None
    for cid in p1.choice.cards:
        assert _cards.db[cid].cost >= 8
        assert _cards.db[cid].type == CardType.MINION
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    summoned = [m for m in p1.field if m.id == chosen]
    assert len(summoned) == 1
    assert summoned[0].dormant


def test_funhouse_mirror():
    game = prepare_game(CardClass.PRIEST, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    original = p2.summon("CS2_200")  # Boulderfist Ogre 6/7
    p1.give("MIS_714").play(target=original)
    copies = [m for m in p1.field if m.id == "CS2_200"]
    assert len(copies) == 1
    # Copy attacked the original: each is a 6/7, both take 6 and survive at 1.
    assert original.damage == 6
    assert copies[0].damage == 6


def test_puppet_theatre():
    game = prepare_game(CardClass.PRIEST, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    enemy = p2.summon("CS2_186")  # War Golem 7/7
    loc = p1.give("MIS_919")
    loc.play()
    loc.turn_played = -5  # bypass the first-turn cooldown
    loc.cooldown = 0
    loc.use(target=enemy)
    copies = [c for c in p1.hand if c.id == "CS2_186"]
    assert len(copies) == 1
    assert copies[0].atk == 1 and copies[0].health == 1 and copies[0].cost == 1


# ---------------------------------------------------------------------------
# Rogue
# ---------------------------------------------------------------------------

_JUNK = {"GAME_005", "EX1_014t", "WW_001t", "CS2_082"}


def test_dust_bunny_battlecry_and_deathrattle():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    bunny = p1.give("MIS_706")
    bunny.play()
    assert len(p1.hand) == 1 and p1.hand[0].id in _JUNK
    bunny.destroy()
    assert len(p1.hand) == 2
    assert all(c.id in _JUNK for c in p1.hand)


def test_twisted_pack():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    p1.give("MIS_708").play()
    assert len(p1.hand) == 5
    for c in p1.hand:
        assert c.temporary
        assert CardClass.ROGUE not in c.data.classes
        assert c.data.classes != [CardClass.NEUTRAL]


def test_dubious_purchase_no_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    _clear_hand(p1)
    p1.combo = False
    p1.give("MIS_903").play()
    assert len(p1.hand) == 3
    assert enemy in p2.field  # not destroyed


def test_dubious_purchase_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    _clear_hand(p1)
    p1.give(MOONFIRE).play(target=p1.hero)  # activate Combo
    p1.give("MIS_903").play()
    assert len(p1.hand) == 3
    assert enemy.dead


# ---------------------------------------------------------------------------
# Shaman
# ---------------------------------------------------------------------------


def test_murloc_growfin():
    game = prepare_game(CardClass.SHAMAN, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    growfin = p1.give("MIS_307")  # 1/1
    growfin.play()
    tiny = [m for m in p1.field if m.id == "MIS_307t"]
    assert len(tiny) == 1
    assert tiny[0].atk == 1 and tiny[0].health == 1
    assert tiny[0].rush
    assert any(c.id == "MIS_307t1" for c in p1.hand)  # Gigantic copy


def test_wave_of_nostalgia():
    game = prepare_game(CardClass.SHAMAN, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon(WISP)
    p1.summon(WISP)
    p2.summon(GOLDSHIRE_FOOTMAN)
    p1.give("MIS_701").play()
    minions = list(p1.field) + list(p2.field)
    assert len(minions) == 3
    for m in minions:
        assert m.rarity == Rarity.LEGENDARY
        assert m.type == CardType.MINION


# ---------------------------------------------------------------------------
# Warlock
# ---------------------------------------------------------------------------


def test_domino_effect_single_direction():
    # Target the leftmost minion: only the right side is available, so the
    # topple direction is forced. Cascade: 2, 3, 4.
    game = prepare_game(CardClass.WARLOCK, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    a = p2.summon("CS2_186")  # leftmost = target
    b = p2.summon("CS2_186")
    c = p2.summon("CS2_186")
    for m in (a, b, c):
        m.max_health = 80
        m.damage = 0
    p1.give("MIS_027").play(target=a)
    assert a.damage == 2
    assert b.damage == 3
    assert c.damage == 4


def test_domino_effect_random_direction():
    # With minions on both sides of the target, the topple direction is random
    # and goes entirely one way. Casting repeatedly (advancing the game RNG)
    # shows both directions; each cast deals 2 to the target and cascades 3, 4
    # down exactly one side, leaving the other untouched.
    game = prepare_game(CardClass.WARLOCK, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    seen = set()
    for _ in range(40):
        for m in list(p2.field):
            m.destroy()
        left2 = p2.summon("CS2_186")
        left1 = p2.summon("CS2_186")
        target = p2.summon("CS2_186")
        right1 = p2.summon("CS2_186")
        right2 = p2.summon("CS2_186")
        for m in (left2, left1, target, right1, right2):
            m.max_health = 80
            m.damage = 0
        sp = p1.give("MIS_027")
        p1.used_mana = 0
        sp.play(target=target)
        assert target.damage == 2
        went_left = left1.damage == 3 and left2.damage == 4
        went_right = right1.damage == 3 and right2.damage == 4
        # Exactly one direction, and the other side is untouched.
        assert went_left ^ went_right
        if went_left:
            assert right1.damage == 0 and right2.damage == 0
        else:
            assert left1.damage == 0 and left2.damage == 0
        seen.add("L" if went_left else "R")
    assert seen == {"L", "R"}  # both directions actually happen


def test_domino_effect_stops_at_untargetable():
    # The cascade stops at the first minion it can't target (Elusive). Target
    # the leftmost; the next minion is a Stone Drake (can't be targeted by
    # spells), so only the target takes damage.
    game = prepare_game(CardClass.WARLOCK, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_186")
    elusive = p2.summon("DEEP_006")  # Stone Drake — Elusive (2/8)
    behind = p2.summon("CS2_186")
    for m in (target, behind):
        m.max_health = 80
        m.damage = 0
    p1.give("MIS_027").play(target=target)
    assert target.damage == 2
    assert elusive.damage == 0
    assert behind.damage == 0


def test_infernal_sets_health_to_15():
    game = prepare_game(CardClass.WARLOCK, CardClass.MAGE)
    p1 = game.player1
    assert p1.hero.health == 30
    p1.give("MIS_703").play()
    assert p1.hero.health == 15


def test_mass_production():
    game = prepare_game(CardClass.WARLOCK, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    hp_before = p1.hero.health
    p1.give("MIS_707").play()
    assert len(p1.hand) == 2  # drew 2
    assert p1.hero.health == hp_before - 3
    assert len([c for c in p1.deck if c.id == "MIS_707"]) == 2


# ---------------------------------------------------------------------------
# Warrior
# ---------------------------------------------------------------------------


def test_standardized_pack():
    game = prepare_game(CardClass.WARRIOR, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    p1.give("MIS_705").play()
    assert len(p1.hand) == 5
    for c in p1.hand:
        assert c.type == CardType.MINION
        assert c.data.tags.get(GameTag.TAUNT, 0)
        assert c.temporary


def test_safety_expert_deathrattle_bombs():
    game = prepare_game(CardClass.WARRIOR, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    expert = p1.summon("MIS_711")
    expert.destroy()
    assert len([c for c in p2.deck if c.id == "BOT_511t"]) == 3


def test_part_scrapper():
    game = prepare_game(CardClass.WARRIOR, CardClass.MAGE)
    p1 = game.player1
    p1.hero.armor = 5
    p1.give("MIS_902").play()
    assert p1.hero.armor == 0
    assert p1._next_mech_cost_reduction == 5


def test_part_scrapper_partial_armor():
    game = prepare_game(CardClass.WARRIOR, CardClass.MAGE)
    p1 = game.player1
    p1.hero.armor = 3
    p1.give("MIS_902").play()
    assert p1.hero.armor == 0
    assert p1._next_mech_cost_reduction == 3


# ---------------------------------------------------------------------------
# Neutral
# ---------------------------------------------------------------------------


def test_replicator_inator():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("MIS_025")  # 5/5/5, Attack 5
    # Play a minion whose Attack (7) differs -> no copy.
    p1.used_mana = 0
    p1.give("CS2_186").play()  # War Golem 7/7 (Attack 7) -> no copy
    assert len([m for m in p1.field if m.id == "CS2_186"]) == 1
    # Play a minion with Attack 5 -> summon a copy of it.
    p1.used_mana = 0
    p1.give("CS2_213").play()  # Reckless Rocketeer 5/2 (Attack 5) -> copy
    assert len([m for m in p1.field if m.id == "CS2_213"]) == 2


def test_puppetmaster_dorian():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("MIS_026")
    _clear_hand(p1)
    target = p1.card("CS2_186")  # Boulderfist Ogre 6/7
    target.zone = Zone.DECK
    p1.draw()
    copies = [c for c in p1.hand if c.id == "CS2_186"]
    # Drew the ogre + got a 1/1 copy costing (1).
    assert len(copies) == 2
    mini = [c for c in copies if c.cost == 1]
    assert len(mini) == 1
    assert mini[0].atk == 1 and mini[0].health == 1


def test_explodineer_end_of_turn_bomb():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon("MIS_308")
    assert len([c for c in p2.deck if c.id == "BOT_511t"]) == 0
    game.end_turn()  # end of p1's turn fires the trigger... actually own turn end
    assert len([c for c in p2.deck if c.id == "BOT_511t"]) == 1


def test_building_block_golem():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    golem = p1.summon("MIS_314")
    golem.destroy()
    summoned = [m for m in p1.field if m.id != "MIS_314"]
    assert len(summoned) == 3
    for m in summoned:
        assert m.cost == 1


def test_pro_gamer_rps_winner_draws_two():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    p1_before, p2_before = len(p1.hand), len(p2.hand)
    p1.give("MIS_916").play()
    _resolve(p1)
    drawn = (len(p1.hand) - p1_before) + (len(p2.hand) - p2_before)
    # Exactly one side draws 2 (win), or nobody (tie) — never both.
    assert drawn in (0, 2)
    # The thrown throw-tokens (MIS_916a/b/c) are not left in hand or on board
    # (the Pro Gamer minion itself, MIS_916, stays on board — that's fine).
    throws = ("MIS_916a", "MIS_916b", "MIS_916c")
    assert not any(c.id in throws for c in p1.hand)
    assert not any(c.id in throws for c in p1.field)
