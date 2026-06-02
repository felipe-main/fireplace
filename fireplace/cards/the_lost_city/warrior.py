from ..utils import *


##
# Weapons


class TLC_478:
    """Axe of the Forefathers"""

    # After your hero attacks, deal 1 damage to all minions.
    events = Attack(FRIENDLY_HERO).after(Hit(ALL_MINIONS, 1))


##
# Minions


class TLC_600:
    """Windpeak Wyrm"""

    # Battlecry: Deal 5 damage and gain 5 Armor.
    # Kindred: Costs (3) less. (Dragon — active if you played a Dragon last turn.)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 5), GainArmor(FRIENDLY_HERO, 5)
    cost_mod = -KindredCost(3)


class TLC_606:
    """Latorvian Armorer"""

    # Battlecry: Deal 2 damage to an enemy minion. If it dies, gain 5 Armor.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = Hit(TARGET, 2), Dead(TARGET) & GainArmor(FRIENDLY_HERO, 5)


class TLC_623:
    """Stonecarver"""

    # At the end of your turn, give a random friendly damaged minion +2/+2.
    events = OWN_TURN_END.on(
        Buff(RANDOM(FRIENDLY_MINIONS + DAMAGED), "TLC_623e")
    )


# Stonecarver buff — +2/+2.
TLC_623e = buff(atk=2, health=2)


class _FullHealthExactCopy(ExactCopy):
    """ExactCopy (buffs/enchantments preserved) but the copy spawns at FULL
    health — "Summon a copy" does not transfer the original's current damage."""

    def copy(self, source, entity):
        ret = super().copy(source, entity)
        ret.damage = 0
        return ret


class TLC_624:
    """Nablya, the Watcher"""

    # Battlecry: Summon copies of your damaged minions. Give the copies Rush.
    play = Summon(
        CONTROLLER, _FullHealthExactCopy(FRIENDLY_MINIONS + DAMAGED - SELF)
    ).then(SetTags(Summon.CARD, {GameTag.RUSH: True}))


##
# Spells


class _ShellnadoSpend(TargetedAction):
    """Shellnado — spend up to 5 Armor; deal that much damage to all minions.
    Reads the hero's current Armor at resolve time, spends min(armor, 5), then
    hits every minion for the amount spent."""

    TARGET = ActionArg()

    def do(self, source, target):
        spent = min(target.armor or 0, 5)
        if spent <= 0:
            return
        target.armor -= spent
        source.game.queue_actions(source, [Hit(ALL_MINIONS, spent)])


class TLC_601:
    """Shellnado"""

    # Spend up to 5 Armor. For each spent, deal 1 damage to all minions.
    play = _ShellnadoSpend(FRIENDLY_HERO)


class TLC_620:
    """Fortify"""

    # Gain 3 Armor. Deal damage equal to your Armor to an enemy minion.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = (
        GainArmor(FRIENDLY_HERO, 3),
        Hit(TARGET, Attr(FRIENDLY_HERO, GameTag.ARMOR)),
    )


class TLC_622:
    """City Defenses"""

    # Summon two 0/6 Security with Taunt. They gain +1 Attack when damaged.
    play = Summon(CONTROLLER, "TLC_622t") * 2


class TLC_622t:
    """Steadfast Security"""

    # Taunt (data). After this takes damage, gain +1 Attack.
    events = Damage(SELF).on(Buff(SELF, "TLC_622e"))


# Stand Strong — +1 Attack (in data).
TLC_622e = buff(atk=1)


##
# Quest


class TLC_602(QuestRewardProtect):
    """Enter the Lost City"""

    # Quest: Survive 10 turns. Reward: Latorvius, Gaze of the City.
    progress_total = 10
    quest = OWN_TURN_END.on(AddProgress(SELF, SELF))
    reward = Give(CONTROLLER, "TLC_602t")


class _LatorviusRewards(TargetedAction):
    """Latorvius — pick 2 random Quest Rewards from the card's entourage to
    GIVE to hand, then SHUFFLE the remaining rewards into the controller's
    deck. A single RNG sample partitions the entourage so the given 2 and the
    shuffled rest are disjoint (no token is both handed over and shuffled)."""

    TARGET = ActionArg()

    def do(self, source, target):
        pool = list(source.entourage)
        n_give = min(2, len(pool))
        given = source.game.random.sample(pool, n_give)
        given_counts = {}
        for cid in given:
            given_counts[cid] = given_counts.get(cid, 0) + 1
        # "the rest" = the entourage minus the exact tokens handed over.
        rest = []
        for cid in pool:
            if given_counts.get(cid, 0) > 0:
                given_counts[cid] -= 1
            else:
                rest.append(cid)
        actions = [Give(target, cid) for cid in given]
        actions += [Shuffle(target, cid) for cid in rest]
        if actions:
            source.game.queue_actions(source, actions)


class TLC_602t:
    """Latorvius, Gaze of the City"""

    # Battlecry: Get 2 random 'Journey to Un'Goro' Quest Rewards. Shuffle the
    # rest into your deck.
    play = _LatorviusRewards(CONTROLLER)
    entourage = [
        "UNG_116t",   # Barnabus the Stomper (Druid quest reward)
        "UNG_028t",   # Time Warp (Mage)
        "UNG_954t1",  # Galvadon (Paladin)
        "UNG_940t8",  # Amara, Warden of Hope (Priest)
        "UNG_067t1",  # Crystal Core (Rogue)
        "UNG_942t",   # Megafin (Shaman)
        "UNG_829t1",  # Nether Portal (Warlock)
        "UNG_934t1",  # Sulfuras (Warrior)
        "UNG_920t1",  # Queen Carnassa (Hunter)
    ]


##
# Story of Sulfuras — Hero Power swap


class TLC_632:
    """Story of Sulfuras"""

    # Swap your Hero Power to "Deal 8 damage to a random enemy." After 2 uses,
    # swap back.
    def play(self):
        player = self.controller
        old_hero_power = player.hero_power
        if old_hero_power == "TLC_632t" or old_hero_power == "TLC_632t2":
            new_hero_power = player.card("TLC_632t")
            new_hero_power._old_hero_power = old_hero_power._old_hero_power
            yield Summon(CONTROLLER, new_hero_power)
        else:
            new_hero_power = player.card("TLC_632t")
            new_hero_power._old_hero_power = old_hero_power
            yield Summon(CONTROLLER, new_hero_power)


class TLC_632t:
    """DIE, INSECT!"""

    # Hero Power — Deal 8 damage to a random enemy. (Two uses left!)
    def activate(self):
        yield Hit(RANDOM_ENEMY_CHARACTER, 8)
        player = self.controller
        new_hero_power = player.card("TLC_632t2")
        new_hero_power._old_hero_power = self._old_hero_power
        yield Summon(CONTROLLER, new_hero_power)
        yield SetTags(new_hero_power, {enums.ACTIVATIONS_THIS_TURN: 1})


class TLC_632t2:
    """DIE, INSECT!"""

    # Hero Power — Deal 8 damage to a random enemy. (Last use!)
    def activate(self):
        yield Hit(RANDOM_ENEMY_CHARACTER, 8)
        yield Summon(CONTROLLER, self.controller.hero_power._old_hero_power)


##
# The Lost City of Un'Goro — Dinosaurs mini-set (DINO_)


class DINO_400:
    """Barricade Basher"""

    # Whenever you gain Armor, gain +2/+2 and attack a random enemy minion.
    events = GainArmor(FRIENDLY_HERO).on(
        Buff(SELF, "DINO_400e"),
        Attack(SELF, RANDOM_ENEMY_MINION),
    )


# Bashful — +2/+2 (in data as DINO_400e).
DINO_400e = buff(atk=2, health=2)


class DINO_401:
    """The Great Dracorex"""

    # Rush (data). After this attacks an enemy minion, it damages ALL other
    # enemy minions (for its Attack).
    events = Attack(SELF, ENEMY_MINIONS).after(
        Hit(ENEMY_MINIONS - Attack.DEFENDER, ATK(SELF))
    )


class DINO_433:
    """Guard Duty"""

    # Summon a random 6, 4, and 2-Cost Taunt minion.
    play = (
        Summon(CONTROLLER, RandomMinion(cost=6, custom_filter=lambda c: c.taunt)),
        Summon(CONTROLLER, RandomMinion(cost=4, custom_filter=lambda c: c.taunt)),
        Summon(CONTROLLER, RandomMinion(cost=2, custom_filter=lambda c: c.taunt)),
    )
