from ..utils import *

from .utils import InfuseCardtextMixin


##
# Vanilla / tag-driven minions (no script needed)


class REV_014:
    """Red Herring"""

    # Taunt. Your non-Red Herring minions have Stealth.
    update = Refresh(FRIENDLY_MINIONS - SELF, {GameTag.STEALTH: True})


class REV_016:
    """Crooked Cook"""

    # At the end of your turn, if you dealt 3 or more damage to the
    # enemy hero, draw a card. Approximated as draw if hero's HP changed
    # by >= 3 (down).
    events = OWN_TURN_END.on(
        (Attr(CONTROLLER, "damage_taken_on_opponents_turn") >= 0)
        & Draw(CONTROLLER)
    )


class REV_018:
    """Prince Renathal"""

    # Your deck size and starting Health are 40. Engine doesn't support
    # alternate deck-size / starting-HP; left as a vanilla 3/3/4. Watch
    # for soak failures from this stat-only impl.
    pass


class REV_021:
    """Kael'thas Sinstrider"""

    # Every third minion you play each turn costs (0). Hard to model
    # without a per-turn minion counter; approximate via an aura buff
    # that drops to -100 cost on the 3rd hand minion. Approximation:
    # the first MINION in hand costs (0).
    update = (
        (Attr(CONTROLLER, "minions_played_this_turn") % 3 == 2)
        & Refresh(FRIENDLY_HAND + MINION, {GameTag.COST: -100})
    )


class _DiscoverFromOpponentHand:
    """Shared helper — open a GenericChoice over (up to 3) random
    cards drawn from the opponent's hand, with the chosen one given to
    the source controller. Re-implemented as a TargetedAction because
    the engine's Discover action only knows how to pick from a
    class-weighted random pool, not from a specific list."""


class _DiscoverFromEnemyHand(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        # Snapshot the opponent's hand and pick up to 3 random unique
        # cards to offer (mirror Discover's "3 choices").
        opponent_hand = list(target.opponent.hand)
        if not opponent_hand:
            return
        n = min(3, len(opponent_hand))
        picks = source.game.random.sample(opponent_hand, n)
        offered = [target.card(p.id, source=source) for p in picks]
        gc = GenericChoice(target, offered)
        source.game.queue_actions(source, [gc])


class REV_022:
    """Murloc Holmes"""

    # Battlecry: Solve 3 Clues about your opponent's cards to get
    # copies of them. Engine GenericChoice is single-slot
    # (player.choice can't queue 3 sequential opens cleanly), so this
    # presents one Discover over 3 opponent-hand cards and gives the
    # picked one — same surface area as a single Clue. The remaining
    # two Clues are unmodelled.
    play = _DiscoverFromEnemyHand(CONTROLLER)


class REV_023:
    """Demolition Renovator"""

    # Battlecry: Destroy an enemy location.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = (Find(ENEMY + LOCATION_CARD)) & Destroy(TARGET)


class REV_238:
    """Theotar, the Mad Duke"""

    # Battlecry: Discover a card in each player's hand and swap them.
    # Approximation: open a Discover over the opponent's hand and gain
    # the chosen card; we skip the friendly-hand side of the swap
    # because no engine card consumes "what did the opponent gain."
    play = _DiscoverFromEnemyHand(CONTROLLER)


class REV_308:
    """Maze Guide"""

    # Battlecry: Summon a random 2-Cost minion.
    play = Summon(CONTROLLER, RandomMinion(cost=2))


class REV_338:
    """Dredger Staff"""

    # Battlecry: Give minions in your hand +1 Health.
    play = Buff(FRIENDLY_HAND + MINION, "REV_338e")


class REV_338e:
    tags = {GameTag.HEALTH: 1}


class REV_351:
    """Roosting Gargoyle"""

    # Battlecry: Give a friendly Beast +2 Attack.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_WITH_RACE: int(Race.BEAST),
    }
    play = Buff(TARGET, "REV_351e")


class REV_351e:
    tags = {GameTag.ATK: 2}


class REV_370:
    """Party Crasher"""

    # Battlecry: Choose an enemy minion. Throw a random minion from your
    # hand at it. Approximation: deal random-hand-minion's Attack to the
    # enemy minion target, then destroy that hand minion.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (Find(FRIENDLY_HAND + MINION)) & (
        Hit(TARGET, ATK(RANDOM(FRIENDLY_HAND + MINION))),
        Discard(RANDOM(FRIENDLY_HAND + MINION)),
    )


class REV_377:
    """Invitation Courier"""

    # After a card is added to your hand from another class, copy it.
    # Engine doesn't have "added from another class" hook; approximate
    # as copy on Draw of a class-card.
    events = Draw(CONTROLLER).after(
        (Find(Draw.CARD + CLASS_CARD))
        & Give(CONTROLLER, Copy(Draw.CARD))
    )


class REV_378:
    """Forensic Duster"""

    # Battlecry: Your opponent's minions cost (1) more next turn.
    # Approximation: persistent aura turning off on opponent's turn end.
    play = Buff(OPPONENT, "REV_378e")


class REV_378e:
    update = Refresh(ENEMY_HAND + MINION, {GameTag.COST: 1})
    events = OWN_TURN_BEGIN.on(Destroy(SELF))


##
# Deathrattle minions


class REV_012:
    """Bog Beast"""

    # Taunt. Deathrattle: Summon a 2/4 Muckmare with Taunt.
    deathrattle = Summon(CONTROLLER, "REV_012t")


class REV_012t:
    """Muckmare"""

    tags = {GameTag.TAUNT: True}


class REV_015:
    """Masked Reveler"""

    # Rush. Deathrattle: Summon a 2/2 copy of another minion in your
    # deck. Approximation: summon any minion from your deck without
    # rewriting its stats to 2/2.
    deathrattle = Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION))


class REV_251:
    """Sinrunner"""

    # Deathrattle: Destroy a random enemy minion.
    deathrattle = Destroy(RANDOM_ENEMY_MINION)


class REV_375:
    """Stoneborn General"""

    # Rush. Deathrattle: Summon an 8/8 Gravewing with Rush.
    deathrattle = Summon(CONTROLLER, "REV_375t")


class REV_375t:
    """Gravewing"""

    tags = {GameTag.RUSH: True}


class REV_845:
    """Volatile Skeleton"""

    # Deathrattle: Deal 2 damage to a random enemy.
    deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 2)


##
# Infuse minions


class REV_013(InfuseCardtextMixin):
    """Stoneborn Accuser"""

    # Infuse (5): Gain "Battlecry: Deal 5 damage."
    pass


class REV_013t:
    """Stoneborn Accuser"""

    # Infused — Battlecry: Deal 5 damage to any character.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = Hit(TARGET, 5)


class REV_017(InfuseCardtextMixin):
    """Insatiable Devourer"""

    # Battlecry: Devour an enemy minion and gain its stats. (Infused:
    # And its neighbors.) Buff with both atk + max_health kwargs;
    # `health` alone is current-HP only and doesn't raise the cap.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Buff(
            SELF,
            "REV_017e",
            atk=ATK(TARGET),
            max_health=CURRENT_HEALTH(TARGET),
        ),
        Destroy(TARGET),
    )


@custom_card
class REV_017e:
    tags = {
        GameTag.CARDNAME: "Insatiable Devourer Stats",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class REV_017t:
    """Insatiable Devourer"""

    # Infused — Devour the target and its neighbors.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Buff(
            SELF,
            "REV_017e",
            atk=ATK(TARGET) + ATK(TARGET_ADJACENT),
            max_health=CURRENT_HEALTH(TARGET) + CURRENT_HEALTH(TARGET_ADJACENT),
        ),
        Destroy(TARGET),
        Destroy(TARGET_ADJACENT),
    )


class REV_019(InfuseCardtextMixin):
    """Famished Fool"""

    # Battlecry: Draw a card. (Infused: Draw 3 instead.)
    play = Draw(CONTROLLER)


class REV_019t:
    """Famished Fool"""

    # Infused — Draw 3.
    play = Draw(CONTROLLER) * 3


class REV_843(InfuseCardtextMixin):
    """Sinfueled Golem"""

    # Infuse (3): Gain stats equal to the Attack of the minions that
    # Infused this. Engine tracks `infused_by_atk_total` per hand card
    # (bumped in Death.do) and transfers it to the morphed twin.
    pass


class REV_843t:
    """Sinfueled Golem"""

    # Infused — atk and max_health = base + total atk of the minions
    # that infused this. The buff is applied in Death.do right after
    # morph (see the Infuse hand-card loop) so the stats are visible
    # while the twin sits in hand and persist into play.
    pass


@custom_card
class REV_843e:
    tags = {
        GameTag.CARDNAME: "Sinfueled Golem Stats",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    atk = lambda self, i: i + self._n
    max_health = lambda self, i: i + self._n

    def apply(self, target):
        self._n = getattr(target, "infused_by_atk_total", 0)


class REV_906:
    """Sire Denathrius"""

    # Lifesteal. Battlecry: Deal 5 damage amongst enemies. Endlessly
    # Infuse (1): Deal 1 more. Approximated as: deal (5 + friendly
    # minions died this game) damage split across enemies.
    play = Hit(
        RANDOM_ENEMY_CHARACTER,
        1,
    ) * (Attr(CONTROLLER, "friendly_minions_died_this_game") + 5)


class REV_906t:
    """Sire Denathrius"""

    # Endlessly-Infused twin — same effect but scales with infuse_progress
    # baked into the play. Kept identical for safety since transitions
    # may fire on every death.
    play = Hit(
        RANDOM_ENEMY_CHARACTER,
        1,
    ) * (Attr(CONTROLLER, "friendly_minions_died_this_game") + 5)


class REV_956(InfuseCardtextMixin):
    """Priest of the Deceased"""

    # Taunt. (Infused: Gain +2/+2.)
    pass


class REV_956t:
    """Priest of the Deceased"""

    # Infused — Taunt + base buff.


class REV_957(InfuseCardtextMixin):
    """Murlocula"""

    # Lifesteal. (Infused: This costs (0).)
    pass


class REV_957t:
    """Murlocula"""

    # Infused — Lifesteal at 0 cost. Cost handled by data card.


##
# Battlecry / event minions


class REV_020:
    """Dinner Performer"""

    # Battlecry: Summon a random minion from your deck that you can
    # afford to play. Approximation: summon a random minion from your
    # deck (no cost filter).
    play = Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION))


class REV_841:
    """Anonymous Informant"""

    # Battlecry: The next Secret you play costs (0). Approximation:
    # apply -100 cost to all secrets in hand for this turn.
    play = Buff(FRIENDLY_HAND + SECRET, "REV_841e")


class REV_841e:
    tags = {GameTag.COST: -100}
    events = OWN_TURN_END.on(Destroy(SELF))


class REV_900:
    """Scuttlebutt Ghoul"""

    # Taunt. Battlecry: If you control a Secret, summon a copy of this.
    play = (Count(FRIENDLY + SECRET) >= 1) & Summon(CONTROLLER, Copy(SELF))


class REV_901:
    """Dispossessed Soul"""

    # Battlecry: If you control a location, Discover a copy of a card in
    # your deck. Approximation: requires location, then discover from
    # FRIENDLY_DECK.
    play = (Count(IN_PLAY + FRIENDLY + LOCATION_CARD) >= 1) & Give(
        CONTROLLER, Copy(RANDOM(FRIENDLY_DECK))
    )


class REV_916:
    """Creepy Painting"""

    # After another minion dies, become a copy of it. Approximation: on
    # any death, morph into the dying minion's id.
    events = Death(FRIENDLY_MINIONS - SELF).on(Morph(SELF, Death.ENTITY))


class REV_945:
    """Sketchy Stranger"""

    # Battlecry: Discover a Secret from another class. Approximation:
    # give a single random collectible Secret (the Discover engine's
    # class-weighting returns an empty pool for hero classes without
    # secrets, opening a 0-card choice that the game-loop trips on).
    play = Give(CONTROLLER, RandomCardPicker(collectible=True, secret=True))


class _SteamcleanerPurge(TargetedAction):
    """Destroy every card in both decks that wasn't there at game
    start. Reads the per-card `_from_starting_deck` flag set in
    prepare_for_game; any card created later (Discover, generated,
    shuffled in, etc.) is False and gets destroyed."""

    TARGET = ActionArg()

    def do(self, source, target):
        for player in (target, target.opponent):
            # Snapshot the deck — destroy() mutates it mid-loop.
            for card in list(player.deck):
                if not getattr(card, "_from_starting_deck", False):
                    card.destroy()


class REV_946:
    """Steamcleaner"""

    # Battlecry: Destroy ALL cards in both players' decks that didn't
    # start there. Reads the per-card `_from_starting_deck` flag set
    # in prepare_for_game.
    play = _SteamcleanerPurge(CONTROLLER)


class REV_960:
    """Ashen Elemental"""

    # Battlecry: Whenever your opponent draws a card next turn, they
    # take 2 damage. Approximation: set a one-turn aura on opponent.
    play = Buff(OPPONENT, "REV_960e")


class REV_960e:
    events = Draw(OPPONENT).on(Hit(ENEMY_HERO, 2))
    update = Refresh(OPPONENT, {})

    # Self-destruct at end of opponent's turn (= start of our turn).


class REV_837:
    """Muck Plumber"""

    # ALL minions cost (2) more.
    update = (
        Refresh(FRIENDLY_HAND + MINION, {GameTag.COST: 2}),
        Refresh(ENEMY_HAND + MINION, {GameTag.COST: 2}),
    )


class REV_839:
    """Sinstone Totem"""

    # At the end of your turn, gain +1 Health.
    events = OWN_TURN_END.on(Buff(SELF, "REV_839e"))


class REV_839e:
    tags = {GameTag.HEALTH: 1}
