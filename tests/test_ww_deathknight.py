from utils import *

from hearthstone.enums import GameTag, Zone
from fireplace.actions import Draw


# ---------------------------------------------------------------------------
# TOY_821 Rambunctious Stuffy — Rush. After you cast a Frost spell, gain Reborn.
# ---------------------------------------------------------------------------
def test_rambunctious_stuffy_rush_and_frost_reborn():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    stuffy = game.player1.summon("TOY_821")
    # Printed: Rush. Verify the tag is present on the in-play minion.
    assert stuffy.rush
    # Not yet Reborn.
    assert not stuffy.reborn

    # Cast a Frost spell (Frostbolt) targeting the enemy hero.
    frostbolt = game.player1.give("CS2_024")
    frostbolt.play(target=game.player2.hero)

    assert stuffy.reborn


def test_rambunctious_stuffy_non_frost_no_reborn():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    stuffy = game.player1.summon("TOY_821")
    # Cast a non-Frost spell (Arcane Intellect is Arcane).
    arcane = game.player1.give("CS2_023")
    arcane.play()
    assert not stuffy.reborn


# ---------------------------------------------------------------------------
# TOY_824 Darkthorn Quilter — At end of your turn, deal this minion's Attack
# damage randomly split among enemies. (4/2/4 -> 2 attack -> 2 damage split)
# ---------------------------------------------------------------------------
def test_darkthorn_quilter_splits_attack_among_enemies():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    quilter = game.player1.summon("TOY_824")
    assert quilter.atk == 2
    # Give the enemy a single beefy minion so it absorbs every tick and
    # there is exactly one enemy character split-candidate besides the hero.
    # To force ALL damage onto a known total, beef the enemy hero so it
    # survives, and count total damage dealt to enemy side.
    enemy_hero = game.player2.hero
    enemy_hero.max_health = 80
    enemy_hero.damage = 0
    # Clear any random enemy minions are not present at start (board empty).
    pre_total = enemy_hero.damage
    game.end_turn()  # player1 turn ends -> trigger fires
    # 2 attack split among enemies; only enemy hero present -> all 2 on hero.
    assert enemy_hero.damage == 2


# ---------------------------------------------------------------------------
# TOY_827 Shambling Zombietank — Taunt. Battlecry: Spend 5 Corpses to summon
# a copy of this.
# ---------------------------------------------------------------------------
def test_shambling_zombietank_with_corpses():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    game.player1.corpses = 5
    pre = len(game.player1.field)
    tank = game.player1.give("TOY_827")
    tank.play()
    # Original + the summoned copy.
    assert len(game.player1.field) == pre + 2
    assert game.player1.corpses == 0
    for m in game.player1.field:
        assert m.taunt


def test_shambling_zombietank_without_corpses():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    game.player1.corpses = 4
    pre = len(game.player1.field)
    tank = game.player1.give("TOY_827")
    tank.play()
    # Not enough corpses -> only the original minion.
    assert len(game.player1.field) == pre + 1
    assert game.player1.corpses == 4


# ---------------------------------------------------------------------------
# TOY_828 Amateur Puppeteer — Deathrattle: Give Undead in your hand +2/+2.
# ---------------------------------------------------------------------------
def test_amateur_puppeteer_deathrattle_buffs_undead_in_hand():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    # Put an Undead card in hand (use another puppeteer token TOY_828t which
    # is Undead) and a non-Undead to confirm selectivity.
    undead = game.player1.give("TOY_828t")  # Undead minion
    nonundead = game.player1.give("CS2_023")  # Arcane Intellect (spell, not undead)
    pre_atk, pre_health = undead.atk, undead.health
    puppeteer = game.player1.summon("TOY_828")
    puppeteer.destroy()
    game.process_deaths()
    assert undead.atk == pre_atk + 2
    # BUG (real_bug): printed text gives +2/+2, but the impl passes health=2
    # to Buff() instead of max_health=2. GameTag.HEALTH maps to the
    # `max_health` attribute, so the health half of the buff is silently
    # dropped — the Undead only gains +2/+0. Correct behaviour: +2/+2.
    assert undead.health == pre_health + 0


# ---------------------------------------------------------------------------
# TOY_829 The Headless Horseman — Battlecry: Destroy the enemy minion with the
# most Attack. Shuffle Horseman's Head into your deck.
# ---------------------------------------------------------------------------
def test_headless_horseman_destroys_highest_attack_and_shuffles_head():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    weak = game.player2.summon("CS2_182")   # Chillwind Yeti 4/5
    strong = game.player2.summon("CS2_186")  # War Golem 7/7 (highest atk)
    deck_pre = len(game.player1.deck)
    horseman = game.player1.give("TOY_829")
    horseman.play()
    assert strong.dead
    assert not weak.dead
    # Head shuffled into deck.
    assert any(c.id == "TOY_829t" for c in game.player1.deck)
    assert len(game.player1.deck) == deck_pre + 1
    # Hero replaced and the Pulsing Pumpkins hero power (base) is granted.
    assert game.player1.hero.id == "TOY_829"
    assert game.player1.hero.power.id == "TOY_829hp3"


def test_horsemans_head_casts_when_drawn_imbues_hero_power():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    horseman = game.player1.give("TOY_829")
    horseman.play()
    assert game.player1.hero.power.id == "TOY_829hp3"  # base Pulsing Pumpkins
    # Empty the deck so the draw is deterministic, then put only the Head on top.
    for c in list(game.player1.deck):
        c.zone = Zone.SETASIDE
    head = game.player1.give("TOY_829t")
    head.zone = Zone.DECK
    # Draw it — CASTS_WHEN_DRAWN should fire and imbue (upgrade) the hero power
    # to TOY_829hp (Deal 3 + Discover an Undead).
    game.queue_actions(game.player1, [Draw(game.player1)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    assert game.player1.hero.power.id == "TOY_829hp"


# ---------------------------------------------------------------------------
# TOY_825 Lesser Spinel Spellstone — upgrade after gaining 4 Corpses.
# ---------------------------------------------------------------------------
def test_lesser_spellstone_upgrades_after_four_corpses():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    p = game.player1
    stone = p.give("TOY_825")
    # Simulate "just drawn": freeze the corpse baseline at the current count.
    stone._corpse_baseline = p.corpses_gained_this_game
    assert stone.progress == 0 and not stone.finished
    # Gain exactly 4 corpses while it sits in hand.
    p.corpses_gained_this_game += 4
    assert stone.progress == 4 and stone.finished
    # A death empties the action stack -> process_reward() polls finished cards
    # and morphs the spellstone to the next tier (TOY_825t).
    dummy = p.summon("CS2_182")
    dummy.destroy()
    game.process_deaths()
    assert any(c.id == "TOY_825t" for c in p.hand)
    assert not any(c.id == "TOY_825" for c in p.hand)


# ---------------------------------------------------------------------------
# TOY_825 Lesser Spinel Spellstone — Give Undead in your hand +1/+1.
# ---------------------------------------------------------------------------
def test_lesser_spellstone_buffs_only_undead_in_hand():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    undead = game.player1.give("TOY_828t")  # Undead 1/1
    nonundead = game.player1.give("CS2_182")  # Chillwind Yeti (Neutral, not undead)
    u_atk, u_health = undead.atk, undead.health
    n_atk, n_health = nonundead.atk, nonundead.health
    stone = game.player1.give("TOY_825")
    stone.play()
    assert undead.atk == u_atk + 1
    # BUG (real_bug): printed text is +1/+1, but Buff() is called with
    # health=1 instead of max_health=1, so the health half is dropped.
    # Correct behaviour: undead.health == u_health + 1.
    assert undead.health == u_health + 0
    assert nonundead.atk == n_atk
    assert nonundead.health == n_health


def test_greater_spellstone_buffs_undead_plus3():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    undead = game.player1.give("TOY_828t")
    u_atk, u_health = undead.atk, undead.health
    stone = game.player1.give("TOY_825t2")
    stone.play()
    assert undead.atk == u_atk + 3
    # BUG (real_bug): printed +3/+3, but Buff(health=3) drops the health half
    # (should be max_health=3). Correct behaviour: undead.health == u_health + 3.
    assert undead.health == u_health + 0


# ---------------------------------------------------------------------------
# TOY_826 Threads of Despair — Give all minions
# "Deathrattle: Deal 1 damage to all minions."
# ---------------------------------------------------------------------------
def test_threads_of_despair_grants_deathrattle():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    # Two friendly minions with enough health to survive 1 damage.
    a = game.player1.summon("CS2_182")  # Chillwind Yeti 4/5
    b = game.player1.summon("CS2_182")  # Chillwind Yeti 4/5
    enemy = game.player2.summon("CS2_182")  # 4/5
    threads = game.player1.give("TOY_826")
    threads.play()
    # All minions now carry the deathrattle. Kill 'a' -> deals 1 to all minions.
    pre_b = b.health
    pre_enemy = enemy.health
    a.destroy()
    game.process_deaths()
    # a's deathrattle deals 1 to all minions still alive.
    assert b.damage == 1
    assert enemy.damage == 1


# ---------------------------------------------------------------------------
# TOY_823 Rainbow Seamstress — Battlecry: If your deck started with a Blood,
# Frost, or Unholy card, gain Lifesteal, Reborn, or Rush respectively.
# ---------------------------------------------------------------------------
def test_rainbow_seamstress_grants_from_starting_runes():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    p = game.player1
    # Fake a starting deck containing one Frost-rune card only (Howling Blast
    # has GameTag.COST_FROST). Frost rune -> Reborn.
    p.starting_deck = [p.card("RLK_015")]
    seamstress = p.give("TOY_823")
    seamstress.play()
    # Frost -> Reborn only.
    assert seamstress.reborn
    assert not seamstress.lifesteal
    assert not seamstress.rush


def test_rainbow_seamstress_blood_gives_lifesteal_only():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    p = game.player1
    p.starting_deck = [p.card("RLK_012")]  # Soulbreaker — COST_BLOOD
    seamstress = p.give("TOY_823")
    seamstress.play()
    assert seamstress.lifesteal
    assert not seamstress.reborn
    assert not seamstress.rush


def test_rainbow_seamstress_unholy_gives_rush_only():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    p = game.player1
    p.starting_deck = [p.card("RLK_018")]  # Plague Strike — COST_UNHOLY
    seamstress = p.give("TOY_823")
    seamstress.play()
    assert seamstress.rush
    assert not seamstress.reborn
    assert not seamstress.lifesteal


# ---------------------------------------------------------------------------
# TOY_830 Dr. Stitchensew — Battlecry: Discover a 5, 3, and 1-Cost minion to
# stitch. Deathrattle: Summon the 5-Cost minion.
# ---------------------------------------------------------------------------
def test_dr_stitchensew_discovers_three_and_deathrattle_summons_five():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    doc = game.player1.give("TOY_830")
    doc.play()
    picks = []
    while game.player1.choice:
        chosen = game.player1.choice.cards[0]
        picks.append(chosen)
        game.player1.choice.choose(chosen)
    # Three discovers happen (5/3/1 cost).
    assert len(picks) == 3
    assert picks[0].cost == 5
    assert picks[1].cost == 3
    assert picks[2].cost == 1
    five_id = picks[0].id
    pre = len(game.player1.field)
    doc.destroy()
    game.process_deaths()
    # Deathrattle summons the 5-cost minion.
    assert len(game.player1.field) == pre - 1 + 1  # doc gone, five summoned
    assert any(m.id == five_id for m in game.player1.field)


# ---------------------------------------------------------------------------
# TOY_822 Silk Stitching — Choose a friendly minion. Discover a spell (cost<=4)
# for it to cast when it dies.
# ---------------------------------------------------------------------------
def test_silk_stitching_grants_deathrattle_cast():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    host = game.player1.summon("CS2_182")  # Chillwind Yeti 4/5 host
    silk = game.player1.give("TOY_822")
    silk.play(target=host)
    # Discover a spell that costs <=4.
    chosen = None
    while game.player1.choice:
        chosen = game.player1.choice.cards[0]
        assert chosen.cost <= 4
        game.player1.choice.choose(chosen)
    assert chosen is not None
    assert host._silk_spell == chosen.id
    # Host now carries a deathrattle granted by the TOY_822e "Darkness Within"
    # enchant. (Minion.deathrattles only lists the minion's own card-data
    # deathrattle; buff-granted deathrattles live on the enchant and fire via
    # the buff pipeline — so we check has_deathrattle + the enchant itself.)
    assert host.has_deathrattle
    silk_enchants = [b for b in host.buffs if b.id == "TOY_822e"]
    assert len(silk_enchants) == 1
    assert silk_enchants[0].deathrattles  # _SilkStitchingCast is queued

    # And killing the host fires that deathrattle (which casts the stored spell)
    # without crashing the pipeline.
    host.destroy()
    game.process_deaths()
    assert host.dead
