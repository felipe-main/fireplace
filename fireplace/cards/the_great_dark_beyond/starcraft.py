from ..utils import *

from ...actions import _StarshipSpellburst  # noqa: F401
from ...dsl.random_picker import RandomCardPicker
from .neutral import _GainBonusEffects
from .tokens import _StarshipToken


##
# Custom actions


class _RandomZergMinion(RandomCardPicker):
    """A random collectible Zerg minion (faction = GameTag.ZERG). Used by
    Larva, which re-rolls into a new one each turn it sits in hand."""

    def find_cards(self, source, **filters):
        from .. import db as _db

        return [
            cid
            for cid, c in _db.items()
            if c.collectible
            and c.type == CardType.MINION
            and c.tags.get(GameTag.ZERG, 0)
        ]


class _SiegeTankDeployed(TargetedAction):
    """Siege Tank, Deployed — deal 10 damage to a random enemy minion; excess
    damage hits the enemy hero."""

    TARGET = ActionArg()

    def do(self, source, target):
        enemies = [m for m in ENEMY_MINIONS.eval(source.game, source) if not m.dead]
        if not enemies:
            return
        victim = source.game.random.choice(enemies)
        source.game.cheat_action(
            source, [Hit(ENEMY_HERO, HitExcessDamage(victim, 10))]
        )


class _ThorPayload(TargetedAction):
    """Thor, Explosive Payload — deal 5 damage to the target, then repeat at a
    random enemy for each Starship you've launched this game."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is not None:
            source.game.cheat_action(source, [Hit(target, 5)])
        launched = getattr(source.controller, "_sc_starships_launched", 0)
        for _ in range(max(0, launched)):
            enemies = [
                c for c in ENEMY_CHARACTERS.eval(source.game, source) if not c.dead
            ]
            if not enemies:
                break
            source.game.cheat_action(
                source, [Hit(source.game.random.choice(enemies), 5)]
            )


class _GiveRandomStarshipPiece(TargetedAction):
    """Wayward Probe — get a random (collectible) Starship Piece."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db

        pool = [
            cid
            for cid, c in _db.items()
            if c.collectible and c.tags.get(GameTag.STARSHIP_PIECE, 0)
        ]
        if pool:
            source.game.cheat_action(
                source, [Give(source.controller, source.game.random.choice(pool))]
            )


class _RavageSplit(TargetedAction):
    """Ravage — deal damage randomly split among all enemies. Base 3, improved
    by +1 for each Zerg minion you control."""

    TARGET = ActionArg()

    def do(self, source, target):
        zerg = len(
            [m for m in (FRIENDLY_MINIONS + ZERG).eval(source.game, source)]
        )
        amount = 3 + zerg
        for _ in range(amount):
            enemies = [
                c for c in ENEMY_CHARACTERS.eval(source.game, source) if not c.dead
            ]
            if not enemies:
                break
            source.game.cheat_action(
                source, [Hit(source.game.random.choice(enemies), 1)]
            )


##
# Zerg tokens


class SC_003t:
    """Larva"""

    # Each turn this is in your hand, transform it into a random Zerg minion.
    # Re-rolls EVERY turn: the morph carries the SC_003te enchant forward, whose
    # own Hand trigger morphs again next turn (Shifting Scroll / Bandersmosh).
    class Hand:
        events = OWN_TURN_BEGIN.on(
            Morph(SELF, _RandomZergMinion()).then(Buff(Morph.CARD, "SC_003te"))
        )


class SC_003te:
    """Transforming Larva"""

    class Hand:
        events = OWN_TURN_BEGIN.on(
            Morph(OWNER, _RandomZergMinion()).then(Buff(Morph.CARD, "SC_003te"))
        )

    events = REMOVED_IN_PLAY


class SC_006:
    """Ultralisk"""

    # Rush (data).


class SC_019t:
    """Baneling"""

    # Deathrattle: Deal damage equal to this minion's Attack to all enemy
    # minions.
    deathrattle = Hit(ENEMY_MINIONS, ATK(SELF))


##
# Terran tokens


class SC_403t:
    """Marine"""

    # Taunt (data).


class SC_403a:
    """Viking"""

    # Starship Piece. When this is launched, gain 7 Armor.
    launch = GainArmor(FRIENDLY_HERO, 7)


class SC_403b:
    """Liberator"""

    # Starship Piece. When this is launched, deal 2 damage to all enemies.
    launch = Hit(ENEMY_CHARACTERS, 2)


class SC_403c:
    """Raven"""

    # Starship Piece. When this is launched, gain 3 random Bonus Effects.
    launch = _GainBonusEffects(SELF, 3)


class SC_403d:
    """Banshee"""

    # Starship Piece. When this is launched, deal 5 damage to a random enemy.
    launch = Hit(RANDOM(ENEMY_CHARACTERS), 5)


class SC_403f:
    """Medivac"""

    # Starship Piece. When this is launched, summon two 2/2 Marines with Taunt.
    launch = Summon(CONTROLLER, "SC_403t") * 2


class SC_412t:
    """Hellbat"""

    # Your other minions have +2 Attack and Rush.
    update = (
        Refresh(FRIENDLY_MINIONS - SELF, {GameTag.ATK: 2}),
        Refresh(FRIENDLY_MINIONS - SELF, {GameTag.RUSH: True}),
    )


class SC_413t:
    """Siege Tank, Deployed"""

    # Battlecry: Deal 10 damage to a random enemy minion. Excess damage hits
    # the enemy hero.
    play = _SiegeTankDeployed(SELF)


class SC_414t:
    """Thor, Explosive Payload"""

    # Battlecry: Deal 5 damage. Repeat at a random enemy for each Starship
    # you've launched this game.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = _ThorPayload(TARGET)


##
# Protoss tokens


class SC_751t:
    """Zealot"""

    # Charge (data).


class SC_756t:
    """Interceptor"""

    # 4/1 vanilla token (summoned by Carrier; attacks a random enemy on
    # summon — that behaviour belongs to Carrier, not the token).


class SC_671t1:
    """Archon"""

    # At the end of your turn, deal 8 damage to the enemy hero and 2 damage to
    # their minions.
    events = OWN_TURN_END.on(Hit(ENEMY_HERO, 8), Hit(ENEMY_MINIONS, 2))


##
# Neutral tokens


class SC_500:
    """Wayward Probe"""

    # Battlecry and Deathrattle: Get a random Starship Piece.
    play = _GiveRandomStarshipPiece(SELF)
    deathrattle = _GiveRandomStarshipPiece(SELF)


##
# Starship assembly token


class SC_999t(_StarshipToken):
    """Battlecruiser"""


##
# Hero powers


class SC_004hp:
    """Ravage"""

    # Deal 3 damage randomly split among all enemies. (Improved by Zerg
    # minions you control!)
    activate = _RavageSplit(CONTROLLER)


class SC_400p:
    """Stimpack"""

    # Summon a 2/2 Marine with Taunt. Give your Terran minions +2 Attack.
    # SC_400e ('Stimpack Boost') carries no ATK tag in this build — supply +2
    # via the buff kwarg.
    activate = (
        Summon(CONTROLLER, "SC_403t"),
        Buff(FRIENDLY_MINIONS + TERRAN, "SC_400e", atk=2),
    )


class SC_754p:
    """Twin Blades"""

    # Give a friendly minion and your hero +1 Attack this turn and Divine
    # Shield.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    # SC_754e ('Twin Blades') carries no ATK tag in this build — supply +1 via
    # the buff kwarg. The enchant is "+1 Attack this turn" (ONE_TURN_EFFECT in
    # data), so it expires at end of turn.
    activate = (
        Buff(TARGET, "SC_754e", atk=1),
        SetTags(TARGET, {GameTag.DIVINE_SHIELD: True}),
        Buff(FRIENDLY_HERO, "SC_754e", atk=1),
        SetTags(FRIENDLY_HERO, {GameTag.DIVINE_SHIELD: True}),
    )
