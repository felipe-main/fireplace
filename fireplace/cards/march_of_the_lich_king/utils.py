"""Shared text-rendering mixins for the March of the Lich King set.

Pattern mirrors `castle_nathria/utils.py:InfuseCardtextMixin` — the
class supplies the threshold/value (here as the `manathirst_threshold`
class attribute) and `custom_cardtext()` substitutes the printed `@`
placeholder at render time.
"""


class ManathirstCardtextMixin:
    """Substitute the `@` placeholder in printed text with the card's
    Manathirst threshold. Cards using this mixin must declare a
    class attribute `manathirst_threshold` (int).

    Several MotLK Manathirst cards print "(@)" where the threshold is
    cosmetic-only (the engine already gates the effect). This mixin
    surfaces the value so the rendered text shows the actual number.
    """

    manathirst_threshold = 0

    def custom_cardtext(self):
        text = self.data.description
        thr = getattr(self, "manathirst_threshold", 0)
        if "@" in text and thr:
            return text.replace("@", str(thr))
        return text


class HeroAttacksCardtextMixin:
    """Substitute `@` with the controller's `num_hero_attacks_this_game`
    counter. Used by RLK_825 Shockspitter ("Deal @ damage")."""

    def custom_cardtext(self):
        text = self.data.description
        if "@" not in text:
            return text
        ctrl = getattr(self, "controller", None)
        if ctrl is None:
            return text
        return text.replace("@", str(getattr(ctrl, "num_hero_attacks_this_game", 0)))
