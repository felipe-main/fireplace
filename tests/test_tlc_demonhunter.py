"""The Lost City of Un'Goro — Demon Hunter unit tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, Zone

# Vanilla helpers
BEAST = "CS2_172"   # Bloodfen Raptor — 3/2 Beast
BEAST2 = "CS2_172"
MURLOC = "CS2_168"  # Murloc Raider — 2/3 Murloc
RACELESS = "CS2_182"  # Chillwind Yeti — 4/5, no race


def _clear_hand(player):
    for card in list(player.hand):
        card.discard()


def test_gorishi_wasp_gives_stinger_on_damage():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    wasp = p1.summon("TLC_630")
    assert len(p1.hand) == 0
    game.queue_actions(p1.hero, [Hit(wasp, 1)])
    assert wasp.damage == 1
    stingers = [c for c in p1.hand if c.id == "TLC_630t"]
    assert len(stingers) == 1
    # Each separate hit grants another Stinger.
    game.queue_actions(p1.hero, [Hit(wasp, 1)])
    assert wasp.damage == 2
    assert len([c for c in p1.hand if c.id == "TLC_630t"]) == 2


def test_gorishi_stinger_deals_2_and_summons_grub():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    target = game.player2.summon(BEAST)
    target.max_health = 10
    target.damage = 0
    stinger = p1.give("TLC_630t")
    stinger.play(target=target)
    assert target.damage == 2
    grubs = [m for m in p1.field if m.id == "TLC_903t"]
    assert len(grubs) == 1
    assert (grubs[0].atk, grubs[0].health) == (2, 1)
    assert grubs[0].rush


def test_bugsquasher_deals_6_to_enemy_minion():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    foe = game.player2.summon(BEAST)
    foe.max_health = 10
    foe.damage = 0
    squasher = p1.give("TLC_633")
    squasher.play(target=foe)
    assert foe.damage == 6


def test_gorishi_tunneler_pings_enemy_hero_after_attack():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    tunneler = p1.summon("TLC_840")
    tunneler.charge = True  # let it attack this turn
    enemy_hero = game.player2.hero
    enemy_hero.max_health = 30
    enemy_hero.damage = 0
    defender = game.player2.summon(MURLOC)  # 2/3
    defender.max_health = 30
    defender.damage = 0
    tunneler.attack(defender)
    # 2 damage to the defender from the attack, then 2 to the enemy hero.
    assert defender.damage == 2
    assert enemy_hero.damage == 2


def test_entomologist_toru_jars_hand_minions():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    p1.give(BEAST)   # a Beast minion in hand to be jarred
    toru = p1.give("TLC_841")
    toru.play()
    jars = [c for c in p1.hand if c.id == "TLC_841t"]
    assert len(jars) == 1
    jar = jars[0]
    assert jar.cost == 1
    assert (jar.atk, jar.health) == (0, 1)
    assert jar.has_deathrattle
    # Break the jar -> release the original Beast.
    jar.play()
    jar.destroy()
    game.process_deaths()
    released = [m for m in p1.field if m.id == BEAST]
    assert len(released) == 1
    assert (released[0].atk, released[0].health) == (3, 2)


def test_silithid_queen_kindred_active_buffs_hero():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p1.give(BEAST).play()             # play a Beast this turn
    game.end_turn(); game.end_turn()  # so it is "last turn"
    assert Race.BEAST in p1.races_played_last_turn
    assert p1.hero.atk == 0
    queen = p1.give("TLC_903")        # Silithid Queen is itself a Beast
    queen.play()
    assert p1.hero.atk == 5


def test_silithid_queen_kindred_inactive_no_buff():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    # Nothing matching played last turn.
    game.end_turn(); game.end_turn()
    assert Race.BEAST not in p1.races_played_last_turn
    assert p1.hero.atk == 0
    queen = p1.give("TLC_903")
    queen.play()
    assert p1.hero.atk == 0


def test_insect_claw_summons_grub_after_hero_attack():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    weapon = p1.give("TLC_833")
    weapon.play()
    assert p1.weapon is weapon
    enemy_hero = game.player2.hero
    enemy_hero.max_health = 30
    enemy_hero.damage = 0
    p1.hero.attack(enemy_hero)
    assert enemy_hero.damage == 2  # weapon attack
    grubs = [m for m in p1.field if m.id == "TLC_903t"]
    assert len(grubs) == 1
    assert (grubs[0].atk, grubs[0].health) == (2, 1)


def test_unleash_the_colossus_quest_rewards_colossus():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    quest = p1.give("TLC_631")
    quest.play()
    assert quest.zone == Zone.SECRET
    total = quest.data.tags.get(GameTag.QUEST_PROGRESS_TOTAL)
    assert quest.progress_total == total
    foe = game.player2.hero
    foe.max_health = 80
    foe.damage = 0
    for _ in range(total - 1):
        game.queue_actions(p1.hero, [Hit(foe, 2)])
    assert quest.progress == total - 1
    assert not any(m.id == "TLC_631t" for m in p1.field)
    # The final exactly-2 hit completes the quest.
    game.queue_actions(p1.hero, [Hit(foe, 2)])
    assert any(m.id == "TLC_631t" for m in p1.field)


def test_unleash_the_colossus_only_counts_exactly_2():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    quest = p1.give("TLC_631")
    quest.play()
    foe = game.player2.hero
    foe.max_health = 80
    foe.damage = 0
    # 3-damage and 1-damage hits do NOT advance the quest.
    game.queue_actions(p1.hero, [Hit(foe, 3)])
    game.queue_actions(p1.hero, [Hit(foe, 1)])
    assert quest.progress == 0


def test_add_progress_on_player_is_a_noop_not_a_crash():
    # Regression (soak crash): progress lives on cards (quests/upgradeables),
    # never on a Player. A few quests gate AddProgress behind a Find() over a
    # player-returning selector, and on rare paths a Player slipped through as
    # the target -> AttributeError: 'Player' has no attribute 'add_progress'.
    # AddProgress must now ignore a non-progressable target instead of crashing.
    from fireplace.actions import AddProgress
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    game.queue_actions(p1.hero, [AddProgress(p1, None, 1)])  # target = a Player
    # No exception; the game is still live.
    assert game.player1 is p1


def test_gorishi_colossus_doubles_2_damage_to_enemy():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    colossus = p1.give("TLC_631t")
    colossus.play()  # battlecry installs the permanent enchant
    foe = game.player2.summon(RACELESS)
    foe.max_health = 30
    foe.damage = 0
    game.queue_actions(p1.hero, [Hit(foe, 2)])
    # Original 2 + the Colossus's extra 2 = 4, and no infinite recursion.
    assert foe.damage == 4


def test_fumigate_hits_target_and_same_type():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    beast_a = game.player2.summon(BEAST)
    beast_b = game.player2.summon(BEAST2)
    murloc = game.player2.summon(MURLOC)
    for m in (beast_a, beast_b, murloc):
        m.max_health = 10
        m.damage = 0
    fumigate = p1.give("TLC_901")
    fumigate.play(target=beast_a)
    assert beast_a.damage == 3
    assert beast_b.damage == 3   # same minion type
    assert murloc.damage == 0    # different type untouched


def test_infestation_gives_two_stingers():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    infestation = p1.give("TLC_902")
    infestation.play()
    stingers = [c for c in p1.hand if c.id == "TLC_630t"]
    assert len(stingers) == 2
    assert all(c.cost == 1 for c in stingers)


def test_hive_map_discovers_fel_spell():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    hive_map = p1.give("TLC_900")
    hive_map.play()
    assert p1.choice is not None
    # All three Discover options are Fel spells.
    assert len(p1.choice.cards) == 3
    for card in p1.choice.cards:
        assert card.spell_school == SpellSchool.FEL
        assert card.type == CardType.SPELL
    offered = list(p1.choice.cards)
    chosen = offered[0]
    others = sorted(c.id for c in offered if c is not chosen)
    p1.choice.choose(chosen)
    held = [c for c in p1.hand if c.id == chosen.id]
    assert len(held) == 1
    # "If you play it this turn, also pick one of the others": stamp + watcher.
    assert sorted(held[0]._pick_other_runners) == others
    assert any(b.id == "_PickOtherWatcher" for b in p1.buffs)


# --------------------------------------------------------------------------
# DINO_137 — Skittish Saucier: snapshot-based neighbour discount (review #562)
# --------------------------------------------------------------------------
# The discount must hit the Saucier's *physical* hand neighbours captured at
# play time (via _play_hand_index/_play_hand_size), NOT a heuristic that can be
# fooled by an earlier play this turn bumping a non-neighbour.


def test_skittish_saucier_discounts_exact_neighbors_after_prior_play():
    """A card played earlier this turn must not be mistaken for a neighbour:
    only the Saucier's two physical hand neighbours at play time get (1) off."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    # Play a Beast FIRST this turn (perturbs any adjacency counters), then set
    # up the Saucier's hand. The fix must ignore this prior play entirely.
    p1.give(BEAST).play()
    far_left = p1.give(RACELESS)   # index 0 — not adjacent
    left = p1.give(RACELESS)       # index 1 — left neighbour
    saucier = p1.give("DINO_137")  # index 2 — played from the middle
    right = p1.give(RACELESS)      # index 3 — right neighbour
    far_right = p1.give(RACELESS)  # index 4 — not adjacent
    base = far_left.cost
    assert left.cost == base and right.cost == base
    saucier.play()
    assert left.cost == base - 1
    assert right.cost == base - 1
    assert far_left.cost == base
    assert far_right.cost == base


def test_skittish_saucier_right_edge_single_neighbor():
    """Saucier at the right edge of hand has only a left neighbour."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    other = p1.give(RACELESS)      # index 0 — not adjacent
    left = p1.give(RACELESS)       # index 1 — left neighbour
    saucier = p1.give("DINO_137")  # index 2 — right edge
    base = other.cost
    saucier.play()
    assert left.cost == base - 1
    assert other.cost == base


# --------------------------------------------------------------------------
# DINO_138 — Diabolus Rex: base Kindred behaviour (review #561 — accepted)
# --------------------------------------------------------------------------
# next_kindred_double (set by Primalfin Challenger) is NOT consulted by the
# Kindred() evaluator — that wiring lives in dsl/ (engine, out of card scope).
# This test pins the base gating + 6-damage outermost hit so a regression in
# the un-doubled path is caught.


def test_diabolus_rex_base_kindred_hits_outermost_only():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p2 = game.player2
    # Activate Kindred: a Beast played last turn.
    p1.give(BEAST).play()
    game.end_turn(); game.end_turn()
    assert Race.BEAST in p1.races_played_last_turn
    left = p2.summon(RACELESS)
    middle = p2.summon(RACELESS)
    right = p2.summon(RACELESS)
    for m in (left, middle, right):
        m.max_health = 30
        m.damage = 0
    p1.give("DINO_138").play()
    # Exactly 6 to each outermost enemy; the middle is untouched (no doubling).
    assert left.damage == 6
    assert right.damage == 6
    assert middle.damage == 0


def test_diabolus_rex_inactive_kindred_no_damage():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p2 = game.player2
    game.end_turn(); game.end_turn()
    assert Race.BEAST not in p1.races_played_last_turn
    foe = p2.summon(RACELESS)
    foe.max_health = 30
    foe.damage = 0
    p1.give("DINO_138").play()
    assert foe.damage == 0
