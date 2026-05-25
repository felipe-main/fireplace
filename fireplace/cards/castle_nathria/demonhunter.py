from ..utils import *


##
# Spells


class REV_506:
    """Sinful Brand"""

    # Brand an enemy minion. Whenever it takes damage, deal 2 damage to the
    # enemy hero. Modeled as an enchantment on the target whose event fires
    # when the target is damaged.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Buff(TARGET, "REV_506e")


class REV_506e:
    events = Damage(OWNER).on(Hit(ENEMY_HERO, 2))


class REV_507:
    """Dispose of Evidence"""

    # Give your hero +3 Attack this turn. Choose a card in your hand to
    # shuffle into your deck. Approximated as the hero buff + shuffle a
    # random hand card into the deck (no UI choice in our engine).
    play = Buff(FRIENDLY_HERO, "REV_507e"), Shuffle(
        CONTROLLER, RANDOM(FRIENDLY_HAND - SELF)
    )


class REV_507e:
    tags = {GameTag.ATK: 3, enums.TEMPORARY: 1}


class _RelicOfDimensionsDraw(TargetedAction):
    """Draw 2 cards and buff each one with REV_508e (a -N cost
    snapshot). Custom action because the `Draw().then(Buff()) * 2`
    DSL pattern shares Draw.CARD state across iterations and both
    Buffs end up on the same (most recently drawn) card. Snapshots
    the hand-before-set, draws twice, then buffs every card that
    landed in hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        before = set(id(c) for c in target.hand)
        target.draw()
        target.draw()
        added = [c for c in target.hand if id(c) not in before]
        for card in added:
            source.game.cheat_action(source, [Buff(card, "REV_508e")])


class REV_508:
    """Relic of Dimensions"""

    # Draw two cards and reduce their Cost by (2 + Relic counter). The
    # counter (relics_played_this_game) bumps AFTER the effect runs in
    # Play.do, so the 1st Relic reads 0, the 2nd reads 1, etc. —
    # exactly the printed "Improve your future Relics" semantics.
    play = _RelicOfDimensionsDraw(CONTROLLER)


@custom_card
class REV_508e:
    # Snapshot (2 + relics_played) at apply-time and stash it on the
    # buff's `cost` tag so the engine's standard cost aggregation
    # applies it once (lambda-based cost re-fires every cost read,
    # which compounded into 0-cost on multi-buff cards).
    tags = {
        GameTag.CARDNAME: "Relic of Dimensions Discount",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }

    def apply(self, target):
        n = 2 + getattr(self.source.controller, "relics_played_this_game", 0)
        self.cost = -n


class REV_834:
    """Relic of Extinction"""

    # Deal (2 + Relic counter) damage to a random enemy minion, twice.
    play = Hit(
        RANDOM_ENEMY_MINION,
        Attr(CONTROLLER, "relics_played_this_game") + 2,
    ) * 2


class REV_943:
    """Relic of Phantasms"""

    # Summon two (2 + counter)/(2 + counter) Spirits. Counter is read
    # at apply-time via the enchantment so each Spirit snapshots the
    # value when summoned (independent of later Relic casts).
    play = Summon(CONTROLLER, "REV_943t").then(
        Buff(Summon.CARD, "REV_943e")
    ) * 2


@custom_card
class REV_943e:
    tags = {
        GameTag.CARDNAME: "Phantasm Stats",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    atk = lambda self, i: i + self._n
    max_health = lambda self, i: i + self._n

    def apply(self, target):
        self._n = 2 + getattr(self.source.controller, "relics_played_this_game", 0)


class REV_943t:
    """Fleeting Spirit"""


##
# Weapons


class REV_509:
    """Magnifying Glaive"""

    # After your hero attacks, draw until you have 3 cards.
    events = Attack(FRIENDLY_HERO).after(DrawUntil(CONTROLLER, 3))


##
# Minions


class REV_510:
    """Kryxis the Voracious"""

    # Battlecry: Discard your hand. Deathrattle: Draw 3 cards.
    play = Discard(FRIENDLY_HAND - SELF)
    deathrattle = Draw(CONTROLLER) * 3


class REV_511:
    """Bibliomite"""

    # Battlecry: Choose a card in your hand to shuffle into your deck.
    # Approximated as shuffling a random hand card.
    play = Shuffle(CONTROLLER, RANDOM(FRIENDLY_HAND))


class _XymoxCastRandomRelic(TargetedAction):
    """Pick one of the 3 Relic spells at random and cast it on the
    controller's side. CastSpell bypasses Play.do, which is where the
    Relic counter normally bumps, so we bump it manually here so the
    cast Relic reads the right counter value (1 for the first cast)."""

    TARGET = ActionArg()

    def do(self, source, target):
        relic_ids = ["REV_508", "REV_834", "REV_943"]
        cid = source.game.random.choice(relic_ids)
        target.relics_played_this_game += 1
        source.game.cheat_action(target, [CastSpell(cid)])


class REV_937:
    """Artificer Xy'mox"""

    # Battlecry: Discover and cast a Relic. Approximated as casting a
    # random Relic (engine GenericChoice doesn't cleanly chain a
    # "re-cast the chosen card" callback).
    play = _XymoxCastRandomRelic(CONTROLLER)


class REV_937t:
    """Artificer Xy'mox"""

    # Infused: cast all three Relics in declared order so the counter
    # bumps between them ("Improve your future Relics").
    play = (
        CastSpell("REV_508"),
        CastSpell("REV_834"),
        CastSpell("REV_943"),
    )


##
# Locations


class _RelicVaultArm(TargetedAction):
    """Stamp the controller with one Relic-recast charge; consumed in
    Play.do when the next Relic spell resolves. Charge expires at the
    end of the controller's turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.next_relic_casts_twice = 1


class _RelicVaultClearCharge(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        target.next_relic_casts_twice = 0


class REV_942:
    """Relic Vault"""

    # The next Relic you play this turn casts twice. The arm-and-fire
    # mechanism is in actions.py: this just sets the controller's
    # Relic-recast charge. An ephemeral REV_942e enchantment ticks
    # OWN_TURN_END to clear any unspent charge.
    activate = _RelicVaultArm(CONTROLLER), Buff(CONTROLLER, "REV_942e")


@custom_card
class REV_942e:
    # Per-turn expiry of the next_relic_casts_twice charge. Lives just
    # long enough to fire its OWN_TURN_END trigger; safe to re-apply.
    tags = {
        GameTag.CARDNAME: "Relic Vault Charge",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_END.on(_RelicVaultClearCharge(CONTROLLER), Destroy(SELF))
