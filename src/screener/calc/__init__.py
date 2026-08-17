"""Pure calculation layer.

Every function in this package is a pure function of its inputs: no database
access, no network calls, no global state. This is deliberate. It is where
correctness is won, and it makes golden-value testing trivial.

NO-LOOKAHEAD CONTRACT
---------------------
Every function returning a series aligned to a bar index guarantees that the
value at position ``t`` is computable using only data at positions ``<= t``.

The one construct that cannot honour this naturally is swing-point detection,
which requires bars *after* the pivot to confirm it. Those functions therefore
return an explicit confirmation lag and are tested for leakage
(``tests/unit/calc/test_no_lookahead.py``).
"""
