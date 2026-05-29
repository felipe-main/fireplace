from ..utils import *


##
# Custom actions


class _WatercolorDraw(TargetedAction):
    """Watercolor Artist battlecry — draw a Frost spell from the deck and
    attach the per-turn cost-reduction driver enchant (TOY_376e1, "Drying").
    The driver lives on the drawn card itself (via its Hand listener), so
    the Cost keeps dropping each turn even if the artist later dies."""

    TARGET = ActionArg()

    def do(self, source, target):
        pool = (FRIENDLY_DECK + SPELL + FROST).eval(source.game, source)
        if not pool:
            return
        card = source.game.random.choice(pool)
        source.game.cheat_action(
            source, [ForceDraw(card).then(Buff(ForceDraw.TARGET, "TOY_376e1"))]
        )


class _GalacticOrbRecast(TargetedAction):
    """The Galactic Projection Orb — for each distinct Cost among the spells
    you've cast this game, recast one random spell of that Cost (targets
    enemies if possible)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = target
        by_cost = {}
        for c in list(ctrl.cards_played_this_game):
            if c.type != CardType.SPELL:
                continue
            by_cost.setdefault(c.cost or 0, []).append(c.id)
        for cost in sorted(by_cost):
            picked = source.game.random.choice(by_cost[cost])
            source.game.cheat_action(
                source, [CastSpellTargetsEnemiesIfPossible(picked)]
            )


##
# Spells


class TOY_037:
    """Hidden Objects"""

    # <b>Discover</b> a <b>Secret</b>. Set its Cost to (1).
    play = Discover(CONTROLLER, RandomSpell(secret=True)).then(
        Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "TOY_037e"))
    )


class TOY_037e:
    # "Found it!" — set the discovered Secret's Cost to exactly (1).
    cost = SET(1)


class TOY_371:
    """Manufacturing Error"""

    # Draw 3 cards. If your deck has no minions, they cost (3) less.
    play = Draw(CONTROLLER).then(
        (-Find(FRIENDLY_DECK + MINION)) & Buff(Draw.CARD, "TOY_371e")
    ) * 3


class TOY_371e:
    # Drawn card costs (3) less.
    tags = {GameTag.COST: -3}
    events = REMOVED_IN_PLAY


class TOY_372:
    """Yogg in the Box"""

    # Cast 5 random spells. If your deck has no minions, the spells cast
    # cost (5) or more.
    def play(self):
        no_minions = not (FRIENDLY_DECK + MINION).eval(self.game, self)
        for _ in range(5):
            if no_minions:
                yield CastSpell(RandomSpell(cost=range(5, 11)))
            else:
                yield CastSpell(RandomSpell())


class TOY_374:
    """Spot the Difference"""

    # <b>Discover</b> a 3-Cost minion to summon. If your deck has no
    # minions, repeat this.
    # The second Discover is nested inside the first's .then() callback —
    # flat tuples of Discovers all set player.choice at once and only the
    # last survives, so the repeat must be sequenced (gated on the deck
    # still having no minions at that point).
    play = Discover(CONTROLLER, RandomMinion(cost=3)).then(
        Summon(CONTROLLER, Discover.CARD).then(
            (-Find(FRIENDLY_DECK + MINION))
            & Discover(CONTROLLER, RandomMinion(cost=3)).then(
                Summon(CONTROLLER, Discover.CARD)
            )
        )
    )


class TOY_377:
    """Frost Lich Cross-Stitch"""

    # Deal $4 damage to a character. If it dies, summon a 3/6 Water
    # Elemental that <b>Freeze</b>s.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 4).then(
        Dead(TARGET) & Summon(CONTROLLER, "ICC_833t")
    )


class TOY_378:
    """The Galactic Projection Orb"""

    # Recast a random spell of each Cost you've cast this game <i>(targets
    # enemies if possible)</i>.
    play = _GalacticOrbRecast(CONTROLLER)


##
# Minions


class TOY_370:
    """Triplewick Trickster"""

    # <b>Battlecry:</b> Deal 2 damage to a random enemy, three times.
    play = Hit(RANDOM(ENEMY_CHARACTERS), 2) * 3


class TOY_373:
    """Puzzlemaster Khadgar"""

    # <b>Battlecry:</b> Equip a 0/6 Wisdomball that casts helpful Mage
    # spells!
    play = Summon(CONTROLLER, "TOY_373t")


class TOY_373t:
    """Magic Wisdomball"""

    # At the end of your turn, cast a helpful Mage spell. Lose 1 Durability.
    events = OWN_TURN_END.on(
        CastSpellTargetsSelfIfPossible(RandomSpell(card_class=CardClass.MAGE)),
        Hit(SELF, 1),
    )


class TOY_376:
    """Watercolor Artist"""

    # <b>Battlecry:</b> Draw a Frost spell. At the start of your turns,
    # reduce its Cost by (1).
    play = _WatercolorDraw(CONTROLLER)


class TOY_376e1:
    # "Drying" — per-turn driver attached to the drawn Frost spell. While
    # the card sits in hand, each of the owner's turn-begins stacks another
    # copy of the (-1) cost enchant.
    class Hand:
        events = OWN_TURN_BEGIN.on(Buff(OWNER, "TOY_376e"))


class TOY_376e:
    # "Washed Out" — stacking (-1) cost reduction on the drawn Frost spell.
    tags = {GameTag.COST: -1}


##
# Miniaturize tokens


class TOY_375:
    """Sleet Skater"""

    # <b>Miniaturize</b> <b>Battlecry:</b> <b>Freeze</b> an enemy minion.
    # Gain Armor equal to its Attack.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = GainArmor(FRIENDLY_HERO, ATK(TARGET)), Freeze(TARGET)


class TOY_375t:
    """Sleet Skater"""

    # <b>Mini</b> <b>Battlecry:</b> <b>Freeze</b> an enemy minion. Gain
    # Armor equal to its Attack.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = GainArmor(FRIENDLY_HERO, ATK(TARGET)), Freeze(TARGET)
