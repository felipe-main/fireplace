from ..utils import *


##
# Custom actions


class _ArcaneQuiverConditionalBuff(TargetedAction):
	"""Arcane Quiver — after the player picks a spell from their deck,
	if that spell's SpellSchool is Arcane, buff it with Spell Damage +1
	(RLK_817e — registered below). Non-arcane picks are given as normal
	with no buff."""

	PLAYER = ActionArg()
	CARD = ActionArg()

	def do(self, source, player, picked):
		if isinstance(picked, list):
			if not picked:
				return
			picked = picked[0]
		if picked is None:
			return
		# Give the card to the picker first.
		source.game.cheat_action(source, [Give(player, picked)])
		# Then, if it's an Arcane spell, attach the spellpower buff.
		if picked.spell_school == SpellSchool.ARCANE:
			source.game.cheat_action(source, [Buff(picked, "RLK_817e")])


##
# Spells


class RLK_804:
	"""Conjured Arrow"""

	# Deal $2 damage to a minion. Manathirst (6): Draw that many cards.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Hit(TARGET, 2),
		MANATHIRST(6) & Draw(CONTROLLER) * 2,
	)


class RLK_817:
	"""Arcane Quiver"""

	# Discover a spell from your deck. If it's Arcane, give it Spell
	# Damage +1. Implemented via a custom Choice over 3 random spells
	# from the deck (matching the engine's existing "Discover from deck"
	# pattern — see CS3_028) and a custom callback that conditionally
	# attaches RLK_817e when the picked card is an Arcane spell.
	play = Choice(
		CONTROLLER, DeDuplicate(RANDOM(FRIENDLY_DECK + SPELL, 3))
	).then(_ArcaneQuiverConditionalBuff(Choice.PLAYER, Choice.CARD))


@custom_card
class RLK_817e:
	# Arcane Quiver — Spell Damage +1 buff for the picked Arcane spell.
	# Not in data (the printed effect is delivered via the picked card
	# directly), so register manually.
	tags = {
		GameTag.CARDNAME: "Arcane Quiver",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.SPELLPOWER: 1,
	}


class RLK_818:
	"""Ricochet Shot"""

	# Deal $1 damage to three random enemies.
	play = Hit(RANDOM_ENEMY_CHARACTER, 1) * 3


class RLK_819:
	"""Eversong Portal"""

	# Summon $1 4/4 Lynx(es) with Rush (improved by Spell Damage).
	# Base count is 1, scaled by the controller's Spell Damage.
	play = Summon(CONTROLLER, "RLK_819t") * SPELL_DAMAGE(1)


class RLK_819t:
	"""Eversong Lynx"""

	# Rush. (Token — Rush is set in data.)


##
# Minions


class RLK_820:
	"""Halduron Brightwing"""

	# Battlecry: Give all Arcane spells in your deck Spell Damage +1.
	play = Buff(FRIENDLY_DECK + SPELL + ARCANE_SPELL, "RLK_820e")


@custom_card
class RLK_820e:
	# Halduron Brightwing — Spell Damage +1 buff stamped on Arcane spells
	# in the deck. Not present in data; register manually.
	tags = {
		GameTag.CARDNAME: "Halduron Brightwing",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.SPELLPOWER: 1,
	}


class RLK_821:
	"""Scourge Tamer"""

	# Battlecry: Craft a custom Zombeast.
	# TODO: The real card opens a Build-a-Beast-style mini-builder that
	# fuses two Undead/Beast minions into a custom token. The full
	# selection UI is out of scope; approximate by summoning one random
	# Beast onto the board so the battlecry isn't a no-op.
	play = Summon(CONTROLLER, RandomMinion(race=Race.BEAST))


class RLK_825:
	"""Shockspitter"""

	# Battlecry: Deal @ damage. (Improved by your hero attacks this game!)
	# Damage scales with the controller's lifetime hero-attack counter
	# (`num_hero_attacks_this_game`, maintained by the engine). Target is
	# any character; falls under standard battlecry targeting reqs.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
	}
	play = Hit(TARGET, Attr(CONTROLLER, "num_hero_attacks_this_game"))


class RLK_826:
	"""Silvermoon Farstrider"""

	# Battlecry: Give all Arcane spells in your hand Spell Damage +1.
	play = Buff(FRIENDLY_HAND + SPELL + ARCANE_SPELL, "RLK_826e")


class RLK_826e:
	# In-data buff "Silvermoon Farstrider Spellpower" — printed text says
	# Spell Damage +1 but the SPELLPOWER tag is not in parsed data, so
	# declare it explicitly here.
	tags = {GameTag.SPELLPOWER: 1}


class RLK_827:
	"""Keeneye Spotter"""

	# Whenever your hero attacks a minion, set its Health to 1.
	# The Attack event's DEFENDER is the target of the hero attack; gate
	# on it being a minion, then stamp RLK_827e (Hunter's Mark) which
	# sets max_health to 1.
	events = Attack(FRIENDLY_HERO).on(
		Find(Attack.DEFENDER + MINION) & Buff(Attack.DEFENDER, "RLK_827e")
	)


class RLK_827e:
	# In-data Hunter's Mark enchant — set the defender's max_health to 1.
	max_health = SET(1)


##
# Weapons


class RLK_828:
	"""Hope of Quel'Thalas"""

	# After your hero attacks, give your minions +1/+1 (wherever they
	# are). "Wherever they are" = board + hand + deck, matching the
	# canonical engine selector pattern.
	events = Attack(FRIENDLY_HERO).after(
		Buff(
			(IN_DECK | IN_HAND | IN_PLAY) + FRIENDLY + MINION,
			"RLK_828e",
		)
	)


class RLK_828e:
	# In-data buff "Light of the Sunwell" — +1/+1. ATK/HEALTH not parsed
	# from data, so declare here.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}
