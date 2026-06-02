"""Cataclysm (CATA_) — Neutral tests."""

from hearthstone.enums import CardClass, GameTag, Race, Zone

from utils import prepare_empty_game, prepare_game


WISP = "CS2_231"          # 0/1/1 vanilla minion (even cost 0)
CHILLWIND = "CS2_182"     # 4/4/5 Chillwind Yeti (even cost 4)
BOULDERFIST = "CS2_200"   # 6/6/7 Boulderfist Ogre (even cost 6)
MAGMA = "EX1_620"         # 10-cost minion (Molten Giant base, even)
FIREBALL = "CS2_029"      # 4-cost fire spell
MOONFIRE = "CS2_008"      # 0-cost spell (even)
STONETUSK = "CS2_171"     # 1-cost (odd) Stonetusk Boar
A_DRAGON = "ds1_whelptoken"  # Whelp (Dragon race token), 1/1


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# CATA_111 Darkscale Broodmother — refresh 2 mana if holding a Dragon
# ---------------------------------------------------------------------------

def test_darkscale_broodmother_refreshes_with_dragon():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.current_player
    p1.give(A_DRAGON)  # a Dragon in hand
    p1.used_mana = 0
    card = p1.give("CATA_111")  # cost 3
    cost = card.cost
    card.play()
    # Play spends `cost`, then refresh 2: used_mana = cost - 2.
    assert p1.used_mana == cost - 2


def test_darkscale_broodmother_no_dragon_no_refresh():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.current_player
    # Clear hand so no Dragon held.
    for c in list(p1.hand):
        c.discard()
    p1.used_mana = 0
    card = p1.give("CATA_111")
    cost = card.cost
    card.play()
    assert p1.used_mana == cost


# ---------------------------------------------------------------------------
# CATA_180 War'loc — next cheap Murloc costs Health
# ---------------------------------------------------------------------------

def test_warloc_next_cheap_murloc_costs_health():
    # Battlecry arms "your next Murloc that costs (3) or less costs Health."
    # The next qualifying Murloc you play pays Health (not Mana), wherever it
    # came from; the flag is then consumed.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.discard_hand()
    p1.give("CATA_180").play()
    assert p1.next_cheap_murloc_costs_health is True
    murloc = p1.give("CS2_168")  # Murloc Raider — 1-cost Murloc
    hp, mana = p1.hero.health, p1.mana
    murloc.play()
    assert p1.hero.health == hp - 1          # paid 1 Health
    assert p1.mana == mana                   # no Mana spent
    assert p1.next_cheap_murloc_costs_health is False  # consumed
    # A second Murloc pays Mana normally.
    murloc2 = p1.give("CS2_168")
    hp2, mana2 = p1.hero.health, p1.mana
    murloc2.play()
    assert p1.hero.health == hp2             # no Health paid
    assert p1.mana == mana2 - 1              # Mana spent


def test_warloc_skips_murloc_costing_more_than_3():
    # A Murloc costing 4+ does not qualify -> pays Mana, and the flag stays
    # armed for the next cheap Murloc.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.discard_hand()
    p1.give("CATA_180").play()
    big = p1.give("AT_076")  # Murloc Knight — 4-cost Murloc
    hp = p1.hero.health
    big.play()
    assert p1.hero.health == hp                       # paid Mana, not Health
    assert p1.next_cheap_murloc_costs_health is True  # still armed


# ---------------------------------------------------------------------------
# CATA_185 Faceless Replicator — transform the killer
# ---------------------------------------------------------------------------

def test_faceless_replicator_transforms_killer():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    fr = p1.summon("CATA_185")  # 3/3
    killer = p2.summon(BOULDERFIST)  # 6/6
    # Killer hits Faceless Replicator dead.
    game.end_turn()  # p1 -> p2 turn so killer (p2) can attack
    killer.attack(fr)
    game.process_deaths()
    # The Boulderfist that killed it is transformed into a Faceless Replicator.
    assert any(m.id == "CATA_185" for m in p2.field)
    assert all(m.id != BOULDERFIST for m in p2.field)


# ---------------------------------------------------------------------------
# CATA_186 Stickybomb Saboteur — give opponent a Sabotage
# ---------------------------------------------------------------------------

def test_stickybomb_gives_opponent_sabotage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    before = len(p2.hand)
    card = p1.give("CATA_186")
    card.play()
    assert len(p2.hand) == before + 1
    assert any(c.id == "CATA_186t" for c in p2.hand)


# ---------------------------------------------------------------------------
# CATA_208 Selfless Protector — takes 1 extra damage
# ---------------------------------------------------------------------------

def test_selfless_protector_extra_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    prot = p1.summon("CATA_208")  # 2/6
    # Moonfire deals 1 -> Selfless Protector takes 1 + 1 = 2.
    moonfire = p2.give(MOONFIRE)
    game.end_turn()  # p2's turn
    moonfire.play(target=prot)
    assert prot.health == 6 - 2  # 1 base + 1 extra


# ---------------------------------------------------------------------------
# CATA_209 Battlefield Blaster — give a hand spell Spell Damage +1
# ---------------------------------------------------------------------------

def test_battlefield_blaster_buffs_hand_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    for c in list(p1.hand):
        c.discard()
    fb = p1.give(FIREBALL)  # 6-damage fire spell
    card = p1.give("CATA_209")
    card.play()
    assert fb._getattr("spellpower", 0) == 1
    # Cast it on a big target: 6 + 1 = 7 damage.
    enemy = p2.summon(BOULDERFIST)
    enemy.max_health = 80
    enemy.damage = 0
    fb.play(target=enemy)
    assert enemy.damage == 7


# ---------------------------------------------------------------------------
# CATA_210 Twilight Egg — deathrattle whelp that grows
# ---------------------------------------------------------------------------

def test_twilight_egg_summons_growing_whelp():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    egg = p1.summon("CATA_210")
    egg.destroy()
    game.process_deaths()
    whelp = p1.field[0]
    assert whelp.id == "CATA_210t"
    assert (whelp.atk, whelp.health) == (2, 2)
    # Grows +1/+1 at the start of your turn.
    game.end_turn()
    game.end_turn()  # back to p1 start
    assert (whelp.atk, whelp.health) == (3, 3)


# ---------------------------------------------------------------------------
# CATA_476 Bronze Keeper — end of turn summon 6/6 divine shield
# ---------------------------------------------------------------------------

def test_bronze_keeper_summons_at_end_of_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("CATA_476")
    game.end_turn()
    sandscale = [m for m in p1.field if m.id == "CATA_476t"]
    assert len(sandscale) == 1
    assert sandscale[0].divine_shield
    assert (sandscale[0].atk, sandscale[0].health) == (6, 6)


# ---------------------------------------------------------------------------
# CATA_497 Ultraxion — Herald + reduce Deathwing cost
# ---------------------------------------------------------------------------

def test_ultraxion_heralds_and_discounts_deathwing():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    dw = p1.give("CATA_190h")  # cost 10
    assert dw.cost == 10
    card = p1.give("CATA_497")
    card.play()
    assert p1.heralds_this_game == 1
    assert dw.cost == 9  # reduced by 1


# ---------------------------------------------------------------------------
# CATA_556 Carrier Whelp — get a cheap dragon
# ---------------------------------------------------------------------------

def test_carrier_whelp_gives_cheap_dragon():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    card = p1.give("CATA_556")
    card.play()
    assert len(p1.hand) == 1
    got = p1.hand[0]
    assert Race.DRAGON in got.races
    assert (got.cost or 0) <= 3


# ---------------------------------------------------------------------------
# CATA_612 Frostbitten Imp — Freeze self
# ---------------------------------------------------------------------------

def test_frostbitten_imp_freezes_self():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    card = p1.give("CATA_612")
    card.play()
    assert card.frozen is True


# ---------------------------------------------------------------------------
# CATA_613 Survivalist — Immune while alone
# ---------------------------------------------------------------------------

def test_survivalist_immune_while_alone():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    surv = p1.summon("CATA_613")
    assert surv.immune is True
    # Add another minion -> no longer immune.
    p1.summon(WISP)
    assert surv.immune is False


# ---------------------------------------------------------------------------
# CATA_614 Shadowed Informant — discover a spell
# ---------------------------------------------------------------------------

def test_shadowed_informant_discovers_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    card = p1.give("CATA_614")
    card.play()
    assert p1.choice is not None
    from hearthstone.enums import CardType
    assert all(c.type == CardType.SPELL for c in p1.choice.cards)
    _resolve_choices(p1)
    assert len(p1.hand) == 1


# ---------------------------------------------------------------------------
# CATA_615 Genn, Cursed King — transform when hand all-even/all-odd
# ---------------------------------------------------------------------------

def test_genn_transforms_when_hand_all_even():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    genn = p1.give("CATA_615")
    p1.give(CHILLWIND)  # cost 4 (even)
    p1.give(MOONFIRE)   # cost 0 (even)
    game.end_turn()
    game.end_turn()  # back to p1 start -> Hand event fires
    # Genn should have transformed into the Worgen King (CATA_615t).
    assert any(c.id == "CATA_615t" for c in p1.hand)
    assert all(c.id != "CATA_615" for c in p1.hand)


def test_genn_no_transform_mixed_parity():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    p1.give("CATA_615")
    p1.give(CHILLWIND)  # cost 4 (even)
    p1.give(STONETUSK)  # cost 1 (odd)  -> mixed
    game.end_turn()
    game.end_turn()
    assert any(c.id == "CATA_615" for c in p1.hand)
    assert all(c.id != "CATA_615t" for c in p1.hand)


# ---------------------------------------------------------------------------
# CATA_615t Genn, Worgen King — upgrades hero power
# ---------------------------------------------------------------------------

def test_worgen_king_upgrades_hero_power():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    before = p1.hero.power.id
    card = p1.give("CATA_615t")
    card.play()
    # Hero power was upgraded (id changed) and costs 1.
    assert p1.hero.power.id != before
    assert p1.hero.power.cost == 1


# ---------------------------------------------------------------------------
# CATA_616 Gronn Giant — cost reduced by last card played
# ---------------------------------------------------------------------------

def test_gronn_giant_cost_reduction():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    giant = p1.give("CATA_616")  # base cost 9
    assert giant.cost == 9
    # Play a 4-cost card.
    yeti = p1.give(CHILLWIND)
    yeti.play()
    assert p1.last_card_played is yeti
    assert giant.cost == 9 - 4  # reduced by 4


# ---------------------------------------------------------------------------
# CATA_720 Warmaster Blackhorn — destroy cheap deck cards both sides
# ---------------------------------------------------------------------------

def test_warmaster_blackhorn_destroys_cheap_deck_cards():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Seed each deck with a 1-cost and a 5-cost card.
    cheap1 = p1.give(WISP)  # 0-cost
    cheap1.zone = Zone.DECK
    big1 = p1.give(MAGMA)   # 10-cost (Molten Giant)
    big1.zone = Zone.DECK
    cheap2 = p2.give(WISP)
    cheap2.zone = Zone.DECK
    card = p1.give("CATA_720")
    card.play()
    assert cheap1.zone == Zone.GRAVEYARD
    assert cheap2.zone == Zone.GRAVEYARD
    assert big1.zone == Zone.DECK


# ---------------------------------------------------------------------------
# CATA_721 Sheltered Survivor — shuffle a hand card, draw
# ---------------------------------------------------------------------------

def test_sheltered_survivor_shuffles_and_draws():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    other = p1.give(WISP)
    card = p1.give("CATA_721")
    card.play()
    # WISP shuffled into deck, then immediately drawn back (only deck card).
    assert other.zone == Zone.HAND
    assert len(p1.hand) == 1
    assert p1.hand[0] is other


# ---------------------------------------------------------------------------
# CATA_722 Envoy of the End — Herald
# ---------------------------------------------------------------------------

def test_envoy_of_the_end_heralds():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    assert p1.heralds_this_game == 0
    card = p1.give("CATA_722")
    card.play()
    assert p1.heralds_this_game == 1
    assert card.taunt is True


# ---------------------------------------------------------------------------
# CATA_723 Drakeadon Mongrel — deathrattle two random 4-cost minions
# ---------------------------------------------------------------------------

def test_drakeadon_mongrel_deathrattle():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    mongrel = p1.summon("CATA_723")
    mongrel.destroy()
    game.process_deaths()
    summoned = [m for m in p1.field if m.id != "CATA_723"]
    assert len(summoned) == 2
    for m in summoned:
        assert m.cost == 4


# ---------------------------------------------------------------------------
# CATA_897 Gemstone Hoarder — discard a card; deathrattle returns it cheaper
# ---------------------------------------------------------------------------

def test_gemstone_hoarder_discard_and_return():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    victim = p1.give(CHILLWIND)  # 4-cost
    hoarder = p1.give("CATA_897")
    hoarder = hoarder.play()
    # Chillwind got discarded (left the hand).
    assert victim.zone != Zone.HAND
    assert hoarder._hoarded_id == CHILLWIND
    hoarder.destroy()
    game.process_deaths()
    back = [c for c in p1.hand if c.id == CHILLWIND]
    assert len(back) == 1
    assert back[0].cost == 4 - 1  # costs (1) less


# ---------------------------------------------------------------------------
# CATA_898 Scaled Lancer — all enemy minions have Taunt
# ---------------------------------------------------------------------------

def test_scaled_lancer_grants_enemy_taunt():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(WISP)
    assert enemy.taunt is False
    p1.summon("CATA_898")
    assert enemy.taunt is True


# ---------------------------------------------------------------------------
# CATA_999 Earthen Drake — end of turn deal 4 to enemy hero
# ---------------------------------------------------------------------------

def test_earthen_drake_end_of_turn_face_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.set_current_health(30)
    p1.summon("CATA_999")
    game.end_turn()
    assert p2.hero.health == 26


# ---------------------------------------------------------------------------
# CATA_213 Vyranoth — no split when condition unmet (empty starting deck)
# ---------------------------------------------------------------------------

def test_vyranoth_no_split_when_condition_unmet():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # starting_deck minion-cost sum is 0 (empty) -> no split, no crash.
    card = p1.give("CATA_213")
    card.play()
    assert card.id == "CATA_213"


# ---------------------------------------------------------------------------
# CATA_190h Deathwing, Worldbreaker — unleash 1 Cataclysm at 0 Heralds
# ---------------------------------------------------------------------------

def test_deathwing_unleashes_one_cataclysm_base():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # Stack enemy board so Raze / Topple have targets; choose deterministically.
    enemy = p2.summon(BOULDERFIST)  # 6/6
    enemy.max_health = 80
    enemy.damage = 0
    dw = p1.give("CATA_190h")
    dw.play()
    # One choice opens offering the four Cataclysms.
    assert p1.choice is not None
    cataclysms = {"CATA_190t10", "CATA_190t11", "CATA_190t12", "CATA_190t13"}
    assert {c.id for c in p1.choice.cards} == cataclysms
    # Pick Raze (deal 4 to all enemy minions): index of CATA_190t12.
    raze = next(c for c in p1.choice.cards if c.id == "CATA_190t12")
    p1.choice.choose(raze)
    # No further choice (1 pick at 0 Heralds).
    assert p1.choice is None
    assert enemy.damage == 4


def test_deathwing_unleashes_more_with_heralds():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.heralds_this_game = 2  # -> N = 1 + min(2,2) = 3 picks
    dw = p1.give("CATA_190h")
    dw.play()
    picks = 0
    while p1.choice is not None and picks < 5:
        # Always pick Dragon's Reign first if available else first card.
        chosen = p1.choice.cards[0]
        p1.choice.choose(chosen)
        picks += 1
    assert picks == 3


def test_deathwing_dragons_reign_summons_12_12():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    dw = p1.give("CATA_190h")
    dw.play()
    reign = next(c for c in p1.choice.cards if c.id == "CATA_190t10")
    p1.choice.choose(reign)
    progeny = [m for m in p1.field if m.id == "CATA_190t14"]
    assert len(progeny) == 1
    assert (progeny[0].atk, progeny[0].health) == (12, 12)
