from ..utils import *

from ..delve_into_deepholm._bonus import roll_bonus_effects


##
# Custom actions


class _CanvasaurBonus(TargetedAction):
    """Painted Canvasaur battlecry. Gives EACH OTHER friendly Beast an
    independently-rolled random bonus effect from the keyword-only pool
    (Taunt, Windfury, Divine Shield, Poisonous, Elusive, Rush, Lifesteal,
    Reborn) — no stat change. SetTags per minion so each rolls
    independently. Excludes the Canvasaur itself ("each OTHER")."""

    TARGET = ActionArg()

    def do(self, source, target):
        for minion in list(source.controller.field):
            if minion is source:
                continue
            if minion.race != Race.BEAST and Race.BEAST not in getattr(
                minion, "races", []
            ):
                continue
            tags = roll_bonus_effects(source.game.random, 1)
            source.game.cheat_action(source, [SetTags(minion, tags)])


class _HemetLegendaryBeast(TargetedAction):
    """Hemet, Foam Marksman trigger. After a friendly Beast dies, add a
    random Legendary Beast "from the past" (a Wild-rotated collectible
    Legendary Beast) to the controller's hand, costing (2) less. The
    Standard set list is read from `is_standard` on the data card so the
    pool tracks future-patch rotations automatically."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db

        pool = [
            cid
            for cid, c in _db.items()
            if c.collectible
            and c.type == CardType.MINION
            and Race.BEAST in getattr(c, "races", [])
            and c.rarity == Rarity.LEGENDARY
            and not getattr(c, "is_standard", False)
        ]
        if not pool:
            # Fallback: any collectible Legendary Beast (avoids a no-op if
            # the data parser doesn't carry is_standard on this patch).
            pool = [
                cid
                for cid, c in _db.items()
                if c.collectible
                and c.type == CardType.MINION
                and Race.BEAST in getattr(c, "races", [])
                and c.rarity == Rarity.LEGENDARY
            ]
        if not pool:
            return
        cid = source.game.random.choice(pool)
        source.game.cheat_action(
            source,
            [Give(source.controller, cid).then(Buff(Give.CARD, "TOY_355e2"))],
        )


class _RCRampage(TargetedAction):
    """R.C. Rampage. Summon six 1/1 Hounds (R.C. Hound). For each that
    can't fit (board already full), give one of the summoned Hounds
    +1/+1 instead."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        total = 6
        slots = max(0, 7 - len(ctrl.field))
        summon_count = min(total, slots)
        overflow = total - summon_count
        summoned = []
        for _ in range(summon_count):
            source.game.cheat_action(source, [Summon(ctrl, "TOY_358t")])
            hounds = [m for m in ctrl.field if m.id == "TOY_358t"]
            if hounds:
                summoned.append(hounds[-1])
        if summoned:
            for i in range(overflow):
                source.game.cheat_action(
                    source,
                    [Buff(summoned[i % len(summoned)], "TOY_354e", atk=1, max_health=1)],
                )


class _KingPlushReturn(TargetedAction):
    """King Plush battlecry. Return all minions (friend and foe) with less
    Attack than King Plush to their owner's decks. Implemented imperatively
    because no primitive moves minions from PLAY to DECK for both owners."""

    TARGET = ActionArg()

    def do(self, source, target):
        threshold = source.atk
        victims = []
        for player in source.game.players:
            for minion in list(player.field):
                if minion is source:
                    continue
                if minion.atk < threshold:
                    victims.append(minion)
        for minion in victims:
            owner = minion.controller
            if len(owner.deck) >= owner.max_deck_size:
                source.game.cheat_action(source, [Destroy(minion)])
                continue
            minion.zone = Zone.DECK
            minion._summon_index = owner.game.random.randint(0, len(owner.deck))


##
# Minions


class TOY_350:
    """Painted Canvasaur"""

    # <b>Battlecry:</b> Give each other friendly Beast a random
    # <b>bonus effect</b>.
    play = _CanvasaurBonus(SELF)


class TOY_351:
    """Mystery Egg"""

    # <b>Miniaturize</b> <b>Deathrattle:</b> Get a copy of a random Beast in
    # your deck. It costs (5) less.
    deathrattle = Give(
        CONTROLLER, Copy(RANDOM(FRIENDLY_DECK + BEAST + MINION))
    ).then(Buff(Give.CARD, "TOY_351e1"))


class TOY_351t:
    """Mystery Egg"""

    # <b>Mini</b> <b>Deathrattle:</b> Get a copy of a random Beast in your
    # deck. It costs (5) less.
    deathrattle = Give(
        CONTROLLER, Copy(RANDOM(FRIENDLY_DECK + BEAST + MINION))
    ).then(Buff(Give.CARD, "TOY_351e1"))


class TOY_355:
    """Hemet, Foam Marksman"""

    # After a friendly Beast dies, get a random <b>Legendary</b> Beast from
    # the past. It costs (2) less.
    events = Death(FRIENDLY + BEAST + MINION).after(_HemetLegendaryBeast(SELF))


class TOY_356:
    """Toyrannosaurus"""

    # <b>Rush</b> <b>Deathrattle:</b> Deal 5 damage to a random enemy.
    # Rush lives in data.
    deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 5)


class TOY_357:
    """King Plush"""

    # <b>Charge</b> <b>Battlecry:</b> Return all minions with less Attack
    # than this to their owner's decks.
    # Charge lives in data.
    play = _KingPlushReturn(SELF)


##
# Spells


class TOY_352:
    """Fetch!"""

    # Draw a minion. If it's a Beast, draw a spell.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION)).then(
        Find(Draw.CARD + BEAST) & Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL))
    )


class TOY_353:
    """Patchwork Pals"""

    # Get all 3 Animal Companions. They cost (1) less.
    play = (
        Give(CONTROLLER, "NEW1_032").then(Buff(Give.CARD, "TOY_353e")),
        Give(CONTROLLER, "NEW1_033").then(Buff(Give.CARD, "TOY_353e")),
        Give(CONTROLLER, "NEW1_034").then(Buff(Give.CARD, "TOY_353e")),
    )


class TOY_354:
    """R.C. Rampage"""

    # Summon six 1/1 Hounds. Any that can't fit give the others +1/+1.
    play = _RCRampage(CONTROLLER)


class TOY_359:
    """Jungle Gym"""

    # Deal 1 damage to a random enemy. Repeat for each friendly Beast.
    # Location: the effect fires on USE (activate), never on play. One base
    # hit plus one per friendly Beast ON THE BATTLEFIELD (in-play only).
    activate = Hit(RANDOM_ENEMY_CHARACTER, 1) * (
        Count(FRIENDLY + BEAST + MINION + IN_PLAY) + 1
    )


##
# Weapons


class TOY_358:
    """Remote Control"""

    # After your hero attacks, summon a 1/1 Hound.
    events = Attack(FRIENDLY_HERO).after(Summon(CONTROLLER, "TOY_358t"))


##
# Tokens


class TOY_358t:
    """R.C. Hound"""

    # 1/1 Mechanical/Beast vanilla token. Stats + races live in data.


##
# Enchantments (exist in data; declare the COST tag the data card omits)


class TOY_351e1:
    # Hatched! — the copied Beast costs (5) less.
    tags = {GameTag.COST: -5}


class TOY_353e:
    # Patchwork — the Animal Companion costs (1) less.
    tags = {GameTag.COST: -1}


class TOY_354e:
    # CHARGE! — R.C. Rampage overflow buff (+1/+1).
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TOY_355e2:
    # Foam Fury — the Legendary Beast costs (2) less.
    tags = {GameTag.COST: -2}


##
# Whizbang's Workshop mini-set


class MIS_104:
    """Wilderness Pack"""

    # Add 5 random Beasts to your hand. They are Temporary.
    play = (
        Give(CONTROLLER, RandomBeast()).then(GiveTemporary(Give.CARD))
    ) * 5


class _BargainBinDraw(TargetedAction):
    """After the opponent plays a minion/spell/weapon, draw a card of one of
    the other two types from your deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        kinds = {CardType.MINION, CardType.SPELL, CardType.WEAPON}
        if target.type not in kinds:
            return
        wanted = kinds - {target.type}
        pool = [c for c in ctrl.deck if c.type in wanted]
        if pool:
            source.game.cheat_action(
                source, [ForceDraw(source.game.random.choice(pool))]
            )


class MIS_105:
    """Bargain Bin"""

    # Secret: After your opponent plays a minion, spell, or weapon, draw a
    # card of the other 2 types.
    secret = Play(OPPONENT, MINION | SPELL | WEAPON).after(
        Reveal(SELF), _BargainBinDraw(Play.CARD)
    )


class _Product9Recast(TargetedAction):
    """Recast every friendly Secret that triggered this game (re-arms them)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for cid in list(ctrl.secrets_triggered_cards_this_game):
            source.game.cheat_action(source, [CastSpell(cid)])


class MIS_914:
    """Product 9"""

    # Battlecry: Recast every friendly Secret that triggered this game.
    play = _Product9Recast(SELF)
