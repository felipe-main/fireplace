from ..utils import *


##
# Custom actions


class _AnnounceDarkness(TargetedAction):
    """Announce Darkness — replace every non-Warlock card in your hand with a
    random Warlock card of the same type, each costing (1) less, and replace
    your Hero Power with the Warlock one (Life Tap)."""

    TARGET = ActionArg()

    def do(self, source, target):
        import random
        from hearthstone.enums import CardClass, CardType

        ctrl = source.controller
        game = source.game

        # Replace the Hero Power with Life Tap (Warlock basic hero power).
        if getattr(ctrl.hero, "power", None) is None or ctrl.hero.power.id != "HERO_07bp":
            game.cheat_action(source, [Summon(ctrl, "HERO_07bp")])

        # Map CardType -> pool of collectible Warlock card ids.
        type_pools = {}

        def pool_for(card_type):
            if card_type not in type_pools:
                ids = db.filter(
                    collectible=True, card_class=CardClass.WARLOCK, type=card_type
                )
                type_pools[card_type] = list(ids)
            return type_pools[card_type]

        # Cards already Warlock are left untouched; everything else is morphed
        # into a random Warlock card of the same type. Track the untouched
        # cards by identity so the cost enchant lands on exactly the
        # replacements during the rescan below — even when a replacement is a
        # self-ranking token (e.g. Imp Swarm) whose hand entity differs from
        # the immediate Morph result, which would slip past a `card.morphed`
        # check. Snapshot the hand first — morphing mutates it as we go.
        untouched = set()
        for card in list(ctrl.hand):
            classes = getattr(card, "classes", None) or [card.card_class]
            if CardClass.WARLOCK in classes:
                untouched.add(id(card))
                continue
            pool = pool_for(card.type)
            if not pool:
                untouched.add(id(card))
                continue
            new_id = random.choice(pool)
            game.cheat_action(source, [Morph(card, new_id)])

        # Stamp the (1)-less enchant on every replacement now in hand.
        for card in list(ctrl.hand):
            if id(card) in untouched:
                continue
            if any(buff.id == "VAC_941e" for buff in card.buffs):
                continue
            game.cheat_action(source, [Buff(card, "VAC_941e")])


##
# Minions


class VAC_503:
    """Summoner Darkmarrow"""

    # Death Knight Tourist. Your Deathrattles trigger twice. After you play a
    # Deathrattle minion, destroy it. (Tourist is deckbuilding-only — no
    # in-game trigger.)
    update = Refresh(CONTROLLER, {GameTag.EXTRA_DEATHRATTLES: True})
    events = Play(CONTROLLER, MINION + DEATHRATTLE).after(Destroy(Play.CARD))


class VAC_503e:
    """Darkmarrow Deathrattles"""

    # Your Deathrattles trigger twice. (Cosmetic enchant in data.)


class VAC_940:
    """Party Fiend"""

    # Battlecry: Summon two 1/1 Felbeasts. Deal 3 damage to your hero.
    play = Summon(CONTROLLER, "VAC_940t") * 2, Hit(FRIENDLY_HERO, 3)


class VAC_940t:
    """Felbeast"""

    # Vanilla 1/1 token.


class VAC_942:
    """Fearless Flamejuggler"""

    # Battlecry: Gain stats equal to the damage your hero has taken this turn.
    def custom_cardtext(self):
        text = self.data.description.split("@")[0]
        return text

    def cardtext_entity_0(self):
        return getattr(self.controller.hero, "damaged_this_turn", 0)

    tags = {
        enums.CUSTOM_CARDTEXT: custom_cardtext,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }

    play = Buff(
        SELF,
        "VAC_942e",
        atk=Attr(FRIENDLY_HERO, "damaged_this_turn"),
        max_health=Attr(FRIENDLY_HERO, "damaged_this_turn"),
    )


class VAC_942e:
    """Hectic Plans"""

    # Increased stats. (Dynamic atk/health supplied at Buff time.)


class VAC_943:
    """Sacrificial Imp"""

    # Deathrattle: If it's your turn, summon a 6/6 Imp with Taunt.
    deathrattle = (Attr(CONTROLLER, GameTag.CURRENT_PLAYER) == 1) & Summon(
        CONTROLLER, "VAC_943t"
    )


class VAC_943t:
    """Monstrous Imp"""

    # 6/6 Taunt token (Taunt in data).


class VAC_945(ThreeSpellsProgressUtils):
    """Party Planner Vona"""

    # Battlecry: If you've taken 8 damage on your turns, summon Ourobos.
    progress_target = 8

    def custom_cardtext(self):
        segments = self.data.description.split("@")
        if len(segments) < 3:
            return self.data.description
        count = getattr(self.controller, "damage_taken_on_own_turns_this_game", 0)
        if count >= 8:
            return segments[0] + segments[2]
        return segments[0] + segments[1]

    def cardtext_entity_0(self):
        count = getattr(self.controller, "damage_taken_on_own_turns_this_game", 0)
        return max(0, 8 - count)

    tags = {
        enums.CUSTOM_CARDTEXT: custom_cardtext,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }

    play = (Attr(CONTROLLER, "damage_taken_on_own_turns_this_game") >= 8) & Summon(
        CONTROLLER, "VAC_945t"
    )


class VAC_945e:
    """Necessary Expenditures"""

    # Deathrattle: Summon Ourobos, World Serpent.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Summon(CONTROLLER, "VAC_945t")


class VAC_945t:
    """Ourobos, World Serpent"""

    # Taunt. Deathrattle: Give a minion in your hand "Deathrattle: Summon
    # Ourobos." (Taunt + Deathrattle flag in data.)
    deathrattle = Find(FRIENDLY_HAND + MINION) & Buff(
        RANDOM(FRIENDLY_HAND + MINION), "VAC_945e"
    )


##
# Spells


class VAC_939:
    """Eat! The! Imp!"""

    # Destroy a friendly minion to draw 3 cards.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = Destroy(TARGET), Draw(CONTROLLER) * 3


class VAC_941:
    """Announce Darkness"""

    # Replace your Hero Power and non-Warlock cards with Warlock ones. They
    # cost (1) less.
    play = _AnnounceDarkness(SELF)


class VAC_941e:
    """Announce Darkness Ench"""

    # Costs (1) less.
    tags = {GameTag.COST: -1}


class VAC_944:
    """Cursed Souvenir"""

    # Give a minion +3/+3 and "At the start of your turn, deal 3 damage to
    # your hero."
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "VAC_944e")


class VAC_944e:
    """Cursed Souvenir"""

    # +3/+3 and "At the start of your turn, deal 3 damage to your hero."
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}
    events = OWN_TURN_BEGIN.on(Hit(FRIENDLY_HERO, 3))


class VAC_951:
    "\"Health\" Drink"

    # Lifesteal. Deal $3 damage to a minion. (3 Drinks left!)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3), Give(CONTROLLER, "VAC_951t")


class VAC_951t:
    "\"Health\" Drink"

    # Lifesteal. Deal $3 damage to a minion. (2 Drinks left!)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3), Give(CONTROLLER, "VAC_951t2")


class VAC_951t2:
    "\"Health\" Drink"

    # Lifesteal. Deal $3 damage to a minion. (Last Drink!)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3)


class VAC_952:
    """Felfire Bonfire"""

    # Deal $4 damage to a minion. If it dies, your next Deathrattle minion
    # costs (3) less.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 4), (Dead(TARGET) & Buff(FRIENDLY_HERO, "VAC_952e"))


class VAC_952e:
    """Ample Offering"""

    # Your next Deathrattle minion costs (3) less. Tracker on the hero: it
    # discounts Deathrattle minions in hand, then removes itself once one is
    # played.
    update = Refresh(FRIENDLY_HAND + DEATHRATTLE + MINION, buff="VAC_952e2")
    events = Play(CONTROLLER, DEATHRATTLE + MINION).on(Destroy(SELF))


class VAC_952e2:
    """Offering Accepted"""

    # Costs (3) less.
    tags = {GameTag.COST: -3}
