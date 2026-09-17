"""Marketing measurement under a decision standard.

Not a library of marketing formulas. A set of tools that each answer a decision a budget has to
take, and that **refuse to return a number when the assumption behind it does not hold.**

The thesis of the whole package is one sentence: almost every figure in a marketing report is a
correct calculation of the wrong quantity. Attribution allocates credit without a counterfactual,
return on ad spend counts revenue that was coming anyway, and a test declared on the first
favourable Monday has spent its error rate several times over. None of those are arithmetic
mistakes. Each is the right arithmetic applied to a quantity nobody chose deliberately, and each
becomes visible the moment the quantity is written down as arithmetic rather than as a slide.

Every table is produced by :mod:`mktlab.synth`, a seeded generator whose parameters are written
down - including the one column no real account has: how likely each user was to convert before
any marketing happened.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
