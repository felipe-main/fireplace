from ..utils import *

from hearthstone.enums import SpellSchool


##
# Cataclysm — Mage
#
# Shared "spell damage dealt this turn" tracker.
#
# Several Mage cards key off "damage you dealt with spells this turn":
#   * CATA_452 Spellweaver's Brilliance — Costs (1) less per such damage point.
#   * CATA_483 Unstable Spellcaster — Battlecry: if you dealt damage with a
#     spell this turn, summon a copy.
#
# The engine has no native per-turn spell-damage counter, so we maintain one on
# the controller (`_cata_spell_dmg_this_turn`) via a card-borne Hand.events
# listener that fires whenever a friendly spell deals damage. The counter is
# turn-stamped (`_cata_spell_dmg_turn`); reads/bumps reset it when the stored
# turn no longer matches the current game turn, so no engine begin_turn hook is
# required. The listener is installed by every card that needs the value while
# it sits in hand (so the value is correct at cost-evaluation / battlecry time).


def _spell_dmg_this_turn(player):
    """Current 'damage dealt with spells this turn', auto-resetting per turn."""
    turn = player.game.turn
    if getattr(player, "_cata_spell_dmg_turn", None) != turn:
        player._cata_spell_dmg_turn = turn
        player._cata_spell_dmg_this_turn = 0
        player._cata_spell_dmg_seen = set()
    return getattr(player, "_cata_spell_dmg_this_turn", 0)


class _TrackSpellDamage(TargetedAction):
    """Listener body: add the spell-damage amount dealt to the per-turn tally.

    More than one Mage card can host this listener in hand simultaneously
    (Spellweaver's Brilliance + Unstable Spellcaster), and every host fires on
    the same Damage broadcast. We deduplicate per damage event using
    (game.tick, target identity): a single Damage action's broadcast shares a
    tick, so the same event is counted exactly once regardless of how many
    hosts observe it."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        player = source.controller
        _spell_dmg_this_turn(player)  # ensure the turn-stamp / seen-set is current
        key = (player.game.tick, id(target))
        seen = player._cata_spell_dmg_seen
        if key in seen:
            return
        seen.add(key)
        player._cata_spell_dmg_this_turn = (
            getattr(player, "_cata_spell_dmg_this_turn", 0) + (amount or 0)
        )


# Event: any friendly spell deals damage to any character.
_SPELL_DAMAGE_DEALT = Damage(source=SPELL + FRIENDLY).on(
    _TrackSpellDamage(CONTROLLER, Damage.AMOUNT)
)


class _SpellDamageThisTurn(LazyNum):
    """Lazily evaluate the controller's spell-damage-dealt-this-turn tally."""

    def evaluate(self, source):
        return self.num(_spell_dmg_this_turn(source.controller))


class _UnstableSpellcasterBattlecry(TargetedAction):
    """Battlecry: if you dealt damage with a spell this turn, summon a copy."""

    TARGET = ActionArg()

    def do(self, source, target):
        if _spell_dmg_this_turn(source.controller) > 0:
            source.game.cheat_action(source, [Summon(source.controller, "CATA_483")])


class _RaincallerGain(TargetedAction):
    """The first time you deal damage with a spell each turn, gain +2 Attack."""

    TARGET = ActionArg()

    def do(self, source, target):
        turn = source.game.turn
        if getattr(source, "_raincaller_turn", None) == turn:
            return
        source._raincaller_turn = turn
        source.game.cheat_action(source, [Buff(source, "CATA_487e")])


class _PlumeGetFireSpell(TargetedAction):
    """Whenever a Plume takes damage: get a random Fire spell costing (3) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        spell_id = RandomSpell(spell_school=SpellSchool.FIRE).evaluate(source)
        if not spell_id:
            return
        card = player.give(spell_id)
        source.game.cheat_action(source, [Buff(card, "CATA_488te")])


class _SindragosaTriumph(TargetedAction):
    """Deal 8 damage to a minion; reduce the Cost of a random card in your hand
    by the excess damage (damage beyond the minion's remaining health). Immune
    to Spell Power."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        amount = 8
        excess = max(0, amount - target.health)
        source.game.cheat_action(source, [Hit(target, amount)])
        if excess <= 0:
            return
        hand = [c for c in source.controller.hand]
        if not hand:
            return
        victim = source.game.random.choice(hand)
        source.game.cheat_action(source, [Buff(victim, "CATA_978e", cost=-excess)])


class _ConjurationSpecialist(TargetedAction):
    """Battlecry: Choose a spell in your hand. Split it into two random spells
    of the same Cost. Hand-targeting is unsupported, so we act on a random
    spell in hand (precedent: REV_511 random-hand approximation)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        spells = [c for c in player.hand if c.type == CardType.SPELL]
        if not spells:
            return
        chosen = source.game.random.choice(spells)
        cost = chosen.cost
        chosen.discard()
        for _ in range(2):
            new_id = RandomSpell(cost=cost).evaluate(source)
            if new_id:
                player.give(new_id)


##
# Spells


class CATA_452:
    """Spellweaver's Brilliance"""

    # Summon a 6/6 Dragon. Costs (1) less for each damage you dealt with
    # spells this turn.
    play = Summon(CONTROLLER, "CATA_452t")
    cost_mod = -_SpellDamageThisTurn()

    # Track spell damage while held so the cost reduction is live in hand.
    class Hand:
        events = _SPELL_DAMAGE_DEALT


class CATA_452t:
    """Azure Warden"""

    # 6/6 Dragon — vanilla token.


class CATA_485:
    """Sleet Storm"""

    # Deal $2 damage. Deal $1 damage to a random enemy minion.
    # No targeting arrow in data -> the 2-damage bolt also strikes a random
    # enemy character.
    play = (
        Hit(RANDOM_ENEMY_CHARACTER, 2),
        Hit(RANDOM_ENEMY_MINION, 1),
    )


class CATA_489:
    """Arcane Flow"""

    # SHATTER parent — never resolves directly; the engine splits it into its
    # two halves (CATA_489t / CATA_489t2) when it is DRAWN.


class CATA_489t:
    """Arcane Flow"""

    # Shattered: Deal $4 damage. (targeted)
    play = Hit(TARGET, 4)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }


class CATA_489t2:
    """Arcane Flow"""

    # Shattered: Deal $2 damage to all enemies.
    play = Hit(ENEMY_CHARACTERS, 2)


class CATA_978:
    """Sindragosa's Triumph"""

    # Deal $8 damage to a minion. Reduce the Cost of a random card in your
    # hand by the excess damage. (Immune to Spell Power.)
    play = _SindragosaTriumph(TARGET)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }


##
# Minions


class CATA_458:
    """Archmage Kalec"""

    # Battlecry: Give all spells in your hand and deck Spell Damage +1.
    play = Buff((FRIENDLY_HAND | FRIENDLY_DECK) + SPELL, "CATA_458e")


class CATA_458e:
    # Spell Damage +1.
    tags = {GameTag.SPELLPOWER: 1}


class CATA_483:
    """Unstable Spellcaster"""

    # Spell Damage +1.
    # Battlecry: If you dealt damage with a spell this turn, summon a copy
    # of this.
    play = _UnstableSpellcasterBattlecry(SELF)

    # Track spell damage while held so the battlecry check is accurate.
    class Hand:
        events = _SPELL_DAMAGE_DEALT


class CATA_484:
    """Winterspring Whelp"""

    # Battlecry: Discover a 1-Cost spell from any class.
    play = DISCOVER(RandomSpell(cost=1))


class CATA_487:
    """Raincaller"""

    # The first time you deal damage with a spell each turn, gain +2 Attack.
    events = Damage(source=SPELL + FRIENDLY).on(_RaincallerGain(SELF))


class CATA_487e:
    # Building Storm — +2 Attack.
    tags = {GameTag.ATK: 2}


class CATA_488:
    """Vulcanos"""

    # Colossal +2 (limbs CATA_488t / t2 are engine-handled).
    # At the end of your turn, deal 2 damage to all other minions.
    events = OWN_TURN_END.on(Hit(ALL_MINIONS - SELF, 2))


class CATA_488t:
    """Plume of Vulcanos"""

    # Whenever this takes damage, get a random Fire spell. It costs (3) less.
    events = SELF_DAMAGE.on(_PlumeGetFireSpell(CONTROLLER))


class CATA_488t2:
    """Plume of Vulcanos"""

    # Whenever this takes damage, get a random Fire spell. It costs (3) less.
    events = SELF_DAMAGE.on(_PlumeGetFireSpell(CONTROLLER))


@custom_card
class CATA_488te:
    # Cost-reduction enchant for the Fire spell granted by Plume of Vulcanos.
    tags = {
        GameTag.CARDNAME: "Cooling Off",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


class CATA_979:
    """Conjuration Specialist"""

    # Battlecry: Choose a spell in your hand. Split it into two random spells
    # of the same Cost. (Hand-targeting is unsupported -> act on a random
    # spell in hand.)
    play = _ConjurationSpecialist(SELF)
