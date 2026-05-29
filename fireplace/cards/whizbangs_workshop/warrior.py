from ..utils import *


##
# Custom actions


class _BotfaceGiveMinis(TargetedAction):
    """Botface — after this takes damage, get two random Minis.  The Mini
    pool is every non-collectible 1/1 "Mini" token in Whizbang's Workshop
    (GameTag.MINI == 1). They aren't is_standard-flagged, so the standard
    RandomCardPicker path would filter them out; pick directly here and
    add the cards to the controller's hand via Give."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        pool = [
            cid
            for cid in db.filter(collectible=False, type=CardType.MINION)
            if db[cid].tags.get(GameTag.MINI) == 1
        ]
        if not pool:
            return
        picks = [source.game.random.choice(pool) for _ in range(2)]
        source.game.cheat_action(source, [Give(ctrl, pick) for pick in picks])


class _LabPatronArmorGain(TargetedAction):
    """Lab Patron — the first time you gain Armor each turn, summon another
    Lab Patron.  GainArmor.do increments controller.armor_gained_this_turn
    *before* broadcasting, so at listen time the gain is the first of the
    turn iff armor_gained_this_turn equals the amount just gained."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        if amount <= 0:
            return
        ctrl = source.controller
        if ctrl.armor_gained_this_turn == amount:
            source.game.cheat_action(source, [Summon(ctrl, "TOY_651")])


##
# Spells


class TOY_602:
    """Chemical Spill"""

    # Summon the highest Cost minion from your hand, then deal $5 damage to it.
    play = Summon(CONTROLLER, HIGHEST_COST(FRIENDLY_HAND + MINION)).then(
        Hit(Summon.CARD, 5)
    )


class TOY_603:
    """Wreck'em and Deck'em"""

    # [x]Choose a friendly Mech. Summon a copy of it that attacks a random
    # enemy, then dies.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_TARGET_WITH_RACE: int(Race.MECHANICAL),
    }
    play = Summon(CONTROLLER, Copy(TARGET)).then(
        Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER), Destroy(Summon.CARD)
    )


class TOY_605:
    """Quality Assurance"""

    # Draw 2 Taunt minions.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + TAUNT)) * 2


class TOY_907:
    """Safety Goggles"""

    # Gain 6 Armor. Costs (0) if you don't have any Armor.
    cost_mod = (Attr(FRIENDLY_HERO, GameTag.ARMOR) == 0) & -2
    play = GainArmor(FRIENDLY_HERO, 6)


##
# Weapons


class TOY_604:
    """Boom Wrench"""

    # [x]<b>Miniaturize</b> <b>Deathrattle:</b> Trigger the <b>Deathrattle</b>
    # of a random friendly Mech.
    deathrattle = Deathrattle(RANDOM(FRIENDLY_MINIONS + MECH + DEATHRATTLE))


class TOY_604t:
    """Boom Wrench"""

    # [x]<b>Mini</b> <b>Deathrattle:</b> Trigger the <b>Deathrattle</b> of a
    # random friendly Mech.
    deathrattle = Deathrattle(RANDOM(FRIENDLY_MINIONS + MECH + DEATHRATTLE))


##
# Minions


class TOY_606:
    """Testing Dummy"""

    # <b>Taunt</b> <b>Deathrattle:</b> Deal 8 damage randomly split among all
    # enemies.
    deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 1) * 8


class TOY_607:
    """Inventor Boom"""

    # [x]<b>Battlecry:</b> Resurrect two friendly Mechs that cost (5) or more.
    # They immediately attack random enemies.
    play = (
        Summon(
            CONTROLLER,
            Copy(RANDOM(FRIENDLY + KILLED + MINION + MECH + (COST >= 5))),
        ).then(Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER))
        * 2
    )


class TOY_651:
    """Lab Patron"""

    # The first time you gain Armor each turn, summon another Lab Patron.
    events = GainArmor(FRIENDLY_HERO).on(
        _LabPatronArmorGain(SELF, GainArmor.AMOUNT)
    )


class TOY_906:
    """Botface"""

    # [x]<b>Taunt</b> After this takes damage, get two random <b>Minis</b>.
    events = Damage(SELF).on(_BotfaceGiveMinis(SELF))


class TOY_908:
    """Fireworker"""

    # <b>Deathrattle:</b> Summon two 1/1 Boom Bots. <i>WARNING: Bots may
    # explode.</i>
    deathrattle = Summon(CONTROLLER, "GVG_110t") * 2
