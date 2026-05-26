from ..utils import *

from .utils import HeroAttacksCardtextMixin


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


class _ScourgeTamerCraftStep2(TargetedAction):
	"""Second-stage Discover callback — picks the Beast body, combines
	with the previously-stored Undead body, and gives the controller a
	custom Zombeast (uses the Beast as the physical card with merged
	atk/health from both bodies)."""

	TARGET = ActionArg()
	CARDS = ActionArg()
	CARD = ActionArg()

	def do(self, source, player, cards_offered, beast_card):
		if isinstance(beast_card, list):
			beast_card = beast_card[0] if beast_card else None
		if beast_card is None:
			return
		undead_id = getattr(player, "_scourge_tamer_undead", None)
		if undead_id is None:
			# No staged Undead body — fall back to giving the Beast.
			source.game.cheat_action(source, [Give(player, beast_card.id)])
			return
		undead_card = player.card(undead_id)
		combined_atk = (undead_card.atk or 0) + (beast_card.atk or 0)
		combined_health = (undead_card.max_health or 0) + (beast_card.max_health or 0)
		combined_cost = max(
			0, ((undead_card.cost or 0) + (beast_card.cost or 0) + 1) // 2
		)
		# Give the Beast (as the host card body) and stamp custom-stat
		# attributes so it acts as the Zombeast. We don't have a true
		# "merged minion" engine path; this is the closest we get with
		# the existing custom_card hook. Find the newly-added card by
		# id-and-not-yet-stamped search (handles nested cheat_action
		# return shapes).
		pre_hand_ids = set(id(c) for c in player.hand)
		source.game.cheat_action(source, [Give(player, beast_card.id)])
		given = next(
			(c for c in player.hand if id(c) not in pre_hand_ids),
			None,
		)
		if given is None:
			return
		given.custom_card = True

		def create(card):
			card.atk = combined_atk
			card.max_health = combined_health
			card.cost = combined_cost

		given.create_custom_card = create
		given.create_custom_card(given)
		player._scourge_tamer_undead = None


class _ScourgeTamerCraftStep1(TargetedAction):
	"""First-stage Discover callback — picks the Undead body and stages
	it on the controller, then opens the Beast Discover."""

	TARGET = ActionArg()
	CARDS = ActionArg()
	CARD = ActionArg()

	def do(self, source, player, cards_offered, undead_card):
		if isinstance(undead_card, list):
			undead_card = undead_card[0] if undead_card else None
		if undead_card is None:
			return
		player._scourge_tamer_undead = undead_card.id
		beast_picker = RandomMinion(race=Race.BEAST)
		beast_discover = Discover(player, beast_picker).then(
			_ScourgeTamerCraftStep2(
				Discover.TARGET, Discover.CARDS, Discover.CARD
			)
		)
		source.game.queue_actions(source, [beast_discover])


class RLK_821:
	"""Scourge Tamer"""

	# Battlecry: Craft a custom Zombeast.
	# Two-stage Discover: pick an Undead body, then a Beast body. The
	# combined Zombeast is given to hand using the Beast as the base
	# entity with custom atk/health/cost derived from the sum of both
	# bodies (the engine has no "merged minion" path so we ride
	# custom_card to set the stats post-Give).
	play = Discover(CONTROLLER, RandomMinion(race=Race.UNDEAD)).then(
		_ScourgeTamerCraftStep1(
			Discover.TARGET, Discover.CARDS, Discover.CARD
		)
	)


class RLK_825(HeroAttacksCardtextMixin):
	"""Shockspitter"""

	# Battlecry: Deal @ damage. (Improved by your hero attacks this game!)
	# Damage scales with the controller's lifetime hero-attack counter
	# (`num_hero_attacks_this_game`, maintained by the engine). Mixin
	# renders the `@` placeholder to the current counter value.
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
