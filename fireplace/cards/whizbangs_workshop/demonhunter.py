from ..utils import *


##
# Custom actions / helpers


class _WorkshopMishapHit(TargetedAction):
    """Workshop Mishap — deal 5 damage to a minion; any excess (damage beyond
    the target's current Health) is dealt to BOTH of its neighbours.

    HitExcessDamage only feeds the leftover into a single 'other' target, so we
    compute the excess ourselves: snapshot the target's neighbours before it can
    die, hit the target for the full amount, then hit each neighbour for the
    overflow (full_amount - pre_hit_health, clamped at 0). Spell Damage is
    folded in via the source's get_damage so +Spell Damage scales all of it."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        if isinstance(target, list):
            target = target[0] if target else None
        if target is None:
            return
        amount = source.get_damage(amount, target)
        # Snapshot neighbours and the target's pre-hit Health.
        neighbours = list(target.adjacent_minions)
        pre_health = target.health
        excess = amount - pre_health
        source.game.cheat_action(source, [Hit(target, amount)])
        if excess > 0 and neighbours:
            for n in neighbours:
                source.game.cheat_action(source, [Hit(n, excess)])


class _WindowShopperSetStats(TargetedAction):
    """Window Shopper — after Discovering a Demon, set the discovered card's
    Attack, Health and Cost to this minion's current values. Snapshot the
    Window Shopper's live stats and stamp them onto the freshly-given card via
    TOY_652e (Literally Me)."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        # SET (not add) the picked card's stats to Window Shopper's snapshot.
        # Stash the values on the enchant instance and read them via lambdas
        # (the Buff kwarg form ADDS and can't take a callable).
        buff = source.controller.card("TOY_652e", source=source)
        buff.source = source
        buff._xatk = source.atk
        buff._xhealth = source.health
        buff._xcost = source.cost
        buff.apply(card)


class TOY_652e:
    # "Literally Me" — set the discovered card's Attack/Health/Cost to Window
    # Shopper's snapshotted values.
    atk = lambda self, _: self._xatk
    max_health = lambda self, _: self._xhealth
    cost = lambda self, _: self._xcost


##
# Minions


class TOY_028:
    """Spirit of the Team"""

    # Stealth for 1 turn. Your hero has +2 Attack on your turn.
    # STEALTH is in data; "for 1 turn" = drop Stealth at the start of your turn.
    # The +2 Attack is a turn-gated aura on your hero (only while it's your turn).
    events = OWN_TURN_BEGIN.on(Unstealth(SELF))
    update = Find(CURRENT_PLAYER + CONTROLLER) & Refresh(FRIENDLY_HERO, buff="TOY_028e")


TOY_028e = buff(atk=2)


class TOY_642:
    """Ball Hog"""

    # Lifesteal. Battlecry and Deathrattle: Deal 3 damage to the lowest Health
    # enemy. LIFESTEAL is in data. The battlecry/deathrattle both deal 3 to the
    # lowest-Health enemy character.
    play = Hit(LOWEST_HEALTH(ENEMY_CHARACTERS), 3)
    deathrattle = Hit(LOWEST_HEALTH(ENEMY_CHARACTERS), 3)


class TOY_647:
    """Magtheridon, Unreleased"""

    # Dormant for 2 turns. While Dormant, deal 3 damage to all enemies at the
    # end of your turn. Timer-based dormancy: awakens automatically after the
    # 2-turn timer; while dormant it dings every enemy for 3 at end of turn.
    tags = {GameTag.DORMANT: True}
    dormant_turns = 2
    dormant_events = OWN_TURN_END.on(Hit(ENEMY_CHARACTERS, 3))


class TOY_652:
    """Window Shopper"""

    # Miniaturize. Battlecry: Discover a Demon. Set its stats and Cost to this
    # minion's. The paired Mini token (TOY_652t) is added automatically by the
    # engine on play — we only implement the Discover + set-stats battlecry.
    play = Discover(CONTROLLER, RandomDemon()).then(
        Give(CONTROLLER, Discover.CARD),
        _WindowShopperSetStats(SELF, Give.CARD),
    )


class TOY_652t:
    """Window Shopper"""

    # Mini. Battlecry: Discover a Demon. Set its stats and Cost to this minion's.
    # Identical script to the full card; this 1/1 stamps 1/1/1 onto the pick.
    play = Discover(CONTROLLER, RandomDemon()).then(
        Give(CONTROLLER, Discover.CARD),
        _WindowShopperSetStats(SELF, Give.CARD),
    )


class TOY_913:
    """Ci'Cigi"""

    # Deathrattle: Get 3 random first-edition Demon Hunter cards (in mint
    # condition). "first-edition" is the load-bearing restriction: the original
    # Demon Hunter pool — Ashes of Outland (BLACK_TEMPLE) + Demon Hunter
    # Initiate. "in mint condition" is flavour. is_standard=False so the wild
    # first-edition sets aren't filtered out in Standard games.
    deathrattle = Give(
        CONTROLLER,
        RandomCard(
            collectible=True,
            card_class=CardClass.DEMONHUNTER,
            card_set=[CardSet.BLACK_TEMPLE, CardSet.DEMON_HUNTER_INITIATE],
            is_standard=False,
        ),
    ) * 3


##
# Spells


class TOY_640:
    """Workshop Mishap"""

    # Deal $5 damage to a minion. Excess damages both neighbors.
    # Outcast: Gain Lifesteal.
    # Outcast replaces play when this is the left/right-most card in hand —
    # there we grant the spell Lifesteal first (so the 5 + overflow all heals),
    # then run the same damage. The base play does the damage without lifesteal.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _WorkshopMishapHit(TARGET, 5)
    outcast = GiveLifesteal(SELF), _WorkshopMishapHit(TARGET, 5)


class TOY_643:
    """Blind Box"""

    # Get 2 random Demons. Outcast: Discover them instead.
    # Base play hands 2 random Demons; Outcast replaces it with two Discovers.
    play = Give(CONTROLLER, RandomDemon()) * 2
    outcast = DISCOVER(RandomDemon()) * 2


class TOY_644:
    """Red Card"""

    # Make a minion go Dormant for 2 turns.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Dormant(TARGET, 2)


class TOY_645:
    """Lesser Opal Spellstone"""

    # Draw 1 card. (Attack with your hero 4 times to upgrade.)
    # AddProgress(SELF, SELF) ticks +1 per FRIENDLY_HERO attack, so the upgrade
    # threshold is the printed 4 hero attacks.
    play = Draw(CONTROLLER)
    progress_total = 4
    reward = Morph(SELF, "TOY_645t")

    class Hand:
        events = Attack(FRIENDLY_HERO).after(AddProgress(SELF, SELF))


class TOY_645t:
    """Opal Spellstone"""

    # Draw 2 cards. (Attack with your hero 4 times to upgrade.)
    play = Draw(CONTROLLER) * 2
    progress_total = 4
    reward = Morph(SELF, "TOY_645t1")

    class Hand:
        events = Attack(FRIENDLY_HERO).after(AddProgress(SELF, SELF))


class TOY_645t1:
    """Greater Opal Spellstone"""

    # Draw 3 cards.
    play = Draw(CONTROLLER) * 3


##
# Weapons


class TOY_641:
    """Umpire's Grasp"""

    # Deathrattle: Draw a Demon and reduce its Cost by (2).
    deathrattle = Find(FRIENDLY_DECK + DEMON) & ForceDraw(
        RANDOM(FRIENDLY_DECK + DEMON)
    ).then(Buff(ForceDraw.TARGET, "TOY_641e"))


class TOY_641e:
    # In-data "Game Time!" — the (2)-cost reduction stamp for the drawn Demon.
    # The COST value isn't parsed from data, so declare it here.
    tags = {GameTag.COST: -2}
