from ..utils import *


##
# "Spent N Mana while holding this" mechanic (Cataclysm Druid)
#
# Several Druid cards check whether the controller has spent a threshold of
# Mana while the card was held in hand. We track the ACTUAL Mana spent: a
# Hand.events listener on SpendMana(CONTROLLER) accumulates every Mana payment
# the controller makes while this card sits in hand (card plays AND hero-power
# uses, post-discount, including Coin/temporary Mana — exactly what HS counts
# as "Mana spent") onto a per-card `_cata_mana_spent` attribute.
#
# Playing the card itself also fires one SpendMana (its own cost is paid while
# it is still in hand), so `_spent_while_holding` subtracts the card's locked-in
# `_played_cost` to exclude the cost of playing it — the threshold counts Mana
# spent *before* this card, not the Mana that plays it.
#
# The accumulator is per-card-instance and resets when the card leaves hand
# (it's a plain attribute, recreated on a fresh draw), matching "while holding
# this". (A card that pays Health instead of Mana — e.g. War'loc — fires no
# SpendMana; such a card is never in this Druid trio, an accepted edge.)


class _CataSpentWatch(TargetedAction):
    """Accumulate Mana spent by the controller while a 'spent N Mana' card is held."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        source._cata_mana_spent = getattr(source, "_cata_mana_spent", 0) + amount


def _spent_while_holding(card):
    spent = getattr(card, "_cata_mana_spent", 0)
    # Exclude the Mana paid to play THIS card (counted because the payment
    # happens while the card is still in hand).
    own = getattr(card, "_played_cost", 0) or 0
    return max(0, spent - own)


# A reusable Hand.events listener factory: bump the held card's accumulator by
# the actual amount of every Mana payment the controller makes.
_SPENT_HAND_EVENTS = SpendMana(CONTROLLER).after(
    lambda self, player, amount: _CataSpentWatch(SELF, amount) if amount > 0 else None
)


##
# Minions


class CATA_130:
    """Crystalspine Cub"""

    # Whenever you spend your last Mana Crystal, gain +1/+1. Fires each time a
    # Mana payment leaves the controller at 0 Mana (i.e. the spend that empties
    # them) — a real per-spend trigger, not a once-per-turn end-of-turn check.
    events = SpendMana(CONTROLLER).after(
        lambda self, player, amount: Buff(SELF, "CATA_130e")
        if amount > 0 and player.mana == 0
        else None
    )


class CATA_130e:
    "Crystalized"
    # +1/+1 (data enchant ships no stat tags; declare them explicitly).
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class CATA_131:
    """Felwood Treant"""

    # Battlecry: Gain a temporary Mana Crystal. If you spent 4 Mana while
    # holding this, it's permanent.
    def play(self):
        if _spent_while_holding(self) >= 4:
            # Permanent empty Mana Crystal.
            yield GainMana(self.controller, 1)
        else:
            # Temporary (this-turn) Mana Crystal.
            yield ManaThisTurn(self.controller, 1)

    class Hand:
        events = _SPENT_HAND_EVENTS


class CATA_132:
    """Broodwatcher"""

    # Battlecry: Get two 3/3 Whelps with Taunt. If you spent 8 Mana while
    # holding this, summon them.
    def play(self):
        if _spent_while_holding(self) >= 8:
            yield Summon(self.controller, "CATA_132t") * 2
        else:
            yield Give(self.controller, "CATA_132t") * 2

    class Hand:
        events = _SPENT_HAND_EVENTS


class CATA_132t:
    """Emerald Whelp"""

    # Taunt (data token ships no TAUNT tag; declare it explicitly).
    tags = {GameTag.TAUNT: True}


class CATA_133:
    """Iridescent Flitterwing"""

    # Elusive. At the end of your turn, give your other minions +1/+1.
    # Elusive: the data's ELUSIVE tag is on an unmapped id, so restore targeting
    # immunity via the legacy split flags (precedent: EDR_272 Evergreen Stag).
    tags = {
        GameTag.CANT_BE_TARGETED_BY_ABILITIES: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }
    events = OWN_TURN_END.on(Buff(FRIENDLY_MINIONS - SELF, "CATA_133e"))


class CATA_133e:
    "Iridescent Glow"
    # +1/+1 (data enchant carries only TAG_SCRIPT_DATA_NUM; declare stats).
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class CATA_139:
    """Wickerfang"""

    # Colossal +4. After one of Wickerfang's Legs gains stats, this gains them
    # too. Limbs are summoned by the engine Colossal hook. The "Symbiotic"
    # stat-mirror is driven by the legs (see CATA_139t): when a leg buffs
    # itself at end of turn, it also buffs the parent.


class CATA_139e:
    "Symbiotic"
    # Increased Stats (in data; applied by the leg's end-of-turn buff).


class _WickerfangLegGrow(TargetedAction):
    """A Wickerfang's Leg gains +1/+1 at end of turn; mirror the gain onto the
    parent Wickerfang (the body that shares the legs' stat gains)."""

    TARGET = ActionArg()

    def do(self, source, target):
        # Buff the leg itself.
        source.game.cheat_action(source, [Buff(source, "CATA_139te")])
        # Mirror onto the parent Wickerfang, if it's still on the board.
        ctrl = source.controller
        for minion in ctrl.field:
            if minion.id == "CATA_139":
                source.game.cheat_action(source, [Buff(minion, "CATA_139e", atk=1, max_health=1)])
                break


class _CataLeg:
    """Shared body for the four Wickerfang's Leg tokens."""

    events = OWN_TURN_END.on(_WickerfangLegGrow(SELF))


class CATA_139t(_CataLeg):
    """Wickerfang's Leg"""


class CATA_139t2(_CataLeg):
    """Wickerfang's Leg"""


class CATA_139t3(_CataLeg):
    """Wickerfang's Leg"""


class CATA_139t4(_CataLeg):
    """Wickerfang's Leg"""


class CATA_139te:
    "Growing Quick!"
    # +1/+1 (data enchant ships no stat tags; declare them explicitly).
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class _MerithraFillDragons(TargetedAction):
    """Merithra of the Dream - fill the controller's hand with random Dragons.
    If you spent 25 Mana while holding this, they cost (1)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        cheap = _spent_while_holding(source) >= 25
        guard = 0
        while len(ctrl.hand) < ctrl.max_hand_size and guard < 20:
            guard += 1
            before = len(ctrl.hand)
            source.game.cheat_action(source, [Give(ctrl, RandomDragon())])
            if len(ctrl.hand) <= before:
                break
            if cheap:
                card = ctrl.hand[-1]
                source.game.cheat_action(source, [Buff(card, "CATA_140e")])


class CATA_140:
    """Merithra of the Dream"""

    # Battlecry: Fill your hand with random Dragons. If you spent 25 Mana while
    # holding this, they cost (1).
    play = _MerithraFillDragons(SELF)

    class Hand:
        events = _SPENT_HAND_EVENTS


@custom_card
class CATA_140e:
    "Cheap Dragon"
    # Not in data: set-cost-to-(1) enchant for Merithra's discounted Dragons.
    # `cost` script overrides the host's cost (precedent: TIME_705e Eternal).
    tags = {
        GameTag.CARDNAME: "Cheap Dragon",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    cost = lambda self, i: 1


class _UlfarSummon(TargetedAction):
    """Granted deathrattle (CATA_006e) — summon a random minion whose Cost
    equals the dying minion's base Cost. The deathrattle runs with the
    enchantment as source, so the host minion (the one that died) is read off
    its ``owner`` reference."""

    TARGET = ActionArg()

    def do(self, source, target):
        host = getattr(source, "owner", None) or source
        ctrl = host.controller
        cost = host.data.cost or 0
        if len(ctrl.field) < 7:
            source.game.cheat_action(
                source, [Summon(ctrl, RandomMinion(cost=cost))]
            )


class CATA_006:
    """Ulfar"""

    # Battlecry: Give your other minions "Deathrattle: Summon a minion with
    # this minion's Cost." The enchant only exists in data under the CORE_
    # reprint id (CORE_CATA_006e); the script merges onto it via CORE_ stripping.
    play = Buff(FRIENDLY_MINIONS - SELF, "CORE_CATA_006e")


class CATA_006e:
    """Thornspeakers' Spirit"""

    # Granted deathrattle: Summon a minion with this minion's Cost.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = _UlfarSummon(SELF)


##
# Spells


class _WildwoodGiveDeathrattle(TargetedAction):
    """Give each friendly minion 'Deathrattle: Summon a 2/2 Treant.'"""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for minion in list(ctrl.field):
            minion.additional_deathrattles.append((Summon(ctrl, "CATA_134t3"),))
            minion.has_deathrattle = True


class CATA_134:
    """Wildwood Circle"""

    # Shatter. Summon two 2/2 Treants. Give your minions "Deathrattle: Summon a
    # 2/2 Treant." Normally split into CATA_134t / CATA_134t2 when drawn; the
    # parent resolves directly only when the halves RECOMBINE, performing BOTH
    # halves' effects.
    play = (
        Summon(CONTROLLER, "CATA_134t3") * 2,
        _WildwoodGiveDeathrattle(CONTROLLER),
    )


class CATA_134t:
    """Wildwood Circle"""

    # Shattered: Summon two 2/2 Treants.
    play = Summon(CONTROLLER, "CATA_134t3") * 2


class CATA_134t2:
    """Wildwood Circle"""

    # Shattered: Give your minions "Deathrattle: Summon a 2/2 Treant."
    play = _WildwoodGiveDeathrattle(CONTROLLER)


class CATA_134e:
    "Wildwood Aura"
    # Deathrattle: Summon a 2/2 Treant (in data; the deathrattle is granted
    # directly via additional_deathrattles by CATA_134t2).


class CATA_134t3:
    """Treant"""

    # 2/2 vanilla Treant token.


class _MossbindingSummon(TargetedAction):
    """Mossbinding - summon two 1/2 Golems, then spend all remaining Mana to
    give them +1/+1 for each Mana spent."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        golems = []
        for _ in range(2):
            before = len(ctrl.field)
            source.game.cheat_action(source, [Summon(ctrl, "CATA_135t")])
            if len(ctrl.field) > before:
                golems.append(ctrl.field[-1])
        # Spend ALL remaining Mana — including temporary (Coin/Innervate)
        # Mana. `ctrl.mana` already sums the regular pool and temp_mana, so
        # it is the true magnitude of the buff. We must actually consume both
        # pools so `ctrl.mana == 0` afterward (mirrors SpendMana's drain):
        # temporary Mana first, then bump used_mana for the regular remainder.
        spent = ctrl.mana
        if spent > 0:
            remainder = spent
            if ctrl.temp_mana:
                used_temp = min(ctrl.temp_mana, remainder)
                ctrl.temp_mana -= used_temp
                remainder -= used_temp
            ctrl.used_mana = max(ctrl.used_mana + remainder, 0)
            for golem in golems:
                source.game.cheat_action(
                    source, [Buff(golem, "CATA_135e", atk=spent, max_health=spent)]
                )


class CATA_135:
    """Mossbinding"""

    # Summon two 1/2 Golems. Spend all your Mana to give them +1/+1 for each
    # Mana spent.
    play = _MossbindingSummon(CONTROLLER)


class CATA_135e:
    "Moss Shaped"
    # Increased stats (in data; +N/+N applied at cast time).


class CATA_135t:
    """Moss Golem"""

    # 1/2 vanilla Golem token.


class _AzsharaShuffle(TargetedAction):
    """Azshara's Triumph - shuffle 5 random minions costing (8)+ into your deck
    with doubled stats."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db

        ctrl = source.controller
        pool = [
            cid
            for cid, c in db.items()
            if c.collectible
            and c.type == CardType.MINION
            and (c.cost or 0) >= 8
        ]
        if not pool:
            return
        for _ in range(5):
            cid = source.game.random.choice(pool)
            card = ctrl.card(cid, source=source)
            atk = card.atk
            health = card.health
            source.game.cheat_action(source, [Shuffle(ctrl, card)])
            # Double stats: +base atk / +base health.
            source.game.cheat_action(
                source, [Buff(card, "CATA_136e", atk=atk, max_health=health)]
            )


class CATA_136:
    """Azshara's Triumph"""

    # Shuffle 5 random minions into your deck that cost (8) or more. Double
    # their stats.
    play = _AzsharaShuffle(CONTROLLER)


class CATA_136e:
    "Azshara's Triumph"
    # Doubled Attack and Health (in data; +base/+base applied at shuffle time).


class CATA_138:
    """Forest's Gift"""

    # Give a friendly minion +1/+1 for each minion you control.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "CATA_138e", atk=Count(FRIENDLY_MINIONS), max_health=Count(FRIENDLY_MINIONS))


class CATA_138e:
    "Tree Hugged"
    # Increased stats (in data; +N/+N applied at cast time).
