"""Perils in Paradise — DEMONHUNTER unit tests.

Covers every collectible Demon Hunter card:
  VAC_501 Aranna, Thrill Seeker  (Priest Tourist)
  VAC_925 Sigil of Skydiving
  VAC_926 Cliff Dive
  VAC_927 Adrenaline Fiend
  VAC_928 Paraglide
  VAC_929 Dangerous Cliffside    (Location)
  VAC_930 All Terrain Voidhound
  VAC_931 Skirting Death
  VAC_932 Climbing Hook          (Weapon)
  VAC_933 Patches the Pilot
"""

from utils import *


# VAC_501 — Aranna, Thrill Seeker: Priest Tourist. Damage your hero takes on
# your turn is redirected to a random enemy.
def test_aranna_redirects_self_damage_on_your_turn():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    # Make the enemy hero a big sink so the redirected damage is exactly measurable.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    p1.summon("VAC_501")
    pre_p1 = p1.hero.health
    # Deal 3 damage to our own hero on our turn -> net healed back, 3 hits enemy.
    game.queue_actions(p1.hero, [Hit(p1.hero, 3)])
    # Hero ends at full (damage redirected/restored).
    assert p1.hero.health == pre_p1
    # The 3 damage landed on the only enemy character (the enemy hero).
    assert p2.hero.health == 80 - 3


def test_aranna_is_minion_stats():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.PRIEST)
    m = game.player1.summon("VAC_501")
    assert (m.atk, m.max_health) == (5, 6)


# VAC_925 — Sigil of Skydiving: At the start of your next turn, summon three
# 1/1 Pirates with Charge.
def test_sigil_of_skydiving_summons_three_pirates_next_turn():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    sigil = p1.give("VAC_925")
    sigil.play()
    pre = len(p1.field)
    # End turn, opponent's turn, back to our turn -> trigger at start.
    game.end_turn()
    game.end_turn()
    pirates = [m for m in p1.field if m.id == "VAC_926t"]
    assert len(pirates) == 3
    assert len(p1.field) == pre + 3
    for pm in pirates:
        assert (pm.atk, pm.max_health) == (1, 1)
        assert pm.charge


# VAC_926t — Falling Illidari: 1/1 Pirate with Charge.
def test_falling_illidari_token_is_charge_pirate():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    m = game.player1.summon("VAC_926t")
    assert Race.PIRATE in m.races
    assert (m.atk, m.max_health) == (1, 1)
    assert m.charge


# VAC_926 — Cliff Dive: Summon 2 minions from your deck and give them Rush.
# They go back to deck at end of your turn.
def test_cliff_dive_summons_two_from_deck_with_rush():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    # Stack the deck with exactly two minions so the random pick is deterministic.
    a = p1.give("CS2_172")  # Bloodfen Raptor 3/2
    a.zone = Zone.DECK
    b = p1.give("CS2_172")
    b.zone = Zone.DECK
    spell = p1.give("VAC_926")
    spell.play()
    summoned = [m for m in p1.field if m.id == "CS2_172"]
    assert len(summoned) == 2
    for m in summoned:
        assert m.rush


def test_cliff_dive_minions_return_to_deck_at_end_of_turn():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    a = p1.give("CS2_172")
    a.zone = Zone.DECK
    b = p1.give("CS2_172")
    b.zone = Zone.DECK
    spell = p1.give("VAC_926")
    spell.play()
    assert len([m for m in p1.field if m.id == "CS2_172"]) == 2
    game.end_turn()
    # Both bounced back to the deck.
    assert len([m for m in p1.field if m.id == "CS2_172"]) == 0
    assert len([c for c in p1.deck if c.id == "CS2_172"]) == 2


# VAC_927 — Adrenaline Fiend: After a friendly Pirate attacks, give your hero
# +1 Attack this turn.
def test_adrenaline_fiend_buffs_hero_after_pirate_attacks():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p1.summon("VAC_927")
    # Summon a Pirate that can attack (Charge token), attack the enemy hero.
    pirate = p1.summon("VAC_926t")  # 1/1 Pirate, Charge
    assert p1.hero.atk == 0
    pirate.attack(p2.hero)
    # Friendly Pirate attacked -> hero gains +1 Attack this turn.
    assert p1.hero.atk == 1


def test_adrenaline_fiend_buff_expires_at_end_of_turn():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p1.summon("VAC_927")
    pirate = p1.summon("VAC_926t")
    pirate.attack(p2.hero)
    assert p1.hero.atk == 1
    game.end_turn()
    assert p1.hero.atk == 0


def test_adrenaline_fiend_ignores_nonpirate_attack():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p1.summon("VAC_927")
    # Wisp is not a Pirate; give it charge so it can attack immediately.
    wisp = p1.summon("CS2_231")
    wisp.charge = True
    wisp.attack(p2.hero)
    assert p1.hero.atk == 0


# VAC_928 — Paraglide: Both players draw 3 cards. Outcast: Only you do.
def test_paraglide_both_players_draw_three():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    for _ in range(5):
        c = p1.give("CS2_231")
        c.zone = Zone.DECK
        c2 = p2.give("CS2_231")
        c2.zone = Zone.DECK
    # Put Paraglide in the MIDDLE of hand so it is NOT an Outcast play.
    filler1 = p1.give("CS2_231")
    glide = p1.give("VAC_928")
    filler2 = p1.give("CS2_231")
    pre1, pre2 = len(p1.hand), len(p2.hand)
    glide.play()
    # Both players drew 3. p1 loses the spell from hand and gains 3.
    assert len(p1.hand) == (pre1 - 1) + 3
    assert len(p2.hand) == pre2 + 3


def test_paraglide_outcast_only_you_draw():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    for _ in range(5):
        c = p1.give("CS2_231")
        c.zone = Zone.DECK
        c2 = p2.give("CS2_231")
        c2.zone = Zone.DECK
    # Clear hand, then give Paraglide so it is the LEFTMOST card (Outcast).
    for c in list(p1.hand):
        c.discard()
    glide = p1.give("VAC_928")
    pre2 = len(p2.hand)
    glide.play()
    # Outcast: only you draw 3; opponent draws nothing.
    assert len(p1.hand) == 3
    assert len(p2.hand) == pre2


# VAC_929 — Dangerous Cliffside (Location): Summon two 1/1 Pirates with Charge.
# After your hero attacks, reopen this.
def test_dangerous_cliffside_summons_two_pirates():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    loc = p1.give("VAC_929")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    pre = len(p1.field)
    loc.use()
    pirates = [m for m in p1.field if m.id == "VAC_926t"]
    assert len(pirates) == 2
    assert loc.cooldown == 2


def test_dangerous_cliffside_reopens_after_hero_attack():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    loc = p1.give("VAC_929")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    assert loc.cooldown == 2
    # Give the hero a weapon so it can attack, then attack the enemy hero.
    p1.give("CS2_091").play()  # Light's Justice 1/4 weapon
    p1.hero.attack(p2.hero)
    # After our hero attacks, the location reopens (cooldown reset to 0).
    assert loc.cooldown == 0


# VAC_930 — All Terrain Voidhound: Whenever this attacks, give your hero +5
# Attack this turn.
def test_voidhound_buffs_hero_when_it_attacks():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    hound = p1.summon("VAC_930")  # 5/8 Demon
    hound.charge = True  # let it attack this turn
    assert p1.hero.atk == 0
    hound.attack(p2.hero)
    assert p1.hero.atk == 5


def test_voidhound_buff_expires_at_end_of_turn():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    hound = p1.summon("VAC_930")
    hound.charge = True
    hound.attack(p2.hero)
    assert p1.hero.atk == 5
    game.end_turn()
    assert p1.hero.atk == 0


# VAC_931 — Skirting Death: Choose a minion. This turn, your hero steals 4
# Attack from it.
def test_skirting_death_steals_four_attack():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    # Target a 5-attack minion so exactly 4 can be stolen.
    target = p2.summon("CS2_186")  # War Golem 7/7 (atk 7)
    pre_atk = target.atk
    spell = p1.give("VAC_931")
    spell.play(target=target)
    assert target.atk == pre_atk - 4
    assert p1.hero.atk == 4


def test_skirting_death_steal_expires_at_end_of_turn():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_186")  # War Golem 7/7
    spell = p1.give("VAC_931")
    spell.play(target=target)
    assert p1.hero.atk == 4
    assert target.atk == 3
    game.end_turn()
    # Both halves of the steal expire at end of our turn.
    assert p1.hero.atk == 0
    assert target.atk == 7


def test_skirting_death_caps_at_target_attack():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    # A 2-attack minion: hero can only steal 2 (min of 4 and the target's atk).
    target = p2.summon("CS2_168")  # Murloc Raider 2/1
    spell = p1.give("VAC_931")
    spell.play(target=target)
    assert target.atk == 0
    assert p1.hero.atk == 2


# VAC_932 — Climbing Hook (Weapon): Doesn't lose Durability while you control a
# minion with 5 or more Attack.
def test_climbing_hook_no_durability_loss_with_big_minion():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    weapon = p1.give("VAC_932")
    weapon.play()
    assert weapon.durability == 2
    # Control a 5-attack minion -> attacking does not consume durability.
    p1.summon("CS2_186")  # War Golem 7/7 (atk 7 >= 5)
    p1.hero.attack(p2.hero)
    assert weapon.durability == 2


def test_climbing_hook_loses_durability_without_big_minion():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    weapon = p1.give("VAC_932")
    weapon.play()
    assert weapon.durability == 2
    # Only a small minion in play (atk 1 < 5) -> durability is consumed.
    p1.summon("CS2_231")  # Wisp 1/1
    p1.hero.attack(p2.hero)
    assert weapon.durability == 1


# VAC_933 — Patches the Pilot: Battlecry: Shuffle six Parachutes into your deck
# that summon a 1/1 Pirate with Charge when drawn.
def test_patches_the_pilot_shuffles_six_parachutes():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    patches = p1.give("VAC_933")
    patches.play()
    parachutes = [c for c in p1.deck if c.id == "VAC_933t"]
    assert len(parachutes) == 6


def test_parachute_casts_when_drawn_summons_pirate():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    # Put a single Parachute in the deck and draw it.
    chute = p1.give("VAC_933t")
    chute.zone = Zone.DECK
    pre_field = len(p1.field)
    p1.draw()
    # Casts When Drawn: it summons a 1/1 Charge Pirate and does not enter hand.
    pirates = [m for m in p1.field if m.id == "VAC_926t"]
    assert len(pirates) == 1
    assert (pirates[0].atk, pirates[0].max_health) == (1, 1)
    assert pirates[0].charge
    assert not any(c.id == "VAC_933t" for c in p1.hand)


# Deck-legality: Aranna is a Priest Tourist (TOURIST->6 == PRIEST), so a
# Demon Hunter deck with a Tourist can include Priest cards.
def test_aranna_priest_tourist_unlocks_priest_cards():
    import fireplace.cards as _cards
    from fireplace.utils import random_draft, tourist_class_of

    cards = random_draft(CardClass.DEMONHUNTER, tourist=CardClass.PRIEST)
    has_priest = False
    has_tourist = False
    for cid in cards:
        cdata = _cards.db[cid]
        classes = list(getattr(cdata, "classes", None) or [cdata.card_class])
        if CardClass.PRIEST in classes and CardClass.DEMONHUNTER not in classes:
            has_priest = True
        if tourist_class_of(cdata) == CardClass.PRIEST:
            has_tourist = True
    assert has_priest
    assert has_tourist


# VAC_501 Aranna (Tier-2 faithful): your-turn hero damage is REDIRECTED
# pre-damage to a random enemy - the hero takes nothing (armor untouched).
def test_aranna_redirects_predamage_hero_untouched():
    from fireplace.actions import Hit
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p, opp = game.player1, game.player2
    opp.hero.max_health = 80
    opp.hero._max_health = 80
    p.summon("VAC_501")
    p.hero.armor = 5
    hp, armor, opp_hp = p.hero.health, p.hero.armor, opp.hero.health
    game.queue_actions(p.hero, [Hit(p.hero, 4)])
    # Hero never takes the damage (armor preserved); the lone enemy takes it.
    assert p.hero.health == hp and p.hero.armor == armor
    assert opp.hero.health == opp_hp - 4
