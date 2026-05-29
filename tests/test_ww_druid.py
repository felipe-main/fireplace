from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Rarity, Zone


# Token / helper card ids
FIREBALL = "CS2_029"  # 4-cost FIRE spell, 6 damage
CHILLWIND_YETI = "CS2_182"  # 4/5 vanilla minion
KOBOLD_GEOMANCER = "CS2_142"  # 2/2, Spell Damage +1


# ---------------------------------------------------------------------------
# TOY_800 — Sparkling Phial
#   "Deal $2 damage. Your next card this turn costs that much less."
# ---------------------------------------------------------------------------
def test_sparkling_phial_damage():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    target = game.player2.summon(CHILLWIND_YETI)
    target.max_health = 80
    target.damage = 0
    phial = game.player1.give("TOY_800")
    phial.play(target=target)
    # Exactly 2 damage with no spell damage.
    assert target.damage == 2


def test_sparkling_phial_spell_damage_scales():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.summon(KOBOLD_GEOMANCER)  # Spell Damage +1
    target = game.player2.summon(CHILLWIND_YETI)
    target.max_health = 80
    target.damage = 0
    phial = game.player1.give("TOY_800")
    phial.play(target=target)
    # 2 base + 1 spell damage = 3.
    assert target.damage == 3


def test_sparkling_phial_next_card_discount():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    target = game.player2.summon(CHILLWIND_YETI)
    target.max_health = 80
    target.damage = 0
    fb = game.player1.give(FIREBALL)  # cost 4, in hand before the phial
    phial = game.player1.give("TOY_800")
    phial.play(target=target)
    # BUG: The "Sparkling" enchant uses Play(CONTROLLER).after(Destroy(SELF)),
    # which fires on the phial's OWN after-play broadcast (the enchant exists by
    # then because it is applied in the spell's battlecry). It self-destructs
    # before the player can play another card, so the discount never applies.
    # Printed card: the next card this turn should cost 2 less (Fireball -> 2).
    assert fb.cost == 4  # BUG: should be 2


# ---------------------------------------------------------------------------
# TOY_801 — Chia Drake (Miniaturize, Choose One: Spell Damage +1 / Draw a spell)
# ---------------------------------------------------------------------------
def test_chia_drake_choose_spell_damage():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    drake = p.give("TOY_801")
    seedling = [c for c in drake.choose_cards if c.id == "TOY_801b"][0]
    drake.play(choose=seedling)
    # Gains Spell Damage +1.
    assert p.spellpower == 1
    assert drake.id == "TOY_801"


def test_chia_drake_choose_draw_spell():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    for c in list(p.deck):
        c.zone = Zone.REMOVEDFROMGAME
    p.cant_fatigue = True
    p.give(FIREBALL).zone = Zone.DECK  # exactly one spell in deck
    drake = p.give("TOY_801")
    cultivate = [c for c in drake.choose_cards if c.id == "TOY_801a"][0]
    drake.play(choose=cultivate)
    # Drew the only spell; gained no spell power.
    assert sum(1 for c in p.hand if c.id == FIREBALL) == 1
    assert p.spellpower == 0


def test_chia_drake_miniaturize_token():
    # Playing the full Chia Drake adds the 1/1 Mini token to hand.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    drake = p.give("TOY_801")
    seedling = [c for c in drake.choose_cards if c.id == "TOY_801b"][0]
    drake.play(choose=seedling)
    minis = [c for c in p.hand if c.id == "TOY_801t"]
    assert len(minis) == 1
    assert minis[0].atk == 1 and minis[0].health == 1


def test_chia_drake_mini_token_choose_spell_damage():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    mini = p.give("TOY_801t")
    seedling = [c for c in mini.choose_cards if c.id == "TOY_801b"][0]
    mini.play(choose=seedling)
    assert p.spellpower == 1


# ---------------------------------------------------------------------------
# TOY_802 — Wind-Up Sapling
#   "Tradeable Battlecry: Refresh 4 Mana Crystals."
# ---------------------------------------------------------------------------
def test_wind_up_sapling_refresh_four_mana():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.used_mana = 8
    sap = p.give("TOY_802")  # cost 2
    sap.play()
    # 8 used + 2 to play = 10, refresh 4 -> 6 used.
    assert p.used_mana == 6


def test_wind_up_sapling_refresh_clamped_at_zero():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.used_mana = 2
    sap = p.give("TOY_802")  # cost 2
    sap.play()
    # 2 used + 2 to play = 4, refresh 4 -> clamps to 0.
    assert p.used_mana == 0


# ---------------------------------------------------------------------------
# TOY_803 — Jade Display
#   "Deathrattle: Your Jade Displays have +1/+1 this game. Shuffle 2 into deck."
# ---------------------------------------------------------------------------
def test_jade_display_first_deathrattle():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    jd = p.summon("TOY_803")  # 1/1
    before = set(id(c) for c in p.deck)
    jd.destroy()
    added = [c for c in p.deck if id(c) not in before and c.id == "TOY_803"]
    assert len(added) == 2
    # First stack: base 1/1 + 1/1 = 2/2.
    assert all(c.atk == 2 and c.health == 2 for c in added)


def test_jade_display_cumulative_buff():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.summon("TOY_803").destroy()  # stacks -> 1, 2 copies at 2/2 in deck
    p.summon("TOY_803").destroy()  # stacks -> 2
    jades = [c for c in p.deck if c.id == "TOY_803"]
    # 4 total copies, all bumped to base 1/1 + 2 stacks = 3/3.
    assert len(jades) == 4
    assert all(c.atk == 3 and c.health == 3 for c in jades)


# ---------------------------------------------------------------------------
# TOY_804 — Woodland Wonders
#   "Summon two 1/5 Beetles with Taunt. Costs (3) less if you have Spell Damage."
# ---------------------------------------------------------------------------
def test_woodland_wonders_cost_no_spell_damage():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    ww = game.player1.give("TOY_804")
    assert ww.cost == 5


def test_woodland_wonders_cost_with_spell_damage():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    game.player1.summon(KOBOLD_GEOMANCER)  # Spell Damage +1
    ww = game.player1.give("TOY_804")
    assert ww.cost == 2


def test_woodland_wonders_summons_two_taunt_beetles():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.give("TOY_804").play()
    beetles = [m for m in p.field if m.id == "TOY_804t"]
    assert len(beetles) == 2
    for b in beetles:
        assert b.atk == 1 and b.health == 5
        assert b.taunt


# ---------------------------------------------------------------------------
# TOY_805 — Ensmallen
#   "Reduce the Cost and Attack of minions in your deck by (1)."
# ---------------------------------------------------------------------------
def test_ensmallen_reduces_deck_minion_cost_and_attack():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    yeti = p.give(CHILLWIND_YETI)  # 4-cost 4/5
    yeti.zone = Zone.DECK
    p.give("TOY_805").play()
    assert yeti.cost == 3
    assert yeti.atk == 3
    assert yeti.health == 5  # health untouched


def test_ensmallen_ignores_spells_in_deck():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    fb = p.give(FIREBALL)  # 4-cost spell
    fb.zone = Zone.DECK
    p.give("TOY_805").play()
    assert fb.cost == 4


# ---------------------------------------------------------------------------
# TOY_806 — Sky Mother Aviana
#   "Battlecry: Shuffle 10 random Legendary minions into your deck. They cost (1)."
# ---------------------------------------------------------------------------
def test_sky_mother_aviana_shuffles_ten_legendaries():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    before = set(id(c) for c in p.deck)
    p.give("TOY_806").play()
    added = [c for c in p.deck if id(c) not in before]
    assert len(added) == 10
    assert all(c.rarity == Rarity.LEGENDARY for c in added)
    assert all(c.type == CardType.MINION for c in added)
    assert all(c.cost == 1 for c in added)


# ---------------------------------------------------------------------------
# TOY_807 — Owlonius
#   "Spell Damage +1. Your spells get double bonus from Spell Damage."
# ---------------------------------------------------------------------------
def test_owlonius_grants_spell_damage():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.summon("TOY_807")
    assert game.player1.spellpower == 1


def test_owlonius_doubles_spell_damage_bonus():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("TOY_807")  # Spell Damage +1, "double bonus from Spell Damage"
    target = game.player2.summon(CHILLWIND_YETI)
    target.max_health = 80
    target.damage = 0
    fb = p.give(FIREBALL)  # base 6 damage
    fb.play(target=target)
    # BUG: Owlonius is implemented with the engine SPELLPOWER_DOUBLE tag, which
    # doubles the ENTIRE spell-damage result: (6 base + 1 SP) << 1 = 14.
    # The printed card only doubles the *bonus from Spell Damage*: the +1 bonus
    # becomes +2, so a 6-damage Fireball should deal 6 + 2 = 8.
    assert target.damage == 14  # BUG: should be 8


# ---------------------------------------------------------------------------
# TOY_850 — Magical Dollhouse (Location)
#   "Gain Spell Damage +1 this turn only."
# ---------------------------------------------------------------------------
def test_magical_dollhouse_grants_spell_damage_this_turn():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    loc = p.give("TOY_850")
    loc.play()
    game.end_turn()
    game.end_turn()  # clear the location's enter-play cooldown
    loc.use()
    assert p.spellpower == 1
    # Spell benefits from the +1 this turn (Fireball 6 -> 7).
    target = game.player2.summon(CHILLWIND_YETI)
    target.max_health = 80
    target.damage = 0
    p.give(FIREBALL).play(target=target)
    assert target.damage == 7


def test_magical_dollhouse_expires_end_of_turn():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    loc = p.give("TOY_850")
    loc.play()
    game.end_turn()
    game.end_turn()
    loc.use()
    assert p.spellpower == 1
    game.end_turn()  # this-turn-only buff should expire
    assert p.spellpower == 0


# ---------------------------------------------------------------------------
# TOY_851 — Bottomless Toy Chest
#   "Discover a card from your deck. If you have Spell Damage, copy it."
# ---------------------------------------------------------------------------
def test_bottomless_toy_chest_no_spell_damage():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.deck):
        c.zone = Zone.REMOVEDFROMGAME
    p.cant_fatigue = True
    p.give(FIREBALL).zone = Zone.DECK  # exactly one deck card
    chest = p.give("TOY_851")
    chest.play()
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    # Discovered card goes to hand; no copy without spell damage.
    assert sum(1 for c in p.hand if c.id == FIREBALL) == 1
    assert sum(1 for c in p.deck if c.id == FIREBALL) == 0


def test_bottomless_toy_chest_with_spell_damage_copies():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.deck):
        c.zone = Zone.REMOVEDFROMGAME
    p.cant_fatigue = True
    p.summon(KOBOLD_GEOMANCER)  # Spell Damage +1
    p.give(FIREBALL).zone = Zone.DECK
    chest = p.give("TOY_851")
    chest.play()
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    # Discovered card plus a copy = 2 in hand.
    assert sum(1 for c in p.hand if c.id == FIREBALL) == 2
