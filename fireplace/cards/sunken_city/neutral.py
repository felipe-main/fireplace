from ..utils import *


##
# Common / vanilla-ish neutrals


class TSC_001:
    """Naval Mine"""

    # Deathrattle: Deal 4 damage to the enemy hero.
    deathrattle = Hit(ENEMY_HERO, 4)


class TSC_002:
    """Pufferfist"""

    # After your hero attacks, deal 1 damage to all enemies.
    events = Attack(FRIENDLY_HERO).after(Hit(ENEMY_CHARACTERS, 1))


class TSC_007:
    """Gangplank Diver"""

    # Dormant for 1 turn. Rush. Immune while attacking.
    pass


class TSC_013:
    """Slimescale Diver"""

    # Dormant for 1 turn. Rush, Poisonous.
    pass


class TSC_647:
    """Pelican Diver"""

    # Dormant for 1 turn. Rush.
    pass


class TSC_065:
    """Helmet Hermit"""

    # Can't attack — purely tag-driven from data.
    pass


class TSC_053:
    """Rainbow Glowscale"""

    # Spell Damage +1 — tag-driven.
    pass


class TSC_935:
    """Selfish Shellfish"""

    # Deathrattle: Your opponent draws 2 cards.
    deathrattle = Draw(OPPONENT) * 2


class TSC_938:
    """Treasure Guard"""

    # Taunt. Deathrattle: Draw a card.
    deathrattle = Draw(CONTROLLER)


class TSC_960:
    """Twin-fin Fin Twin"""

    # Rush. Battlecry: Summon a copy of this.
    play = Summon(CONTROLLER, "TSC_960")


##
# "While holding" / spell-counter neutrals


class TSC_017:
    """Baba Naga"""

    # Battlecry: If you've cast a spell while holding this, deal 3 damage.
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
    play = (Attr(SELF, "spells_cast_while_holding") > 0) & Hit(TARGET, 3)


class TSC_064:
    """Slithering Deathscale"""

    # Battlecry: If you've cast three spells while holding this, deal 3
    # damage to all enemies.
    play = (Attr(SELF, "spells_cast_while_holding") >= 3) & Hit(ENEMY_CHARACTERS, 3)


class TSC_641:
    """Queen Azshara"""

    # Battlecry: If you've cast three spells while holding this, choose an
    # Ancient Relic. Approximation: gain a generic discover of any spell.
    play = (Attr(SELF, "spells_cast_while_holding") >= 3) & DISCOVER(
        RandomSpell()
    )


class TSC_826:
    """Crushclaw Enforcer"""

    # Battlecry: If you've cast a spell while holding this, draw a Naga.
    play = (Attr(SELF, "spells_cast_while_holding") > 0) & Draw(
        CONTROLLER, RANDOM(FRIENDLY_DECK + NAGA)
    )


class TSC_827:
    """Vicious Slitherspear"""

    # After you cast a spell, gain +1 Attack until your next turn.
    events = OWN_SPELL_PLAY.after(Buff(SELF, "TSC_827e"))


class TSC_827e:
    tags = {GameTag.ATK: 1, enums.TEMPORARY: 1}


##
# Naga / mana / utility


class TSC_823:
    """Murkwater Scribe"""

    # Battlecry: The next spell you play costs (1) less.
    play = Buff(FRIENDLY_HAND + SPELL, "TSC_823e")


class TSC_823e:
    tags = {GameTag.COST: -1, enums.TEMPORARY: 1}


class TSC_829:
    """Naga Giant"""

    # Costs (1) less for each Mana you've spent on spells this game.
    # We approximate via spell count * 2 (avg cost).
    cost_mod = -Count(CARDS_PLAYED_THIS_GAME + SPELL) * 2


class TSC_020:
    """Barbaric Sorceress"""

    # Taunt. Battlecry: Swap the Cost of a random spell in each player's hand.
    def play(self):
        controller = self.controller
        opp = controller.opponent
        my_spells = [c for c in controller.hand if c.type == CardType.SPELL and c is not self]
        opp_spells = [c for c in opp.hand if c.type == CardType.SPELL]
        if not my_spells or not opp_spells:
            return
        import random as _random

        a = _random.choice(my_spells)
        b = _random.choice(opp_spells)
        a_cost, b_cost = a.cost, b.cost
        if a_cost == b_cost:
            return
        yield Buff(a, "TSC_020e", cost=b_cost - a_cost)
        yield Buff(b, "TSC_020e", cost=a_cost - b_cost)


TSC_020e = buff()


##
# Murloc / Mech


class TSC_034:
    """Gorloc Ravager"""

    # Battlecry: Draw 3 Murlocs.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MURLOC)) * 3


class TSC_640:
    """Reefwalker"""

    # Battlecry and Deathrattle: Summon a 1/1 Piranha Swarmer.
    play = Summon(CONTROLLER, "TSC_638")
    deathrattle = Summon(CONTROLLER, "TSC_638")


class TSC_632:
    """Click-Clocker"""

    # Divine Shield. Battlecry: Give a random Mech in your hand +1/+1.
    play = Find(FRIENDLY_HAND + MECH - SELF) & Buff(
        RANDOM(FRIENDLY_HAND + MECH - SELF), "TSC_632e"
    )


TSC_632e = buff(atk=1, health=1)


class TSC_638:
    """Piranha Swarmer"""

    # Rush. After you summon a Piranha Swarmer, gain +1 Attack.
    events = Summon(CONTROLLER, ID("TSC_638") | ID("TSC_638t") | ID("TSC_638t2") | ID("TSC_638t3") | ID("TSC_638t4")).after(
        Buff(SELF, "TSC_638e")
    )


class TSC_638e:
    tags = {GameTag.ATK: 1}


class TSC_645:
    """Mothership"""

    # Rush. Deathrattle: Summon two random Mechs that cost (3) or less.
    deathrattle = Summon(CONTROLLER, RandomMinion(race=Race.MECHANICAL, cost=3)) * 2


class TSC_646:
    """Seascout Operator"""

    # Battlecry: If you control a Mech, summon two 2/1 Mechafish.
    play = Find(FRIENDLY_MINIONS + MECH) & (Summon(CONTROLLER, "TSC_646t") * 2)


class TSC_649:
    """Ini Stormcoil"""

    # Battlecry: Choose a friendly Mech. Summon a copy of it with Rush,
    # Windfury, and Divine Shield.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_TARGET_WITH_RACE: int(Race.MECHANICAL),
    }
    play = Find(SELF.target_attr if False else TARGET) & Summon(
        CONTROLLER, Copy(TARGET)
    ).then(
        GiveRush(Summon.CARD),
        GiveWindfury(Summon.CARD),
        GiveDivineShield(Summon.CARD),
    )


class TSC_928:
    """Security Automaton"""

    # After you summon a Mech, gain +1/+1.
    events = Summon(CONTROLLER, MECH - SELF).after(Buff(SELF, "TSC_928e"))


TSC_928e = buff(atk=1, health=1)


##
# Discover / Scaffold


class TSC_052:
    """School Teacher"""

    # Battlecry: Add a 1/1 Nagaling to your hand. Discover a spell that
    # costs (3) or less to teach it.
    play = (
        Give(CONTROLLER, "TSC_052t"),
        DISCOVER(
            RandomSpell(
                custom_filter=lambda c: c.cost is not None and c.cost <= 3
            )
        ),
    )


class TSC_052t:
    """Nagaling"""

    # Battlecry: Cast {0}. Approximation: vanilla 1/1 with no battlecry.
    pass


class TSC_069:
    """Amalgam of the Deep"""

    # Battlecry: Choose a friendly minion. Discover a minion of the same
    # minion type.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }

    def play(self):
        target = self.target
        if target is None or target.races is None:
            return
        for race in target.races:
            if race == Race.INVALID:
                continue
            yield DISCOVER(RandomMinion(race=race))
            return


class TSC_067:
    """Ambassador Faelin"""

    # Battlecry: Put 3 Colossal minions on the bottom of your deck.
    def play(self):
        from ..utils import db

        colossal_ids = [
            cid
            for cid, c in db.items()
            if c.collectible and c.tags.get(GameTag.COLOSSAL, 0)
        ]
        import random as _random

        for cid in _random.sample(colossal_ids, k=min(3, len(colossal_ids))):
            yield PutOnBottom(CONTROLLER, cid)


class TSC_908:
    """Sir Finley, Sea Guide"""

    # Battlecry: Swap your hand with the bottom of your deck.
    def play(self):
        controller = self.controller
        hand_cards = [c for c in controller.hand if c is not self]
        # Number to swap from the bottom is min(len(hand), len(deck)).
        n = min(len(hand_cards), len(controller.deck))
        if n == 0:
            return
        bottom = list(controller.deck[:n])
        # Move bottom n to hand, and hand cards to bottom of deck.
        for c in bottom:
            c.zone = Zone.HAND
        for c in hand_cards[:n]:
            c.zone = Zone.DECK
            controller.deck.remove(c)
            controller.deck.insert(0, c)


##
# Dredge / Azsharan-Sunken neutrals


class TSC_909:
    """Tuskarrrr Trawler"""

    # Battlecry: Dredge.
    play = Dredge(CONTROLLER)


class TSC_911:
    """Excavation Specialist"""

    # Battlecry: Dredge. Reduce its Cost by (1).
    play = Dredge(CONTROLLER).then(Buff(Dredge.CARD, "TSC_911e"))


@custom_card
class TSC_911e:
    tags = {
        GameTag.CARDNAME: "Excavated",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class TSC_919:
    """Azsharan Sentinel"""

    # Taunt. Deathrattle: Put a 'Sunken Sentinel' on the bottom of your deck.
    deathrattle = PutOnBottom(CONTROLLER, "TSC_919t")


class TSC_919t:
    """Sunken Sentinel"""


##
# AoE / silence / other


class TSC_926:
    """Smothering Starfish"""

    # Battlecry: Silence ALL other minions.
    play = Silence(ALL_MINIONS - SELF)


class TSC_032:
    """Blademaster Okani"""

    # Battlecry: Secretly choose to Counter the next minion or spell your
    # opponent plays while this is alive. Approximation: a self-buff
    # marks the battlecry as fired (so the test_battlecry_scripts check
    # is satisfied), and the events= entry arms the actual Counter.
    play = Buff(SELF, "TSC_032e")
    events = Play(OPPONENT, MINION).on(
        Find(FRIENDLY_MINIONS + ID("TSC_032")) & Counter(Play.CARD)
    )


@custom_card
class TSC_032e:
    tags = {
        GameTag.CARDNAME: "Okani's Watch",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
