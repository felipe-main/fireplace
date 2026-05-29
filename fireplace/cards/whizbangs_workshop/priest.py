from ..utils import *


##
# Custom actions


class _ZarimiBumpDragons(TargetedAction):
    """Timewinder Zarimi — bump the per-card `_dragons_summoned` counter each
    time the controller summons a Dragon while Zarimi is in hand or deck.
    Zarimi's battlecry reads this to check the 'summoned 5 other Dragons'
    threshold (mirrors Fye, the Setting Sun)."""

    TARGET = ActionArg()

    def do(self, source, target):
        source._dragons_summoned = getattr(source, "_dragons_summoned", 0) + 1


class _ChalkArtistTransform(TargetedAction):
    """Chalk Artist — transform the just-drawn minion into a random Legendary
    minion, keeping its original Attack, Health and Cost (re-applied via the
    TOY_388e2 enchant, mirroring Lady Prestor)."""

    TARGET = ActionArg()

    def do(self, source, target):
        cost = target.cost
        atk = target.atk
        health = target.health
        new_id = RandomLegendaryMinion().evaluate(source)
        if not new_id:
            return
        if isinstance(new_id, (list, tuple)):
            if not new_id:
                return
            new_id = new_id[0]
        morphed = source.controller.card(new_id, source=source)
        source.game.cheat_action(
            source,
            [Morph(target, morphed).then(
                _ChalkApplyStats(Morph.TARGET, cost, atk, health)
            )],
        )


class _ChalkApplyStats(TargetedAction):
    """Stamp the captured original Attack/Health/Cost onto the morphed card via
    the TOY_388e2 'Adjusted stats' enchant."""

    TARGET = ActionArg()
    COST = IntArg()
    ATK = IntArg()
    HEALTH = IntArg()

    def do(self, source, target, cost, atk, health):
        buff = source.controller.card("TOY_388e2", source=source)
        buff.source = source
        buff._xcost = cost
        buff._xatk = atk
        buff._xhealth = health
        buff.apply(target)


class _RepackageStuff(TargetedAction):
    """Repackage — move every minion on the board to SETASIDE (preserving full
    state), stash them on a freshly created 2-Cost Repackaged Box, and shuffle
    that Box into the opponent's deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        minions = list(target)
        box = source.controller.opponent.card("TOY_879t", source=source)
        box._packaged = minions
        for m in minions:
            m.zone = Zone.SETASIDE
        source.game.cheat_action(
            source, [Shuffle(source.controller.opponent, box)]
        )


class _RepackageOpen(TargetedAction):
    """Repackaged Box — add the stashed minions to the box owner's hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        packaged = getattr(target, "_packaged", None) or []
        for m in packaged:
            if m.zone != Zone.SETASIDE:
                continue
            m.controller = target.controller
            if len(target.controller.hand) >= target.controller.max_hand_size:
                m.zone = Zone.GRAVEYARD
                continue
            m.zone = Zone.HAND
        target._packaged = []


##
# Minions


class TOY_380:
    """Clay Matriarch"""

    # Miniaturize. Taunt. Deathrattle: Summon a 4/4 Whelp with Elusive.
    # (Taunt + Miniaturize are in data; engine adds the Mini token on play.)
    deathrattle = Summon(CONTROLLER, "TOY_380t2")


class TOY_380t:
    """Clay Matriarch"""

    # Mini. Taunt. Deathrattle: Summon a 4/4 Whelp with Elusive.
    deathrattle = Summon(CONTROLLER, "TOY_380t2")


class TOY_380t2:
    """Clay Whelp"""

    # Elusive — can't be targeted by spells or Hero Powers. (ELUSIVE tag is
    # in data but the engine reads the underlying targetability tags, so set
    # them explicitly to guarantee the keyword works.)
    tags = {
        GameTag.CANT_BE_TARGETED_BY_ABILITIES: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }


class TOY_381:
    """Papercraft Angel"""

    # Your Hero Power costs (0). (Ongoing aura while in play.)
    update = Refresh(FRIENDLY_HERO_POWER, {GameTag.COST: SET(0)})


class TOY_382:
    """Careless Crafter"""

    # Deathrattle: Get two 0-Cost Bandages that restore 3 Health.
    deathrattle = Give(CONTROLLER, "TOY_382t") * 2


class TOY_382t:
    """Bandage"""

    # Restore #3 Health.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Heal(TARGET, 3)


class TOY_383:
    """Raza the Resealed"""

    # Battlecry: For the rest of the game, your Hero Power refreshes whenever
    # you play a card.
    play = Buff(CONTROLLER, "TOY_383e")


class TOY_383e:
    # Persistent listener stamped on the controller: refresh the Hero Power
    # after every card the controller plays.
    events = OWN_CARD_PLAY.after(RefreshHeroPower(FRIENDLY_HERO_POWER))


class TOY_385:
    """Timewinder Zarimi"""

    # Battlecry: Once per game, if you've summoned 5 other Dragons, take an
    # extra turn. Dragon-summon count is tracked per-card via the Deck/Hand
    # listeners below (mirrors Fye, the Setting Sun) so it reflects only
    # *other* Dragons summoned before Zarimi resolves.
    def play(self):
        if getattr(self.controller, "_zarimi_used", False):
            return
        if getattr(self, "_dragons_summoned", 0) >= 5:
            self.controller._zarimi_used = True
            self.game.next_players.append(self.controller)

    class Deck:
        events = Summon(CONTROLLER, DRAGON).after(_ZarimiBumpDragons(SELF))

    class Hand:
        events = Summon(CONTROLLER, DRAGON).after(_ZarimiBumpDragons(SELF))


class TOY_388:
    """Chalk Artist"""

    # Battlecry: Draw a minion. Transform it into a random Legendary one
    # (keeping its original stats and Cost).
    play = ForceDraw(FRIENDLY_DECK + MINION).then(_ChalkArtistTransform(ForceDraw.TARGET))


class TOY_388e2:
    # "Covered in Chalk" — re-applies the original minion's Attack, Health and
    # Cost after the Legendary transform (Lady Prestor pattern).
    events = REMOVED_IN_PLAY
    atk = lambda self, _: self._xatk
    max_health = lambda self, _: self._xhealth
    cost = lambda self, _: self._xcost


##
# Spells


class TOY_384:
    """Purifying Power"""

    # Silence all friendly minions, then give them +1/+2.
    play = Silence(FRIENDLY_MINIONS), Buff(FRIENDLY_MINIONS, "TOY_384e")


TOY_384e = buff(+1, +2)


class TOY_387:
    """Scale Replica"""

    # Draw your lowest and highest Cost Dragon.
    play = (
        ForceDraw(LOWEST_COST(FRIENDLY_DECK + MINION + DRAGON)),
        ForceDraw(HIGHEST_COST(FRIENDLY_DECK + MINION + DRAGON)),
    )


class TOY_714:
    """Fly Off the Shelves"""

    # Deal $1 damage to all enemy minions. Repeat for each Dragon you're
    # holding. Total hits = 1 + (Dragons in hand).
    play = Hit(ENEMY_MINIONS, 1) * (Count(FRIENDLY_HAND + DRAGON) + 1)


class TOY_879:
    """Repackage"""

    # Stuff all minions into a 2-Cost Box, then shuffle it into the
    # opponent's deck.
    play = _RepackageStuff(ALL_MINIONS)


class TOY_879t:
    """Repackaged Box"""

    # Add the resealed minions to your hand.
    play = _RepackageOpen(SELF)
