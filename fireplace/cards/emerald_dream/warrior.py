from ..utils import *

from hearthstone.enums import CardType as _CardType

from .neutral import _GiveDarkGift


##
# Into the Emerald Dream — WARRIOR collectible cards.
#
# Warrior is NOT an Imbue class (it keeps its base Hero Power), so none of
# these cards call Imbue(CONTROLLER). The set leans on Dragons, Eggs and
# board-clear/Armor effects.


# EDR_531 — Siphoning Growth (1 mana spell)
# Destroy a friendly minion to gain 8 Armor.
class EDR_531:
    """Siphoning Growth"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = Destroy(TARGET), GainArmor(FRIENDLY_HERO, 8)


# EDR_570 — Ominous Nightmares (1 mana spell)
# Choose One - Deal 1 damage to all minions; or Give a damaged minion +2/+2.
class EDR_570:
    """Ominous Nightmares"""

    choose = ("EDR_570A", "EDR_570B")
    play = ChooseBoth(CONTROLLER) & (
        Hit(ALL_MINIONS, 1),
        Buff(RANDOM(DAMAGED + ALL_MINIONS), "EDR_570e"),
    )


class EDR_570A:
    """Nightmarish Burst"""

    # Deal 1 damage to all minions.
    play = Hit(ALL_MINIONS, 1)


class EDR_570B:
    """Unstable Power"""

    # Give a damaged minion +2/+2.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_DAMAGED_TARGET: 0,
    }
    play = Buff(TARGET, "EDR_570e")


class EDR_570e:
    """Terror of the Night"""

    # +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


# EDR_459 — Afflicted Devastator (4/6/6 minion)
# Battlecry: Deal 3 damage to all other friendly minions.
# Deathrattle: Deal 3 damage to all enemy minions.
class EDR_459:
    """Afflicted Devastator"""

    play = Hit(FRIENDLY_MINIONS - SELF, 3)
    deathrattle = Hit(ENEMY_MINIONS, 3)


# EDR_468 — Eggbasher (4/3/5 minion)
# Battlecry: Deal 1 damage to a minion and give it +4 Attack.
class EDR_468:
    """Eggbasher"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 1), Buff(TARGET, "EDR_468e1")


class EDR_468e1:
    """Scrambled Attack"""

    # +4 Attack.
    tags = {GameTag.ATK: 4}


# EDR_457 — Brood Keeper (2/2/3 minion)
# Battlecry: If you're holding a Dragon, equip a 2/2 Sword.
class EDR_457:
    """Brood Keeper"""

    play = HOLDING_DRAGON & Summon(CONTROLLER, "EDR_457t")


class EDR_457t:
    """Nightmare Slicer"""

    # 2/2 Sword token (weapon).


# EDR_456 — Darkrider (1/1/1 minion)
# Battlecry: If you're holding a Dragon, Discover a Dragon with a Dark Gift.
#
# Dark Gift is the set-wide Nightmare keyword shared across EDR. Rather than a
# bespoke fixed +2/+2 rider, Darkrider now routes through the same
# `_GiveDarkGift` helper as every other EDR Dark-Gift card (neutral.py): the
# discovered Dragon receives a random keyword Bonus Effect (always granted,
# random, strict upgrade). The exact gift-pool identity remains the set-wide
# Dark Gift approximation flagged in neutral.py.
class EDR_456:
    """Darkrider"""

    play = HOLDING_DRAGON & Discover(
        CONTROLLER, RandomMinion(race=Race.DRAGON)
    ).then(Give(CONTROLLER, Discover.CARD).then(_GiveDarkGift(Give.CARD)))


# EDR_454 — Clutch of Corruption (2 mana, Location, 2 durability)
# Choose a friendly Dragon. Summon a 0/2 Egg that hatches into a copy of it.
#
# Targeting is restricted to friendly DRAGONS (REQ_TARGET_WITH_RACE), and the
# egg hatches into a full snapshot copy of the chosen Dragon — including any
# buffs / enchantments it carried at cast time — by stashing an ExactCopy card
# object on the egg rather than re-summoning a fresh base-stat minion by id.
class _ClutchHatch(TargetedAction):
    """Summon a 0/2 Egg that snapshots an exact copy of the chosen friendly
    Dragon (stored on the egg for its deathrattle)."""

    TARGET = ActionArg()

    def do(self, source, target):
        chosen = source.target
        if chosen is None:
            return
        egg = source.controller.card("EDR_454t", source=source)
        # Snapshot the chosen Dragon now (with its current buffs/stats) so the
        # later hatch reproduces it faithfully even if the original changes/dies.
        # ExactCopy.copy(source, entity) clones the live entity including buffs
        # and silenceable stats; it ignores the selector arg (pass SELF as a
        # placeholder).
        egg._hatch_card = ExactCopy(SELF).copy(source, chosen)
        return source.game.cheat_action(source, [Summon(CONTROLLER, egg)])


class EDR_454:
    """Clutch of Corruption"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_TARGET_WITH_RACE: Race.DRAGON,
    }
    activate = _ClutchHatch(CONTROLLER)


class EDR_454t:
    """Horrible Egg"""

    # The token data carries no DEATHRATTLE tag, so declare it here or the
    # script below is never collected.
    tags = {GameTag.DEATHRATTLE: True}

    # Deathrattle: Summon the stored Dragon snapshot.
    def deathrattle(self):
        hatch_card = getattr(self, "_hatch_card", None)
        if hatch_card is not None:
            yield Summon(CONTROLLER, hatch_card)


# EDR_455 — Succumb to Madness (3 mana spell)
# Discover a friendly Dragon that died this game. Resummon it.
class _ResummonChoice(Choice):
    """A Discover-style choice whose picked card is SUMMONED (resummoned to the
    battlefield) instead of added to hand. The unpicked offered copies are
    discarded."""

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        self.player.discovers_this_game += 1
        self.player.discovers_this_turn += 1
        for offered in self.cards:
            if offered is not card:
                offered.discard()
        self.source.game.queue_actions(self.source, [Summon(self.player, card)])
        self.trigger_choice_callback()


class _SuccumbDiscover(TargetedAction):
    """Discover a friendly Dragon that died this game, then resummon the chosen
    one. Built as a custom Choice over the graveyard since the engine Discover
    only picks from a class-weighted random pool."""

    TARGET = ActionArg()

    def do(self, source, target):
        candidates = [
            m
            for m in list(target.graveyard)
            if m.type == _CardType.MINION and Race.DRAGON in m.races
        ]
        if not candidates:
            return
        # De-duplicate by id (offer distinct dead Dragons).
        seen = {}
        for m in candidates:
            seen.setdefault(m.id, m)
        picks = list(seen.values())
        n = min(3, len(picks))
        offered = [
            target.card(m.id, source=source)
            for m in source.game.random.sample(picks, n)
        ]
        return source.game.cheat_action(source, [_ResummonChoice(target, offered)])


class EDR_455:
    """Succumb to Madness"""

    play = _SuccumbDiscover(CONTROLLER)


# EDR_465 — Ysondre (7/8/5 minion, Taunt, Legendary)
# Taunt. Deathrattle: Summon a random Dragon for each time Ysondre has died
# this game.
class _YsondreDeathrattle(TargetedAction):
    """Bump the controller's Ysondre death count, then summon that many random
    Dragons (resummoned Ysondres add to the count, so a second death summons
    two, etc.)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        count = getattr(player, "_ysondre_deaths", 0) + 1
        player._ysondre_deaths = count
        return source.game.cheat_action(
            source, [Summon(CONTROLLER, RandomMinion(race=Race.DRAGON)) * count]
        )


class EDR_465:
    """Ysondre"""

    tags = {GameTag.TAUNT: True}
    deathrattle = _YsondreDeathrattle(SELF)


# EDR_471 — Tortolla (10/1/30 minion, Taunt, Elusive, Legendary)
# Taunt, Elusive. After this takes damage, gain 1 Armor and give this minion
# +1 Attack.
class EDR_471:
    """Tortolla"""

    tags = {
        GameTag.TAUNT: True,
        # Elusive — can't be targeted by spells or Hero Powers.
        GameTag.CANT_BE_TARGETED_BY_ABILITIES: True,
    }
    events = SELF_DAMAGE.on(
        GainArmor(FRIENDLY_HERO, 1),
        Buff(SELF, "EDR_471e"),
    )


class EDR_471e:
    """Tortolla's Rage"""

    # +1 Attack.
    tags = {GameTag.ATK: 1}
