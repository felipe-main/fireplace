"""Into the Emerald Dream — DEATHKNIGHT collectible cards (EDR_).

Mechanics in this file:
  * Leeches (EDR_810t Bloated Leech) — at end of your turn your hero "steals"
    N Health from the lowest-Health enemy = deal N damage to that enemy and
    heal your hero for N. Base N = 2; Hideous Husk (EDR_810) auras +1 each.
  * Corpse-spending (EDR_811 / EDR_813 / EDR_815) — gate on `controller.corpses`
    and decrement via `SpendCorpses`.
  * Nythendra (EDR_818) split/reform Beetle (EDR_818t) mechanic.
  * Ursoc (EDR_819) attack-ALL battlecry + resurrect-what-it-killed deathrattle.
"""

from ..utils import *

from hearthstone.enums import GameTag, CardType, Zone, Race

# Shared set-wide Dark Gift granter (random Nightmare keyword Bonus Effect).
from .neutral import _GiveDarkGift


##
# Custom actions / helpers


def _hideous_husk_count(controller):
    """How many Hideous Husks (EDR_810) the controller has in play — each
    makes your Leeches steal 1 more Health."""
    return sum(1 for m in controller.field if m.id == "EDR_810")


class _LeechSteal(TargetedAction):
    """Bloated Leech end-of-turn: your hero steals N Health from the lowest
    Health enemy. N = 2 + (number of friendly Hideous Husks). "Steal" = deal
    N damage to the lowest-Health enemy character, then heal your hero N."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        amount = 2 + _hideous_husk_count(controller)
        enemies = [
            c for c in (list(controller.opponent.field) + [controller.opponent.hero])
            if c.zone == Zone.PLAY and not c.dead
        ]
        if not enemies:
            return
        lowest = min(c.health for c in enemies)
        victims = [c for c in enemies if c.health == lowest]
        victim = controller.game.random.choice(victims)
        source.game.cheat_action(source, [Hit(victim, amount)])
        source.game.cheat_action(source, [Heal(controller.hero, amount)])


class _GrotesqueRuneblade(TargetedAction):
    """Grotesque Runeblade battlecry: if the last card you played (before this
    weapon) had an Unholy rune, gain +1 Attack; if it had a Blood rune, gain
    +1 Durability. (Both can apply.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        last = source.controller.last_card_played
        if last is None:
            return
        # Runes live on the printed (data) card, not the live Card's tags.
        data = getattr(last, "data", last)
        tags = getattr(data, "tags", {})
        unholy = tags.get(GameTag.COST_UNHOLY, 0) >= 1
        blood = tags.get(GameTag.COST_BLOOD, 0) >= 1
        if unholy:
            source.game.cheat_action(source, [Buff(source, "EDR_812e")])
        if blood:
            source.game.cheat_action(source, [Buff(source, "EDR_812e1")])


class _NythendraTrackHealth(TargetedAction):
    """Stamp Nythendra's remaining Health whenever it takes damage, so the
    deathrattle can split into the right number of Beetles.

    SELF_DAMAGE fires from Damage.do *after* `target._hit(amount)` has already
    been applied, so on a lethal blow `source.health` is already <= 0 and would
    stamp 0 Beetles. Instead we reconstruct the Health Nythendra had *before*
    this blow landed (`current health + amount`, clamped to its max Health):
    that is the "remaining Health when it died" the printed card refers to
    (e.g. killed while at 3 Health -> 3 Beetles), and it is unaffected by
    overkill. The amount is read live from the Damage broadcast arg."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount=0):
        # A non-lethal hit leaves `source.health` at the real post-hit value
        # (e.g. 7 -> 3), which is the Health to stamp. A *lethal* hit has
        # already driven `source.health` <= 0, so we instead recover the
        # Health Nythendra was sitting at right before the killing blow
        # (`health + amount`), which is the "Health it died at" the printed
        # card splits on (e.g. killed while at 3 Health -> 3 Beetles). Either
        # way the stamp is clamped to [0, max Health] and is overkill-proof.
        if source.health > 0:
            remaining = source.health
        else:
            remaining = source.health + (amount or 0)
        source._nyth_remaining = max(0, min(remaining, source.max_health))


class _NythendraSplit(TargetedAction):
    """Nythendra deathrattle: split into 1/1 Beetles equal to its remaining
    Health at the moment it died (capped at its max Health)."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        remaining = getattr(source, "_nyth_remaining", source.max_health)
        count = max(0, min(remaining, source.max_health))
        for _ in range(count):
            source.game.cheat_action(source, [Summon(controller, "EDR_818t")])


class _NythendraReform(TargetedAction):
    """Nythendric Beetle start-of-turn: combine with every other friendly
    Beetle and reform Nythendra (Health = number of Beetles consumed, capped
    at 7). Every Beetle fires this at turn-begin, but only the FIRST one
    actually reforms — it consumes all the others, after which the remaining
    Beetles see an empty Beetle list and bail out."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        if getattr(controller, "_nyth_reforming", False):
            return
        beetles = [m for m in controller.field if m.id == "EDR_818t"]
        if source not in beetles or not beetles:
            return
        controller._nyth_reforming = True
        try:
            count = len(beetles)
            for b in beetles:
                source.game.cheat_action(source, [Destroy(b)])
            source.game.cheat_action(source, [Deaths()])
            before = set(controller.field)
            source.game.cheat_action(source, [Summon(controller, "EDR_818")])
            new = [
                m for m in controller.field
                if m not in before and m.id == "EDR_818"
            ]
            if not new:
                return
            nyth = new[0]
            health = min(count, nyth.max_health)
            if health < nyth.max_health:
                nyth.damage = nyth.max_health - health
        finally:
            controller._nyth_reforming = False


class _UrsocAttackAll(TargetedAction):
    """Ursoc battlecry: attack ALL other minions, recording each minion this
    kills (for the deathrattle resurrect)."""

    TARGET = ActionArg()

    def do(self, source, target):
        source._ursoc_killed = getattr(source, "_ursoc_killed", [])
        entities = (ALL_MINIONS - SELF - DEAD).eval(source.game.live_entities, source)
        source.game.random.shuffle(entities)
        for entity in entities:
            if source.dead or source.zone != Zone.PLAY:
                break
            if entity.dead or entity.zone != Zone.PLAY:
                continue
            cid = entity.id
            source.game.cheat_action(source, [Attack(source, entity)])
            source.game.cheat_action(source, [Deaths()])
            if entity.dead or entity.zone == Zone.GRAVEYARD:
                source._ursoc_killed.append(cid)


class _UrsocResurrect(TargetedAction):
    """Ursoc deathrattle: resurrect every minion it killed with its battlecry.
    Resurrection summons under Ursoc's OWN controller (the resurrector), as all
    Hearthstone resurrect effects do — not the minion's original owner."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        for cid in getattr(source, "_ursoc_killed", []):
            source.game.cheat_action(source, [Summon(controller, cid)])


class _RiteDarkGift(TargetedAction):
    """Rite of Atrocity — if you have 2+ Corpses, spend them and give the
    Discovered Undead a Dark Gift. The Dark Gift is granted through the shared
    set-wide `_GiveDarkGift` helper (a random keyword Bonus Effect from the
    Nightmare pool), matching every other EDR Dark-Gift card; the true Dark
    Gift pool is not enumerated in the card data, so this is the agreed
    faithful-shape approximation rather than a bespoke flat +2/+2 enchant."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        if controller.corpses >= 2:
            source.game.cheat_action(source, [SpendCorpses(controller, 2)])
            source.game.cheat_action(source, [_GiveDarkGift(target)])


##
# Minions


class EDR_810:
    """Hideous Husk"""

    # Your Leeches steal 1 more Health from their victims.
    # Battlecry: Summon two 0/2 Leeches.
    # (The "+1 steal" is read live by _LeechSteal, so no aura enchant needed.)
    play = Summon(CONTROLLER, "EDR_810t") * 2


class EDR_810t:
    """Bloated Leech"""

    # At the end of your turn, your hero steals 2 Health from the lowest
    # Health enemy. (Hideous Husk adds +1 each.)
    events = OWN_TURN_END.on(_LeechSteal(SELF))


class EDR_815:
    """Corpse Flower"""

    # After your opponent summons a minion, spend 2 Corpses to deal 3 damage
    # to it.
    events = Summon(OPPONENT, MINION).after(
        (Attr(CONTROLLER, "corpses") >= 2)
        & (SpendCorpses(CONTROLLER, 2), Hit(Summon.CARD, 3))
    )


class EDR_816:
    """Monstrous Mosquito"""

    # At the end of your turn, give your other minions +1 Attack.
    events = OWN_TURN_END.on(Buff(FRIENDLY_MINIONS - SELF, "EDR_816e"))


class EDR_818:
    """Nythendra"""

    # Taunt (in data). Deathrattle: Split into 1/1 Beetles. At the start of
    # your turn, reform with any remaining.
    events = SELF_DAMAGE.on(_NythendraTrackHealth(SELF, Damage.AMOUNT))
    deathrattle = _NythendraSplit(SELF)


class EDR_818t:
    """Nythendric Beetle"""

    # At the start of your turn, combine with any other friendly Beetles and
    # reform Nythendra.
    events = OWN_TURN_BEGIN.on(_NythendraReform(SELF))


class EDR_819:
    """Ursoc"""

    # Battlecry: Attack ALL other minions.
    # Deathrattle: Resurrect any this killed.
    play = _UrsocAttackAll(SELF)
    deathrattle = _UrsocResurrect(SELF)


##
# Spells


class EDR_811:
    """Rite of Atrocity"""

    # Discover an Undead. Spend 2 Corpses to give it a Dark Gift.
    play = Discover(CONTROLLER, RandomMinion(race=Race.UNDEAD)).then(
        Give(CONTROLLER, Discover.CARD).then(_RiteDarkGift(Give.CARD))
    )


class EDR_813:
    """Morbid Swarm"""

    # Choose One - Summon two 1/1 Ants; or Spend 2 Corpses to deal 4 damage
    # to a minion. (The parent accepts an optional minion target so the
    # "Bug Bites" sub-mode can hit it; the "Ants" sub-mode ignores it.)
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    choose = ("EDR_813a", "EDR_813b")
    play = ChooseBoth(CONTROLLER) & (
        Summon(CONTROLLER, "EDR_813at") * 2,
        (Attr(CONTROLLER, "corpses") >= 2)
        & (SpendCorpses(CONTROLLER, 2), Hit(TARGET, 4)),
    )


class EDR_813a:
    """Contaminated Colony"""

    # Summon two 1/1 Ants.
    play = Summon(CONTROLLER, "EDR_813at") * 2


class EDR_813at:
    """Ant Husk"""

    # 1/1 vanilla token.


class EDR_813b:
    """Bug Bites"""

    # Spend 2 Corpses to deal 4 damage to a minion.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (Attr(CONTROLLER, "corpses") >= 2) & (
        SpendCorpses(CONTROLLER, 2),
        Hit(TARGET, 4),
    )


class EDR_814:
    """Infested Breath"""

    # Deal 2 damage. Summon a 0/2 Leech.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 2), Summon(CONTROLLER, "EDR_810t")


class EDR_817:
    """Sanguine Infestation"""

    # Draw 2 cards. Summon two 0/2 Leeches.
    play = Draw(CONTROLLER) * 2, Summon(CONTROLLER, "EDR_810t") * 2


##
# Weapons


class EDR_812:
    """Grotesque Runeblade"""

    # Battlecry: If the last card you played had an Unholy rune, gain +1
    # Attack. Repeat for Blood and +1 Durability.
    play = _GrotesqueRuneblade(SELF)


##
# Enchantments


class EDR_812e:
    """Unholy Corruption"""

    # +1 Attack.
    tags = {GameTag.ATK: 1}


class EDR_812e1:
    """Bloody Corruption"""

    # +1 Durability.
    tags = {GameTag.DURABILITY: 1}


class EDR_816e:
    """Shared Blood"""

    # +1 Attack.
    tags = {GameTag.ATK: 1}


@custom_card
class EDR_811e:
    """Dark Gift"""

    # Approximation of the Dark Gift mechanic: a representative +2/+2 buff.
    tags = {
        GameTag.CARDNAME: "Dark Gift",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 2,
        GameTag.HEALTH: 2,
    }


# Corpse-spender deck selector (cards tagged CORPSE_SPENDER).
_CORPSE_SPENDER = FuncSelector(
    lambda entities, src: [
        e
        for e in entities
        if getattr(e, "data", None) and e.data.tags.get(GameTag.CORPSE_SPENDER, 0)
    ]
)


def _falric_count(controller):
    """Number of Falrics (CORE_EDR_003) currently in the controller's play."""
    return sum(1 for m in controller.field if m.id == "CORE_EDR_003")


class _FalricSyncDoubling(TargetedAction):
    """Reconcile `controller.corpses_doubled` to the live number of Falrics in
    play, each refresh.

    Falric's "You gain twice as many Corpses" is a passive while-in-play aura.
    Modelling it as a deathrattle was doubly broken: (1) the data card carries
    no DEATHRATTLE tag, so `has_deathrattle` is False and the undo never fired
    on death either, leaving the doubling stuck on permanently; (2) even with a
    tag, a deathrattle would not undo on silence / bounce / transform.

    Driving it from the `update` aura hook fixes both: `refresh_auras` runs this
    every refresh for each Falric still in PLAY, so the count tracks the live
    board and is torn down the instant a Falric leaves by ANY means."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.corpses_doubled = _falric_count(target)


class _FalricResetDoubling(TargetedAction):
    """Hand/Deck-side companion: while a Falric sits in the controller's hand
    or deck (i.e. NOT in play), force `corpses_doubled` back to the live
    in-play Falric count. This closes the only window the in-play `update`
    can't cover — when the *last* Falric leaves play, its own `update` no
    longer runs, so a hand/deck Falric (there is one whenever Falric was
    bounced) re-zeroes the stale value on the next refresh."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.corpses_doubled = _falric_count(target)


class EDR_003:
    """Falric"""

    # You gain twice as many Corpses. Battlecry: Draw a card that spends Corpses.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + _CORPSE_SPENDER))
    update = _FalricSyncDoubling(CONTROLLER)

    class Hand:
        update = _FalricResetDoubling(CONTROLLER)

    class Deck:
        update = _FalricResetDoubling(CONTROLLER)


##
# Firelands mini-set (FIR_) — DEATHKNIGHT
#
#   * Cremate (FIR_900): Discover a minion with a Dark Gift; it costs (2) less.
#     The Dark Gift is granted through the shared set-wide `_GiveDarkGift`
#     helper (a random keyword Bonus Effect from the Nightmare pool), matching
#     every other Emerald Dream Dark-Gift card — the true per-gift pool is not
#     enumerated in the card data, so this is the agreed faithful-shape
#     approximation. The (2)-less discount is a permanent COST: -2 enchant.
#   * Frostburn Matriarch (FIR_901): Battlecry that checks for a held minion
#     "with a Dark Gift" via the shared `_dark_gifts` marker.
#   * Volcoross (FIR_951): Rush/Taunt, Battlecry — choose to spend 10/20/30
#     Corpses to gain that many stats (presented via a Corpse-gated GenericChoice
#     of three marker options).


def _holding_dark_gift_minion(controller):
    """True if the controller is holding a minion that carries a Dark Gift
    (detected via the shared `_dark_gifts` marker set by `_GiveDarkGift`)."""
    return any(
        c.type == CardType.MINION and getattr(c, "_dark_gifts", None)
        for c in controller.hand
    )


class _FrostburnMatriarch(TargetedAction):
    """Frostburn Matriarch battlecry: if you're holding a minion with a Dark
    Gift, summon two 4/4 Dragons with Taunt (FIR_901t)."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        if _holding_dark_gift_minion(controller):
            source.game.cheat_action(
                source, [Summon(controller, "FIR_901t") * 2]
            )


class _VolcorossChoice(Choice):
    """Volcoross battlecry choice: pick one of the three Corpse-spend options.
    Choosing an option spends that many Corpses and grants Volcoross that many
    +Attack/+Health. The marker cards are never zoned to hand — choosing one
    resolves the gain directly."""

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        amount = card._volcoross_amount
        volcoross = self.source
        controller = volcoross.controller
        self.source.game.cheat_action(
            volcoross,
            [
                SpendCorpses(controller, amount),
                Buff(volcoross, "FIR_951e", atk=amount, max_health=amount),
            ],
        )
        # Marker cards are never zoned (they stay in SETASIDE) so nothing
        # leaks into hand/play — no cleanup needed.
        self.trigger_choice_callback()


class _VolcorossBattlecry(TargetedAction):
    """Build the Volcoross choice: offer each of 10/20/30 Corpses that the
    controller can currently afford. Affordable-only mirrors the printed card,
    which only presents options you have the Corpses for."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        markers = []
        for amount in (10, 20, 30):
            if controller.corpses >= amount:
                marker = controller.card("FIR_951e", source=source)
                marker._volcoross_amount = amount
                markers.append(marker)
        if not markers:
            return
        source.game.queue_actions(source, [_VolcorossChoice(controller, markers)])


class FIR_900:
    """Cremate"""

    # Discover a minion with a Dark Gift. It costs (2) less.
    play = Discover(CONTROLLER, RandomMinion()).then(
        Give(CONTROLLER, Discover.CARD).then(
            _GiveDarkGift(Give.CARD), Buff(Give.CARD, "FIR_900e")
        )
    )


@custom_card
class FIR_900e:
    # Cremate — the discovered minion costs (2) less. Not present in card data,
    # so registered as an engine-internal cost enchant.
    tags = {
        GameTag.CARDNAME: "Cremate",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


class FIR_901:
    """Frostburn Matriarch"""

    # Battlecry: If you're holding a minion with a Dark Gift, summon two 4/4
    # Dragons with Taunt.
    play = _FrostburnMatriarch(SELF)


class FIR_901t:
    """Frostburn Broodling"""

    # 4/4 Dragon with Taunt (Taunt comes from data).


class FIR_951:
    """Volcoross"""

    # Rush, Taunt (from data). Battlecry: Choose to spend 10, 20, or 30
    # Corpses to gain that many stats.
    play = _VolcorossBattlecry(SELF)


class FIR_951e:
    """Voracious Appetite"""

    # Increased Stats. (Atk/Health set dynamically by the chosen Corpse amount.)
