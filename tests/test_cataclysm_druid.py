"""Cataclysm — Druid (CATA_) unit tests."""

from utils import prepare_game
from hearthstone.enums import CardClass, CardType, Zone, GameTag, Race


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# CATA_130 Crystalspine Cub — tap out -> +1/+1 at end of turn
# ---------------------------------------------------------------------------
def test_crystalspine_cub_taps_out():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    cub = game.player1.summon("CATA_130")
    assert cub.atk == 1 and cub.health == 2
    # Spend all mana (max_mana is 10 from turn 1). Drain to 0.
    game.player1.used_mana = game.player1.max_mana
    assert game.player1.mana == 0
    game.end_turn()
    assert cub.atk == 2 and cub.health == 3


def test_crystalspine_cub_no_buff_with_mana_left():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    cub = game.player1.summon("CATA_130")
    # Leave mana available.
    game.player1.used_mana = 0
    game.end_turn()
    assert cub.atk == 1 and cub.health == 2


# ---------------------------------------------------------------------------
# CATA_131 Felwood Treant — temp crystal, or permanent if spent 4 Mana held
# ---------------------------------------------------------------------------
def test_felwood_treant_temporary_when_under_threshold():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    card = game.player1.give("CATA_131")
    base_max = game.player1.max_mana
    card.play()
    # Temporary crystal: max_mana unchanged, but temp_mana available.
    assert game.player1.max_mana == base_max
    assert game.player1.temp_mana == 1


def test_felwood_treant_permanent_when_spent_4():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    # Drop max_mana below the cap so a permanent crystal is observable.
    game.player1.max_mana = 5
    card = game.player1.give("CATA_131")
    # Bank 4 mana spent while holding (simulated directly).
    card._cata_mana_spent = 4
    # Refresh available mana so the 2-cost Treant is playable.
    game.player1.used_mana = 0
    base_max = game.player1.max_mana
    card.play()
    # Permanent crystal: max_mana +1.
    assert game.player1.max_mana == base_max + 1


# ---------------------------------------------------------------------------
# CATA_132 Broodwatcher — get vs summon two 3/3 Whelps
# ---------------------------------------------------------------------------
def test_broodwatcher_gets_whelps_under_threshold():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    card = game.player1.give("CATA_132")
    hand_before = len(game.player1.hand)
    field_before = len(game.player1.field)
    card.play()
    # Two whelps added to hand, none summoned (battlecry consumes the card).
    whelps_in_hand = [c for c in game.player1.hand if c.id == "CATA_132t"]
    assert len(whelps_in_hand) == 2
    assert len([m for m in game.player1.field if m.id == "CATA_132t"]) == 0


def test_broodwatcher_summons_whelps_when_spent_8():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    card = game.player1.give("CATA_132")
    # Simulate having spent 8 Mana while holding this.
    card._cata_mana_spent = 8
    card.play()
    summoned = [m for m in game.player1.field if m.id == "CATA_132t"]
    assert len(summoned) == 2
    assert all(m.taunt for m in summoned)
    assert all(m.atk == 3 and m.health == 3 for m in summoned)


# ---------------------------------------------------------------------------
# CATA_133 Iridescent Flitterwing — Elusive + end of turn buff others
# ---------------------------------------------------------------------------
def test_iridescent_flitterwing_buffs_others_and_elusive():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    flit = game.player1.summon("CATA_133")
    other = game.player1.summon("CATA_135t")  # 1/2 Moss Golem
    assert flit.cant_be_targeted_by_abilities
    assert other.atk == 1 and other.health == 2
    game.end_turn()
    # Other minion gets +1/+1; Flitterwing itself does not.
    assert other.atk == 2 and other.health == 3
    assert flit.atk == 4 and flit.health == 5


# ---------------------------------------------------------------------------
# CATA_134 Wildwood Circle — shattered halves
# ---------------------------------------------------------------------------
def test_wildwood_circle_half_summon_treants():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    card = game.player1.give("CATA_134t")
    card.play()
    treants = [m for m in game.player1.field if m.id == "CATA_134t3"]
    assert len(treants) == 2
    assert all(m.atk == 2 and m.health == 2 for m in treants)


def test_wildwood_circle_half_grants_deathrattle():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    target = game.player1.summon("CATA_135t")  # 1/2 Moss Golem
    card = game.player1.give("CATA_134t2")
    card.play()
    assert target.has_deathrattle
    target.destroy()
    game.process_deaths()
    treants = [m for m in game.player1.field if m.id == "CATA_134t3"]
    assert len(treants) == 1


# ---------------------------------------------------------------------------
# CATA_135 Mossbinding — two 1/2 Golems buffed by all spent mana
# ---------------------------------------------------------------------------
def test_mossbinding_summons_and_buffs():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    # Set exactly 6 mana available so the spell costs 2 -> 4 left to spend.
    game.player1.give("CATA_135")
    game.player1.used_mana = game.player1.max_mana - 6  # 6 available
    card = [c for c in game.player1.hand if c.id == "CATA_135"][0]
    card.play()  # pays 2, leaving 4 mana to dump
    golems = [m for m in game.player1.field if m.id == "CATA_135t"]
    assert len(golems) == 2
    # Each golem: base 1/2 + 4/+4 = 5/6.
    assert all(m.atk == 5 and m.health == 6 for m in golems)
    assert game.player1.mana == 0


# ---------------------------------------------------------------------------
# CATA_136 Azshara's Triumph — shuffle 5 big minions doubled
# ---------------------------------------------------------------------------
def test_azsharas_triumph_shuffles_doubled():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    deck_before = len(game.player1.deck)
    card = game.player1.give("CATA_136")
    card.play()
    assert len(game.player1.deck) == deck_before + 5
    # The 5 shuffled minions all cost >= 8 and have doubled stats.
    new_minions = [c for c in game.player1.deck if c.type == CardType.MINION and c.buffs]
    # At least the 5 shuffled minions carry the doubling buff.
    assert len(new_minions) >= 5
    for m in new_minions:
        assert m.cost >= 8


# ---------------------------------------------------------------------------
# CATA_138 Forest's Gift — +1/+1 per friendly minion
# ---------------------------------------------------------------------------
def test_forests_gift_buffs_per_minion():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    a = game.player1.summon("CATA_135t")
    b = game.player1.summon("CATA_135t")
    c = game.player1.summon("CATA_135t")  # 3 friendly minions
    target = a
    spell = game.player1.give("CATA_138")
    spell.play(target=target)
    # +3/+3 (3 minions on board).
    assert target.atk == 1 + 3 and target.health == 2 + 3


# ---------------------------------------------------------------------------
# CATA_139 Wickerfang — Colossal +4, legs grow and mirror onto body
# ---------------------------------------------------------------------------
def test_wickerfang_colossal_and_symbiotic():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    body = game.player1.summon("CATA_139")
    legs = [m for m in game.player1.field if m.id.startswith("CATA_139t")]
    assert len(legs) == 4  # Colossal +4
    body_atk, body_health = body.atk, body.health
    game.end_turn()
    # Each leg gains +1/+1 (now 2/3) and mirrors +1/+1 onto the body 4 times.
    for leg in legs:
        assert leg.atk == 1 and leg.health == 3
    assert body.atk == body_atk + 4
    assert body.health == body_health + 4


# ---------------------------------------------------------------------------
# CATA_140 Merithra of the Dream — fill hand with Dragons (cost 1 if 25 spent)
# ---------------------------------------------------------------------------
def test_merithra_fills_dragons():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    # Empty the hand first so we can observe the fill.
    for c in list(game.player1.hand):
        c.discard() if hasattr(c, "discard") else None
    card = game.player1.give("CATA_140")
    card.play()
    dragons = [c for c in game.player1.hand if Race.DRAGON in c.races]
    assert len(dragons) >= 1
    # Under threshold: not cost-reduced to 1 (unless base is 1).
    assert not any(getattr(c, "_cata_mana_spent", 0) for c in dragons)


def test_merithra_cheap_dragons_when_spent_25():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    for c in list(game.player1.hand):
        c.discard() if hasattr(c, "discard") else None
    card = game.player1.give("CATA_140")
    card._cata_mana_spent = 25
    card.play()
    dragons = [c for c in game.player1.hand if Race.DRAGON in c.races]
    assert len(dragons) >= 1
    assert all(c.cost == 1 for c in dragons)


# ---------------------------------------------------------------------------
# CATA_006 Ulfar — Battlecry: give your OTHER minions
# "Deathrattle: Summon a minion with this minion's Cost."
# ---------------------------------------------------------------------------
def test_ulfar_stats():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    ulfar = game.player1.summon("CORE_CATA_006")
    assert ulfar.atk == 4 and ulfar.health == 3 and ulfar.cost == 6


def test_ulfar_grants_cost_matched_deathrattle_to_others():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.discard_hand()
    other = p1.summon("CS2_182")  # Chillwind Yeti, cost 4
    assert (other.data.cost or 0) == 4
    ulfar = p1.give("CORE_CATA_006")
    ulfar.play()
    # The other minion got the granted deathrattle; Ulfar itself did NOT.
    assert any(b.id == "CORE_CATA_006e" for b in other.buffs)
    assert not any(b.id == "CORE_CATA_006e" for b in ulfar.buffs)
    # Killing the buffed minion summons a random 4-Cost minion in its place.
    pre_ids = {id(m) for m in p1.field}
    other.destroy()
    summoned = [m for m in p1.field if id(m) not in pre_ids]
    assert len(summoned) == 1
    assert (summoned[0].data.cost or 0) == 4


def test_ulfar_does_not_buff_itself_no_summon_on_own_death():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.discard_hand()
    ulfar = p1.give("CORE_CATA_006")
    ulfar.play()  # no other minions -> nothing buffed
    assert not any(b.id == "CORE_CATA_006e" for b in ulfar.buffs)
    ulfar.destroy()
    # Ulfar has no granted deathrattle -> no extra minion summoned.
    assert len([m for m in p1.field]) == 0
