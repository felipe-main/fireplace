from ..utils import *


##
# Minions


class AV_210:
    """Pathmaker"""

    # [x]<b>Battlecry:</b> Cast the other choice from the last <b>Choose
    # One</b> spell you've cast.
    def play(self):
        player = self.controller
        parent_id = player.last_choose_one_parent_id
        chosen_id = player.last_choose_one_chosen_id
        if not parent_id or not chosen_id:
            return
        parent = db.get(parent_id)
        if parent is None:
            return
        # The parent's choose_cards is a list of card-id strings in data.
        for sub_id in getattr(parent, "choose_cards", []):
            if sub_id != chosen_id:
                yield CastSpell(sub_id)
                return


class AV_211:
    """Dire Frostwolf"""

    # <b>Stealth</b> <b>Deathrattle:</b> Summon a 2/2 Wolf with <b>Stealth</b>.
    deathrattle = Summon(CONTROLLER, "AV_211t")


class AV_291:
    """Frostsaber Matriarch"""

    # [x]<b>Taunt</b>. Costs (1) less for each Beast you've _summoned this
    # game.
    cost_mod = -Count(CARDS_PLAYED_THIS_GAME + BEAST + MINION)


class AV_293:
    """Wing Commander Mulverick"""

    # [x]<b>Rush</b>. Your minions have "<b>Honorable Kill:</b> Summon a_ 2/2
    # Wyvern with <b>Rush</b>."
    update = Refresh(FRIENDLY_MINIONS, buff="AV_293e")


class AV_293e:
    tags = {GameTag.HONORABLE_KILL: True}
    honorable_kill = Summon(CONTROLLER, "AV_293t")


class AV_294:
    """Clawfury Adept"""

    # <b>Battlecry:</b> Give all other friendly characters +1 Attack this turn.
    play = Buff(FRIENDLY_CHARACTERS - SELF, "AV_294e")


class AV_294e:
    tags = {GameTag.ATK: 1, enums.TEMPORARY: 1}


class AV_296:
    """Pride Seeker"""

    # [x]<b>Battlecry:</b> Your next <b>Choose One</b> card costs (2) less.
    play = IncreaseAttr(CONTROLLER, "next_choose_one_discount", 2)


##
# Spells


class AV_292:
    """Heart of the Wild"""

    # Give a minion +2/+2, then give your Beasts +1/+1.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "AV_292e"), Buff(FRIENDLY_MINIONS + BEAST, "AV_292e2")


AV_292e = buff(atk=2, health=2)
AV_292e2 = buff(atk=1, health=1)


class AV_295:
    """Capture Coldtooth Mine"""

    # <b>Choose One -</b> Draw your lowest Cost card; or Draw your highest Cost
    # card.
    play = (
        ForceDraw(LOWEST_COST(FRIENDLY_DECK)),
        ForceDraw(HIGHEST_COST(FRIENDLY_DECK)),
    )


class AV_360:
    """Frostwolf Kennels"""

    # [x]At the end of your turn, summon a 2/2 Wolf with <b>Stealth</b>. Lasts
    # 3 turns.
    events = OWN_TURN_END.on(Summon(CONTROLLER, "AV_211t"))


##
# Heros


class AV_205:
    """Wildheart Guff"""

    # [x]<b>Battlecry:</b> Set your maximum Mana to 20. Gain a Mana Crystal.
    # Draw a card.
    play = (
        IncreaseAttr(CONTROLLER, "max_resources", 10),
        GainMana(CONTROLLER, 1),
        Draw(CONTROLLER),
    )
