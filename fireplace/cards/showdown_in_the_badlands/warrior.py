"""Showdown in the Badlands — Warrior cards (WILD_WEST)."""

from ..utils import *
from ... import enums as _enums


##
# Custom actions


class _MarkWinsBrawl(TargetedAction):
    """Badlands Brawler — flag SELF as guaranteed to win the next Brawl."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.tags[_enums.ALWAYS_WINS_BRAWLS] = True
        target.always_wins_brawls = True
        return []


class _SlagmawHasten(TargetedAction):
    """Slagmaw the Slumbering — each Excavate awakens it 2 turns sooner."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not target.dormant:
            return []
        # Reduce the remaining dormant countdown by 2 (never below 1 — the
        # begin-of-turn handler awakens it when it reaches 0).
        target.dormant_turns = max(1, target.dormant_turns - 2)
        return []


##
# Minions


class WW_329:
    """Detonation Juggernaut"""

    # Taunt. Battlecry: Give Taunt minions in your hand +2/+2.
    play = Buff(FRIENDLY_HAND + MINION + TAUNT, "WW_329e")


class WW_346:
    """Blast Tortoise"""

    # Taunt. Battlecry: Deal damage to all enemy minions equal to this
    # minion's Attack.
    play = Hit(ENEMY_MINIONS, ATK(SELF))


class WW_349:
    """Badlands Brawler"""

    # Battlecry: Start a Brawl! If you've Excavated twice, this always wins.
    play = (
        (Attr(CONTROLLER, "excavates_this_game") >= 2) & _MarkWinsBrawl(SELF),
        Find(ALL_MINIONS + ALWAYS_WINS_BRAWLS)
        & Destroy(ALL_MINIONS - RANDOM(ALL_MINIONS + ALWAYS_WINS_BRAWLS))
        | Destroy(ALL_MINIONS - RANDOM_MINION),
    )


class WW_367:
    """Unlucky Powderman"""

    # Taunt. Deathrattle: Give Taunt minions in your hand and deck +1/+1.
    deathrattle = Buff((FRIENDLY_HAND | FRIENDLY_DECK) + MINION + TAUNT, "WW_367e")


class WW_372:
    """Boomboss Tho'grun"""

    # Battlecry: Shuffle 3 T.N.T. into your deck. When drawn, blow up a card
    # in the enemy hand, deck, and battlefield.
    play = Shuffle(CONTROLLER, ["WW_372t", "WW_372t", "WW_372t"])


class WW_375:
    """Slagmaw the Slumbering"""

    # Rush, Taunt. Dormant for 8 turns. (Excavate to awaken 2 turns sooner!)
    tags = {GameTag.DORMANT: True}
    dormant_turns = 8
    dormant_events = Excavate(CONTROLLER).after(_SlagmawHasten(SELF))


##
# Tokens


class WW_372t:
    """T.N.T."""

    # Casts When Drawn. Destroy a random card in your opponent's hand, deck,
    # and battlefield.
    play = (
        Destroy(RANDOM(ENEMY_HAND)),
        Destroy(RANDOM(ENEMY_DECK)),
        Destroy(RANDOM(ENEMY_MINIONS)),
    )


##
# Spells


class WW_334:
    """Reinforced Plating"""

    # Gain 6 Armor. Excavate a treasure.
    play = GainArmor(FRIENDLY_HERO, 6), Excavate(CONTROLLER)


class WW_348:
    """Misfire"""

    # Deal 3, 2, and 1 damage to random minions. Quickdraw: Choose the targets.
    # Quickdraw chains three ChoiceTargets so the player picks each victim in
    # turn (a flat tuple of choices would clobber player.choice — see CLAUDE.md).
    play = QUICKDRAW & ChoiceTarget(CONTROLLER, ALL_MINIONS).then(
        Hit(ChoiceTarget.CARD, 3),
        ChoiceTarget(CONTROLLER, ALL_MINIONS).then(
            Hit(ChoiceTarget.CARD, 2),
            ChoiceTarget(CONTROLLER, ALL_MINIONS).then(Hit(ChoiceTarget.CARD, 1)),
        ),
    ) | (
        Hit(RANDOM_MINION, 3),
        Hit(RANDOM_MINION, 2),
        Hit(RANDOM_MINION, 1),
    )


class WW_380:
    """Blast Charge"""

    # Destroy a damaged enemy minion. Excavate a treasure.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_DAMAGED_TARGET: 0,
    }
    play = Destroy(TARGET), Excavate(CONTROLLER)


##
# Weapons


class WW_347:
    """Battlepickaxe"""

    # After you play a Taunt minion, gain +1 Durability.
    events = Play(CONTROLLER, MINION + TAUNT).after(Buff(SELF, "WW_347e"))


##
# Enchantments


WW_329e = buff(atk=2, health=2)  # Tauntier Taunt — +2/+2
WW_367e = buff(atk=1, health=1)  # Coal Dust — +1/+1
WW_347e = buff(health=1)  # Back in the Mine — +1 Durability
