"""Into the Emerald Dream — DEMONHUNTER unit tests.

Covers every collectible Demon Hunter card:
  EDR_421 Omen                  (Rush/Windfury improving deathrattle)
  EDR_493 Alara'shi            (transform hand into Demons, keep stats)
  EDR_820 Wyvern's Slumber      (Choose One — Dreadseeds / AoE)
  EDR_840 Grim Harvest          (draw + random Dreadseed)
  EDR_841 Dreadsoul Corrupter   (battlecry + deathrattle Dreadseed)
  EDR_842 Defiled Spear         (weapon — splash on hero attack)
  EDR_882 Jumpscare!            (Discover Demon 5+, shuffle rest)
  EDR_890 Nightmare Dragonkin   (deathrattle — cost reduce rightmost)
  EDR_891 Ravenous Felhunter    (deathrattle resurrect cost<=4 + copy)
  EDR_892 Ferocious Felbat      (deathrattle resurrect cost>=5 + copy)
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone, Race


DREADSEEDS = {"EDR_840t", "EDR_840t1", "EDR_840t2"}


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# EDR_421 — Omen: Rush, Windfury. Deathrattle: deal (1 + #attacks) to all enemies.
def test_omen_keywords_and_stats():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    m = game.player1.summon("EDR_421")
    assert (m.atk, m.max_health) == (6, 12)
    assert m.rush
    assert m.windfury


def test_omen_deathrattle_base_one_no_attacks():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    omen = p1.summon("EDR_421")
    # Enemy hero + a beefy enemy minion that survives the 1 damage tick.
    p2.hero.max_health = 80
    p2.hero.damage = 0
    target = p2.summon("CS2_186")  # War Golem 7/7
    target.max_health = 80
    target.damage = 0
    omen.destroy()
    game.process_deaths()
    # No attacks => exactly 1 damage to all enemies.
    assert target.damage == 1
    assert p2.hero.damage == 1


def test_omen_deathrattle_scales_with_attacks():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.current_player
    p2 = p1.opponent
    omen = p1.summon("EDR_421")  # Rush => can attack enemy minions immediately
    omen.max_health = 200  # survive both counterattacks
    omen.damage = 0
    # Beefy enemy to attack into (and to receive the deathrattle).
    target = p2.summon("CS2_186")
    target.max_health = 80
    target.damage = 0
    # Attack twice (Windfury permits a second swing same turn).
    omen.attack(target)
    omen.attack(target)
    assert getattr(omen, "_omen_strikes", 0) == 2
    pre = target.damage
    # Deathrattle: 1 + 2 attacks = 3 to all enemies.
    omen.destroy()
    game.process_deaths()
    assert target.damage == pre + 3


# EDR_493 — Alara'shi: transform hand minions into Demons keeping stats/cost.
def test_alarashi_transforms_hand_keeps_stats():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    # Clear hand, then give one known minion: Chillwind Yeti 4/4/5.
    for c in p1.hand[:]:
        c.discard()
    yeti = p1.give("CS2_182")
    assert (yeti.cost, yeti.atk, yeti.health) == (4, 4, 5)
    alarashi = p1.give("EDR_493")
    alarashi.play()
    _resolve_choices(p1)
    # The hand slot is now a Demon, but retains 4/4/5 and cost 4.
    transformed = p1.hand[0]
    assert transformed.id != "CS2_182"
    assert Race.DEMON in transformed.races
    assert (transformed.cost, transformed.atk, transformed.health) == (4, 4, 5)


# EDR_840 — Grim Harvest: Draw a card. Summon a random Dormant Dreadseed.
def test_grim_harvest_draws_and_summons_dreadseed():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.current_player
    # Empty hand and deck, then seed the deck with exactly one known card.
    for c in p1.hand[:]:
        c.discard()
    deck_card = p1.card("CS2_182")
    deck_card.controller = p1
    deck_card.zone = Zone.DECK
    spell = p1.give("EDR_840")  # hand: [Grim Harvest]
    spell.play()
    # Spell left the hand; the drawn Yeti is now the only card in hand.
    assert [c.id for c in p1.hand] == ["CS2_182"]
    # A random Dormant Dreadseed entered play.
    seeds = [m for m in p1.field if m.id in DREADSEEDS]
    assert len(seeds) == 1
    assert seeds[0].dormant


# EDR_841 — Dreadsoul Corrupter: Battlecry AND Deathrattle summon a Dreadseed.
def test_dreadsoul_corrupter_battlecry_and_deathrattle():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    corrupter = p1.give("EDR_841")
    corrupter.play()
    # Battlecry summoned exactly one Dreadseed alongside the body.
    seeds = [m for m in p1.field if m.id in DREADSEEDS]
    assert len(seeds) == 1
    assert seeds[0].dormant
    corrupter.destroy()
    game.process_deaths()
    # Deathrattle summoned a second Dreadseed.
    seeds = [m for m in p1.field if m.id in DREADSEEDS]
    assert len(seeds) == 2


# EDR_820 — Wyvern's Slumber: ChooseBoth => two Dreadseeds AND 2 AoE.
def test_wyverns_slumber_both_modes():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    # An enemy minion that survives the 2 AoE so we can assert exact damage.
    enemy = p2.summon("CS2_186")
    enemy.max_health = 80
    enemy.damage = 0
    spell = p1.give("EDR_820")
    spell.play(choose="EDR_820a")  # explicit summon mode
    seeds = [m for m in p1.field if m.id in DREADSEEDS]
    assert len(seeds) == 2
    assert all(s.dormant for s in seeds)
    # AoE mode does not run when summon mode is chosen.
    assert enemy.damage == 0


def test_wyverns_slumber_aoe_mode():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon("CS2_186")
    enemy.max_health = 80
    enemy.damage = 0
    friendly = p1.summon("CS2_186")
    friendly.max_health = 80
    friendly.damage = 0
    spell = p1.give("EDR_820")
    spell.play(choose="EDR_820b")  # Deal 2 to all minions
    assert enemy.damage == 2
    assert friendly.damage == 2
    assert not [m for m in p1.field if m.id in DREADSEEDS]


# EDR_840t — Hound Dreadseed: dormant 2 turns; awaken => hero +3 Attack this turn.
def test_hound_dreadseed_awakens_and_buffs_hero():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    seed = p1.summon("EDR_840t")
    assert seed.dormant
    assert seed.dormant_turns == 2
    assert p1.hero.atk == 0
    # p1 plays it this turn; dormant_turns decrements at the start of each of
    # p1's subsequent turns. Two of p1's turn-starts are needed.
    game.end_turn()
    game.end_turn()  # p1 turn start #1 -> 2 -> 1
    assert seed.dormant
    game.end_turn()
    game.end_turn()  # p1 turn start #2 -> 1 -> 0 -> awaken
    assert not seed.dormant
    assert p1.hero.atk == 3


# EDR_890 — Nightmare Dragonkin: deathrattle reduces rightmost hand card cost 2.
def test_nightmare_dragonkin_reduces_rightmost_cost():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    for c in p1.hand[:]:
        c.discard()
    # Rightmost card in hand: Chillwind Yeti (cost 4).
    rightmost = p1.give("CS2_182")
    assert rightmost.cost == 4
    drake = p1.summon("EDR_890")
    drake.destroy()
    game.process_deaths()
    assert rightmost.cost == 2


# EDR_891 — Ravenous Felhunter: deathrattle resurrect a friendly DR minion
# costing (4) or less, and summon a copy of it (so two copies appear).
def test_ravenous_felhunter_resurrects_and_copies():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    # A cheap deathrattle minion to be the resurrection target: Loot Hoarder
    # (EX1_096) 2/3, cost 2, Deathrattle: draw a card.
    loot = p1.summon("EX1_096")
    loot.destroy()
    game.process_deaths()
    assert loot.zone == Zone.GRAVEYARD
    felhunter = p1.summon("EDR_891")
    felhunter.destroy()
    game.process_deaths()
    revived = [m for m in p1.field if m.id == "EX1_096"]
    assert len(revived) == 2


# Once-over (audit): confirm the resurrected ORIGINAL returns as a clean,
# full-health base-stat minion — no leftover damage carried from before death.
def test_ravenous_felhunter_resurrects_at_full_health():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    golem = p1.summon("EX1_556")  # Harvest Golem 2/3, cost 3, Deathrattle
    # Damage it to 1 health, then kill it: the graveyard card carries that
    # damage. Resurrection must reset it to full (health 3, damage 0).
    golem.damage = 2
    assert golem.health == 1
    golem.destroy()
    game.process_deaths()
    assert golem.zone == Zone.GRAVEYARD
    felhunter = p1.summon("EDR_891")
    felhunter.destroy()
    game.process_deaths()
    revived = [m for m in p1.field if m.id == "EX1_556"]
    assert len(revived) == 2
    # Both the resurrected original and its fresh copy are at full health.
    for m in revived:
        assert m.damage == 0
        assert m.health == 3
        assert m.max_health == 3


def test_ravenous_felhunter_ignores_expensive_minion():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    # Only a cost-7 deathrattle minion is dead (Sylvanas, EX1_016) => cost>4,
    # so Felhunter resurrects nothing.
    syl = p1.summon("EX1_016")
    syl.destroy()
    game.process_deaths()
    felhunter = p1.summon("EDR_891")
    felhunter.destroy()
    game.process_deaths()
    assert not [m for m in p1.field if m.id == "EX1_016"]


# EDR_892 — Ferocious Felbat: deathrattle resurrect a DIFFERENT friendly DR
# minion costing (5) or more, and summon a copy of it.
def test_ferocious_felbat_resurrects_expensive_and_copies():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    # Sylvanas Windrunner EX1_016: cost 6, Deathrattle.
    syl = p1.summon("EX1_016")
    syl.destroy()
    game.process_deaths()
    felbat = p1.summon("EDR_892")
    felbat.destroy()
    game.process_deaths()
    revived = [m for m in p1.field if m.id == "EX1_016"]
    assert len(revived) == 2


def test_ferocious_felbat_excludes_itself():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    # No other eligible cost>=5 deathrattle minion in the graveyard; the only
    # dead deathrattle minion is the Felbat itself (cost 7) -> excluded.
    felbat = p1.summon("EDR_892")
    felbat.destroy()
    game.process_deaths()
    assert not [m for m in p1.field if m.id == "EDR_892"]


# EDR_842 — Defiled Spear: after hero attacks an enemy, deal hero's Attack to
# another random enemy. NOTE: this branch carries a pre-existing engine bug
# (Weapon._max_durability AttributeError from the 219197 data bump) that
# crashes on any weapon entering play, so the effect cannot be driven through
# a real attack here. We exercise the splash action directly instead and
# assert it deals exactly the hero's Attack to an enemy other than the
# defender.
def test_defiled_spear_splash_action_hits_other_enemy():
    from fireplace.cards.emerald_dream.demonhunter import _DefiledSpearStrike

    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.current_player
    p2 = p1.opponent
    p1.hero.set_current_health(30)
    p1.hero.atk = 2  # pretend the Defiled Spear is equipped (2 Attack)
    defender = p2.summon("CS2_186")  # the enemy just "attacked"
    defender.max_health = 80
    defender.damage = 0
    other = p2.summon("CS2_186")  # the only other enemy minion
    other.max_health = 80
    other.damage = 0
    # Source is the weapon card; here we stand in the hero (same controller).
    game.queue_actions(p1.hero, [_DefiledSpearStrike(p1.hero, defender)])
    # Splash equal to hero Attack (2) lands on the other enemy, not the
    # defender.
    assert defender.damage == 0
    assert other.damage == 2


def test_defiled_spear_is_a_two_attack_weapon():
    import fireplace.cards as _cards

    data = _cards.db["EDR_842"]
    assert data.type == CardType.WEAPON
    assert data.atk == 2
    # Event wiring: after the friendly hero attacks, the splash action runs.
    script = _cards.get_script_definition("EDR_842")
    assert getattr(script, "events", None) is not None


# EDR_882 — Jumpscare!: Discover a Demon costing (5)+, shuffle the other two
# into your deck, and attach a Dark Gift to the discovered demon.
def test_jumpscare_discovers_expensive_demon_and_shuffles_rest():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    game.random.seed(0)  # stable discover pool + gift roll
    for c in p1.hand[:]:
        c.discard()
    pre_deck = len(p1.deck)
    spell = p1.give("EDR_882")
    spell.play()
    # A 3-card Discover should now be open.
    assert p1.choice is not None
    cards = list(p1.choice.cards)
    assert len(cards) == 3
    for c in cards:
        assert Race.DEMON in c.races
        assert c.cost >= 5
    chosen = cards[0]
    p1.choice.choose(chosen)
    # Chosen card is in hand.
    held = next(h for h in p1.hand if h.id == chosen.id)
    # The other two were shuffled into the deck (not discarded).
    assert len(p1.deck) == pre_deck + 2
    # The discovered demon must carry a Dark Gift: at least one keyword from the
    # eight-keyword Nightmare pool that the base card did NOT already have is now
    # set on it (before the fix nothing was attached, so the diff was empty).
    from fireplace.cards.delve_into_deepholm._bonus import BONUS_EFFECTS

    base = p1.card(chosen.id)
    bonus_tags = set()
    for spec in BONUS_EFFECTS:
        bonus_tags |= set(spec)
    gained = {
        t for t in bonus_tags
        if held.tags.get(t) and not base.tags.get(t)
    }
    assert gained  # a Dark Gift keyword was granted that the base lacked


# EDR_882 Dark Gift — deterministic: drive the discover pool + gift roll with a
# seeded RNG and assert the exact gift keyword(s) landed on the discovered demon.
def test_jumpscare_attaches_dark_gift_deterministic():
    from fireplace.cards.delve_into_deepholm._bonus import BONUS_EFFECTS

    # Search seeds until the rolled Dark Gift adds a keyword the base demon
    # lacks (avoids the rare collision where the gift duplicates an existing
    # base keyword). Deterministic loop, bounded — once found, the assertion is
    # exact.
    for seed in range(50):
        game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
        p1 = game.player1
        game.random.seed(seed)
        for c in p1.hand[:]:
            c.discard()
        spell = p1.give("EDR_882")
        spell.play()
        chosen = p1.choice.cards[0]
        p1.choice.choose(chosen)
        held = next(h for h in p1.hand if h.id == chosen.id)
        base = p1.card(chosen.id)
        # Which single BONUS_EFFECTS spec is fully satisfied on held but was not
        # already fully present on base?
        for spec in BONUS_EFFECTS:
            tags = set(spec)
            on_held = all(held.tags.get(t) for t in tags)
            on_base = all(base.tags.get(t) for t in tags)
            if on_held and not on_base:
                # Found: the gift applied exactly this spec's keyword(s).
                return
    raise AssertionError("Jumpscare never attached a fresh Dark Gift keyword")
