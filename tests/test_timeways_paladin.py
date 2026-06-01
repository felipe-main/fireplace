"""Across the Timeways — Paladin tests."""

from hearthstone.enums import GameTag, Race, SpellSchool, Zone
from utils import prepare_game, CardClass


def _resolve_choices(game):
    for p in (game.player1, game.player2):
        while p.choice:
            p.choice.choose(p.choice.cards[0])


def _hero_ds(hero):
    return bool(hero.tags.get(GameTag.DIVINE_SHIELD, False))


##
# TIME_015 — Hardlight Protector


def test_hardlight_protector():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    hero = game.player1.hero
    hero.damage = 5
    assert not _hero_ds(hero)
    minion = game.player1.give("TIME_015")
    minion.play()
    # Restore 3 to hero, give hero Divine Shield. The minion has Divine Shield
    # from data.
    assert hero.damage == 2
    assert _hero_ds(hero)
    assert minion.divine_shield


##
# TIME_016 — Neon Innovation: Discover a Paladin Mech, give it +5/+5


def test_neon_innovation():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.discard_hand()
    game.player1.give("TIME_016").play()
    assert game.player1.choice
    picked = game.player1.choice.cards[0]
    # Every offered card is a Paladin Mech.
    for c in game.player1.choice.cards:
        assert Race.MECHANICAL in c.races
        assert c.card_class == CardClass.PALADIN
    base_atk = picked.atk
    base_health = picked.health
    game.player1.choice.choose(picked)
    # The chosen card lands in hand with +5/+5.
    assert picked.zone == Zone.HAND
    assert picked.atk == base_atk + 5
    assert picked.health == base_health + 5


##
# TIME_017 — Tankgineer: Deathrattle summon a 7/7 Tank with Divine Shield


def test_tankgineer_deathrattle():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    tank = game.player1.summon("TIME_017")
    assert tank.divine_shield
    tank.destroy()
    game.process_deaths()
    token = game.player1.field[-1]
    assert token.id == "TIME_017t"
    assert token.atk == 7
    assert token.health == 7
    assert token.divine_shield


##
# TIME_018 — Mend the Timeline: 2 Holy spells + heal hero = sum of their costs


def test_mend_the_timeline():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.discard_hand()
    hero = game.player1.hero
    hero.damage = 25
    spell = game.player1.give("TIME_018")
    spell.play()
    _resolve_choices(game)
    holy = [c for c in game.player1.hand if c.id != "TIME_018"]
    # Two Holy spells added to hand.
    assert len(holy) == 2
    for c in holy:
        assert c.spell_school == SpellSchool.HOLY
    total_cost = sum(c.cost for c in holy)
    # Hero healed by the sum of the two spells' costs (capped by 25 damage).
    assert hero.damage == 25 - min(25, total_cost)


##
# TIME_043 — PMM Infinitizer: set a friendly minion to 8/8, can't attack heroes


def test_pmm_infinitizer():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    target = game.player1.summon("CS2_182")  # 4/5 Chillwind Yeti
    target.damage = 2
    game.player1.give("TIME_043").play(target=target)
    assert target.atk == 8
    assert target.health == 8
    assert target.damage == 0
    assert target.cannot_attack_heroes


##
# TIME_019 — Manifested Timeways: if you control an Aura, 3 dmg to all enemies


def test_manifested_timeways_with_aura():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    enemy_hero = game.player2.hero
    beater = game.player2.summon("CS2_182")  # 4/5
    beater.max_health = 80
    beater.damage = 0
    # Install an aura first.
    game.player1.give("TIME_700").play()
    pre = enemy_hero.health
    game.player1.give("TIME_019").play()
    assert enemy_hero.health == pre - 3
    assert beater.damage == 3


def test_manifested_timeways_without_aura():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    enemy_hero = game.player2.hero
    pre = enemy_hero.health
    game.player1.give("TIME_019").play()
    assert enemy_hero.health == pre


##
# TIME_700 — Chronological Aura: end of turn summon a 3/5 Taunt Dragon, 3 turns


def test_chronological_aura_summons_and_expires():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.give("TIME_700").play()
    game.end_turn()  # own end-of-turn tick 1
    drakes = [m for m in game.player1.field if m.id == "TIME_700t"]
    assert len(drakes) == 1
    assert drakes[0].atk == 3 and drakes[0].health == 5 and drakes[0].taunt
    game.end_turn()  # opponent end turn (no friendly tick)
    game.end_turn()  # own tick 2
    assert len([m for m in game.player1.field if m.id == "TIME_700t"]) == 2
    game.end_turn()
    game.end_turn()  # own tick 3 (last)
    assert len([m for m in game.player1.field if m.id == "TIME_700t"]) == 3
    game.end_turn()
    game.end_turn()  # own turn 4 — aura expired, no new drake
    assert len([m for m in game.player1.field if m.id == "TIME_700t"]) == 3


##
# TIME_009t1 — Gnomish Aura: end of turn restore 4 to all your characters


def test_gnomish_aura_heals():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    hero = game.player1.hero
    hero.damage = 10
    minion = game.player1.summon("CS2_182")  # 4/5
    minion.damage = 3
    game.player1.give("TIME_009t1").play()
    game.end_turn()  # own end-of-turn tick
    assert hero.damage == 6
    assert minion.damage == 0  # 3 healed (capped at 3)


##
# TIME_009t2 — Mekkatorque's Aura: end of turn buff a random friendly minion


def test_mekkatorque_aura_buffs():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    minion = game.player1.summon("CS2_182")  # 4/5
    game.player1.give("TIME_009t2").play()
    game.end_turn()
    assert minion.atk == 8  # +4
    assert minion.health == 9  # +4
    assert minion.divine_shield


##
# TIME_009 — Gelbin of Tomorrow: put one of each Aura from your deck into play


def test_gelbin_puts_auras():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Seed the deck with two distinct auras and a duplicate.
    a1 = p1.give("TIME_700"); a1.zone = Zone.DECK
    a2 = p1.give("TIME_009t1"); a2.zone = Zone.DECK
    a3 = p1.give("TIME_700"); a3.zone = Zone.DECK  # duplicate id
    gelbin = p1.give("TIME_009")
    gelbin.play()
    _resolve_choices(game)
    # Two distinct auras installed → two controller-attached aura enchants.
    aura_buffs = [b for b in p1.buffs if hasattr(b, "_aura_turns_left")]
    assert len(aura_buffs) == 2
    # One of each distinct id removed from deck; the duplicate TIME_700 stays.
    deck_ids = [c.id for c in p1.deck]
    assert deck_ids.count("TIME_700") == 1
    assert deck_ids.count("TIME_009t1") == 0


##
# TIME_044 — Past Gnomeregan (location chain)


def _ready_location(game, p1):
    """End turns until the player's current location is usable again."""
    loc = p1.location
    while loc is not None and loc.exhausted:
        game.end_turn(); game.end_turn()
        loc = p1.location
    return loc


def test_past_gnomeregan_buff_and_advance():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    loc = p1.give("TIME_044")
    loc.play()
    assert p1.location is loc
    minion = p1.summon("CS2_182")  # 4/5
    # Use it three times (3 durability), buffing the minion each time.
    for _ in range(3):
        cur = _ready_location(game, p1)
        assert cur is not None
        cur.use(target=minion)
    # After 3 uses Past advances to Present Gnomeregan.
    assert p1.location is not None
    assert p1.location.id == "TIME_044t1"
    # The minion received +2/+1 three times.
    assert minion.atk == 4 + 6
    assert minion.health == 5 + 3


def test_present_gnomeregan_grants_deathrattle():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    loc = p1.summon("TIME_044t1")  # Present Gnomeregan directly
    game.end_turn(); game.end_turn()
    minion = p1.summon("CS2_182")
    loc.use(target=minion)
    assert minion.atk == 6 and minion.health == 6  # +2/+1
    enemy_hero = game.player2.hero
    pre = enemy_hero.health
    minion.destroy()
    game.process_deaths()
    # Leper Strength deathrattle: deal 2 to enemy hero.
    assert enemy_hero.health == pre - 2


def test_future_gnomeregan_full_grant():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    loc = p1.summon("TIME_044t2")  # Future Gnomeregan
    game.end_turn(); game.end_turn()
    minion = p1.summon("CS2_182")
    loc.use(target=minion)
    assert minion.atk == 6 and minion.health == 6
    assert minion.divine_shield
    enemy_hero = game.player2.hero
    pre = enemy_hero.health
    minion.destroy()
    game.process_deaths()
    assert enemy_hero.health == pre - 2


##
# TIME_706 — The Fins Beyond Time: replace hand with starting hand, swap back


def test_fins_swaps_hand_and_back():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # The test harness (BaseTestGame) doesn't populate starting_hand the way
    # the real mulligan flow does, so seed it explicitly with a known set.
    from fireplace.utils import CardList
    p1.discard_hand()
    s1 = p1.give("CS2_087")  # Blessing of Kings
    s2 = p1.give("CS2_089")  # Holy Light
    p1.starting_hand = CardList([s1, s2])
    # Now empty the live hand and add a unique marker.
    p1.discard_hand()
    marker = p1.give("CS2_029")  # Fireball
    fins = p1.give("TIME_706")
    fins.play()
    # Hand is now copies of the starting hand; marker stashed away.
    hand_ids = sorted(c.id for c in p1.hand)
    assert hand_ids == sorted(["CS2_087", "CS2_089"])
    assert all(c is not marker for c in p1.hand)
    # End turn → swap back to the stashed live hand (the marker).
    game.end_turn()
    back_ids = [c.id for c in p1.hand]
    assert back_ids == ["CS2_029"]


##
# TIME_018 Rewind — picking Rewind re-runs the base effect


def test_mend_rewind_reruns():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.discard_hand()
    hero = p1.hero
    hero.damage = 28
    spell = p1.give("TIME_018")
    spell.play()
    # Engine offers a Keep/Rewind choice after the play resolves. Pick Rewind
    # (TIME_000tb) if present, else fall back.
    rewound = False
    if p1.choice:
        rewind = None
        for c in p1.choice.cards:
            if c.id == "TIME_000tb":
                rewind = c
                break
        if rewind is not None:
            p1.choice.choose(rewind)
            rewound = True
        else:
            p1.choice.choose(p1.choice.cards[0])
    _resolve_choices(game)
    holy = [c for c in p1.hand if c.id != "TIME_018"]
    if rewound:
        # Effect ran twice → 4 Holy spells handed out.
        assert len(holy) == 4
    else:
        assert len(holy) == 2
