"""The Lost City of Un'Goro - Warlock (TLC_) unit tests."""

from utils import prepare_game

from hearthstone.enums import CardClass, CardType, Race, SpellSchool, Zone

from fireplace.cards.utils import enums

BEAST = "CS2_172"   # Bloodfen Raptor (Beast 3/2)
MURLOC = "CS2_168"  # Murloc Raider (Murloc 2/1)
YETI = "CS2_182"    # Chillwind Yeti (4/5)
BOAR = "CS2_171"    # Stonetusk Boar (1-cost 1/1)


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def _make_temporary(card):
    card.tags[enums.TEMPORARY] = True
    card.game.refresh_auras()


# ---------------------------------------------------------------------------
# TLC_450 Spelunker - Battlecry: Your next Temporary card costs (2) less.
# ---------------------------------------------------------------------------

def test_spelunker_discounts_next_temporary():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.give("TLC_450").play()
    assert "TLC_450host" in [b.id for b in p1.hero.buffs]

    yeti = p1.give(YETI)          # base cost 4
    assert yeti.cost == 4
    _make_temporary(yeti)
    assert yeti.cost == 2         # reduced by (2)

    # A non-Temporary card is unaffected.
    plain = p1.give(YETI)
    assert plain.cost == 4


def test_spelunker_only_affects_one_temporary():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.give("TLC_450").play()

    first = p1.give(BOAR)         # 1-cost; cost clamps at 0 with -2
    _make_temporary(first)
    assert first.cost == 0
    first.play()                  # playing a Temporary consumes the host

    assert "TLC_450host" not in [b.id for b in p1.hero.buffs]
    second = p1.give(YETI)
    _make_temporary(second)
    assert second.cost == 4       # no longer discounted


# ---------------------------------------------------------------------------
# TLC_463 Razidir - Battlecry: Discard a random card from your hand.
# Kindred: Your opponent's hand instead.
# ---------------------------------------------------------------------------

def test_razidir_no_kindred_discards_own():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    p1.give(YETI)
    p1.give(MURLOC)
    razidir = p1.give("TLC_463")
    assert len(p1.hand) == 3              # 2 vanilla + Razidir
    opp_before = len(game.player2.hand)
    razidir.play()
    # Razidir leaves hand (played) and exactly one vanilla card is discarded.
    assert len(p1.hand) == 1
    assert len(game.player2.hand) == opp_before


def test_razidir_kindred_discards_opponent():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Razidir is a Demon/Beast; play a Beast last turn to arm Kindred.
    p1.give(BEAST).play()
    game.end_turn(); game.end_turn()
    assert Race.BEAST in p1.races_played_last_turn

    for c in list(p1.hand):
        c.discard()
    p1.give(YETI)
    p1.give(MURLOC)
    razidir = p1.give("TLC_463")
    own_before = len(p1.hand)             # 3
    opp_before = len(game.player2.hand)
    razidir.play()
    # Only Razidir leaves our hand; none of our cards are discarded.
    assert len(p1.hand) == own_before - 1
    # Opponent loses exactly one card.
    assert len(game.player2.hand) == opp_before - 1


# ---------------------------------------------------------------------------
# TLC_467 Whispering Stone - Taunt, Deathrattle: Get 2 random Fel spells.
# They cost Health instead of Mana.
# ---------------------------------------------------------------------------

def test_whispering_stone_deathrattle():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    before = len(p1.hand)
    stone = p1.summon("TLC_467")
    assert stone.taunt
    stone.destroy()
    game.process_deaths()
    assert len(p1.hand) - before == 2
    fel = [c for c in p1.hand if getattr(c, "spell_school", None) == SpellSchool.FEL]
    assert len(fel) == 2
    assert all(c.card_costs_health for c in fel)


# ---------------------------------------------------------------------------
# TLC_469 Tunnel Terror - Deathrattle: Get two random Temporary 2-Cost minions.
# ---------------------------------------------------------------------------

def test_tunnel_terror_deathrattle():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    before = len(p1.hand)
    terror = p1.summon("TLC_469")
    terror.destroy()
    game.process_deaths()
    got = [c for c in p1.hand if c.tags.get(enums.TEMPORARY)]
    assert len(p1.hand) - before == 2
    assert len(got) == 2
    assert all(c.type == CardType.MINION for c in got)
    assert all(c.cost == 2 for c in got)


# ---------------------------------------------------------------------------
# TLC_479 Deathrot Maw - Taunt, Deathrattle: Summon a random Fel Beast.
# ---------------------------------------------------------------------------

def test_deathrot_maw_summons_fel_beast():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    maw = p1.summon("TLC_479")
    assert maw.taunt
    maw.destroy()
    game.process_deaths()
    beasts = [m for m in p1.field if m.id in ("TLC_446t2", "TLC_446t3", "TLC_446t4")]
    assert len(beasts) == 1


# ---------------------------------------------------------------------------
# TLC_447 Caustic Fumes - Destroy an enemy minion.
# Kindred: Deal 2 damage to all minions.
# ---------------------------------------------------------------------------

def test_caustic_fumes_no_kindred():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    enemy = game.player2.summon(YETI)
    ally = p1.summon(BEAST)         # 3/2
    fumes = p1.give("TLC_447")
    fumes.play(target=enemy)
    assert enemy.dead               # destroyed
    assert not ally.dead            # no AoE without Kindred
    assert ally.health == 2


def test_caustic_fumes_kindred():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Caustic Fumes is a Fel spell; cast one last turn to arm Kindred.
    e0 = game.player2.summon(YETI)
    p1.give("TLC_447").play(target=e0)
    game.end_turn(); game.end_turn()
    assert SpellSchool.FEL in p1.schools_played_last_turn

    enemy = game.player2.summon(YETI)   # destroyed by the targeted half
    ally = p1.summon(BEAST)             # buff to 3/5 so it survives the AoE
    ally.max_health = 5
    ally.damage = 0
    other = game.player2.summon(BEAST)  # 3/2 -> dies to the 2 AoE
    fumes = p1.give("TLC_447")
    fumes.play(target=enemy)
    assert enemy.dead                   # target destroyed outright
    assert other.dead                   # 3/2 killed by 2 AoE
    assert not ally.dead
    assert ally.damage == 2             # ally took exactly 2 from AoE


# ---------------------------------------------------------------------------
# TLC_451 Cursed Catacombs - Discover a minion from your deck. Make it Temporary.
# ---------------------------------------------------------------------------

def test_cursed_catacombs():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    cc = p1.give("TLC_451")
    cc.play()
    _resolve_choices(p1)
    got = [c for c in p1.hand if c.tags.get(enums.TEMPORARY)]
    assert len(got) == 1
    assert got[0].type == CardType.MINION


# ---------------------------------------------------------------------------
# TLC_446 Escape the Underfel - Quest: Play 6 Temporary cards. Reward: Rift.
# ---------------------------------------------------------------------------

def test_escape_the_underfel_quest():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    quest = p1.give("TLC_446")
    quest.play()
    assert quest.zone == Zone.SECRET
    assert quest.progress_total == 6

    for i in range(5):
        t = p1.give(BOAR)
        t.tags[enums.TEMPORARY] = True
        t.play()
    assert quest.progress == 5
    assert not quest.finished
    assert not any(c.id == "TLC_446t1" for c in p1.hand)

    t = p1.give(BOAR)
    t.tags[enums.TEMPORARY] = True
    t.play()
    # 6th Temporary play completes the quest -> Underfel Rift to hand.
    assert any(c.id == "TLC_446t1" for c in p1.hand)
    assert quest.zone != Zone.SECRET


def test_escape_the_underfel_ignores_non_temporary():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    quest = p1.give("TLC_446")
    quest.play()
    for i in range(4):
        p1.give(BOAR).play()        # not Temporary
    assert quest.progress == 0


# ---------------------------------------------------------------------------
# TLC_446t1 Underfel Rift - throw a card in to summon 2 random Fel Beasts.
# ---------------------------------------------------------------------------

def test_underfel_rift_summons_two_fel_beasts():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    p1.give(YETI)                   # a card to "throw in"
    rift = p1.give("TLC_446t1")
    rift.play()
    beasts = [m for m in p1.field if m.id in ("TLC_446t2", "TLC_446t3", "TLC_446t4")]
    assert len(beasts) == 2
    # The Yeti was thrown in (discarded); hand is now empty.
    assert len(p1.hand) == 0


# ---------------------------------------------------------------------------
# TLC_466 Story of Lakkari - EOT discard a card, fill board with 3/2 Imps.
# Lasts 3 turns.
# ---------------------------------------------------------------------------

def test_story_of_lakkari_fills_board_three_turns():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.give("TLC_466").play()
    counts = []
    for _ in range(4):
        game.end_turn(); game.end_turn()
        imps = [m for m in p1.field if m.id == "TLC_466t"]
        counts.append(len(imps))
        if imps:
            assert imps[0].atk == 3 and imps[0].max_health == 2
        for m in list(imps):
            m.destroy()
        game.process_deaths()
    # Three end-of-turns fill the board (7 imps each); the fourth does not.
    assert counts == [7, 7, 7, 0]


# ---------------------------------------------------------------------------
# TLC_449 Bloodpetal Biome (Location) - Discover a Temporary 1-Cost minion.
# ---------------------------------------------------------------------------

def test_bloodpetal_biome_discovers_temporary_one_cost():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    loc = p1.summon("TLC_449")
    loc.use()
    _resolve_choices(p1)
    got = [c for c in p1.hand if c.tags.get(enums.TEMPORARY)]
    assert len(got) == 1
    assert got[0].type == CardType.MINION
    assert got[0].cost == 1
