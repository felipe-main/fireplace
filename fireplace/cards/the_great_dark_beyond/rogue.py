from ..utils import *


def _other_class_pieces(player):
    """Collectible Starship Pieces that belong to a different class than the
    player's hero."""
    from .. import db as _db

    cls = getattr(player.hero, "card_class", None)
    return [
        cid
        for cid, c in _db.items()
        if c.collectible
        and c.tags.get(GameTag.STARSHIP_PIECE, 0)
        and c.card_class != cls
    ]


##
# Custom actions


class _DiscoverOtherClassPiece(TargetedAction):
    """Starship Schematic — Discover a Starship Piece from another class; it
    costs (1) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        pool = _other_class_pieces(source.controller)
        if not pool:
            return
        source.game.queue_actions(
            source,
            [
                Discover(source.controller, RandomID(*pool)).then(
                    Give(source.controller, Discover.CARD).then(
                        Buff(Give.CARD, "GDB_102e")
                    )
                )
            ],
        )


class _GiveOtherClassPiece(TargetedAction):
    """Scrounging Shipwright — get a random Starship Piece from another class."""

    TARGET = ActionArg()

    def do(self, source, target):
        pool = _other_class_pieces(source.controller)
        if pool:
            source.game.cheat_action(
                source, [Give(source.controller, source.game.random.choice(pool))]
            )


class _ArmComboTwice(TargetedAction):
    """Lucky Comet — the next Combo minion you play triggers its Combo twice."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.next_combo_triggers_twice += 1


class _ArmComboDiscount(TargetedAction):
    """Spacerock Collector — your next Combo card costs (1) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.next_combo_discount += 1


##
# Minions


class GDB_466:
    """The Gravitational Displacer"""

    # Starship Piece. When this is launched, summon a copy of the Starship.
    # (Launch effect handled by the engine's LaunchStarship.)


class GDB_472:
    """Talgath"""

    # Undamaged enemy minions take double damage. Combo: Get a Backstab.
    # Continuous aura: while Talgath is in play, every enemy minion that has
    # taken no damage carries INCOMING_DAMAGE_MULTIPLIER 1 (the engine left-
    # shifts the damage by the multiplier, so 1 == double). The instant a
    # minion is damaged it drops out of (ENEMY_MINIONS - DAMAGED) and the aura
    # buff is reclaimed, so only the first hit while undamaged is doubled.
    update = Refresh(ENEMY_MINIONS - DAMAGED, {GameTag.INCOMING_DAMAGE_MULTIPLIER: 1})
    combo = Give(CONTROLLER, "CS2_072")


class GDB_870:
    """Eredar Skulker"""

    # Combo and Spellburst: Gain +2 Attack and Stealth. The GDB_870e2 data
    # enchant ('Skulking') carries no ATK tag in this build, so supply +2 via
    # the buff kwarg.
    combo = Buff(SELF, "GDB_870e2", atk=2), SetTags(SELF, {GameTag.STEALTH: True})
    spellburst = Buff(SELF, "GDB_870e2", atk=2), SetTags(SELF, {GameTag.STEALTH: True})


class GDB_875:
    """Spacerock Collector"""

    # Battlecry: Your next Combo card costs (1) less.
    play = _ArmComboDiscount(CONTROLLER)


class GDB_876:
    """Scrounging Shipwright"""

    # Battlecry: Get a random Starship Piece from another class.
    play = _GiveOtherClassPiece(SELF)


##
# Spells


class GDB_102:
    """Starship Schematic"""

    # Discover a Starship Piece from another class. It costs (1) less.
    play = _DiscoverOtherClassPiece(SELF)


class GDB_465:
    """Barrel Roll"""

    # Deal $5 damage to an undamaged character. Costs (1) if you're building a
    # Starship.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_UNDAMAGED_TARGET: 0,
    }
    cost_mod = BUILDING_STARSHIP(CONTROLLER) & -2
    play = Hit(TARGET, 5)


class GDB_467:
    """Quasar"""

    # Shuffle your hand into your deck. Reduce the Cost of cards in your deck
    # by (3).
    play = Shuffle(CONTROLLER, FRIENDLY_HAND), Buff(FRIENDLY_DECK, "GDB_467e")


class GDB_873:
    """Lucky Comet"""

    # Discover a Combo minion. The next one you play triggers its Combo twice.
    play = Discover(CONTROLLER, RandomMinion(combo=True)).then(
        Give(CONTROLLER, Discover.CARD), _ArmComboTwice(CONTROLLER)
    )


class GDB_881:
    """Pressure Points"""

    # Deal $3 damage to a minion. Reduce the Cost of Combo cards in your hand
    # by (1).
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3), Buff(FRIENDLY_HAND + COMBO, "GDB_881e")


##
# Enchantments


@custom_card
class GDB_102e:
    # Starship Schematic — the discovered Piece costs (1) less.
    tags = {
        GameTag.CARDNAME: "Starship Schematic",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


@custom_card
class GDB_467e:
    # Quasar — card in deck costs (3) less.
    tags = {
        GameTag.CARDNAME: "Quasar",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


@custom_card
class GDB_881e:
    # Pressure Points — Combo card costs (1) less.
    tags = {
        GameTag.CARDNAME: "Pressure Points",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }
