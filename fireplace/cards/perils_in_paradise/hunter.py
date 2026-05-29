from ..utils import *


##
# Custom actions / helpers


def _replay_card(source, card):
    """Replay a single card by id: spells are cast at a random legal target,
    everything else is re-played through a fresh copy in hand so the
    battlecry / on-play hooks fire."""
    ctrl = source.controller
    if card.type == CardType.SPELL:
        copy = ctrl.card(card.id, source=source)
        copy.zone = Zone.HAND
        source.game.cheat_action(source, [CastSpell(copy)])
    else:
        if card.type == CardType.MINION and len(ctrl.field) >= 7:
            return
        copy = ctrl.card(card.id, source=source)
        copy.zone = Zone.HAND
        source.game.cheat_action(source, [Play(copy)])


class _RepeatLastSpellAtEnemy(TargetedAction):
    """Chatty Macaw — Battlecry: Repeat the last spell you cast, targeting
    an enemy (a random enemy if it needs a target). A fresh copy of the
    most-recent cast spell is cast via CastSpellTargetsEnemiesIfPossible so
    its target is chosen among enemies when one is required."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spells = [c for c in ctrl.spells_cast_this_game if c.type == CardType.SPELL]
        if not spells:
            return
        last = spells[-1]
        copy = ctrl.card(last.id, source=source)
        copy.zone = Zone.HAND
        source.game.cheat_action(
            source, [CastSpellTargetsEnemiesIfPossible(copy)]
        )


class _RepeatLast1CostCard(TargetedAction):
    """Pet Parrot — Battlecry: Repeat the last 1-Cost card you played.
    Eligibility uses the printed (data) Cost so in-hand discounts don't
    change what counts."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        played = [
            c for c in ctrl.cards_played_this_game
            if (c.data.cost or 0) == 1
        ]
        if not played:
            return
        _replay_card(source, played[-1])


class _RepeatCardsPlayedLastTurn(TargetedAction):
    """Sasquawk — Battlecry: Repeat each card you played last turn. The
    controller's previous turn is two game-turns ago (turns alternate, so
    game.turn increments by one per player turn). Replays, in play order,
    every card whose `turn_played` equals game.turn - 2."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        last_turn = source.game.turn - 2
        cards = [
            c for c in ctrl.cards_played_this_game
            if getattr(c, "turn_played", None) == last_turn
        ]
        for card in cards:
            _replay_card(source, card)


class _BirdwatchingBuffAllCopies(TargetedAction):
    """Birdwatching — after the player Discovers a minion from their deck,
    give every copy of it +2/+1 wherever it is (deck, hand, or battlefield,
    both players). Matched by card id."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, picked):
        if isinstance(picked, list):
            if not picked:
                return
            picked = picked[0]
        if picked is None:
            return
        cid = picked.id
        targets = []
        for player in source.game.players:
            for zone in (player.deck, player.hand, player.field):
                for c in list(zone):
                    if c.id == cid:
                        targets.append(c)
        for c in targets:
            source.game.cheat_action(source, [Buff(c, "VAC_408e")])


class _BirdwatchingDiscoverDeck(TargetedAction):
    """Birdwatching — Discover a minion from your deck (a real 3-card pick
    among unique deck-minion ids), then buff all copies of the chosen one.
    No-op when the deck has no minions."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        deck_minions = [c for c in ctrl.deck if c.type == CardType.MINION]
        if not deck_minions:
            return
        unique_ids = list({c.id for c in deck_minions})
        picks = source.game.random.sample(unique_ids, min(3, len(unique_ids)))
        cards = [ctrl.card(cid) for cid in picks]
        source.game.cheat_action(
            source,
            [GenericChoice(ctrl, cards).then(
                _BirdwatchingBuffAllCopies(ctrl, GenericChoice.CARD)
            )],
        )


class _DeathRollDestroyAndSplit(TargetedAction):
    """Death Roll — destroy an enemy minion, then deal damage equal to its
    Attack randomly split among all enemies (one point per random enemy
    hit, repeated Attack times). Attack is captured BEFORE the destroy."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        atk = target.atk or 0
        source.game.cheat_action(source, [Destroy(target)])
        for _ in range(atk):
            source.game.cheat_action(source, [Hit(RANDOM_ENEMY_CHARACTER, 1)])


class _TrustyFishingRodSummon(TargetedAction):
    """Trusty Fishing Rod — after your hero attacks, summon a 1-Cost minion
    from your deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        pool = [
            c for c in ctrl.deck
            if c.type == CardType.MINION and (c.cost or 0) == 1
        ]
        if not pool:
            return
        pick = source.game.random.choice(pool)
        source.game.cheat_action(source, [Summon(ctrl, pick)])


##
# Minions


class VAC_407:
    """Chatty Macaw"""

    # [x]<b>Battlecry:</b> Repeat the last spell you cast at an enemy
    # <i>(at a random enemy if possible)</i>.
    play = _RepeatLastSpellAtEnemy(SELF)


class VAC_412:
    """Catch of the Day"""

    # [x]<b>Rush</b> <b>Battlecry:</b> Summon a 2/1 Worm for your opponent.
    # Rush lives in data.
    play = Summon(OPPONENT, "VAC_412t")


class VAC_413:
    """Ranger Gilly"""

    # [x]<b>Warrior Tourist.</b> At the end of your turn, get a 2/3
    # Crocolisk. <b>Deathrattle:</b> Give all minions in your hand +2/+3.
    # Tourist is deckbuilding-only (no in-game trigger).
    events = OWN_TURN_END.on(Give(CONTROLLER, "VAC_413t"))
    deathrattle = Buff(FRIENDLY_HAND + MINION, "VAC_413e3")


class VAC_415:
    """Sasquawk"""

    # <b>Battlecry:</b> Repeat each card you played last turn.
    play = _RepeatCardsPlayedLastTurn(SELF)


class VAC_961:
    """Pet Parrot"""

    # <b>Battlecry:</b> Repeat the last 1-Cost card you played.
    play = _RepeatLast1CostCard(SELF)


##
# Spells


class VAC_408:
    """Birdwatching"""

    # [x]<b>Discover</b> a minion from your deck. Give all copies of it
    # +2/+1 <i>(wherever they are)</i>.
    play = _BirdwatchingDiscoverDeck(CONTROLLER)


class VAC_410:
    """Furious Fowls"""

    # Choose an enemy. Summon two 3/2 Birds with <b>Immune</b> while
    # attacking to attack it. The chosen enemy is TARGET; each summoned
    # bird is forced to attack that target.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = (
        Summon(CONTROLLER, "VAC_410t").then(Attack(Summon.CARD, TARGET)),
        Summon(CONTROLLER, "VAC_410t").then(Attack(Summon.CARD, TARGET)),
    )


class VAC_416:
    """Death Roll"""

    # [x]Destroy an enemy minion. Deal damage equal to its Attack randomly
    # split among all enemies.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _DeathRollDestroyAndSplit(TARGET)


##
# Locations


class VAC_409:
    """Parrot Sanctuary"""

    # [x]Your next <b>Battlecry</b> minion costs (1) less. After you play a
    # <b>Battlecry</b> minion, reopen this.
    activate = Buff(CONTROLLER, "VAC_409e")
    events = Play(CONTROLLER, BATTLECRY + MINION).after(ReopenLocation(SELF))


class VAC_409e:
    """Parroting"""

    # Your next Battlecry minion costs (1) less. Consumed when a Battlecry
    # minion is played.
    update = Refresh(FRIENDLY_HAND + BATTLECRY + MINION, {GameTag.COST: -1})
    events = Play(CONTROLLER, BATTLECRY + MINION).after(Destroy(SELF))


##
# Weapons


class VAC_960:
    """Trusty Fishing Rod"""

    # [x]After your hero attacks, summon a 1-Cost minion from your deck.
    events = Attack(FRIENDLY_HERO).after(_TrustyFishingRodSummon(SELF))


##
# Tokens


class VAC_410t:
    """Angry Bird"""

    # 3/2 Beast with "Immune while attacking" (IMMUNE_WHILE_ATTACKING in
    # data). Stats + keyword live in data.


class VAC_412t:
    """Delicious Worm"""

    # 2/1 Beast vanilla token. Stats live in data.


class VAC_413t:
    """Island Crocolisk"""

    # 2/3 Beast vanilla token. Stats live in data.


##
# Enchantments (exist in data; declare the stat/cost tags the XML omits)


class VAC_408e:
    """A Bird in the Hand"""

    # +2/+1.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}


class VAC_413e3:
    """Toothy"""

    # +2/+3.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 3}
