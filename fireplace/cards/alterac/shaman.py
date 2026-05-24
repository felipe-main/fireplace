from ..utils import *


##
# Minions


class AV_251:
    """Cheaty Snobold"""

    # After an enemy is <b>Frozen</b>, deal 3 damage to it.
    events = SetTags(ENEMY_CHARACTERS, (GameTag.FROZEN,)).after(
        Hit(SetTags.TARGET, 3)
    )


class AV_255:
    """Snowfall Guardian"""

    # <b>Battlecry:</b> <b>Freeze</b> all other minions. Gain +1/+1 for each
    # <b>Frozen</b> minion.
    play = (
        Freeze(ALL_MINIONS - SELF),
        Buff(SELF, "AV_255e") * Count(ALL_MINIONS + FROZEN),
    )


AV_255e = buff(atk=1, health=1)


class AV_257:
    """Bearon Gla'shear"""

    # [x]<b>Battlecry:</b> For each Frost spell you've cast this game, summon
    # a 3/4 Elemental that <b>Freezes</b>.
    # AV_257t Frozen Stagguard is the shared 3/4 freeze-on-damage token.
    play = Summon(CONTROLLER, "AV_257t") * Count(
        CARDS_PLAYED_THIS_GAME + SPELL + FROST_SPELL
    )


class AV_260:
    """Sleetbreaker"""

    # <b>Battlecry:</b> Add a Windchill to your hand.
    play = Give(CONTROLLER, "AV_266")


##
# Spells


class AV_107:
    """Glaciate"""

    # <b>Discover</b> an 8-Cost minion. Summon and <b>Freeze</b> it.
    play = DISCOVER(RandomCollectible(cost=8, type=CardType.MINION)).then(
        Summon(CONTROLLER, Discover.CARD).then(Freeze(Summon.CARD))
    )


class AV_250:
    """Snowball Fight!"""

    # Deal $1 damage to a minion and <b>Freeze</b> it. If it survives,
    # repeat this on another minion! Cascades while the current target
    # survives; each repeat picks a fresh random minion we haven't hit yet.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}

    def play(self):
        target = self.target
        already_hit = set()
        for _ in range(14):  # safety bound — board can have at most 14 minions
            if target is None or target in already_hit:
                return
            already_hit.add(target)
            yield Hit(target, 1)
            yield Freeze(target)
            if target.dead:
                return
            candidates = [
                m for m in ALL_MINIONS.eval(self.game.entities, self)
                if m not in already_hit
            ]
            if not candidates:
                return
            target = self.game.random.choice(candidates)


class AV_259:
    """Frostbite"""

    # Deal $3 damage. <b>Honorable Kill:</b> Your opponent's next spell costs
    # (2) more.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 3)
    # "Opponent's next spell costs +2" approximation: buff all opponent
    # spells in hand by +2 cost.
    honorable_kill = Buff(ENEMY_HAND + SPELL, "AV_259e")


class AV_259e:
    tags = {GameTag.COST: 2}


class AV_266:
    """Windchill"""

    # <b>Freeze</b> a minion. Draw a card.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Freeze(TARGET), Draw(CONTROLLER)


class AV_268:
    """Wildpaw Cavern"""

    # [x]At the end of your turn, summon a 3/4 Elemental that <b>Freezes</b>.
    # Lasts 3 turns.
    # AV_257t Frozen Stagguard is the shared 3/4 freeze-on-damage token.
    events = OWN_TURN_END.on(Summon(CONTROLLER, "AV_257t"))


##
# Heros


class AV_258:
    """Bru'kan of the Elements"""

    # [x]<b>Battlecry:</b> Call upon the power of two Elements!
    # The four Element spells (Blizzard's tokens):
    #   AV_258t  — Earth: summon two 2/3 Taunt elementals (AV_258t6)
    #   AV_258t2 — Water: restore 6 health to all friendly characters
    #   AV_258t3 — Fire: deal 6 damage to enemy hero
    #   AV_258t4 — Lightning: deal 2 damage to all enemy minions
    def play(self):
        elements = ["AV_258t", "AV_258t2", "AV_258t3", "AV_258t4"]
        picks = self.game.random.sample(elements, 2)
        for spell_id in picks:
            yield CastSpell(spell_id)


class AV_258t:
    """Earth Invocation"""

    # Summon two 2/3 Elementals with Taunt.
    play = Summon(CONTROLLER, "AV_258t6") * 2


class AV_258t2:
    """Water Invocation"""

    # Restore #6 Health to all friendly characters.
    play = Heal(FRIENDLY_CHARACTERS, 6)


class AV_258t3:
    """Fire Invocation"""

    # Deal 6 damage to the enemy hero.
    play = Hit(ENEMY_HERO, 6)


class AV_258t4:
    """Lightning Invocation"""

    # Deal 2 damage to all enemy minions.
    play = Hit(ENEMY_MINIONS, 2)
