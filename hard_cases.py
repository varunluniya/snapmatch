"""
Hard cases: mismatches that share most of their words (v1's blind spot) and
genuine matches phrased differently (so v2 must not over-flag).
Each tuple: (id, category, description, photo caption, is_mismatch)
"""

HARD_CASES = [
    ("H-01", "Footwear", "Black leather ankle boots with a 2-inch heel and side zipper.",
     "Brown leather ankle boots with a 2-inch heel and a side zipper.", True),
    ("H-02", "Home Goods", "Stainless steel water bottle, 750ml, matte black.",
     "Matte black plastic water bottle, 750ml.", True),
    ("H-03", "Jackets", "Navy wool overcoat, size L, two-button closure.",
     "A navy blue wool overcoat with a two-button front.", False),
    ("H-04", "Jackets", "Red leather jacket, size M.", "A crimson leather jacket, medium size.", False),
    ("H-05", "Home Goods", "Ceramic dinner plate set, 4 pieces, white.",
     "Four white ceramic dinner plates stacked.", False),
    ("H-06", "Jackets", "Olive green cotton field jacket with four front pockets.",
     "A khaki cotton field jacket with four pockets on the front.", False),
    ("H-07", "Electronics", "Grey fabric bluetooth soundbar, 2.1 channel.",
     "A black bluetooth soundbar with a subwoofer.", True),
]
