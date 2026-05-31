from ..utils import *

from hearthstone.enums import CardType, GameTag

from ._smolder import _SmolderTick, smolder_level


##
# Into the Emerald Dream — PRIEST collectible cards.
#
# Two Imbue cards (EDR_449 Lunarwing Messenger, EDR_970 Kaldorei Priestess)
# call Imbue(CONTROLLER) — the engine swaps in the Priest Imbued Hero Power
# (EDR_449p Blessing of the Moon, in tokens.py) and bumps
# player.imbues_this_game.
#
# The two "New Moon" spells (EDR_460 / EDR_461) are the lunar spell-counting
# mechanic: "(Cast 4 spells to ...)" — the upgraded effect fires once this is
# your 4th-or-later spell of the game. Play.do bumps
# spells_played_this_game AFTER queueing the spell's actions, so at play-time
# the counter does NOT yet include this spell. The 4th spell therefore sees
# spells_played_this_game >= 3.


##
# Custom actions


class _NewMoonLifesteal(TargetedAction):
    """Wish of the New Moon — if this is your 4th spell this game, the source
    spell gains Lifesteal so the follow-up Hit heals."""

    TARGET = ActionArg()

    def do(self, source, target):
        if source.controller.spells_played_this_game >= 3:
            source.lifesteal = True


def _is_fourth_spell(source):
    # True when the spell being played is the controller's 4th-or-later this
    # game (the current spell is not yet counted at play-time).
    return source.controller.spells_played_this_game >= 3


class _RitualSummon(TargetedAction):
    """Ritual of the New Moon — summon two random minions; 3-Cost normally,
    6-Cost once this is your 4th spell this game."""

    TARGET = ActionArg()

    def do(self, source, target):
        cost = 6 if _is_fourth_spell(source) else 3
        source.game.cheat_action(
            source, [Summon(source.controller, RandomMinion(cost=cost)) * 2]
        )


class _LunarCycleTick(TargetedAction):
    """Aviana — advance the three-turn lunar cycle. On the third own-turn
    begin the Full Moon rises: your cards cost (1) this game."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target  # the Moon Cycle enchant carrying the counter
        enchant._lunar_turns = getattr(enchant, "_lunar_turns", 0) + 1
        if enchant._lunar_turns >= 3:
            source.game.cheat_action(
                source, [Buff(source.controller, "EDR_895e")]
            )
            source.game.cheat_action(source, [Destroy(enchant)])


##
# Cards


class EDR_449:
    """Lunarwing Messenger"""

    # Lifesteal. Battlecry: Imbue your Hero Power.
    play = Imbue(CONTROLLER)


class EDR_460:
    """Wish of the New Moon"""

    # Deal $6 damage to a minion. (Cast 4 spells to gain Lifesteal.)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _NewMoonLifesteal(TARGET).then(Hit(TARGET, 6))


class EDR_461:
    """Ritual of the New Moon"""

    # Summon two random 3-Cost minions. (Cast 4 spells to summon 6-Cost
    # minions instead.)
    play = _RitualSummon(CONTROLLER)


class EDR_462:
    """Selenic Drake"""

    # Elusive. At the end of your turn, get a random Dragon.
    # The ELUSIVE keyword is in data as an unmapped tag, so the targeting
    # code never sees it — restore it via the legacy split flags.
    tags = {
        GameTag.CANT_BE_TARGETED_BY_ABILITIES: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }
    events = OWN_TURN_END.on(Give(CONTROLLER, RandomDragon()))


class EDR_463:
    """Twilight Influence"""

    # Choose One - Destroy a minion with 3 or less Attack; or Summon a
    # random 2-Cost minion.
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
    choose = ("EDR_463a", "EDR_463b")
    play = ChooseBoth(CONTROLLER) & (
        Destroy(TARGET),
        Summon(CONTROLLER, RandomMinion(cost=2)),
    )


class EDR_463a:
    """Constricting Thorns"""

    # Destroy a minion with 3 or less Attack.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_MAX_ATTACK: 3,
    }
    play = Destroy(TARGET)


class EDR_463b:
    """Controlling Vines"""

    # Summon a random 2-Cost minion.
    play = Summon(CONTROLLER, RandomMinion(cost=2))


class EDR_464:
    """Tyrande"""

    # Battlecry: The next 3 spells you play cast twice.
    play = Buff(CONTROLLER, "EDR_464e2")


class EDR_464e2:
    """Pull of the Moon"""

    # Your next 3 spells cast twice. Grant the SPELLS_CAST_TWICE aura and
    # count down three spell plays before expiring.
    progress_total = 3
    update = Refresh(CONTROLLER, {GameTag.SPELLS_CAST_TWICE: True})
    events = Play(CONTROLLER, SPELL).after(AddProgress(SELF, Play.CARD))
    reward = Destroy(SELF)


class EDR_472:
    """Weaver of the Cycle"""

    # Battlecry: If you're holding a spell that costs (5) or more, deal 3
    # damage.
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
    play = Find(FRIENDLY_HAND + SPELL + (COST >= 5)) & Hit(TARGET, 3)


class EDR_476:
    """Moonwell"""

    # Deal $4 damage to all enemy characters. Restore #4 Health to all
    # friendly characters.
    play = Hit(ENEMY_CHARACTERS, 4), Heal(FRIENDLY_CHARACTERS, 4)


class EDR_895:
    """Aviana, Elune's Chosen"""

    # Battlecry: Start a three turn lunar cycle. When the Full Moon rises,
    # your cards cost (1) this game.
    play = Buff(FRIENDLY_HERO, "EDR_895t")


class EDR_895t:
    """Moon Cycle"""

    # In @ turns, your cards cost (1). Countdown enchant attached to the
    # hero; the Full Moon rises on the third of your turn-begins.
    events = OWN_TURN_BEGIN.on(_LunarCycleTick(SELF))


class EDR_895e:
    """Full Moon"""

    # Your cards cost (1). Persists this game (attached to the controller).
    update = Refresh(FRIENDLY_HAND, {GameTag.COST: SET(1)})


class EDR_970:
    """Kaldorei Priestess"""

    # Battlecry: Give all enemy minions -2 Attack until your next turn.
    # Imbue your Hero Power.
    play = (
        Buff(ENEMY_MINIONS, "EDR_970e"),
        Imbue(CONTROLLER),
    )


class EDR_970e:
    """Pacified"""

    # -2 Attack until your next turn.
    tags = {GameTag.ATK: -2}
    events = OWN_TURN_BEGIN.on(Destroy(SELF))


##
# Emerald Dream mini-set (Firelands, FIR_) — PRIEST collectibles.
#
# FIR_777 Spirit of the Kaldorei — Taunt/Lifesteal, +2/+2 battlecry gated on
#   having used your Hero Power this turn.
# FIR_916 Smoldering Ascent — board-clear Smoldering spell (see _smolder.py).
# FIR_918 Light of the New Moon — +3/+3 buff that bounces back to hand once it
#   is your 4th-or-later spell of the game.


class _UsedHeroPowerThisTurnBuff(TargetedAction):
    """Spirit of the Kaldorei — if the controller has activated their Hero
    Power this turn, buff the target (the just-played minion) +2/+2."""

    TARGET = ActionArg()

    def do(self, source, target):
        power = source.controller.hero.power
        if power is not None and getattr(power, "activations_this_turn", 0) >= 1:
            source.game.cheat_action(source, [Buff(target, "FIR_777e")])


@custom_card
class FIR_777e:
    """Kaldorei Spirit"""

    # +2/+2. Not present in CardXML for this build, so registered as a custom
    # enchantment.
    tags = {
        GameTag.CARDNAME: "Kaldorei Spirit",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 2,
        GameTag.HEALTH: 2,
    }


class FIR_777:
    """Spirit of the Kaldorei"""

    # Taunt, Lifesteal. Battlecry: If you used your Hero Power this turn, gain
    # +2/+2. (Taunt + Lifesteal come from data.)
    play = _UsedHeroPowerThisTurnBuff(SELF)


class FIR_916:
    """Smoldering Ascent"""

    # Deal ${0} damage to all enemy minions. (Upgrades each turn, but discards
    # after {1}!)  The {0} start/step and {1} discard threshold are
    # server-resolved (absent from CardXML) — best-fidelity defaults from
    # _smolder.py: base 1, +1 per held turn, discarded after 3 of your turns.
    class Hand:
        events = OWN_TURN_BEGIN.on(_SmolderTick(SELF))

    def play(self):
        yield Hit(ENEMY_MINIONS, smolder_level(self, base=1))


class FIR_918:
    """Light of the New Moon"""

    # Give a minion +3/+3. (Cast 4 spells to return this to your hand when
    # played.)  Play.do bumps spells_played_this_game AFTER queueing this
    # spell's actions, so the 4th-or-later spell sees the counter at >= 3.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "FIR_918e"), (
        Attr(CONTROLLER, "spells_played_this_game") >= 3
    ) & Give(CONTROLLER, "FIR_918")


@custom_card
class FIR_918e:
    """Lunar Blessing"""

    # +3/+3. Not present in CardXML for this build, so registered as a custom
    # enchantment.
    tags = {
        GameTag.CARDNAME: "Lunar Blessing",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
    }
