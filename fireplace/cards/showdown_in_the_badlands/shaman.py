"""Showdown in the Badlands — Shaman cards (WILD_WEST)."""

from ..utils import *


##
# Custom actions


class _SkarrElementalStreak(TargetedAction):
    """Skarr, the Catastrophe — deal damage to all enemies equal to the
    number of turns in a row you've played an Elemental, where the current
    turn (on which Skarr itself — an Elemental — is being played) always
    counts.

    The engine maintains the global `azerite_elemental_streak` counter:
    the number of *completed* consecutive own-turns ending with the
    controller's last turn on which an Elemental was played (reset to 0 in
    `game._begin_turn` whenever a turn passed with no Elemental). Skarr
    being played guarantees the current turn is an Elemental turn, so the
    full streak is always `azerite_elemental_streak + 1` — fresh board
    yields 1 (Skarr alone), an Elemental last turn + Skarr yields 2, etc.
    Skarr therefore never deals 0.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        streak = ctrl.azerite_elemental_streak + 1
        source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, streak)])


class _TrustyCompanionDraw(TargetedAction):
    """Trusty Companion — after the +2/+3 buff, if the buffed minion has a
    minion type, draw a minion of that type from the controller's deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        if isinstance(target, (list, tuple)):
            target = target[0] if target else None
        if target is None:
            return
        races = [r for r in getattr(target, "races", []) if r != Race.INVALID]
        if not races:
            return
        ctrl = source.controller
        if Race.ALL in races:
            candidates = [c for c in ctrl.deck if c.type == CardType.MINION]
        else:
            wanted = set(races)
            candidates = [
                c
                for c in ctrl.deck
                if c.type == CardType.MINION
                and (
                    set(getattr(c, "races", [])) & wanted
                    or Race.ALL in getattr(c, "races", [])
                )
            ]
        if not candidates:
            return
        import random

        pick = random.choice(candidates)
        source.game.cheat_action(source, [ForceDraw(pick)])


class _CactusCutterDraw(TargetedAction):
    """Cactus Cutter — draw a spell and remember it on the minion. If that
    exact spell is cast this turn, the minion's OWN_SPELL_PLAY listener
    buffs it +1/+2 and Taunt (see WW_327 events)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spells = [c for c in ctrl.deck if c.type == CardType.SPELL]
        source._cactus_spell = None
        source._cactus_done = False
        if not spells:
            return
        import random

        pick = random.choice(spells)
        source.game.cheat_action(source, [ForceDraw(pick)])
        source._cactus_spell = pick


class _CactusCutterCheck(TargetedAction):
    """Fires on every spell the controller plays while Cactus Cutter is in
    play. If the played spell is the one Cactus Cutter drew this turn (and
    Cactus Cutter hasn't already triggered), buff +1/+2 and Taunt."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        if isinstance(card, (list, tuple)):
            card = card[0] if card else None
        played = getattr(source, "_cactus_spell", None)
        if played is None or card is not played:
            return
        if getattr(source, "_cactus_done", False):
            return
        source._cactus_done = True
        source.game.cheat_action(source, [Buff(source, "WW_327e")])


class _StaffSummonFrog(TargetedAction):
    """Staff of the Nine Frogs — summon a Frog whose stats grow by +1/+1
    over the previous one. The first Frog is the base 1/1 WW_010hexfrog;
    each subsequent Frog gets +n/+n where n is how many Frogs preceded
    it. Tracks a per-weapon counter."""

    TARGET = ActionArg()

    def do(self, source, target):
        n = getattr(source, "frogs_summoned", 0)
        source.frogs_summoned = n + 1
        if n == 0:
            source.game.cheat_action(
                source, [Summon(source.controller, "WW_010hexfrog")]
            )
        else:
            source.game.cheat_action(
                source,
                [
                    Summon(source.controller, "WW_010hexfrog").then(
                        Buff(Summon.CARD, "WW_010frog_e", atk=n, max_health=n)
                    )
                ],
            )


@custom_card
class WW_010frog_e:
    # Growing-Frog enchant for Staff of the Nine Frogs. Atk/health are
    # supplied per-summon as Buff kwargs.
    tags = {
        GameTag.CARDNAME: "Bigger Frog",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


##
# Minions


class WW_010:
    """Doctor Holli'dae"""

    # Battlecry: If your deck has no duplicates, equip the Staff of the
    # Nine Frogs.
    powered_up = -FindDuplicates(FRIENDLY_DECK)
    play = powered_up & Summon(CONTROLLER, "WW_010t")


class WW_024:
    """Living Prairie"""

    # Battlecry: If you played an Elemental last turn, summon two 3/3 Cows
    # with Rush. (Rush is in data on the Startled Cow token.)
    play = ELEMENTAL_PLAYED_LAST_TURN & (Summon(CONTROLLER, "WW_024t") * 2)


class WW_026:
    """Skarr, the Catastrophe"""

    # Battlecry: Deal X damage to all enemies (improved by each turn in a
    # row you've played an Elemental).
    play = _SkarrElementalStreak(SELF)


class WW_326:
    """Minecart Cruiser"""

    # Rush, Overload: (2). Battlecry: If you played an Elemental last turn,
    # don't Overload. Rush + Overload(2) live in data; the engine queues
    # the Overload AFTER the battlecry, so setting cant_overload during
    # the battlecry suppresses it for this turn.
    play = ELEMENTAL_PLAYED_LAST_TURN & Buff(
        CONTROLLER, "WW_326e", cant_overload=True
    )


@custom_card
class WW_326e:
    # One-turn "can't be Overloaded" marker for Minecart Cruiser (not in
    # data). cant_overload is supplied as a Buff kwarg; the enchant tears
    # itself down at end of turn.
    tags = {
        GameTag.CARDNAME: "Minecart Cruiser",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_END.on(Destroy(SELF))


class WW_327:
    """Cactus Cutter"""

    # Battlecry: Draw a spell. If you cast it this turn, gain +1/+2 and
    # Taunt.
    play = _CactusCutterDraw(SELF)
    events = OWN_SPELL_PLAY.on(_CactusCutterCheck(SELF, Play.CARD))


class WW_382:
    """Walking Mountain"""

    # Rush, Lifesteal, Mega-Windfury, Overload: (2). Rush/Lifesteal/
    # Overload are in data; Mega-Windfury is not, so grant it here.
    tags = {GameTag.MEGA_WINDFURY: True}


##
# Enchantments (in data, but need stat tags supplied here)


class WW_027e:
    # Sidekick's Sidearm — +2/+3 from Trusty Companion.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 3}


class WW_327e:
    # Cactus Cutter — +1/+2 and Taunt when the drawn spell is cast.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2, GameTag.TAUNT: True}


##
# Spells


class WW_027:
    """Trusty Companion"""

    # Give a minion +2/+3. If it has a minion type, draw one of that type.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "WW_027e"), _TrustyCompanionDraw(TARGET)


class WW_080:
    """Amphibious Elixir"""

    # Restore 5 Health. Discover a spell.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Heal(TARGET, 5), DISCOVER(RandomSpell())


class WW_090:
    """Giant Tumbleweed!!!"""

    # Deal 6 damage to all minions. Summon a 6/6 Tumbleweed.
    play = Hit(ALL_MINIONS, 6), Summon(CONTROLLER, "WW_090t")


class WW_325:
    """Dehydrate"""

    # Lifesteal. Deal 4 damage to a minion. Quickdraw: Costs (1).
    # Lifesteal is in data on the spell. The cost drops to 1 while
    # Quickdraw is live in hand (card played the same turn it was drawn).
    # cost_mod is an additive delta in this engine; base cost is 3 so a
    # -2 delta lands the card at 1 ("Costs (1)").
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    cost_mod = QUICKDRAW_HAND & -2
    play = Hit(TARGET, 4)


##
# Tokens / Weapons


class WW_024t:
    """Startled Cow"""

    # 3/3 with Rush — Rush is in data. Vanilla token.


class WW_090t:
    """Tumbleweed"""

    # 6/6 vanilla token.


class WW_010t:
    """Staff of the Nine Frogs"""

    # After your hero attacks, summon a growing Frog with Taunt (each
    # Frog is bigger than the last).
    frogs_summoned = 0
    events = Attack(FRIENDLY_HERO).after(_StaffSummonFrog(SELF))
