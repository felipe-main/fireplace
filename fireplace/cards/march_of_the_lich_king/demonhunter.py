from ..utils import *

from ...dsl.lazynum import LazyNum


##
# Custom actions / helpers


class _OutcastsPlayedCount(LazyNum):
	"""Read the controller's lifetime Outcast-cards-played counter, or 0
	if never bumped. Used by Vengeful Walloper's cost_mod. The counter
	is bumped by Wretched Exile's listener (RLK_210) and any other
	in-file effect that wants to credit an Outcast play. A bona-fide
	engine-level counter (Play.do bump on `card.play_outcast`) would be
	the cleaner home; until then we count via card-driven listeners,
	which is enough to make Walloper's discount visible whenever its
	relevant tracking minions are in play."""

	def __init__(self):
		super().__init__()
		self.selector = None

	def evaluate(self, source):
		return getattr(source.controller, "outcasts_played_this_game", 0)


class _BumpOutcastsPlayed(TargetedAction):
	"""Increment controller's outcasts_played_this_game counter by 1."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.outcasts_played_this_game = (
			getattr(target, "outcasts_played_this_game", 0) + 1
		)


class _MarkOfScornDrawAndPunish(TargetedAction):
	"""Mark of Scorn — draw a card; if the drawn card is not a minion,
	deal 3 damage to the lowest-Health enemy. Custom action because the
	Draw().then(...) DSL doesn't let us branch on "type != MINION" and
	then re-pick the lowest-Health target after the draw resolves."""

	TARGET = ActionArg()

	def do(self, source, target):
		pre = set(id(c) for c in target.hand)
		source.game.cheat_action(source, [Draw(target)])
		new = [c for c in target.hand if id(c) not in pre]
		if not new:
			return
		drawn = new[0]
		if drawn.type == CardType.MINION:
			return
		pool = LOWEST_HEALTH(ENEMY_CHARACTERS).eval(source.game, source)
		if not pool:
			return
		victim = source.game.random.choice(pool)
		source.game.cheat_action(source, [Hit(victim, 3)])


def _random_dh_outcast_id(game):
	"""Pick a random collectible Demon Hunter card that prints Outcast.
	Returns a card id, or None if the pool is empty."""
	from .. import db
	pool = [
		cid for cid, c in db.items()
		if c.collectible
		and c.card_class == CardClass.DEMONHUNTER
		and c.tags.get(GameTag.OUTCAST, 0)
	]
	if not pool:
		return None
	return game.random.choice(pool)


class _WretchedExileAddOne(TargetedAction):
	"""After an Outcast play, add a single random Outcast card to the
	controller's hand (no discount, no edge placement — Felerin handles
	the discount/edge variant)."""

	TARGET = ActionArg()

	def do(self, source, target):
		cid = _random_dh_outcast_id(source.game)
		if cid is None:
			return
		source.game.cheat_action(source, [Give(target, cid)])


class _FelerinAddOutcastsAtEdges(TargetedAction):
	"""Felerin, the Forgotten — add a random Outcast card to the left
	and right sides of the controller's hand and discount each by (2)
	via RLK_215e. Two independent picks. We insert directly at the hand
	bounds so the new cards become the literal leftmost and rightmost
	entries, matching the printed effect."""

	TARGET = ActionArg()

	def do(self, source, target):
		from ...card import Card
		for edge in ("left", "right"):
			cid = _random_dh_outcast_id(source.game)
			if cid is None:
				continue
			card = Card(cid)
			card.controller = target
			card.zone = Zone.HAND
			if edge == "left":
				target.hand.insert(0, card)
			else:
				target.hand.append(card)
			source.game.cheat_action(source, [Buff(card, "RLK_215e")])


class _BrutalAnnihilanRetaliate(TargetedAction):
	"""Brutal Annihilan — after surviving damage, deal that amount to
	the enemy hero. Reads Damage.AMOUNT from the triggering event arg."""

	TARGET = ActionArg()
	AMOUNT = ActionArg()

	def do(self, source, target, amount):
		if isinstance(amount, list):
			amount = amount[0] if amount else 0
		if not amount:
			return
		source.game.cheat_action(source, [Hit(ENEMY_HERO, amount)])


##
# Spells


class RLK_206:
	"""Mark of Scorn"""

	# Draw a card. If it's not a minion, deal $3 damage to the lowest
	# Health enemy.
	play = _MarkOfScornDrawAndPunish(CONTROLLER)


class RLK_208:
	"""Fel'dorei Warband"""

	# Deal $4 damage. If your deck has no minions, summon four 1/1
	# Illidari with Rush. Reusing BT_036t (Illidari Initiate, 1/1 Rush)
	# as the printed token — no RLK_208t exists in data.
	requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
	play = (
		Hit(TARGET, 4),
		(Count(FRIENDLY_DECK + MINION) == 0)
		& (Summon(CONTROLLER, "BT_036t") * 4),
	)


class RLK_209:
	"""Unleash Fel"""

	# Deal $1 damage to all enemies. Manathirst (4): With Lifesteal.
	# There's no general "this spell has Lifesteal" hook, so we
	# approximate by healing the friendly hero for the total damage
	# dealt when the Manathirst condition is met.
	play = (
		Hit(ENEMY_CHARACTERS, 1),
		MANATHIRST(4) & Heal(FRIENDLY_HERO, Count(ENEMY_CHARACTERS)),
	)


class RLK_211:
	"""Deal with a Devil"""

	# Summon two 3/3 Felfiends with Lifesteal. If your deck has no
	# minions, summon another. RLK_211t (Felfiend) has LIFESTEAL set
	# in data already.
	play = (
		Summon(CONTROLLER, "RLK_211t") * 2,
		(Count(FRIENDLY_DECK + MINION) == 0)
		& Summon(CONTROLLER, "RLK_211t"),
	)


##
# Minions


class RLK_207:
	"""Fierce Outsider"""

	# Rush. Outcast: Your next Outcast card costs (1) less.
	# Approximation: drop a hand-wide -1-cost aura on Outcast cards
	# (RLK_207e), and let the aura self-destroy the first time the
	# controller plays *any* Outcast card. Matches "your next Outcast
	# card" in the common case (single Outcast in hand).
	outcast = Buff(CONTROLLER, "RLK_207e")


class RLK_210:
	"""Wretched Exile"""

	# After you play an Outcast card, add a random Outcast card to your
	# hand. The same listener bumps the controller's
	# outcasts_played_this_game counter so Vengeful Walloper's discount
	# stays in sync whenever Exile sees an Outcast play. (Walloper
	# played on its own with no Exile-style tracker on the board will
	# see a stale 0 — a future engine bump in Play.do will close the
	# gap. See RLK_213 docstring.)
	events = Play(CONTROLLER, OUTCAST).after(
		_BumpOutcastsPlayed(CONTROLLER),
		_WretchedExileAddOne(CONTROLLER),
	)


class RLK_212:
	"""Brutal Annihilan"""

	# Taunt, Rush. After this minion survives damage, deal that amount
	# to the enemy hero. TAUNT/RUSH come from card data; we only need
	# the retaliate trigger. Gated on `Dead(SELF) | ...` so death-by-
	# damage doesn't fire the hit.
	events = SELF_DAMAGE.on(
		Dead(SELF)
		| _BrutalAnnihilanRetaliate(SELF, Damage.AMOUNT)
	)


class RLK_213:
	"""Vengeful Walloper"""

	# Rush. Costs (1) less for each Outcast card you've played this
	# game. Reads outcasts_played_this_game off the controller (bumped
	# by RLK_210's listener while Wretched Exile is on the board, and
	# by any future engine-level Play.do hook on `card.play_outcast`).
	# Until that engine hook lands, Walloper's discount only ticks
	# while a tracking minion is in play — flagged in review.csv.
	cost_mod = -_OutcastsPlayedCount()


class RLK_215:
	"""Felerin, the Forgotten"""

	# Battlecry: Add a random Outcast card to the left and right sides
	# of your hand. They cost (2) less.
	play = _FelerinAddOutcastsAtEdges(CONTROLLER)


##
# Weapons


class RLK_214:
	"""Souleater's Scythe"""

	# Start of Game: Consume 3 different minions in your deck. Leave
	# behind Souls that Discover them.
	# TODO: SoG mechanic — needs an engine Start-of-Game hook plus
	# multi-card state (the consumed minion ids → their Soul tokens'
	# Discover pools). Ships as a vanilla 4/2 weapon for now. RLK_214t
	# ("Bound Soul") exists in data as the Soul spell token.


##
# Enchantments


class RLK_207e:
	# In-data card "Introverted" (the Fierce Outsider Outcast aura);
	# parsed data has no scripts attached, so we wire the cost-discount
	# update and the self-destroy-on-next-Outcast-play listener here.
	update = Refresh(FRIENDLY_HAND + OUTCAST, {GameTag.COST: -1})
	events = Play(CONTROLLER, OUTCAST).on(Destroy(SELF))


@custom_card
class RLK_215e:
	# Not present in data — register manually. -2 cost stamp for the
	# two Outcast cards Felerin adds to the hand edges.
	tags = {
		GameTag.CARDNAME: "Felerin's Gift",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -2,
	}
