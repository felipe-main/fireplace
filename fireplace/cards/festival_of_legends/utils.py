"""Festival of Legends — shared per-set helpers.

Houses two flavours of shared infrastructure used by Festival cards:

1. The Harmonic-spell phase-swap dispatcher (`_HarmonicSwap`) used by
   the five "Swaps each turn" spells — Mood, Metal, Hip Hop, Pop, Disco
   (Druid / Death Knight / Rogue / Priest / Paladin). The "Swaps each
   turn" line on each Harmonic card means the printed text alternates
   between a base branch and an alt branch on alternating turns. We
   approximate the 6-way HS rotation as a binary swap (base ↔ alt)
   which pins the alternating-effect invariant tests assert.

   Each Harmonic card script declares:

       _HARMONIC_BASE = <action or tuple of actions>   # printed text
       _HARMONIC_ALT  = <action or tuple of actions>   # alt branch

   …then sets `play = _HarmonicSwap(TARGET)` (or `SELF` if untargeted).
   At cast time `_HarmonicSwap.do` reads the controller's
   `_harmonic_phase_swapped` boolean (lives on Player, toggled in
   `Game.end_turn_cleanup`) and fires the chosen branch via cheat_action.

2. Cosmetic `custom_cardtext` mixins that fill `@` / `{0}` placeholders
   in printed text. Festival ships ~20 cards whose printed `description`
   contains `@` (Hearthstone's render-time placeholder) or python-format
   `{N}` slots that need values supplied at render time. None of these
   affect engine behaviour — the cards' play / events / deathrattle
   scripts already read the underlying counters directly. These mixins
   only fill in what the rendered card text would show.

   Important plumbing constraint: `Card.description` (in
   ``fireplace/card.py``) looks up the cardtext_entity_N callable from
   ``self.tags[GameTag.CARDTEXT_ENTITY_N]`` and invokes it with the
   *card entity* as ``self``. Methods defined on the cardscript class
   (e.g. ``_resolve_count``) are NOT copied onto the entity. So
   cardtext_entity_N callables must read attributes that live on the
   entity (``controller``, ``_metrognome_n``, ``data``, …) or call
   ``getattr(self, "<attr>", 0)``.

   We split the mixins in two:
     * The *text-rewrite* mixin (``_AtToFormatCardtextMixin``,
       ``_FatigueCardtextMixin``) rewrites the description string and
       supplies a default ``cardtext_entity_0`` that reads
       ``self.<counter_attr>`` on the entity.
     * For counters that live on the *controller* (combo cards played,
       Freebird count, etc.), the cardscript overrides
       ``cardtext_entity_0`` (and the merge in cards/__init__.py only
       wires _0 / _1 by name; counters in higher positions live on the
       tags dict).

   Mirrors the ``ThreeSpellsProgressUtils`` (Sunken City) and
   ``ManathirstCardtextMixin`` (March of the Lich King) precedents.
"""

from hearthstone.enums import GameTag

from ..utils import *


class _HarmonicSwap(TargetedAction):
	"""Reads the source card's `_HARMONIC_BASE` / `_HARMONIC_ALT` class
	attributes and the controller's `_harmonic_phase_swapped` flag,
	then fires the appropriate branch's actions."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		swapped = getattr(ctrl, "_harmonic_phase_swapped", False)
		attr = "_HARMONIC_ALT" if swapped else "_HARMONIC_BASE"
		branch = getattr(source.data.scripts, attr, None)
		if branch is None:
			return
		if not isinstance(branch, (list, tuple)):
			branch = (branch,)
		# The branch may reference TARGET / SELF / CONTROLLER selectors;
		# cheat_action resolves those in this source/target context.
		for action in branch:
			if action is None:
				continue
			source.game.cheat_action(source, [action])


# ---------------------------------------------------------------------------
# Cosmetic placeholder mixins
# ---------------------------------------------------------------------------


def _entity_attr(self, attr):
	"""Read int counter `attr` off the entity, defaulting to 0."""
	return int(getattr(self, attr, 0) or 0)


class _FatigueCardtextMixin:
	"""Baritone Imp / Crescendo / Crazed Conductor.

	Data ships two `@`-separated variants — the first (pre-`@`) wording
	uses the literal "Fatigue" and the second uses "Take {0} Fatigue".
	We always render the {0}-form using `fatigue_counter + 1` (the
	amount the *next* Fatigue tick would deal)."""

	def custom_cardtext(self):
		text = self.data.description
		halves = text.split("@", 1)
		return halves[1] if len(halves) == 2 else text

	def cardtext_entity_0(self):
		ctrl = getattr(self, "controller", None)
		if ctrl is None:
			return "1"
		return str((getattr(ctrl, "fatigue_counter", 0) or 0) + 1)

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
	}


class _TrailingProgressCardtextMixin:
	"""Cards whose printed text ends in "...@ <i>(@)</i>" — the first
	`@` is a leading separator (renders empty in HS too), the second
	`@` is the counter readout. Default ``cardtext_entity_0`` reads
	``self.<counter_attr>`` off the entity; cardscripts that need a
	derived value override ``cardtext_entity_0`` directly (and re-stamp
	the tag in their own tags dict)."""

	counter_attr = ""

	def custom_cardtext(self):
		text = self.data.description
		first, rest = text.split("@", 1)
		rest = rest.replace("@", "{0}", 1)
		return first + rest

	def cardtext_entity_0(self):
		attr = getattr(self.data.scripts, "counter_attr", "")
		return str(_entity_attr(self, attr)) if attr else "0"

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
	}


class _WeaponCounterCardtextMixin:
	"""Single-`@` weapon-counter cards: Timber Tambourine, Glaivetar,
	Record Scratcher, Kodohide Drumkit, Jazz Bass, Jungle Jammer.
	The counter is a plain attribute on the weapon entity itself."""

	counter_attr = ""

	def custom_cardtext(self):
		return self.data.description.replace("@", "{0}")

	def cardtext_entity_0(self):
		attr = getattr(self.data.scripts, "counter_attr", "")
		return str(_entity_attr(self, attr)) if attr else "0"

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
	}


class _DoubleAtCardtextMixin:
	"""`+@/+@` or `@/@` cards (Disco Maul, Arcanite Ripper) — the same
	counter is rendered twice. ``replace`` with no count substitutes
	every `@`."""

	counter_attr = ""

	def custom_cardtext(self):
		return self.data.description.replace("@", "{0}")

	def cardtext_entity_0(self):
		attr = getattr(self.data.scripts, "counter_attr", "")
		return str(_entity_attr(self, attr)) if attr else "0"

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
	}


class _ZokFogsnoutCardtextMixin:
	"""Zok Fogsnout — `{0}/{1}` rendered as
	(hero_atk + armor_gained_this_turn) / (same).

	Both slots show the same value (printed token's stats are symmetric).
	Reads from the controller's hero and the
	``_zok_armor_at_turn_start`` snapshot stamped by the turn-begin hook."""

	def custom_cardtext(self):
		return self.data.description

	def _zok_value(self):
		ctrl = getattr(self, "controller", None)
		if ctrl is None or ctrl.hero is None:
			return "0"
		hero_atk = ctrl.hero.atk or 0
		armor_now = ctrl.hero.armor or 0
		armor_start = getattr(ctrl, "_zok_armor_at_turn_start", armor_now)
		armor_gained = max(0, armor_now - armor_start)
		return str(hero_atk + armor_gained)

	def cardtext_entity_0(self):
		return _ZokFogsnoutCardtextMixin._zok_value(self)

	def cardtext_entity_1(self):
		return _ZokFogsnoutCardtextMixin._zok_value(self)

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
		GameTag.CARDTEXT_ENTITY_1: cardtext_entity_1,
	}


class _MetrognomeCardtextMixin:
	"""Metrognome — `{0}` next-cost-to-play, `{1}` next-cost-to-draw.

	`_metrognome_n` lives on the minion entity (in-play only); mirrors
	the counter `_MetrognomeTick.do` reads and bumps."""

	def custom_cardtext(self):
		return self.data.description

	def cardtext_entity_0(self):
		return str(_entity_attr(self, "_metrognome_n"))

	def cardtext_entity_1(self):
		return str(_entity_attr(self, "_metrognome_n") + 1)

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
		GameTag.CARDTEXT_ENTITY_1: cardtext_entity_1,
	}


class _ClimacticExplosionCardtextMixin:
	"""Climactic Necrotic Explosion — `${0}` damage, `{1}` Souls,
	`{2}/{3}` Soul stats. The actual values are rolled at cast time
	(see `_ClimacticExplosion.do`); the printed-text contract here is
	the *base* (pre-improvement) values, mirroring what HS itself
	renders before the spell resolves."""

	def custom_cardtext(self):
		return self.data.description

	def cardtext_entity_0(self):
		return "1"  # base damage

	def cardtext_entity_1(self):
		return "1"  # base soul count

	def cardtext_entity_2(self):
		return "1"  # base soul atk

	def cardtext_entity_3(self):
		return "1"  # base soul health

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
		GameTag.CARDTEXT_ENTITY_1: cardtext_entity_1,
		GameTag.CARDTEXT_ENTITY_2: cardtext_entity_2,
		GameTag.CARDTEXT_ENTITY_3: cardtext_entity_3,
	}
