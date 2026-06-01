from ..utils import *

from hearthstone.enums import CardType, Zone


# ---------------------------------------------------------------------------
# Custom LazyNum
# ---------------------------------------------------------------------------


class _FriendlyAttacksThisGame(LazyNum):
    """Muradin's Last Stand — count every time a friendly character attacked
    this game. The engine has no per-game "all friendly attacks" counter, so
    the spell maintains its own (bumped by its Deck.events + Hand.events while
    it waits to be played). A spell is always either in deck or hand before it
    is cast, so this observes the whole game."""

    def evaluate(self, source):
        return self.num(getattr(source, "_muradin_attacks", 0))


# ---------------------------------------------------------------------------
# Custom actions
# ---------------------------------------------------------------------------


class _MuradinCountAttack(TargetedAction):
    """Bump the spell's private friendly-attack counter (while it waits in
    deck/hand)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._muradin_attacks = getattr(target, "_muradin_attacks", 0) + 1


class _AlakirGet(TargetedAction):
    """Al'Akir, Lord of Storms — Battlecry: Get 2 minions with Cost equal to
    this minion's Attack. They cost (1)."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        cost = source.atk
        for _ in range(2):
            pick = RandomMinion(cost=cost).evaluate(source)
            if isinstance(pick, list):
                pick = pick[0] if pick else None
            if not pick:
                continue
            card = controller.card(pick.id, source=source)
            card.zone = Zone.HAND
            # "They cost (1)": stamp a permanent cost reduction down to 1.
            reduction = (card.cost or 0) - 1
            if reduction > 0:
                card.tags[GameTag.COST] = (card.tags.get(GameTag.COST, card.cost or 0)) - reduction


class _CracklingAbsorb(TargetedAction):
    """Crackling Cloudstrider — Battlecry: choose a spell in your hand that
    costs (4) or less to absorb (store its id, remove it from hand).
    Approximation: engine hand-targeting is unsupported, so absorb a RANDOM
    eligible hand spell (precedent: castle_nathria REV_511)."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        candidates = [
            c for c in controller.hand
            if c.type == CardType.SPELL and (c.cost or 0) <= 4
        ]
        if not candidates:
            return
        spell = source.game.random.choice(candidates)
        target._absorbed_spell = spell.id
        spell.discard()


class _CracklingCast(TargetedAction):
    """Crackling Cloudstrider — Deathrattle: cast the absorbed spell."""

    TARGET = ActionArg()

    def do(self, source, target):
        sid = getattr(source, "_absorbed_spell", None)
        if sid:
            # Cast from the hero: the absorbing minion is in the graveyard by
            # the time its deathrattle fires, so it is not a valid cast source.
            source.game.cheat_action(
                source.controller.hero, [CastSpellTargetsEnemiesIfPossible(sid)]
            )


class _AscendanceMorph(TargetedAction):
    """Ascendance — transform all friendly minions into random ones that cost
    (1) more; the new minion summons the original when it dies."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        for minion in list(controller.field):
            if minion.zone != Zone.PLAY:
                continue
            if getattr(minion, "_ascended", False):
                continue
            original_id = minion.id
            pick = RandomMinion(cost=(minion.cost or 0) + 1).evaluate(source)
            if isinstance(pick, list):
                pick = pick[0] if pick else None
            if not pick:
                continue
            new_card = controller.card(pick.id, source=source)
            new_card._ascended = True
            new_card._ascendance_original = original_id
            source.game.cheat_action(source, [Morph(minion, new_card)])
            new_card.additional_deathrattles.append(
                (_AscendanceSummonOriginal(SELF),)
            )
            if not new_card.has_deathrattle:
                new_card.has_deathrattle = True


class _AscendanceSummonOriginal(TargetedAction):
    """Deathrattle attached by Ascendance — summon the original minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        original = getattr(source, "_ascendance_original", None)
        if original:
            source.game.cheat_action(
                source, [Summon(source.controller, original)]
            )


class _MorchokDraw(TargetedAction):
    """Morchok — Battlecry: Draw a card and reduce its Cost by (10). Repeat
    with excess Cost reduction (so a card cheaper than the leftover keeps the
    chain going)."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        budget = 10
        # Safety bound: at most one draw per card in deck.
        for _ in range(len(controller.deck) + 1):
            if budget <= 0 or not controller.deck:
                return
            drawn = source.game.cheat_action(source, [Draw(controller)])
            # Draw returns nested lists; pull the card out.
            card = None
            stack = list(drawn)
            while stack:
                item = stack.pop()
                if isinstance(item, (list, tuple)):
                    stack.extend(item)
                elif hasattr(item, "cost"):
                    card = item
                    break
            if card is None:
                return
            cost = card.cost or 0
            reduce_by = min(budget, cost)
            if reduce_by > 0:
                card.tags[GameTag.COST] = (
                    card.tags.get(GameTag.COST, cost) - reduce_by
                )
            budget -= cost
            if cost > 0 and budget < 0:
                # Card was pricier than remaining budget — chain stops.
                return


# ---------------------------------------------------------------------------
# Minions
# ---------------------------------------------------------------------------


class CATA_153:
    """Al'Akir, Lord of Storms"""

    # Colossal +2, Rush, Windfury (data tags + engine-summoned limbs).
    # Battlecry: Get 2 minions with Cost equal to this minion's Attack. They
    # cost (1).
    play = _AlakirGet(SELF)


class CATA_563:
    """Crackling Cloudstrider"""

    # Battlecry: Choose a spell in your hand that costs (4) or less to absorb.
    # Deathrattle: Cast it. (Battlecry choose-in-hand approximated as random
    # eligible hand spell.)
    play = _CracklingAbsorb(SELF)
    deathrattle = _CracklingCast(SELF)


class CATA_564:
    """Air Support"""

    # Battlecry: Give a friendly minion Mega-Windfury. It can't attack heroes.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = Buff(TARGET, "CATA_564e")


class CATA_565:
    """Skywall Sentinel"""

    # Taunt (data). Battlecry: Herald {0}.
    play = Herald(CONTROLLER)


class CATA_570:
    """Morchok"""

    # Battlecry: Draw a card and reduce its Cost by (10). Repeat this with
    # excess Cost reduction.
    play = _MorchokDraw(SELF)


class CATA_004:
    """Rehgar Earthfury"""

    # After this or an adjacent minion attacks, get a Lightning Bolt.
    # Lightning Bolt is the 1-cost Shaman spell EX1_238 ("Deal 3 damage.
    # Overload: (1)").
    events = Attack(SELF | SELF_ADJACENT).after(Give(CONTROLLER, "EX1_238"))


class CATA_724:
    """Stormbinder"""

    # Overload: (3) (data). Deathrattle: Unlock your Overloaded Mana Crystals.
    deathrattle = UnlockOverload(CONTROLLER)


# ---------------------------------------------------------------------------
# Spells
# ---------------------------------------------------------------------------


class CATA_561:
    """Ritual of Power"""

    # Herald {0}. Get two 1/1 Elementals with Rush.
    play = Herald(CONTROLLER), Give(CONTROLLER, "CATA_561t") * 2


class CATA_567:
    """Ascendance"""

    # Transform all friendly minions into ones that cost (1) more. They summon
    # the originals when they die.
    play = _AscendanceMorph(SELF)


class CATA_568:
    """Muradin's Last Stand"""

    # Draw 2 cards. Costs (1) less for each time a friendly character attacked
    # this game.
    cost_mod = -_FriendlyAttacksThisGame()
    play = Draw(CONTROLLER) * 2

    class Deck:
        events = Attack(FRIENDLY).on(_MuradinCountAttack(SELF))

    class Hand:
        events = Attack(FRIENDLY).on(_MuradinCountAttack(SELF))


class CATA_569:
    """Ceremonial Clash"""

    # Summon a random 3, 2, and 1-Cost minion. Overload: (1) (data).
    play = (
        Summon(CONTROLLER, RandomMinion(cost=3)),
        Summon(CONTROLLER, RandomMinion(cost=2)),
        Summon(CONTROLLER, RandomMinion(cost=1)),
    )


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


class CATA_561t:
    """Breezling"""

    # Rush (data). Vanilla 1/1 Elemental.


class CATA_153t:
    """Charged Hand of Al'Akir"""

    # Colossal limb (engine-summoned). Aura: Adjacent minions have +N Attack
    # (Herald upgrades the bonus). Base printed value is 1.
    update = Refresh(SELF_ADJACENT, buff="CATA_153e")


class CATA_153t1:
    """Charged Hand of Al'Akir"""

    update = Refresh(SELF_ADJACENT, buff="CATA_153e")


class CATA_565t:
    """Soldier of Al'Akir"""

    # Aura: Adjacent minions have +N Attack.
    update = Refresh(SELF_ADJACENT, buff="CATA_153e")


# ---------------------------------------------------------------------------
# Enchantments
# ---------------------------------------------------------------------------


class CATA_153e:
    """Spark of Fury"""

    # Adjacent-minion Attack aura buff (base +1).
    tags = {GameTag.ATK: 1}


class CATA_564e:
    """Air Support"""

    # Mega-Windfury. Can't attack heroes.
    tags = {
        GameTag.MEGA_WINDFURY: True,
        GameTag.CANNOT_ATTACK_HEROES: True,
    }
