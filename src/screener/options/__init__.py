"""Option contract selection for an existing stock trade plan.

This package does not decide WHETHER to use options. It answers a narrower
question: given a directional swing plan that already has an entry, a stop and
a holding period, which contract expresses it least badly, and what does that
expression cost?

The costs are computed and displayed rather than buried, because they are the
whole argument. An option converts a position that would have lost 5% into one
that can lose most of its premium, and it charges rent every day the thesis
takes to work.
"""
