"""Castle Nathria shared mixins for cosmetic @ placeholder fills."""
from ..utils import *


class InfuseCardtextMixin:
    """Infuse cards' printed text contains "Infuse (@)" — fill the @
    with the card's infuse_threshold (TAG_SCRIPT_DATA_NUM_1 in data)."""

    def custom_cardtext(self):
        text = self.data.description
        thr = getattr(self, "infuse_threshold", 0)
        if "@" in text and thr > 0:
            return text.replace("@", str(thr))
        return text

    def cardtext_entity_0(self):
        return getattr(self, "infuse_threshold", 0)

    tags = {
        enums.CUSTOM_CARDTEXT: custom_cardtext,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }


class RelicCardtextMixin:
    """The three Relic spells' printed text contains an @ placeholder
    that resolves to "(2 + relics_played_this_game)" — the value the
    spell would use right now if cast."""

    def custom_cardtext(self):
        text = self.data.description
        n = 2 + getattr(self.controller, "relics_played_this_game", 0) if self.controller else 2
        if "@" in text:
            return text.replace("@", str(n))
        return text

    def cardtext_entity_0(self):
        n = 2 + getattr(self.controller, "relics_played_this_game", 0) if self.controller else 2
        return n

    tags = {
        enums.CUSTOM_CARDTEXT: custom_cardtext,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }
