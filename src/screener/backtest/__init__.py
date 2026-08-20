"""Backtesting: split discipline, simulation, and evaluation.

Nothing in this package decides whether a hypothesis is true. It produces the
numbers that the pre-registered criteria in docs/03-HYPOTHESES.md are applied
to, and it refuses to make that application easy to fudge -- the test split is
sealed behind an explicit budget check, and every run is recorded whether or
not its result was liked.
"""
