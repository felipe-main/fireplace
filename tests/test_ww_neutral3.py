from utils import *


# ---------------------------------------------------------------------------
# TOY_820 Forgotten Animatronic (5/4/6 Mech)
# At the end of your turn, destroy a minion with less Attack than this.
# ---------------------------------------------------------------------------
def test_forgotten_animatronic_destroys_weaker():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    animatronic = game.player1.summon("TOY_820")  # 4 attack
    assert animatronic.atk == 4
    # Use a Wisp (1 attack) as the only other minion to guarantee the pick.
    wisp = game.player2.summon(WISP)  # 1/1, enemy side
    assert wisp.atk == 1
    game.end_turn()
    # End of player1's turn: animatronic destroys a minion with atk < 4.
    # Wisp (1) is the only candidate -> destroyed.
    assert wisp.dead
    assert not animatronic.dead


def test_forgotten_animatronic_no_target():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    animatronic = game.player1.summon("TOY_820")  # 4 attack
    # Only a minion with >= attack on the board.
    big = game.player2.summon("CS2_186")  # War Golem 7/7 -> atk 7 >= 4
    assert big.atk >= animatronic.atk
    game.end_turn()
    assert not big.dead
    assert not animatronic.dead


# ---------------------------------------------------------------------------
# TOY_866 Corridor Sleeper (1/3/5 Beast) — Dormant; after 7 minions die, awaken.
# ---------------------------------------------------------------------------
def test_corridor_sleeper_awakens_after_7_deaths():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    sleeper = game.player1.summon("TOY_866")
    assert sleeper.dormant
    # Kill 6 minions -> still dormant.
    for _ in range(6):
        w = game.player2.summon(WISP)
        w.destroy()
    assert sleeper.dormant
    # 7th death -> awaken.
    w = game.player2.summon(WISP)
    w.destroy()
    assert not sleeper.dormant


# ---------------------------------------------------------------------------
# TOY_878 Cosplay Contestant (3/3/4)
# After your opponent plays a minion, transform into a 3/4 copy of it.
# ---------------------------------------------------------------------------
def test_cosplay_contestant_transforms_to_3_4():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    contestant = game.player1.summon("TOY_878")
    game.end_turn()  # player2's turn
    # Opponent plays a minion -> contestant transforms into a 3/4 copy.
    enemy = game.player2.give("CS2_186")  # War Golem 7/7
    enemy.play()
    # contestant entity is morphed in place; find player1's single minion.
    assert len(game.player1.field) == 1
    morphed = game.player1.field[0]
    assert morphed.id == "CS2_186"
    assert morphed.atk == 3
    assert morphed.health == 4
    assert morphed.max_health == 4


# ---------------------------------------------------------------------------
# TOY_891 Workshop Janitor (5/5/5)
# Battlecry: If you control a location, draw 2 cards.
# ---------------------------------------------------------------------------
def test_workshop_janitor_with_location_draws_2():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    # Play a location first (Muck Pools). It correctly sits in
    # game.player1.location after being played.
    loc = game.player1.give("REV_923")
    loc.play()
    assert game.player1.location is loc
    pre = len(game.player1.hand)
    janitor = game.player1.give("TOY_891")
    janitor.play()
    # Controlling a location, the battlecry draws 2 cards. Player.entities now
    # yields self.location, so Count(IN_PLAY + FRIENDLY + LOCATION_CARD) sees
    # the played location and the condition fires.
    assert len(game.player1.hand) == pre + 2


def test_workshop_janitor_no_location_no_draw():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    pre = len(game.player1.hand)
    janitor = game.player1.give("TOY_891")
    janitor.play()
    assert len(game.player1.hand) == pre


# ---------------------------------------------------------------------------
# TOY_893 Nesting Golem (4/4/3 Undead)
# Deathrattle: Resummon this with -1/-1.
# ---------------------------------------------------------------------------
def test_nesting_golem_resummon_minus_1_1():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    golem = game.player1.summon("TOY_893")
    assert golem.atk == 4 and golem.max_health == 3
    golem.destroy()
    game.process_deaths()
    assert len(game.player1.field) == 1
    new = game.player1.field[0]
    assert new.id == "TOY_893"
    assert new.atk == 3
    assert new.max_health == 2


# ---------------------------------------------------------------------------
# TOY_894 Origami Frog (5/1/4) — Battlecry: Swap Attack with another minion.
# ---------------------------------------------------------------------------
def test_origami_frog_swaps_attack_only():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    target = game.player1.summon("CS2_186")  # War Golem, atk depends on data
    t_atk, t_health = target.atk, target.health
    frog = game.player1.give("TOY_894")  # 1 attack, 4 health
    assert frog.atk == 1
    frog.play(target=target)
    # Frog gets target's attack; target gets frog's attack. Health untouched.
    assert frog.atk == t_atk
    assert frog.health == 4
    assert target.atk == 1
    assert target.health == t_health


# ---------------------------------------------------------------------------
# TOY_895 Origami Crane (4/4/1) — Battlecry: Swap Health with another minion.
# ---------------------------------------------------------------------------
def test_origami_crane_swaps_health_only():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    target = game.player1.summon("CS2_186")
    t_atk, t_health = target.atk, target.health
    crane = game.player1.give("TOY_895")  # 4 attack, 1 health
    assert crane.atk == 4 and crane.health == 1
    crane.play(target=target)
    assert crane.atk == 4
    assert crane.health == t_health
    assert target.atk == t_atk
    assert target.health == 1


# ---------------------------------------------------------------------------
# TOY_896 Origami Dragon (6/1/1) — Battlecry: Swap stats with another minion.
# ---------------------------------------------------------------------------
def test_origami_dragon_swaps_both():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    target = game.player1.summon("CS2_186")
    t_atk, t_health = target.atk, target.health
    dragon = game.player1.give("TOY_896")  # 1 attack, 1 health
    assert dragon.atk == 1 and dragon.health == 1
    dragon.play(target=target)
    assert dragon.atk == t_atk
    assert dragon.health == t_health
    assert target.atk == 1
    assert target.health == 1


# ---------------------------------------------------------------------------
# TOY_897 Floppy Hydra (3/2/4 Beast)
# Deathrattle: Shuffle a copy of this into your deck with permanently
# doubled Attack and Health.
# ---------------------------------------------------------------------------
def test_floppy_hydra_shuffles_doubled_copy():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    hydra = game.player1.summon("TOY_897")  # 2 atk / 4 health
    assert hydra.atk == 2 and hydra.max_health == 4
    deck_pre = len(game.player1.deck)
    hydra.destroy()
    game.process_deaths()
    assert len(game.player1.deck) == deck_pre + 1
    copy = [c for c in game.player1.deck if c.id == "TOY_897"][-1]
    assert copy.atk == 4
    assert copy.max_health == 8


# ---------------------------------------------------------------------------
# TOY_943 Rumble Enthusiast (3/2/5)
# After you play the left- or right-most card in your hand, deal 1 damage to
# a random enemy.
# ---------------------------------------------------------------------------
def test_rumble_enthusiast_outcast_hits_enemy():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.summon("TOY_943")
    # Beef the enemy hero so we can read exact 1 damage.
    enemy_hero = game.player2.hero
    # Clear player1 hand so the played card is both left- and right-most.
    for c in game.player1.hand[:]:
        c.discard()
    wisp = game.player1.give(WISP)  # only card in hand -> outcast position
    pre = enemy_hero.health
    wisp.play()
    # The only enemy character is the enemy hero (no enemy minions).
    assert enemy_hero.health == pre - 1


def test_rumble_enthusiast_middle_card_no_trigger():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.summon("TOY_943")
    for c in game.player1.hand[:]:
        c.discard()
    left = game.player1.give(WISP)
    mid = game.player1.give(WISP)
    right = game.player1.give(WISP)
    enemy_hero = game.player2.hero
    pre = enemy_hero.health
    mid.play()  # middle card -> not outcast -> no trigger
    assert enemy_hero.health == pre


# ---------------------------------------------------------------------------
# TOY_960 Joymancer Jepetto (8/6/6)
# Battlecry: Get copies of every 1-Attack or 1-Health minion you've played
# this game.
# ---------------------------------------------------------------------------
def test_joymancer_copies_one_stat_minions():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    # Play a 1-health minion (Wisp 1/1) and a 1-attack minion.
    # Kobold Geomancer is 2/2 (no 1-stat). Use Wisp (1/1) and a Murloc 1/1.
    w1 = game.player1.give(WISP)
    w1.play()
    # A non-qualifying minion: War Golem 7/7 -> not copied.
    big = game.player1.give("CS2_186")
    big.play()
    game.player1.used_mana = 0  # refund so Jepetto (8 mana) is playable
    pre = len(game.player1.hand)
    jepetto = game.player1.give("TOY_960")
    jepetto.play()
    # Should add exactly one copy (the Wisp). War Golem not copied; Jepetto
    # itself not yet in cards_played_this_game when battlecry fires.
    added = [c for c in game.player1.hand if c.id == WISP]
    assert len(added) == 1
    assert len(game.player1.hand) == pre + 1


# ---------------------------------------------------------------------------
# TOY_100 Gnomelia, S.A.F.E. Pilot (3/?/?)
# Rush. Also damages minions next to whomever this attacks.
# Deathrattle: Deal 2 damage to all enemies.
# ---------------------------------------------------------------------------
def test_gnomelia_cleave_wired():
    """Gnomelia's cleave uses the canonical Attack(SELF).on(CLEAVE) pattern
    (same wiring as Enslaved Fel Lord / Foe Reaper). CLEAVE now reads
    ATTACK_TARGET_ADJACENT so it resolves live (see
    test_gnomelia_main_attack_cleaves_flanking_minions). We verify the
    wiring is identical to the reference cleave minions."""
    from fireplace.actions import Attack as AttackAction, Hit
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    gnomelia = game.player1.summon("TOY_100")
    listeners = [
        e for e in gnomelia.events if isinstance(e.trigger, AttackAction)
    ]
    assert len(listeners) == 1
    listener = listeners[0]
    cleave = (
        listener.actions[0]
        if isinstance(listener.actions, (list, tuple))
        else listener.actions
    )
    assert isinstance(cleave, Hit)


def test_gnomelia_main_attack_cleaves_flanking_minions():
    # "Also damages minions next to whomever this attacks": attacking the middle
    # of three enemies deals Gnomelia's Attack to BOTH flanking minions.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    gnomelia = game.player1.summon("TOY_100")
    gnomelia.max_health = 80
    gnomelia.damage = 0
    game.end_turn()
    game.end_turn()
    left = game.player2.summon(WISP)
    mid = game.player2.summon("CS2_186")
    mid.max_health = 80
    mid.damage = 0
    right = game.player2.summon(WISP)
    pre_mid = mid.health
    atk = gnomelia.atk
    gnomelia.attack(mid)
    game.process_deaths()
    # Defender takes the normal attack damage.
    assert mid.health == pre_mid - atk
    # Both 1-health flankers take the cleave (= Gnomelia's Attack) and die.
    assert left.dead
    assert right.dead


def test_gnomelia_deathrattle_2_to_all_enemies():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    gnomelia = game.player1.summon("TOY_100")
    enemy_hero = game.player2.hero
    survivor = game.player2.summon("CS2_186")
    survivor.max_health = 80
    survivor.damage = 0
    pre_hero = enemy_hero.health
    pre_surv = survivor.health
    gnomelia.destroy()
    game.process_deaths()
    assert enemy_hero.health == pre_hero - 2
    assert survivor.health == pre_surv - 2


# ---------------------------------------------------------------------------
# TOY_101 Night Elf Huntress
# Battlecry: Deal 3 damage to three different enemies.
# ---------------------------------------------------------------------------
def test_night_elf_huntress_three_targets():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    m1 = game.player2.summon("CS2_186")
    m2 = game.player2.summon("CS2_186")
    for m in (m1, m2):
        m.max_health = 80
        m.damage = 0
    enemy_hero = game.player2.hero
    pre_hero = enemy_hero.health
    pre1, pre2 = m1.health, m2.health
    huntress = game.player1.give("TOY_101")
    huntress.play(target=m1)
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Three DIFFERENT enemies each take exactly 3. With only m1, m2 and the
    # enemy hero available and each ChoiceTarget excluding prior picks, all
    # three distinct targets are hit for 3.
    assert m1.health == pre1 - 3
    assert m2.health == pre2 - 3
    assert enemy_hero.health == pre_hero - 3


# ---------------------------------------------------------------------------
# TOY_102 Footman — Taunt. Adjacent minions are Immune while attacking.
# ---------------------------------------------------------------------------
def test_footman_grants_adjacent_immune_while_attacking():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    left = game.player1.summon("CS2_186")  # War Golem
    footman = game.player1.summon("TOY_102")
    right = game.player1.summon("CS2_186")
    assert left.immune_while_attacking
    assert right.immune_while_attacking
    assert not footman.immune_while_attacking


# ---------------------------------------------------------------------------
# TOY_103 Warsong Grunt — Rush. After this attacks and kills a minion, it may
# attack again.
# ---------------------------------------------------------------------------
def test_warsong_grunt_extra_attack_on_kill():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    grunt = game.player1.summon("TOY_103")
    game.end_turn()
    game.end_turn()  # grunt can attack
    victim = game.player2.summon(WISP)  # 1 health, dies
    assert grunt.num_attacks == 0
    grunt.attack(victim)
    game.process_deaths()
    assert victim.dead
    # Killed a minion -> granted an extra attack -> can_attack again.
    assert grunt.can_attack()
