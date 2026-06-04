from ..utils import *

from hearthstone.enums import GameTag, Zone


# ---------------------------------------------------------------------------
# Dark Gift — the real Nightmare-bonus pool.
#
# A "Dark Gift" is a random bonus attached to a minion chosen from a Discover
# (or otherwise gifted). The data ships the ten gifts as discrete cards under
# the EDR_100t* prefix, but every gift "executes nightmare bonus" entirely
# script-side (the enchants carry no stat tags), so the effects are rebuilt
# here from the printed card text:
#
#   Waking Terror     (EDR_100t)   +3 Attack and Lifesteal      [no Lifesteal]
#   Well Rested       (EDR_100t1)  +2/+2 and Elusive            [not Elusive]
#   Short Claws       (EDR_100t2)  Costs (2) less, -2 Attack    [>=3 Attack]
#   Bundled Up        (EDR_100t3)  +4 Health and Taunt          [no Taunt]
#   Living Nightmare  (EDR_100t5)  When played, summon a 2/2 copy
#   Sleepwalker       (EDR_100t6)  Charge                       [>=1 Atk, no Charge]
#   Rude Awakening    (EDR_100t7)  Battlecries trigger twice    [has Battlecry]
#   Sweet Dreams      (EDR_100t8)  +4/+5, place on top of deck
#   Persisting Horror (EDR_100t9)  Reborn                       [no Reborn]
#   Harpy's Talons    (EDR_100t13) Divine Shield and Windfury   [lacks both]
#
# The bracketed eligibility mirrors the printed "(minions without X only)"
# riders — a gift whose effect would be a no-op is never offered. Living
# Nightmare and Sweet Dreams have no rider and are always eligible.
#
# Gifts are recorded on the recipient as a list of gift ids in `_dark_gifts`
# (readers — Wallow, Overgrown Horror, etc. — test truthiness; Wallow re-runs
# `apply_dark_gift` for each absorbed id to copy the real effect).
# ---------------------------------------------------------------------------

WAKING_TERROR = "EDR_100t"
WELL_RESTED = "EDR_100t1"
SHORT_CLAWS = "EDR_100t2"
BUNDLED_UP = "EDR_100t3"
LIVING_NIGHTMARE = "EDR_100t5"
SLEEPWALKER = "EDR_100t6"
RUDE_AWAKENING = "EDR_100t7"
SWEET_DREAMS = "EDR_100t8"
PERSISTING_HORROR = "EDR_100t9"
HARPYS_TALONS = "EDR_100t13"

# Elusive = can't be targeted by spells or Hero Powers (two engine tags).
_ELUSIVE = {
    GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
    GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
}


def eligible_gifts(target):
    """Return the gift ids whose effect would not be a strict no-op on the
    given minion, mirroring the printed eligibility riders."""
    atk = target.atk
    out = []
    if not target.lifesteal:
        out.append(WAKING_TERROR)
    if not target.taunt:
        out.append(BUNDLED_UP)
    if not getattr(target, "cant_be_targeted_by_abilities", False):
        out.append(WELL_RESTED)
    if atk >= 1 and not target.charge:
        out.append(SLEEPWALKER)
    if not target.divine_shield and not target.windfury:
        out.append(HARPYS_TALONS)
    if not target.reborn:
        out.append(PERSISTING_HORROR)
    if atk >= 3:
        out.append(SHORT_CLAWS)
    if target.has_battlecry:
        out.append(RUDE_AWAKENING)
    out.append(LIVING_NIGHTMARE)
    out.append(SWEET_DREAMS)
    return out


def apply_dark_gift(source, target, gift):
    """Apply one Dark Gift (by id) to `target`. Runs each sub-effect through
    `cheat_action` so it threads the normal pipeline; the stat halves ride on
    the matching data enchant id with dynamic amounts supplied as kwargs."""
    game = source.game
    if gift == WAKING_TERROR:
        game.cheat_action(source, [Buff(target, "EDR_100te", atk=3)])
        game.cheat_action(source, [SetTags(target, {GameTag.LIFESTEAL: True})])
    elif gift == WELL_RESTED:
        game.cheat_action(source, [Buff(target, "EDR_100t1e", atk=2, max_health=2)])
        game.cheat_action(source, [SetTags(target, dict(_ELUSIVE))])
    elif gift == SHORT_CLAWS:
        game.cheat_action(source, [Buff(target, "EDR_100t2e", atk=-2, cost=-2)])
    elif gift == BUNDLED_UP:
        game.cheat_action(source, [Buff(target, "EDR_100t3e", max_health=4)])
        game.cheat_action(source, [SetTags(target, {GameTag.TAUNT: True})])
    elif gift == SLEEPWALKER:
        game.cheat_action(source, [SetTags(target, {GameTag.CHARGE: True})])
    elif gift == HARPYS_TALONS:
        game.cheat_action(source, [SetTags(target, {
            GameTag.DIVINE_SHIELD: True, GameTag.WINDFURY: True,
        })])
    elif gift == PERSISTING_HORROR:
        game.cheat_action(source, [SetTags(target, {GameTag.REBORN: True})])
    elif gift == RUDE_AWAKENING:
        # Per-minion "Battlecries trigger twice" — read by Battlecry.has_extra_battlecries.
        target._battlecries_twice = True
    elif gift == LIVING_NIGHTMARE:
        # "When you play this minion, summon a 2/2 copy" — read by Play.do.
        target._living_nightmare = True
    elif gift == SWEET_DREAMS:
        game.cheat_action(source, [Buff(target, "EDR_100t8e1", atk=4, max_health=5)])
        # "Place this card on top of your deck." Only meaningful for a card
        # currently in hand (the Discover-and-gift flow); a minion already in
        # play keeps the +4/+5 and the relocation simply doesn't apply.
        owner = target.controller
        if target.zone == Zone.HAND and len(owner.deck) < owner.max_deck_size:
            target.zone = Zone.DECK
            if target in owner.deck:
                owner.deck.remove(target)
            owner.deck.append(target)  # deck[-1] is the next draw = top
    # Record the gift so readers ("minions with a Dark Gift", Wallow) see it.
    target._dark_gifts = getattr(target, "_dark_gifts", []) + [gift]
