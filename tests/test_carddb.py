import re

import utils
import pytest
from hearthstone.enums import CardType, GameTag, Rarity

CARDS = utils.fireplace.cards.db


# Out-of-scope cards that became collectible (or were reworked to carry a
# Battlecry/Deathrattle tag) only in the Patch 31.2.2 data (build 213852,
# pinned for The Great Dark Beyond). None belong to any implemented standard
# expansion, so they are skipped exactly like the NX2_/YOG_ deferred mini-sets:
#   - VAN_*  : VANILLA set — Classic-mode reprints of EX1_/CS2_/NEW1_/… cards.
#   - LEG_*  : LEGACY set — Legacy-format reprints (CS3_/RLK_).
#   - WORK_* : ISLAND_VACATION (Perils in Paradise) Tourist/Travel cards added
#              after the VAC_ Perils pass; out of scope for the GDB expansion.
# Plus individual stragglers from other modes/sets reworked in this build:
#   - BG31_BOB           : EVENT (Battlegrounds) — different game mode.
#   - WON_145            : EVENT (Caverns of Time) — different game mode.
#   - BT_307 (Darkglare) : BLACK_TEMPLE — reworked to a Battlecry in newer data.
#   - TOY_913 (Ci'Cigi)  : WHIZBANGS_WORKSHOP straggler outside the MIS_ mini-set.
#   - Core_UNG_*, CORE_VAN_* : CORE-set reprints of Un'Goro/Vanilla cards.
# TLC_EVENT_* : EVENT set — Tavern-Brawl/event-mode cards (e.g. Staff of the
#               Endbringer TLC_EVENT_402) that became collectible at build
#               226928; not part of the standard Lost City expansion.
_OUT_OF_SCOPE_PREFIXES = ("NX2_", "YOG_", "VAN_", "LEG_", "WORK_", "TLC_EVENT_", "TIME_EVENT_")
_OUT_OF_SCOPE_IDS = frozenset(
    [
        "BG31_BOB",          # Battlegrounds-only action card
        "WON_145",           # Avatar of Hearthstone — special pack-opener
        "CORE_WON_145",      # CORE reprint of the same special card
        "CORE_VAN_EX1_561",  # vanilla Alexstrasza reprint (VAN_ out of scope)
        # CORE id-collisions: these CORE cards are DIFFERENT cards that happen to
        # share an id with one of our expansion cards after CORE_-stripping, so
        # get_script_definition resolves them to the wrong (expansion) script.
        # They are out-of-scope CORE reprints, not the expansion card.
        "CORE_EDR_001",  # "Babbling Bookcase" (collides with EDR_001 Hopeful Dryad)
    ]
)


def _out_of_scope(cid):
    return cid in _OUT_OF_SCOPE_IDS or cid.startswith(_OUT_OF_SCOPE_PREFIXES)


# def test_all_tags_known():
#     """
#     Iterate through the card database and check that all specified GameTags
#     are known in hearthstone.enums.GameTag
#     """
#     unknown_tags = set()
#     known_tags = list(GameTag)
#     known_rarities = list(Rarity)
#
#     # Check the db loaded correctly
#     assert utils.fireplace.cards.db
#
#     for card in CARDS.values():
#         for tag in card.tags:
#             # We have fake tags in fireplace.enums which are always negative
#             if tag not in known_tags and tag > 0:
#                 unknown_tags.add(tag)
#
#         # Test rarities as well (cf. TB_BlingBrawl_Blade1e in 10956...)
#         assert card.rarity in known_rarities
#
#     assert not unknown_tags


def test_play_scripts():
    for card in CARDS.values():
        if card.scripts.activate:
            assert card.type in (
                CardType.HERO_POWER,
                CardType.SPELL,
                CardType.MINION,
                CardType.LOCATION,
            )
        elif card.scripts.play:
            assert card.type not in (CardType.HERO_POWER, CardType.ENCHANTMENT)


def test_battlecry_scripts():
    for card in CARDS.values():
        if card.battlecry and card.collectible:
            if card.id in ["DRG_308", "GIL_614", "ULD_003"]:
                continue
            # Harth Stonebrew (GIFT_01) is an anniversary EVENT card that
            # replaces your hand with a hardcoded "iconic" historical decklist
            # — content not present in the data and unrelated to any
            # implemented expansion. Out of scope.
            if card.id in ["GIFT_01", "CORE_GIFT_01"]:
                continue
            if _out_of_scope(card.id):
                continue
            assert card.scripts.play


def test_deathrattle_scripts():
    for card in CARDS.values():
        if card.deathrattle and card.collectible:
            if card.id in [
                "BOT_558",
                "DRG_086",
                "ULD_163",
                "UNG_953",
                "BT_126",
                "SCH_714",
                "SW_069",
            ]:
                continue
            if _out_of_scope(card.id):
                continue
            assert card.scripts.deathrattle


def test_card_docstrings():
    for card in CARDS.values():
        if card.locale != "enUS":
            continue
        if _out_of_scope(card.id):
            continue
        c = utils.fireplace.cards.get_script_definition(card.id)
        name = c.__doc__
        if name is not None:
            if name.endswith(")"):
                continue
            if GameTag.DECK_RULE_COUNT_AS_COPY_OF_CARD_ID in card.tags:
                continue
            # Some CORE reprints carry a cosmetic "[CORE 2024] " name prefix in
            # the data (e.g. CORE_LOOT_204 Cheat Death); the script docstring is
            # the bare printed name, so strip the prefix before comparing.
            card_name = re.sub(r"^\[CORE \d+\] ", "", card.name)
            if name != card_name:
                assert name == card_name
