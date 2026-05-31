"""The Lost City of Un'Goro — NEUTRAL collectible cards.

Tight unit tests asserting the PRINTED behaviour of every collectible
NEUTRAL card (TLC_ prefix). One test (or a small cluster) per card.

Kindred (the set keyword) activates a bonus if you played a matching minion
type or spell school on your PREVIOUS turn. Tests set up that previous-turn
state with a matching play + two end_turns, and include a negative case.
"""

import pytest

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Race, Rarity, Zone

import fireplace.cards as _cards


# Tokens / helpers used across tests
BLOODFEN = "CS2_172"   # Bloodfen Raptor 3/2 Beast
MURLOC_RAIDER = "CS2_168"  # 2/1 Murloc
YETI = "CS2_182"       # Chillwind Yeti 4/5 (FREE rarity)
ELEMENTAL_TOK = "UNG_809t1"  # 2/1 Elemental token
FIREBALL = "CS2_029"   # Fire spell
LEPER_GNOME = "EX1_029"  # Deathrattle: deal 2 to enemy hero


def _kindred_setup(player, game, token_id=BLOODFEN):
    """Play `token_id` then pass two turns so its type is 'last turn'."""
    player.give(token_id).play()
    game.end_turn()
    game.end_turn()


# ---------------------------------------------------------------------------
# TLC_100 — Elise the Navigator: craft a custom location (approx).
# ---------------------------------------------------------------------------
def test_elise_the_navigator():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("TLC_100").play()
    locations = [
        c for c in game.entities
        if getattr(c, "id", None) == "TLC_100t1" and c.zone == Zone.PLAY
    ]
    assert len(locations) == 1
    assert locations[0].type == CardType.LOCATION


# ---------------------------------------------------------------------------
# TLC_101 — Undercover Cultist: Taunt, Reborn, +3 Attack while damaged.
# ---------------------------------------------------------------------------
def test_undercover_cultist():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    uc = p1.summon("TLC_101")
    assert uc.taunt
    assert _cards.db["TLC_101"].tags.get(GameTag.REBORN)
    assert uc.atk == 2
    from fireplace.actions import Hit
    game.queue_actions(p1.hero, [Hit(uc, 1)])
    assert uc.atk == 5  # 2 + 3 while damaged
    assert uc.health == 2


# ---------------------------------------------------------------------------
# TLC_102 — Torga: draw two cards (Kindred-pair approx).
# ---------------------------------------------------------------------------
def test_torga():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for _ in range(3):
        p1.card(YETI, zone=Zone.DECK)
    pre = len(p1.hand)
    p1.give("TLC_102").play()
    assert len(p1.hand) == pre + 2


# ---------------------------------------------------------------------------
# TLC_106 — Endbringer Umbra: trigger Deathrattles of 5 friendly minions.
# ---------------------------------------------------------------------------
def test_endbringer_umbra():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.opponent.hero.max_health = 80
    p1.opponent.hero.damage = 0
    for _ in range(6):
        m = p1.summon(LEPER_GNOME)  # Deathrattle: 2 dmg to enemy hero
        m.destroy()
        game.process_deaths()
    before = p1.opponent.hero.damage
    p1.give("TLC_106").play()
    # Exactly 5 deathrattles re-trigger => 10 extra damage.
    assert p1.opponent.hero.damage - before == 10


# ---------------------------------------------------------------------------
# TLC_107 — Stormbrewer: deal 3 first; Kindred: Gain Rush.
# ---------------------------------------------------------------------------
def test_stormbrewer_attacks_deal_three():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    sb = p1.summon("TLC_107")
    sb.turns_in_play = 1
    foe = p1.opponent.summon(YETI)  # 4/5
    sb.attack(foe)
    # 3 pre-damage, then 3 attack damage = 6 total on a 5-health Yeti -> dead.
    assert foe.dead


def test_stormbrewer_kindred_rush():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _kindred_setup(p1, game, ELEMENTAL_TOK)  # Stormbrewer is Elemental
    assert Race.ELEMENTAL in p1.races_played_last_turn
    sb = p1.give("TLC_107")
    sb.play()
    assert sb.rush

    game2 = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    sb2 = game2.player1.give("TLC_107")
    sb2.play()
    assert not sb2.rush


# ---------------------------------------------------------------------------
# TLC_109 — Relic Miner: destroy top of deck, Discover same Rarity.
# ---------------------------------------------------------------------------
def test_relic_miner():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    top = p1.card("TLC_401", zone=Zone.DECK)  # a COMMON-rarity minion
    assert Rarity(int(top.rarity)) == Rarity.COMMON
    p1.give("TLC_109").play()
    assert top.zone == Zone.REMOVEDFROMGAME
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    assert all(Rarity(int(c.rarity)) == Rarity.COMMON for c in p1.choice.cards)
    p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == 1


# ---------------------------------------------------------------------------
# TLC_110 — City Chief Esho: if all deck minions share a type, +2/+2 others.
# ---------------------------------------------------------------------------
def test_city_chief_esho_all_one_type():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for _ in range(3):
        p1.card(BLOODFEN, zone=Zone.DECK)  # all Beasts
    ally = p1.summon(YETI)  # 4/5
    p1.give("TLC_110").play()
    assert (ally.atk, ally.health) == (6, 7)


def test_city_chief_esho_mixed_types():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.card(BLOODFEN, zone=Zone.DECK)   # Beast
    p1.card(MURLOC_RAIDER, zone=Zone.DECK)  # Murloc
    ally = p1.summon(YETI)
    p1.give("TLC_110").play()
    assert (ally.atk, ally.health) == (4, 5)


# ---------------------------------------------------------------------------
# TLC_242 — Ancient Stegodon: Choose Taunt / Poisonous / +1/+1.
# ---------------------------------------------------------------------------
def test_ancient_stegodon_choices():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    s1 = p1.give("TLC_242"); s1.play()
    p1.choice.choose(p1.choice.cards[0])  # Taunt
    assert s1.taunt and len(p1.hand) == 0

    s2 = p1.give("TLC_242"); s2.play()
    p1.choice.choose(p1.choice.cards[1])  # Poisonous
    assert s2.poisonous

    s3 = p1.give("TLC_242"); s3.play()
    p1.choice.choose(p1.choice.cards[2])  # +1/+1
    assert (s3.atk, s3.health) == (2, 6)  # base 1/5


# ---------------------------------------------------------------------------
# TLC_243 — Whirling Stormdrake: Rush, Windfury; Kindred: Immune this turn.
# ---------------------------------------------------------------------------
def test_whirling_stormdrake_kindred_immune():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _kindred_setup(p1, game, ELEMENTAL_TOK)  # Stormdrake is Elemental/Dragon
    wd = p1.give("TLC_243"); wd.play()
    assert wd.immune
    assert wd.rush and wd.windfury
    game.end_turn()  # our OWN_TURN_END destroys the immune enchant
    assert not wd.immune


def test_whirling_stormdrake_no_kindred():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    wd = game.player1.give("TLC_243"); wd.play()
    assert not wd.immune


# ---------------------------------------------------------------------------
# TLC_244 — Curious Explorer: Deathrattle reduce a foe-hand minion's cost (2).
# ---------------------------------------------------------------------------
def test_curious_explorer():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    foe = p1.opponent.give(YETI)  # cost 4
    ce = p1.summon("TLC_244")
    ce.destroy()
    game.process_deaths()
    assert foe.cost == 2


# ---------------------------------------------------------------------------
# TLC_245 — Ancient Raptor: Choose +3 Atk / Divine Shield / DR two 1/1 Plants.
# ---------------------------------------------------------------------------
def test_ancient_raptor_choices():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    r1 = p1.give("TLC_245"); r1.play()
    p1.choice.choose(p1.choice.cards[0])  # +3 Attack
    assert r1.atk == 5  # base 2 + 3

    r2 = p1.give("TLC_245"); r2.play()
    p1.choice.choose(p1.choice.cards[1])  # Divine Shield
    assert r2.divine_shield

    r3 = p1.give("TLC_245"); r3.play()
    p1.choice.choose(p1.choice.cards[2])  # Deathrattle: two Plants
    assert r3.has_deathrattle
    r3.destroy()
    game.process_deaths()
    plants = [m for m in p1.field if m.id == "UNG_999t2t1"]
    assert len(plants) == 2


# ---------------------------------------------------------------------------
# TLC_246 — Ancient Pterrordax: Choose Stealth / Elusive / Windfury.
# ---------------------------------------------------------------------------
def test_ancient_pterrordax_choices():
    # Pterrordax costs 4, so use a fresh game per option to avoid mana limits.
    g1 = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    a = g1.player1.give("TLC_246"); a.play()
    g1.player1.choice.choose(g1.player1.choice.cards[0])  # Stealth
    assert a.stealthed

    g2 = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    b = g2.player1.give("TLC_246"); b.play()
    g2.player1.choice.choose(g2.player1.choice.cards[1])  # Elusive
    assert b.cant_be_targeted_by_abilities and b.cant_be_targeted_by_hero_powers

    g3 = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    c = g3.player1.give("TLC_246"); c.play()
    g3.player1.choice.choose(g3.player1.choice.cards[2])  # Windfury
    assert c.windfury


# ---------------------------------------------------------------------------
# TLC_247 — Primal Sabretooth: after attacking & killing a minion, copy it.
# ---------------------------------------------------------------------------
def test_primal_sabretooth():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    st = p1.summon("TLC_247")
    st.turns_in_play = 1
    assert st.stealthed
    victim = p1.opponent.summon(MURLOC_RAIDER)  # 2/1
    st.attack(victim)
    assert victim.dead
    assert [c.id for c in p1.hand] == [MURLOC_RAIDER]


# ---------------------------------------------------------------------------
# TLC_248 — Ultragigasaur: vanilla 14/28.
# ---------------------------------------------------------------------------
def test_ultragigasaur():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    m = game.player1.summon("TLC_248")
    assert (m.atk, m.health) == (14, 28)


# ---------------------------------------------------------------------------
# TLC_249 — Sizzling Cinder: Deathrattle deal 2 split among all enemies.
# ---------------------------------------------------------------------------
def test_sizzling_cinder():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.opponent.hero.max_health = 80
    p1.opponent.hero.damage = 0
    cind = p1.summon("TLC_249")
    cind.destroy()
    game.process_deaths()
    # No enemy minions, so all 2 damage lands on the enemy hero.
    assert p1.opponent.hero.damage == 2


# ---------------------------------------------------------------------------
# TLC_250 — Crater Gator: enemy hero can't be healed until our next turn.
# ---------------------------------------------------------------------------
def test_crater_gator():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    from fireplace.actions import Heal, Hit
    p1.opponent.hero.damage = 10
    p1.give("TLC_250").play()
    game.queue_actions(p1.opponent.hero, [Heal(p1.opponent.hero, 5)])
    assert p1.opponent.hero.damage == 10  # heal blocked
    # damage still applies
    game.queue_actions(p1.hero, [Hit(p1.opponent.hero, 3)])
    assert p1.opponent.hero.damage == 13
    game.end_turn(); game.end_turn()  # back to our turn -> block expires
    game.queue_actions(p1.opponent.hero, [Heal(p1.opponent.hero, 5)])
    assert p1.opponent.hero.damage == 8


# ---------------------------------------------------------------------------
# TLC_251 — Primalfin Challenger: arm next-Kindred-double flag.
# ---------------------------------------------------------------------------
def test_primalfin_challenger():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    assert p1.next_kindred_double == 0
    p1.give("TLC_251").play()
    assert p1.next_kindred_double == 1


# ---------------------------------------------------------------------------
# TLC_252 — Dissolving Ooze: destroy a friendly minion, Bones to hand.
# ---------------------------------------------------------------------------
def test_dissolving_ooze():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    victim = p1.summon(YETI)  # 4/5
    ooze = p1.give("TLC_252")
    ooze.play(target=victim)
    assert victim.dead
    bones = [c for c in p1.hand if c.id == "TLC_829t"]
    assert len(bones) == 1
    buff = bones[0].buffs[0]
    assert (buff.atk, buff.max_health) == (4, 5)


# ---------------------------------------------------------------------------
# TLC_253 — Petrified Ogre: Dormant, +2/+2 each turn (50% awaken instead).
# ---------------------------------------------------------------------------
def test_petrified_ogre():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    ogre = p1.summon("TLC_253")
    assert ogre.dormant
    assert (ogre.atk, ogre.health) == (5, 5)
    game.random.random = lambda: 0.99  # >= 0.5 => buff, not awaken
    game.end_turn(); game.end_turn()
    assert ogre.dormant
    assert (ogre.atk, ogre.health) == (7, 7)


def test_petrified_ogre_awakens():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    ogre = p1.summon("TLC_253")
    game.random.random = lambda: 0.0  # < 0.5 => awaken
    game.end_turn(); game.end_turn()
    assert not ogre.dormant


# ---------------------------------------------------------------------------
# TLC_254 — Tortollan Storyteller: end of turn, +1/+1 per distinct type.
# ---------------------------------------------------------------------------
def test_tortollan_storyteller():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    beast = p1.summon(BLOODFEN)     # 3/2
    murloc = p1.summon(MURLOC_RAIDER)  # 2/1
    ts = p1.summon("TLC_254")       # 1/2 (no race)
    game.end_turn()  # our OWN_TURN_END
    # Three distinct type-signatures (Beast, Murloc, none) each get +1/+1.
    assert (beast.atk, beast.health) == (4, 3)
    assert (murloc.atk, murloc.health) == (3, 2)
    assert (ts.atk, ts.health) == (2, 3)


# ---------------------------------------------------------------------------
# TLC_255 — Crystal Tender: gain empty Mana until both players equal.
# ---------------------------------------------------------------------------
def test_crystal_tender():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.max_mana = 5
    p1.opponent.max_mana = 8
    p1.give("TLC_255").play()
    assert p1.max_mana == 8


# ---------------------------------------------------------------------------
# TLC_256 — Marshland Thresher: after you cast a spell, gain Divine Shield.
# ---------------------------------------------------------------------------
def test_marshland_thresher():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    mt = p1.summon("TLC_256")
    assert not mt.divine_shield
    p1.give(FIREBALL).play(target=p1.opponent.hero)
    assert mt.divine_shield


# ---------------------------------------------------------------------------
# TLC_427 — Rockskipper: get a 1-Cost Rock that deals 3 damage.
# ---------------------------------------------------------------------------
def test_rockskipper():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("TLC_427").play()
    rocks = [c for c in p1.hand if c.id == "WW_001t"]
    assert len(rocks) == 1
    assert rocks[0].cost == 1


# ---------------------------------------------------------------------------
# TLC_429 — Steamfin Thief: Kindred: Summon two 1/1 Murlocs with Rush.
# ---------------------------------------------------------------------------
def test_steamfin_thief_kindred():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _kindred_setup(p1, game, MURLOC_RAIDER)  # Steamfin is a Murloc
    p1.give("TLC_429").play()
    murlocs = [m for m in p1.field if m.id == "TLC_429t"]
    assert len(murlocs) == 2
    assert all(m.rush for m in murlocs)


def test_steamfin_thief_no_kindred():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("TLC_429").play()
    assert not [m for m in p1.field if m.id == "TLC_429t"]


# ---------------------------------------------------------------------------
# TLC_454 — Scalehide Kodo: destroy lowest-Atk enemy; Kindred: highest.
# ---------------------------------------------------------------------------
def test_scalehide_kodo_no_kindred():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    low = p1.opponent.summon(MURLOC_RAIDER)  # atk 2
    high = p1.opponent.summon(YETI)          # atk 4
    p1.give("TLC_454").play()
    assert low.dead and not high.dead


def test_scalehide_kodo_kindred():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _kindred_setup(p1, game, BLOODFEN)  # Kodo is a Beast
    low = p1.opponent.summon(MURLOC_RAIDER)
    high = p1.opponent.summon(YETI)
    p1.give("TLC_454").play()
    assert high.dead and not low.dead


# ---------------------------------------------------------------------------
# TLC_465 — Stranglevine: Deathrattle give random ally a Bonus + this DR.
# ---------------------------------------------------------------------------
def test_stranglevine():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    ally = p1.summon(YETI)
    sv = p1.summon("TLC_465")
    sv.destroy()
    game.process_deaths()
    got_bonus = (ally.taunt or ally.divine_shield or ally.poisonous
                 or ally.windfury or ally.rush or ally.lifesteal)
    assert got_bonus
    assert ally.has_deathrattle  # the propagated deathrattle


# ---------------------------------------------------------------------------
# TLC_468 — Blob of Tar: Poisonous, Taunt; DR two 1/2 Blobs (Poison + Taunt).
# ---------------------------------------------------------------------------
def test_blob_of_tar():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    blob = p1.summon("TLC_468")
    assert blob.poisonous and blob.taunt
    blob.destroy()
    game.process_deaths()
    spawned = [m for m in p1.field]
    assert len(spawned) == 2
    assert any(m.poisonous for m in spawned)
    assert any(m.taunt for m in spawned)


# ---------------------------------------------------------------------------
# TLC_480 — Krog, Crater King: end of turn, set all enemy minions to 1/1.
# ---------------------------------------------------------------------------
def test_krog_crater_king():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("TLC_480")
    enemy = p1.opponent.summon(YETI)  # 4/5
    game.end_turn()  # our OWN_TURN_END
    assert (enemy.atk, enemy.health) == (1, 1)


# ---------------------------------------------------------------------------
# TLC_603 — Platysaur: Battlecry draw; Deathrattle discard it.
# ---------------------------------------------------------------------------
def test_platysaur():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    drawn = p1.card(YETI, zone=Zone.DECK)
    plat = p1.give("TLC_603")
    plat.play()
    assert drawn.zone == Zone.HAND
    field_plat = [m for m in p1.field if m.id == "TLC_603"][0]
    field_plat.destroy()
    game.process_deaths()
    # Discard removes the drawn card from hand (engine discards to
    # REMOVEDFROMGAME) — it is no longer in hand.
    assert drawn.zone != Zone.HAND
    assert drawn not in p1.hand


# ---------------------------------------------------------------------------
# TLC_605 — Tar Tyrant: +6 Attack during opponent's turn.
# ---------------------------------------------------------------------------
def test_tar_tyrant():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    tt = p1.summon("TLC_605")  # base 1 atk
    assert tt.taunt and tt.lifesteal
    assert tt.atk == 1
    game.end_turn()  # now opponent's turn
    assert tt.atk == 7


# ---------------------------------------------------------------------------
# TLC_621 — Willful Watcher: Taunt; Deathrattle destroy top 3 deck cards.
# ---------------------------------------------------------------------------
def test_willful_watcher():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for _ in range(5):
        p1.card(YETI, zone=Zone.DECK)
    ww = p1.summon("TLC_621")
    assert ww.taunt
    ww.destroy()
    game.process_deaths()
    assert len(p1.deck) == 2  # 5 - 3 milled


# ---------------------------------------------------------------------------
# TLC_829 — Ravenous Devilsaur: destroy a minion; Kindred: gain its stats.
# ---------------------------------------------------------------------------
def test_ravenous_devilsaur_no_kindred():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    foe = p1.opponent.summon(YETI)
    dv = p1.give("TLC_829")
    dv.play(target=foe)
    assert foe.dead
    assert (dv.atk, dv.health) == (3, 3)  # unchanged base


def test_ravenous_devilsaur_kindred():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _kindred_setup(p1, game, BLOODFEN)  # Devilsaur is a Beast
    foe = p1.opponent.summon(YETI)  # 4/5
    dv = p1.give("TLC_829")
    dv.play(target=foe)
    assert foe.dead
    assert (dv.atk, dv.health) == (7, 8)  # 3/3 + 4/5


# ---------------------------------------------------------------------------
# TLC_831 — Pterrordax Egg: DR summon 3/3 that steals 1 Health from others.
# ---------------------------------------------------------------------------
def test_pterrordax_egg():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    egg = p1.summon("TLC_831")
    other = p1.summon(YETI)          # 4/5
    enemy = p1.opponent.summon(YETI)  # 4/5
    egg.destroy()
    game.process_deaths()
    pter = [m for m in p1.field if m.id == "TLC_831t"][0]
    # 3/3 base + steals 1 health from each of the 2 other minions => +2 health.
    assert (pter.atk, pter.health) == (3, 5)
    assert other.health == 4
    assert enemy.health == 4


# ---------------------------------------------------------------------------
# TLC_888 — Cloud Serpent: get a copy of another Elemental/Dragon in hand.
# ---------------------------------------------------------------------------
def test_cloud_serpent():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give(ELEMENTAL_TOK)  # one Elemental in hand
    p1.give("TLC_888").play()
    copies = [c for c in p1.hand if c.id == ELEMENTAL_TOK]
    assert len(copies) == 2


# ---------------------------------------------------------------------------
# TLC_987 — Questing Assistant: if you played a Quest this game, deal 2.
# ---------------------------------------------------------------------------
def test_questing_assistant_with_quest():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.MAGE)
    p1 = game.player1
    p1.opponent.hero.max_health = 80
    p1.opponent.hero.damage = 0
    p1.give("UNG_028").play()  # The Marsh Queen (Quest)
    qa = p1.give("TLC_987")
    qa.play(target=p1.opponent.hero)
    assert p1.opponent.hero.damage == 2


def test_questing_assistant_no_quest():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.opponent.hero.max_health = 80
    p1.opponent.hero.damage = 0
    qa = p1.give("TLC_987")
    qa.play(target=p1.opponent.hero)
    assert p1.opponent.hero.damage == 0
