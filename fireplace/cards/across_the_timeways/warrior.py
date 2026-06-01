from ..utils import *


# Blood Fighter token ids (Lo'Gosh + Broll + Valeera). Used to find a
# "Blood Fighter" in hand for the Lo'Gosh family of deathrattles.
BLOOD_FIGHTERS = ["TIME_850", "TIME_850t", "TIME_850t1"]


class _FillEnemyBoard(TargetedAction):
    """Undefeated Champion — fill the opponent's board with random
    1-Cost minions until it is full."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        while len(opp.field) < source.game.MAX_MINIONS_ON_FIELD:
            pick = RandomMinion(cost=1, is_standard=True).evaluate(source)
            if not pick:
                pick = RandomMinion(cost=1).evaluate(source)
            if not pick:
                break
            source.game.cheat_action(source, [Summon(opp, pick)])


##
# Minions


class TIME_034:
    "Stadium Announcer"
    # Rewind Battlecry: Both players equip a random weapon. Give yours +1/+1.
    play = (
        Summon(CONTROLLER, RandomWeapon()).then(Buff(Summon.CARD, "TIME_034e")),
        Summon(OPPONENT, RandomWeapon()),
    )


class TIME_034e:
    "Upper Hand"
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TIME_714:
    "Chrono-Lord Epoch"
    # Battlecry: Destroy all minions that your opponent played last turn.
    play = Destroy(ENEMY_MINIONS + CARDS_OPPONENT_PLAYED_LAST_TURN)


class TIME_850:
    "Lo'Gosh, Blood Fighter"
    # Fabled, Rush. Deathrattle: Summon a Blood Fighter from your hand.
    # It gains +5/+5 and attacks a random enemy.
    deathrattle = Summon(
        CONTROLLER, RANDOM(FRIENDLY_HAND + IDS(BLOOD_FIGHTERS))
    ).then(
        Buff(Summon.CARD, "TIME_850e"),
        Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER),
    )


class TIME_850e:
    "Crimson Blood"
    tags = {GameTag.ATK: 5, GameTag.HEALTH: 5}


class TIME_850t:
    "Broll, Blood Fighter"
    # Taunt. Deathrattle: Summon a Blood Fighter from your hand. Give it
    # +5/+5 and Taunt.
    deathrattle = Summon(
        CONTROLLER, RANDOM(FRIENDLY_HAND + IDS(BLOOD_FIGHTERS))
    ).then(
        Buff(Summon.CARD, "TIME_850e"),
        Taunt(Summon.CARD),
    )


class TIME_850t1:
    "Valeera, Blood Fighter"
    # Elusive. Deathrattle: Summon a Blood Fighter from your hand. Give it
    # +5/+5 and Elusive.
    # ELUSIVE is in data only as the unmapped tag 1211, so the targeting
    # code never sees it — restore it via the functional split flags.
    tags = {
        GameTag.CANT_BE_TARGETED_BY_ABILITIES: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }
    deathrattle = Summon(
        CONTROLLER, RANDOM(FRIENDLY_HAND + IDS(BLOOD_FIGHTERS))
    ).then(
        Buff(Summon.CARD, "TIME_850e"),
        SetTags(
            Summon.CARD,
            (
                GameTag.CANT_BE_TARGETED_BY_ABILITIES,
                GameTag.CANT_BE_TARGETED_BY_HERO_POWERS,
            ),
        ),
    )


class TIME_871:
    "Heir of Hereafter"
    # Taunt. Battlecry: Gain +2/+2 for each damaged minion.
    play = Buff(SELF, "TIME_871e") * Count(ALL_MINIONS + DAMAGED)


class TIME_871e:
    "Bloodthirsty"
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class TIME_872:
    "Undefeated Champion"
    # Rush. Battlecry: Fill your opponent's board with random 1-Cost minions.
    play = _FillEnemyBoard(CONTROLLER)


##
# Spells


class TIME_715:
    "For Glory!"
    # Draw 2 cards. Costs (1) less for each minion your opponent controls.
    play = Draw(CONTROLLER) * 2
    cost_mod = -Count(ENEMY_MINIONS)


class TIME_716:
    "Slow Motion"
    # Your opponent's cards cost (1) more next turn. Aura enchant placed on
    # the opponent. Buff keeps the *caster's* controller, so ENEMY_HAND (=
    # the opponent's hand) is the right selector. The aura covers cards the
    # opponent draws next turn too, and self-destructs at the caster's next
    # turn begin — i.e. after the opponent's full next turn has elapsed.
    play = Buff(OPPONENT, "TIME_716e3")


class TIME_716e3:
    "Slowed Down"
    update = Refresh(ENEMY_HAND, {GameTag.COST: 1})
    events = OWN_TURN_BEGIN.on(Destroy(SELF))


class TIME_716e:
    "Sloooowwedd Dooowwwnnn"
    tags = {GameTag.COST: 1}


class TIME_750:
    "Precursory Strike"
    # Deal 3 damage. If you're holding a minion that costs (5) or more,
    # draw a minion.
    play = (
        Hit(TARGET, 3),
        Find(FRIENDLY_HAND + MINION + (COST >= 5))
        & Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION)),
    )
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}


class TIME_870:
    "Gladiatorial Combat"
    # Summon a random minion from your deck. Summon a 5/5 Tiger with
    # Stealth for your opponent.
    play = (
        RECRUIT,
        Summon(OPPONENT, "TIME_870t"),
    )


class TIME_870t:
    "Coliseum Tiger"
    # Stealth (vanilla beast token).


class TIME_873:
    "Unleash the Crocolisks"
    # Gain 10 Armor. Summon two 2/3 Beasts for your opponent.
    play = (
        GainArmor(FRIENDLY_HERO, 10),
        Summon(OPPONENT, "TIME_873t") * 2,
    )


class TIME_873t:
    "Coliseum Crocolisk"
    # Vanilla 2/3 beast token.


##
# Across the Timeways — End Time mini-set (END_)


class END_021:
    "Dimensional Weaponsmith"
    # Battlecry: Give all minions and weapons in your hand +2 Attack.
    play = Buff(FRIENDLY_HAND + (MINION | WEAPON), "END_021e")


class END_021e:
    "Cutting Edge"
    # Data enchant carries no stat tags — supply the printed +2 Attack.
    tags = {GameTag.ATK: 2}
