from ..utils import *

from hearthstone.enums import SpellSchool


##
# Shared Herald scaling for the "Hand/Soldier of Ragnaros" deathrattle tokens.
#
# Each token's printed deathrattle is "Deal {0} damage to a random enemy",
# where {0} starts at 2 (TAG_SCRIPT_DATA_NUM_1) and upgrades twice as the
# controller Heralds ("Herald twice to upgrade", then "Herald once to
# upgrade"). We model the upgraded value as 2 + min(heralds_this_game, 2)
# => 2 / 3 / 4 damage at 0 / 1 / 2+ heralds.


class _RagnarosDeathrattle(TargetedAction):
    """Hand / Soldier of Ragnaros deathrattle: deal (2 + min(heralds, 2))
    damage to a random enemy character."""

    TARGET = ActionArg()

    def do(self, source, target):
        heralds = getattr(source.controller, "heralds_this_game", 0)
        amount = 2 + min(heralds, 2)
        enemies = (ENEMY_CHARACTERS - DEAD).eval(source.game.entities, source)
        if not enemies:
            return
        import random

        victim = random.choice(enemies)
        source.game.cheat_action(source, [Hit(victim, amount)])


##
# Minions


class CATA_150:
    """Ragnaros, the Great Fire"""

    # Colossal +2 (limbs are the two Hand of Ragnaros tokens, engine-handled).
    # At the end of your turn, trigger your minions' Deathrattles.
    events = OWN_TURN_END.on(Deathrattle(FRIENDLY_MINIONS + DEATHRATTLE))


class CATA_150t:
    """Hand of Ragnaros"""

    # Deathrattle: Deal {0} damage to a random enemy. (Herald to upgrade.)
    deathrattle = _RagnarosDeathrattle(SELF)


class CATA_150t1:
    """Hand of Ragnaros"""

    deathrattle = _RagnarosDeathrattle(SELF)


class CATA_160:
    """Scorching Ravager"""

    # Battlecry: Herald {0}. Give the Soldier Rush.
    # The "Soldier" is the Soldier of Ragnaros token (CATA_580t) this battlecry
    # summons; it enters with Rush.
    play = (
        Herald(CONTROLLER),
        Summon(CONTROLLER, "CATA_580t").then(
            SetTags(Summon.CARD, (GameTag.RUSH,))
        ),
    )


class CATA_586:
    """Destructive Blaze"""

    # After this survives damage, summon a Destructive Blaze.
    # Deathrattle: Deal 2 damage to a random enemy.
    events = SELF_DAMAGE.on(Dead(SELF) | Summon(CONTROLLER, "CATA_586"))
    deathrattle = Hit(RANDOM(ENEMY_CHARACTERS), 2)


class CATA_591:
    """Commander Geddon"""

    # Battlecry: Instead of drawing each turn, Discover a card from your deck.
    # It costs (3) less. Destroy the others.
    #
    # Approximation: we suppress the controller's normal draw (cant_draw) and
    # apply the Barren enchant to the hero. Each turn-start Barren surfaces a
    # 3-card choice copied from the deck (Discover-style) and the chosen card
    # enters hand cost-reduced by (3). The un-picked options are copies, so the
    # deck itself is not actually thinned/"destroyed" — this is a fidelity gap.
    def play(self):
        self.controller.cant_draw = True
        yield Buff(self.controller.hero, "CATA_591e")


@custom_card
class CATA_591e:
    """Barren"""

    # At the start of your turns, Discover a card from your deck to play.
    tags = {
        GameTag.CARDNAME: "Barren",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_BEGIN.on(
        GenericChoice(CONTROLLER, Copy(RANDOM(FRIENDLY_DECK) * 3)).then(
            Buff(GenericChoice.CARD, "CATA_591e2")
        )
    )


class CATA_591e2:
    """Overheat"""

    # Costs (3) less.
    tags = {GameTag.COST: -3}


##
# Weapons


class CATA_580:
    """Cataclysmic War Axe"""

    # Battlecry: Herald {0}.
    play = Herald(CONTROLLER)


class CATA_580t:
    """Soldier of Ragnaros"""

    # Deathrattle: Deal {0} damage to a random enemy. (Herald to upgrade.)
    deathrattle = _RagnarosDeathrattle(SELF)


##
# Spells


class _Decimation(TargetedAction):
    """Decimation — deal (1 + number of minions on the battlefield) damage to
    all minions. The count is snapshotted before any minion dies so every
    minion takes the full improved amount."""

    TARGET = ActionArg()

    def do(self, source, target):
        minions = (ALL_MINIONS).eval(source.game.entities, source)
        amount = 1 + len(minions)
        for m in list(minions):
            source.game.cheat_action(source, [Hit(m, amount)])


class CATA_581:
    """Decimation"""

    # Deal $@ damage to all minions. (Improved for each minion on the
    # battlefield.) Spell-school: Fire.
    play = _Decimation(CONTROLLER)


class CATA_582:
    """Searing Fissure"""

    # Deal $1 damage to all minions. Give your hero +3 Attack this turn.
    play = (Hit(ALL_MINIONS, 1), Buff(FRIENDLY_HERO, "CATA_582e"))


class CATA_582e:
    """Flamebound"""

    # +3 Attack this turn.
    tags = {GameTag.ATK: 3, GameTag.TAG_ONE_TURN_EFFECT: True}


class _FireSpellPlayedThisTurn(Evaluator):
    """True if the controller has played a Fire spell this turn."""

    def check(self, source):
        played = getattr(source.controller, "schools_played_this_turn", set())
        return SpellSchool.FIRE in played


class CATA_584:
    """Erupting Volcano"""

    # Deal 3 damage randomly split among enemies. If you've played a Fire
    # spell this turn, deal 3 more.
    activate = (
        Hit(RANDOM(ENEMY_CHARACTERS), 1) * 3,
        (_FireSpellPlayedThisTurn() & (Hit(RANDOM(ENEMY_CHARACTERS), 1) * 3)),
    )


class _Torch(TargetedAction):
    """Torch — deal up to 8 damage (default) to a damaged minion; return a copy
    of Torch to hand carrying the *excess* damage. Each card stashes its own
    damage in ``_torch_damage`` (defaulting to 8); the returned copy's stash is
    set to the overkill so the next cast deals exactly that much. Spell damage
    is intentionally not applied (data flags ImmuneToSpellpower)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        amount = getattr(source, "_torch_damage", 8)
        excess = max(0, amount - target.health)
        source.game.cheat_action(source, [Hit(target, amount)])
        if excess > 0:
            copy = source.controller.give("CATA_585")
            copy._torch_damage = excess


class CATA_585:
    """Torch"""

    # Deal $@ damage to a damaged minion. Return this to hand with any
    # excess damage. ($@ = 8.)
    play = _Torch(TARGET)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_DAMAGED_TARGET: 0,
    }


class CATA_610:
    """Lo'Gosh's Last Stand"""

    # Give a minion "Deathrattle: Summon a random minion from your hand."
    play = Buff(TARGET, "CATA_610e")
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }


@custom_card
class CATA_610e:
    """Holding On"""

    # Deathrattle: Summon a random minion from your hand.
    tags = {
        GameTag.CARDNAME: "Holding On",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, RANDOM(FRIENDLY_HAND + MINION))
