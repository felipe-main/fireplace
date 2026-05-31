from ..utils import *


##
# Custom actions


class _GorishiColossusBonus(TargetedAction):
    """Gorishi Colossus permanent enchant tick: when the controller deals
    exactly 2 damage to an enemy, deal 2 more — guarded against re-triggering
    on its own bonus hit."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        if getattr(player, "_gorishi_colossus_bonus_active", False):
            return
        if target is None or target.dead:
            return
        if target.controller is player:
            return
        player._gorishi_colossus_bonus_active = True
        try:
            source.game.queue_actions(source, [Hit(target, 2)])
        finally:
            player._gorishi_colossus_bonus_active = False


class _EntomologistJar(TargetedAction):
    """Entomologist Toru battlecry: replace each minion in the controller's
    hand with a 0/1 Specimen Jar that costs (1) and whose deathrattle releases
    the original minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        minions = [c for c in list(player.hand) if c.type == CardType.MINION]
        for original in minions:
            jar = player.card("TLC_841t", source=source)
            jar.controller = player
            jar._summon_index = original.zone_position
            jar.zone = Zone.HAND
            original.zone = Zone.SETASIDE
            jar._jarred_minion = original
        source.game.manager.targeted_action(self, source, target)


class _ReleaseJarredMinion(TargetedAction):
    """Specimen Jar deathrattle: summon the minion stored inside the jar."""

    TARGET = ActionArg()

    def do(self, source, target):
        original = getattr(source, "_jarred_minion", None)
        if original is None:
            return
        player = source.controller
        original.controller = player
        source.game.queue_actions(player, [Summon(player, original)])
        source._jarred_minion = None


##
# Minions


class TLC_630:
    """Gorishi Wasp"""

    # Whenever this takes damage, get a 1-Cost Gorishi Stinger.
    events = SELF_DAMAGE.on(Give(CONTROLLER, "TLC_630t"))


class TLC_633:
    """Bugsquasher"""

    # <b>Battlecry:</b> Deal 6 damage to an enemy minion with a minion type.
    # NOTE: the engine's REQ_TARGET_WITH_RACE needs a *specific* race param, so
    # "any minion type" can't be a targeting filter; we require an enemy minion
    # target and deal the damage (the race restriction is cosmetic targeting).
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Hit(TARGET, 6)


class TLC_840:
    """Gorishi Tunneler"""

    # <b>Stealth</b> After this attacks, deal 2 damage to the enemy hero.
    events = Attack(SELF).after(Hit(ENEMY_HERO, 2))


class TLC_841:
    """Entomologist Toru"""

    # <b>Battlecry:</b> Put each minion in your hand into 0/1 Jars that cost
    # (1). Break them to release the minions!
    play = _EntomologistJar(CONTROLLER)


class TLC_903:
    """Silithid Queen"""

    # <b>Rush</b> <b>Kindred</b>: Give your hero +5 Attack this turn.
    play = Kindred() & Buff(FRIENDLY_HERO, "TLC_903e")


##
# Tokens


class TLC_841t:
    """Specimen Jar"""

    # <b>Deathrattle:</b> Release the stored minion.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = _ReleaseJarredMinion(SELF)


class TLC_903t:
    """Silithid Grub"""

    # <b>Rush</b> (vanilla 2/1 token; keywords come from data)


class TLC_630t:
    """Gorishi Stinger"""

    # Deal $2 damage. Summon a 2/1 Grub with <b>Rush</b>.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 2), Summon(CONTROLLER, "TLC_903t")


class TLC_631t:
    """Gorishi Colossus"""

    # <b>Battlecry:</b> For the rest of the game, whenever you deal exactly 2
    # damage to an enemy, deal 2 more.
    play = Buff(CONTROLLER, "TLC_631e")


class TLC_631e:
    # Gorishi's Favor — permanent controller enchant powering the Colossus.
    events = Damage(ENEMY_CHARACTERS, source=FRIENDLY).after(
        (Damage.AMOUNT == 2) & _GorishiColossusBonus(Damage.TARGET)
    )


##
# Weapons


class TLC_833:
    """Insect Claw"""

    # After your hero attacks, summon a 2/1 Grub with <b>Rush</b>.
    events = Attack(FRIENDLY_HERO).after(Summon(CONTROLLER, "TLC_903t"))


##
# Spells


class TLC_631:
    """Unleash the Colossus"""

    # <b>Quest:</b> Deal exactly 2 damage to an enemy on your turn, 15 times.
    # <b>Reward:</b> Gorishi Colossus.
    quest = Damage(ENEMY_CHARACTERS, source=FRIENDLY).after(
        (Damage.AMOUNT == 2)
        & (Find(CURRENT_PLAYER + CONTROLLER) & AddProgress(SELF, 1))
    )
    reward = Summon(CONTROLLER, "TLC_631t")


class TLC_900:
    """Hive Map"""

    # <b>Discover</b> a Fel spell. If you play it this turn, also pick one of
    # the others.
    play = Discover(CONTROLLER, RandomSpell(spell_school=SpellSchool.FEL)).then(
        Give(CONTROLLER, Discover.CARD),
        Buff(Discover.CARD, "TLC_900e"),
    )


class TLC_900e:
    # Marks a Hive Map-discovered spell: when played this turn, present a
    # choice of two more Fel spells (approximation of "pick one of the others").
    events = Play(OWNER).after(
        GenericChoice(CONTROLLER, RandomSpell(spell_school=SpellSchool.FEL) * 2)
    )


class TLC_901:
    """Fumigate"""

    # Deal $3 damage to a minion and all others of the same minion type.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3), Hit(ALL_MINIONS + SAME_RACE_TARGET - TARGET, 3)


class TLC_902:
    """Infestation"""

    # Get two 1-Cost Gorishi Stingers. Each one deals $2 damage and summons a
    # 2/1 Grub with <b>Rush</b>.
    play = Give(CONTROLLER, "TLC_630t") * 2


##
# Enchantments


class TLC_903e:
    """Queen's Stinger"""

    # +5 Attack this turn.
    tags = {GameTag.ATK: 5, GameTag.TAG_ONE_TURN_EFFECT: True}
