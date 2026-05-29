from ..utils import *


##
# Spells


class _MismatchedFossilsSwap(TargetedAction):
    """Mismatched Fossils — printed text: "Discover a Beast and an Undead.
    Swap their stats."

    Faithful implementation: open a true Discover over 3 random Beasts, give
    the chosen one to hand; then open a second true Discover over 3 random
    Undead, give that one to hand; then swap the two given cards' Attack and
    Health via the DEEP_001e enchant (each enchant overrides atk/max_health
    to the *other* card's pre-swap stats, captured before either buff is
    applied so neither read sees an already-swapped value).
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # First Discover: a Beast. On choose, give it, then chain the second
        # Discover (an Undead). On that choose, give it and run the swap.
        source.game.cheat_action(
            source,
            [
                Discover(ctrl, RandomBeast()).then(
                    Give(ctrl, Discover.CARD).then(
                        _MismatchedFossilsSecond(SELF, Give.CARD)
                    )
                )
            ],
        )


class _MismatchedFossilsSecond(TargetedAction):
    """Second leg of Mismatched Fossils: remember the given Beast, open the
    Undead Discover, then swap stats once the Undead is in hand."""

    TARGET = ActionArg()
    BEAST = ActionArg()

    def do(self, source, target, beast):
        if isinstance(beast, list):
            beast = beast[0] if beast else None
        if beast is None:
            return
        ctrl = source.controller
        source.game.cheat_action(
            source,
            [
                Discover(ctrl, RandomMinion(race=Race.UNDEAD)).then(
                    Give(ctrl, Discover.CARD).then(
                        _MismatchedFossilsFinish(SELF, beast, Give.CARD)
                    )
                )
            ],
        )


class _MismatchedFossilsFinish(TargetedAction):
    """Swap the Attack and Health of the discovered Beast and Undead via the
    DEEP_001e stat-swap enchant."""

    TARGET = ActionArg()
    BEAST = ActionArg()
    UNDEAD = ActionArg()

    def do(self, source, target, beast, undead):
        if isinstance(beast, list):
            beast = beast[0] if beast else None
        if isinstance(undead, list):
            undead = undead[0] if undead else None
        if beast is None or undead is None:
            return
        # Capture both sets of stats BEFORE applying either enchant so the
        # second read does not see an already-swapped value.
        b_atk, b_health = beast.atk, beast.health
        u_atk, u_health = undead.atk, undead.health
        buff_b = source.controller.card("DEEP_001e", source=source)
        buff_b.source = source
        buff_b._xatk = u_atk
        buff_b._xhealth = u_health
        buff_u = source.controller.card("DEEP_001e", source=source)
        buff_u.source = source
        buff_u._xatk = b_atk
        buff_u._xhealth = b_health
        buff_b.apply(beast)
        buff_u.apply(undead)


class DEEP_001:
    """Mismatched Fossils"""

    # <b>Discover</b> a Beast and an Undead. Swap their stats.
    play = _MismatchedFossilsSwap(SELF)


class DEEP_001e:
    # A "New" Species! — Stats swapped with another card.
    atk = lambda self, i: self._xatk
    max_health = lambda self, i: self._xhealth


class DEEP_003:
    """Shimmer Shot"""

    # Deal $1 damage. Summon a random minion of that Cost.
    # "That Cost" is the damage actually dealt, which scales with Spell Damage
    # (Hit on a spell source adds spellpower). SPELL_DAMAGE(1) resolves to the
    # same spell-damage-adjusted value, so the summoned minion's Cost matches
    # the damage (e.g. Spell Damage +1 -> deal 2, summon a 2-cost minion).
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 1), Summon(CONTROLLER, RandomMinion(cost=SPELL_DAMAGE(1)))


##
# Minions


class DEEP_005:
    """Obsidian Revenant"""

    # <b>Taunt</b> <b>Deathrattle</b>: Summon two random <b>Deathrattle</b>
    # minions that cost (3) or less.
    deathrattle = Summon(
        CONTROLLER, RandomMinion(deathrattle=True, cost=[0, 1, 2, 3])
    ) * 2
