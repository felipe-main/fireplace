from ..utils import *


##
# Minions


class _FrostbittenFreebooter(TargetedAction):
    """Deathrattle: Freeze 3 random enemies. Any that were already Frozen
    take 5 damage instead of being Frozen."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        game = source.game
        # Pool of living enemy characters.
        enemies = [
            c
            for c in ctrl.opponent.characters
            if not c.dead and c.zone == Zone.PLAY
        ]
        game.random.shuffle(enemies)
        chosen = enemies[:3]
        for c in chosen:
            if c.frozen:
                game.cheat_action(source, [Hit(c, 5)])
            else:
                game.cheat_action(source, [Freeze(c)])


# Deathrattle: Freeze 3 random enemies. Any that were already Frozen take 5
# damage instead.
class VAC_402:
    """Frostbitten Freebooter"""

    deathrattle = _FrostbittenFreebooter(SELF)


# Deathrattle: For the rest of the game, your minions have +1 Attack.
class VAC_426:
    """Eliza Goreblade"""

    deathrattle = Buff(CONTROLLER, "VAC_426e")


# For the rest of the game, your minions have +1 Attack.
class VAC_426e:
    """Vitality Shift"""

    update = Refresh(FRIENDLY_MINIONS, buff="VAC_426e2")


# +1 Attack
class VAC_426e2:
    """Vitalized"""

    tags = {GameTag.ATK: 1}


# Costs (1) if a character is Frozen.
# cost_mod is an additive delta; base cost is 4 so a -3 delta lands the
# card at 1 ("Costs (1)") whenever any character is Frozen.
class VAC_429:
    """Snow Shredder"""

    cost_mod = Find(ALL_CHARACTERS + FROZEN) & -3


# Whenever you play a Deathrattle minion, give it Reborn.
class VAC_436:
    """Brittlebone Buccaneer"""

    events = Play(CONTROLLER, MINION + DEATHRATTLE).after(GiveReborn(Play.CARD))


# Shaman Tourist. Battlecry: Draw a spell of each spell school.
class VAC_437:
    """Buttons"""

    play = (
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + ARCANE_SPELL)),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + FIRE_SPELL)),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + FROST_SPELL)),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + NATURE_SPELL)),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + HOLY_SPELL)),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + SHADOW_SPELL)),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + FEL_SPELL)),
    )


# Rush. Deathrattle: Summon a 1/1 Dreadhound with Reborn.
class VAC_514:
    """Dreadhound Handler"""

    tags = {GameTag.RUSH: True}
    deathrattle = Summon(CONTROLLER, "VAC_514t")


# Reborn (data tag).
class VAC_514t:
    """Dreadhound"""


##
# Locations


# Deal 3 damage randomly split among all enemies. After a friendly minion
# dies, reopen this.
class VAC_425:
    """Horizon's Edge"""

    activate = Hit(RANDOM_ENEMY_CHARACTER, 1) * 3
    events = Death(FRIENDLY + MINION).after(ReopenLocation(SELF))


##
# Spells


# Deal 3 damage. Spend 3 Corpses to return this to your hand at the end of
# your turn.
class VAC_427:
    """Corpsicle"""

    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 3), (CORPSES >= 3) & (
        SpendCorpses(CONTROLLER, 3),
        Buff(CONTROLLER, "VAC_427e"),
    )


# Get a Corpsicle at the end of the turn.
class VAC_427e:
    """Corpsicle"""

    events = OWN_TURN_END.on(Give(CONTROLLER, "VAC_427"), Destroy(SELF))


# Summon five 1/1 Ghouls that attack random enemies.
class VAC_445:
    """Ghouls' Night"""

    play = (
        Summon(CONTROLLER, "VAC_445t").then(
            Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER)
        )
        * 5
    )


# 1/1 Ghoul token.
class VAC_445t:
    """Slumbering Ghoul"""


# Freeze a character. Draw a card for each Frozen character.
class VAC_513:
    """Slippery Slope"""

    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Freeze(TARGET), Draw(CONTROLLER) * Count(ALL_CHARACTERS + FROZEN)
