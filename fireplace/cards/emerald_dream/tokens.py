from ..utils import *


##
# Into the Emerald Dream — Imbued Hero Powers.
#
# These six tokens (one per Imbue-enabled class) are installed by the engine
# `Imbue(CONTROLLER)` action, which replaces the controller's Hero Power with
# the matching token and bumps `player.imbues_this_game`. Each token caches
# the imbue level on `self.imbue_level` (set by Imbue at install time and
# refreshed on every subsequent imbue), so its effect scales: the @ in the
# printed text grows with the number of times you've imbued this game.
#
# Scaling is keyed off `self.imbue_level` (>= 1 once installed). The first
# imbue is level 1; each further imbue increments it. We read it live in each
# `activate` so the power always reflects the current level even if the same
# token instance is reused across imbues.


class EDR_445p:
    """Blessing of the Dragon"""

    # Shuffle two Emerald Portals into your deck.
    # (Your Portals summon @-Cost Dragons.)  @ scales 4 / 6 / 8 ...
    def activate(self):
        level = max(1, self.imbue_level)
        dragon_cost = 2 + 2 * level  # L1=4, L2=6, L3=8 ...
        for _ in range(2):
            portal = self.controller.card("EDR_445pt3", source=self)
            # Stash the summon cost so the portal's Casts-When-Drawn knows
            # which Dragon tier to roll.
            portal._portal_dragon_cost = dragon_cost
            yield Shuffle(CONTROLLER, portal)


class EDR_445pt3:
    """Emerald Portal"""

    # Casts When Drawn: Summon a random @-Cost Dragon.
    def draw(self):
        cost = getattr(self, "_portal_dragon_cost", 4)
        yield Summon(CONTROLLER, RandomDragon(cost=cost))


class EDR_448p:
    """Blessing of the Wind"""

    # Transform a friendly minion into a random one that costs (@) more.
    # @ scales 1 / 2 / 3 ...
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }

    def activate(self):
        level = max(1, self.imbue_level)
        yield Evolve(TARGET, level)


class EDR_449p:
    """Blessing of the Moon"""

    # Choose a Priest minion or Priest spell to add to your hand.
    # It costs (@) less, but is Temporary.  @ scales 1 / 2 / 3 ...
    # NOTE: the "but is Temporary" downside is not modelled (this engine has
    # no Temporary-card lifetime). The cost reduction is full-fidelity.
    def activate(self):
        level = max(1, self.imbue_level)
        yield Discover(
            CONTROLLER,
            RandomCard(card_class=CardClass.PRIEST),
        ).then(
            Give(CONTROLLER, Discover.CARD).then(
                Buff(Give.CARD, "EDR_449pe", cost=-level)
            )
        )


@custom_card
class EDR_449pe:
    # Blessing of the Moon — discovered Priest card costs (@) less.
    # Amount set dynamically by Buff(cost=-level) at activate time.
    tags = {
        GameTag.CARDNAME: "Blessing of the Moon",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class EDR_847p:
    """Blessing of the Golem"""

    # Summon a @/@ Plant Golem.  @ scales 2 / 4 / 6 ...
    def activate(self):
        level = max(1, self.imbue_level)
        stat = 2 * level
        golem = self.controller.card("EDR_847pt2", source=self)
        golem.atk = stat
        golem.max_health = stat
        yield Summon(CONTROLLER, golem)


class EDR_847pt2:
    """Plant Golem"""


class EDR_850p:
    """Blessing of the Wolf"""

    # Give a random Beast in your hand +@ Attack. It costs (@) less.
    # @ scales 1 / 2 / 3 ...
    def activate(self):
        level = max(1, self.imbue_level)
        yield Buff(
            RANDOM(FRIENDLY_HAND + BEAST),
            "EDR_850pe1",
            atk=level,
        ).then(Buff(Buff.TARGET, "EDR_850pe5", cost=-level))


class EDR_850pe1:
    """Goldrinn's Courage"""

    # +@ Attack (data enchant). Amount set dynamically by Buff(atk=level).


class EDR_850pe5:
    """Great Wolf's Howl"""

    # Costs less (data enchant). Amount set dynamically by Buff(cost=-level).


class EDR_851p:
    """Blessing of the Wisp"""

    # Summon @ Wisps. Deal @ damage randomly split among all enemies.
    # @ scales 2 / 3 / 4 ...
    def activate(self):
        level = max(1, self.imbue_level)
        amount = level + 1  # L1=2, L2=3, L3=4 ...
        yield Summon(CONTROLLER, "EDR_851t") * amount
        yield Hit(RANDOM(ENEMY_CHARACTERS), 1) * amount


class EDR_851t:
    """Wisp"""
