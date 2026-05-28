from ..utils import *


##
# Custom actions / helpers


class _HodirSetStatsBuff(TargetedAction):
    """Hodir, Father of Giants — whenever a friendly minion is played,
    if hodir_charges > 0, set its stats to 8/8 and decrement the counter."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        charges = getattr(ctrl, "hodir_charges", 0)
        if charges <= 0:
            return
        # Set ATK to 8 and max_health to 8 via a runtime-stamped buff.
        source.game.cheat_action(
            source,
            [Buff(target, "TTN_752e", atk=max(0, 8 - target.atk),
                  max_health=max(0, 8 - target.max_health))],
        )
        ctrl.hodir_charges = charges - 1


class _AggramarAbilityMaintainOrder(TargetedAction):
    """Aggramar — Maintain Order ability: Give your weapon an after-attack
    draw-a-card effect (TTN_092e enchant on the weapon)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not source.controller.weapon:
            return
        source.game.queue_actions(
            source, [Buff(FRIENDLY_WEAPON, "TTN_092e")]
        )


class _AggramarAbilityCommandingPresence(TargetedAction):
    """Aggramar — Commanding Presence ability: Give your weapon an
    after-attack summon-Enforcer effect (TTN_092e2 enchant on the weapon)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not source.controller.weapon:
            return
        source.game.queue_actions(
            source, [Buff(FRIENDLY_WEAPON, "TTN_092e2")]
        )


class _AggramarAbilitySwiftSlash(TargetedAction):
    """Aggramar — Swift Slash ability: Give your weapon +2 Attack and
    Immune-while-attacking (TTN_092e3 enchant on the weapon)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not source.controller.weapon:
            return
        source.game.queue_actions(
            source, [Buff(FRIENDLY_WEAPON, "TTN_092e3")]
        )


##
# Minions


class TTN_078:
    """Observer of Myths"""

    # After you summon a minion with more Attack than this, give all
    # friendly minions +1 Attack.
    events = Summon(CONTROLLER, MINION).after(
        (Attr(Summon.CARD, GameTag.ATK) > Attr(SELF, GameTag.ATK))
        & Buff(FRIENDLY_MINIONS, "TTN_078e"),
    )


TTN_078e = buff(atk=1)


class TTN_080:
    """Fable Stablehand"""

    # Rush. Battlecry: If you control a minion with 4 or more Attack,
    # gain +2/+2. Rush is in data.
    powered_up = Find(FRIENDLY_MINIONS - SELF + (ATK >= 4))
    play = powered_up & Buff(SELF, "TTN_080e")


@custom_card
class TTN_080e:
    # Fable Stablehand — +2/+2 (not in data).
    tags = {
        GameTag.CARDNAME: "Inspired",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 2,
        GameTag.HEALTH: 2,
    }


class TTN_092:
    """Aggramar, the Avenger"""

    # Titan. Battlecry: Equip a 3/3 Taeshalach (TTN_092t).
    titan_ability_order = ["TTN_092t1", "TTN_092t2", "TTN_092t3"]
    play = Summon(CONTROLLER, "TTN_092t")


class TTN_092t:
    """Taeshalach"""

    # 3/3 weapon — stats and durability in data.


class TTN_092t1:
    """Maintain Order"""

    # Give your weapon "After your hero attacks, draw a card."
    play = _AggramarAbilityMaintainOrder(CONTROLLER)


class TTN_092t2:
    """Commanding Presence"""

    # Give your weapon "After your hero attacks, summon a 3/3 Enforcer."
    play = _AggramarAbilityCommandingPresence(CONTROLLER)


class TTN_092t3:
    """Swift Slash"""

    # Give your weapon +2 Attack and "Your hero is Immune while attacking."
    play = _AggramarAbilitySwiftSlash(CONTROLLER)


class TTN_092e:
    """Scouring"""

    # After your hero attacks, draw a card.
    events = Attack(FRIENDLY_HERO).after(Draw(CONTROLLER))


class TTN_092e2:
    """Commanding"""

    # After your hero attacks, summon a 3/3 Vry'kul Enforcer with Taunt.
    events = Attack(FRIENDLY_HERO).after(Summon(CONTROLLER, "TTN_092e2t"))


class TTN_092e2t:
    """Vry'kul Enforcer"""

    # 3/3 Taunt token — stats and Taunt in data.


class TTN_092e3:
    """Swiftness"""

    # +2 Attack and Immune while attacking.
    tags = {GameTag.ATK: 2, GameTag.IMMUNE_WHILE_ATTACKING: True}


class TTN_752:
    """Hodir, Father of Giants"""

    # Battlecry: Set the stats of the next three minions you play to 8/8.
    # Arm three charges on the controller; an in-play trigger consumes one
    # per friendly minion played and stamps 8/8 stats on it.
    def play(self):
        ctrl = self.controller
        ctrl.hodir_charges = getattr(ctrl, "hodir_charges", 0) + 3

    events = Play(CONTROLLER, MINION).after(
        _HodirSetStatsBuff(Play.CARD)
    )


##
# Spells


class TTN_079:
    """Always a Bigger Jormungar"""

    # Give a minion +2 Attack and "Excess damage dealt by attacks hits
    # the enemy hero." TTN_079e is in data and marks the piercing effect.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "TTN_079e")


class _JormungarPierce(TargetedAction):
    """Always a Bigger Jormungar — excess damage piercing. When the buffed
    minion attacks a minion and the attack would deal more damage than the
    defender's health, the overflow hits the enemy hero.

    Called from TTN_079e's events listener. `attacker` and `defender` come
    from Attack.ATTACKER/DEFENDER. We compute excess BEFORE damage resolves
    (using attacker.atk - defender.health) and hit the enemy hero with it.
    """

    TARGET = ActionArg()
    ATTACKER = ActionArg()
    DEFENDER = ActionArg()

    def do(self, source, target, attacker, defender):
        # Attack args come through as lists from selectors — normalize.
        if isinstance(attacker, (list, tuple)):
            attacker = attacker[0] if attacker else None
        if isinstance(defender, (list, tuple)):
            defender = defender[0] if defender else None
        if not attacker or not defender:
            return
        if defender.type != CardType.MINION:
            return
        # Excess = attacker.atk - defender.health (after armor/divine shield
        # adjustments, the defender's effective HP at this point is .health).
        excess = attacker.atk - defender.health
        if excess <= 0:
            return
        enemy_hero = attacker.controller.opponent.hero
        source.game.cheat_action(source, [Hit(enemy_hero, excess)])


class TTN_079e:
    """Gift of the Hunt"""

    # +2 Attack and "Excess damage dealt by attacks hits the enemy hero."
    # Uses OWNER selector — the buffed minion — as the attacker in the event.
    tags = {GameTag.ATK: 2}
    events = Attack(OWNER, MINION).on(
        _JormungarPierce(SELF, Attack.ATTACKER, Attack.DEFENDER)
    )


class TTN_081:
    """Awakening Tremors"""

    # Get three 4/1 Bursting Jormungars. They cost (1).
    # TTN_081t is a 4/1 Bursting Jormungar that already costs (1) in data.
    play = Give(CONTROLLER, "TTN_081t") * 3


class TTN_081t:
    """Bursting Jormungar"""

    # 4/1 costing (1) — stats and cost in data.


class TTN_088:
    """Starstrung Bow"""

    # Costs (1) less for each friendly Secret that has triggered this game.
    cost_mod = -Attr(CONTROLLER, "secrets_triggered_this_game")


class TTN_302:
    """Titanforged Traps"""

    # Discover and cast a Secret. Forge: Do it twice.
    forge_card = "TTN_302t"
    play = DISCOVER(RandomSpell(secret=True)).then(CastSpell(Discover.CARD))


class TTN_302t:
    """Titanforged Traps"""

    # Forged — Discover and cast a Secret. Then do it again.
    play = (
        DISCOVER(RandomSpell(secret=True)).then(CastSpell(Discover.CARD)),
        DISCOVER(RandomSpell(secret=True)).then(CastSpell(Discover.CARD)),
    )


##
# Secrets


class TTN_504:
    """Bait and Switch"""

    # Secret: When a friendly minion is attacked, give it +3/+3.
    secret = Attack(None, FRIENDLY_MINIONS).on(
        Reveal(SELF), Buff(Attack.DEFENDER, "TTN_504e")
    )


TTN_504e = buff(+3, +3)


##
# Weapons

# TTN_088 is listed above in Spells section as it loads as a weapon card class.
# The class body is 'pass' with a TODO for cost_mod.


##
# Enchantments


@custom_card
class TTN_752e:
    # Not in data — runtime stat-setter for Hodir. ATK and max_health are
    # supplied dynamically by _HodirSetStatsBuff as keyword arguments.
    tags = {
        GameTag.CARDNAME: "Hodir, Father of Giants",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
