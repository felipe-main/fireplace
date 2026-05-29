import sys

# The action pipeline resolves nested triggers via Python recursion. A few
# legitimate, finite card chains go very deep - most notably Shudderwock
# (GIL_820), which repeats up to 30 battlecries, compounded by Shudderblock
# (TOY_501) and a large modern card pool. These finite chains can exceed
# CPython default recursion limit (1000) and raise a spurious RecursionError.
# Raise the limit so such chains complete; a genuinely unbounded loop still
# errors (cleanly) at the higher ceiling.
if sys.getrecursionlimit() < 10000:
    sys.setrecursionlimit(10000)
