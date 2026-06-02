"""Cataclysm — Demon Hunter (CATA_) card tests."""
from utils import prepare_game
from hearthstone.enums import CardClass, GameTag, Zone, Race


# ---------------------------------------------------------------------------
# CATA_151 Azshara, Ocean Lord — Colossal +2, hero Windfury; tentacle tokens
# ---------------------------------------------------------------------------


def test_azshara_colossal_and_hero_windfury():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    azshara = p1.give("CATA_151")
    azshara.play()
    # Colossal +2: Azshara plus two Azshara's Tentacle limbs on board.
    tentacles = [m for m in p1.field if m.id in ("CATA_151t", "CATA_151t1")]
    assert len(tentacles) == 2
    assert azshara in p1.field
    # Hero has Windfury while Azshara is in play.
    assert p1.hero.windfury
    # Each Tentacle's "When summoned, give your hero +Attack this turn" fires
    # when the limbs arrive via the engine's Colossal-limb placement
    # (_summon_colossal_limbs now runs each limb's `summoned` actions). With 0
    # Heralds each tentacle grants +1, so two tentacles give the hero +2.
    assert p1.hero.atk == 2


def test_azshara_tentacle_attack_scales_with_heralds():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p1.heralds_this_game = 2  # tentacle should now grant +3 (1 + min(2,2))
    tentacle = p1.summon("CATA_151t")
    assert tentacle in p1.field
    assert p1.hero.atk == 3


def test_azshara_hero_windfury_drops_when_azshara_leaves():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    azshara = p1.give("CATA_151")
    azshara.play()
    assert p1.hero.windfury
    azshara.destroy()
    assert not p1.hero.windfury


# ---------------------------------------------------------------------------
# CATA_525 Armored Bloodletter — Rush, Battlecry: Herald
# ---------------------------------------------------------------------------


def test_armored_bloodletter_heralds():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    assert p1.heralds_this_game == 0
    bl = p1.give("CATA_525")
    bl.play()
    assert p1.heralds_this_game == 1
    assert bl.rush


def test_soldier_of_azshara_token_buffs_hero():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p1.heralds_this_game = 1  # +2 attack (1 + min(1,2))
    soldier = p1.summon("CATA_525t")
    assert soldier in p1.field
    assert p1.hero.atk == 2


# ---------------------------------------------------------------------------
# CATA_526 Broxigar's Last Stand — deal 1 to all minions, draw per death
# ---------------------------------------------------------------------------


def test_broxigars_last_stand_draws_per_death():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    # Two 1-health minions (will die) and one big minion (survives).
    a = p1.summon("CS2_171")   # Stonetusk Boar 1/1
    b = p2.summon("CS2_171")   # 1/1
    big = p2.summon("CATA_528t")  # 3/3 Naga Monstrosity — survives 1 dmg
    pre_hand = len(p1.hand)
    brox = p1.give("CATA_526")
    brox.play()
    # Two 1/1s died, big survives -> draw exactly 2.
    assert a.zone == Zone.GRAVEYARD
    assert b.zone == Zone.GRAVEYARD
    assert big.zone == Zone.PLAY
    assert big.health == 2
    assert len(p1.hand) == pre_hand + 2


def test_broxigars_last_stand_no_deaths_no_draw():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    big = p2.summon("CATA_528t")  # 3/3 survives
    pre_hand = len(p1.hand)
    p1.give("CATA_526").play()
    assert big.zone == Zone.PLAY
    assert len(p1.hand) == pre_hand


# ---------------------------------------------------------------------------
# CATA_527 Nespirah, Enthralled — Location: deal 1; reopen on Fel; DR summon
# ---------------------------------------------------------------------------


def test_nespirah_location_deals_and_reopens_on_fel():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CATA_528t")  # 3/3
    loc = p1.give("CATA_527")
    loc.play()
    # Locations can't be used the turn they are played; clear that gate.
    loc.turn_played = -1
    loc.cooldown = 0
    # First use: deal 1 damage.
    loc.use(target=target)
    assert target.health == 2
    assert loc.cooldown > 0  # on cooldown after use
    # Cast a Fel spell -> reopen (cooldown cleared).
    fel = p1.give("CATA_530")  # Fel Infusion (Fel spell)
    fel.play()
    assert loc.cooldown == 0


def test_nespirah_deathrattle_summons_unshackled():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CATA_528t")
    loc = p1.give("CATA_527")
    loc.play()
    # Drain its durability fully: it has 5 durability; use until it dies.
    # Easier: directly destroy to fire deathrattle.
    loc.destroy()
    game.process_deaths()
    assert any(m.id == "CATA_527t2" for m in p1.field)


def test_nespirah_unshackled_fel_gives_cheap_naga():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p1.discard_hand()
    nes = p1.summon("CATA_527t2")
    assert nes in p1.field
    p1.give("CATA_530").play()  # Fel spell
    naga = [c for c in p1.hand if c.race == Race.NAGA]
    assert len(naga) == 1
    assert naga[0].cost == 1


# ---------------------------------------------------------------------------
# CATA_528 Sigil of the Seas — start of next turn summon 3/3 Taunt Naga
# ---------------------------------------------------------------------------


def test_sigil_of_the_seas_summons_next_turn():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p1.give("CATA_528").play()
    # Not summoned yet this turn.
    assert not any(m.id == "CATA_528t" for m in p1.field)
    game.end_turn()  # opponent turn
    game.end_turn()  # back to p1 -> start-of-turn trigger fires
    monstrosities = [m for m in p1.field if m.id == "CATA_528t"]
    assert len(monstrosities) == 1
    m = monstrosities[0]
    assert m.atk == 3 and m.health == 3
    assert m.taunt


# ---------------------------------------------------------------------------
# CATA_529 Ravenous Felfisher — costs 1 less per Fel spell cast this game
# ---------------------------------------------------------------------------


def test_ravenous_felfisher_cost_reduction():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    fisher = p1.give("CATA_529")
    assert fisher.cost == 6
    p1.give("CATA_530").play()  # 1 Fel spell
    assert fisher.cost == 5
    p1.give("CATA_533").play()  # Flash Flood — another Fel spell
    assert fisher.cost == 4


# ---------------------------------------------------------------------------
# CATA_530 Fel Infusion — Herald + hero Lifesteal this turn
# ---------------------------------------------------------------------------


def test_fel_infusion_herald_and_lifesteal():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p1.hero.atk = 4  # give hero attack to swing
    p1.hero.damage = 10  # hero at 20 health
    pre_health = p1.hero.health
    p1.give("CATA_530").play()
    assert p1.heralds_this_game == 1
    assert p1.hero.lifesteal
    # Attack the enemy hero: lifesteal heals for 4.
    p1.hero.attack(p2.hero)
    assert p1.hero.health == pre_health + 4


def test_fel_infusion_lifesteal_expires_end_of_turn():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p1.give("CATA_530").play()
    assert p1.hero.lifesteal
    game.end_turn()
    assert not p1.hero.lifesteal


# ---------------------------------------------------------------------------
# CATA_533 Flash Flood — 5 dmg to outermost enemy minions; Outcast: again
# ---------------------------------------------------------------------------


def test_flash_flood_hits_outermost():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    left = p2.summon("CATA_699")    # 9/6 — beef HP so it survives one 5-hit
    left.max_health = 80
    left.damage = 0
    mid = p2.summon("CATA_699")
    mid.max_health = 80
    mid.damage = 0
    right = p2.summon("CATA_699")
    right.max_health = 80
    right.damage = 0
    flood = p1.give("CATA_533")
    # Make sure it is NOT outcast (play from a middle hand slot).
    filler = p1.give("CS2_171")
    flood.play()
    assert left.damage == 5
    assert right.damage == 5
    assert mid.damage == 0  # middle minion untouched


def test_flash_flood_outcast_doubles():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    left = p2.summon("CATA_699")
    left.max_health = 80
    left.damage = 0
    right = p2.summon("CATA_699")
    right.max_health = 80
    right.damage = 0
    flood = p1.give("CATA_533")  # leftmost (only card) -> Outcast
    flood.play()
    # Outcast: do it again -> outermost hit twice = 10 each.
    assert left.damage == 10
    assert right.damage == 10


# ---------------------------------------------------------------------------
# CATA_697 Malevolent Mutant — Battlecry: copy a Fel spell from hand
# ---------------------------------------------------------------------------


def test_malevolent_mutant_copies_fel_spell():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p1.discard_hand()
    fel = p1.give("CATA_530")  # the only Fel spell in hand
    mutant = p1.give("CATA_697")
    mutant.play()
    copies = [c for c in p1.hand if c.id == "CATA_530"]
    # Original fel + the new copy = 2.
    assert len(copies) == 2


# ---------------------------------------------------------------------------
# CATA_699 Dread Leviathan — Taunt; steal 3 Health from a minion, three times
# ---------------------------------------------------------------------------


def test_dread_leviathan_steals_health_three_times():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CATA_699")  # 9/6 -> beef so it survives -9 health
    victim.max_health = 30
    victim.damage = 0
    lev = p1.give("CATA_699")
    lev.play(target=victim)
    assert lev.taunt
    # Victim lost 9 max Health (3 x 3).
    assert victim.max_health == 21
    # Dread Leviathan gained 9 Health (6 -> 15).
    assert lev.max_health == 15
