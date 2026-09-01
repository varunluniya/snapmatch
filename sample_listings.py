"""
Sample listings: a mix of genuinely matched and genuinely mismatched
description/image-caption pairs, so the detector has real signal to work
with. image_caption stands in for a vision-language model's description
of the actual product photo (see mismatch_detector.py docstring).
"""

from mismatch_detector import Listing

LISTINGS = [
    Listing("L-1001", "Jackets",
            "Red leather jacket with silver zippers, size M, genuine cowhide leather.",
            "A red leather jacket with silver zipper details, medium size, cowhide texture."),
    Listing("L-1002", "Jackets",
            "Maroon suede jacket, size L, soft suede fabric with button closure.",
            "A red leather jacket with silver zipper details, worn by a model outdoors."),
    Listing("L-1003", "Footwear",
            "White canvas sneakers with rubber sole, lace-up closure, unisex sizing.",
            "White canvas sneakers with a rubber sole, laces, casual unisex shoe."),
    Listing("L-1004", "Footwear",
            "Black leather ankle boots with a 2-inch heel and side zipper.",
            "White canvas sneakers, lace-up, casual style, worn with jeans."),
    Listing("L-1005", "Electronics",
            "Wireless over-ear headphones, noise cancelling, 30-hour battery life, black.",
            "Black over-ear wireless headphones with cushioned ear cups, noise cancelling."),
    Listing("L-1006", "Electronics",
            "Compact bluetooth speaker, waterproof, 12-hour playtime, blue colorway.",
            "Black over-ear wireless headphones sitting on a wooden desk."),
    Listing("L-1007", "Home Goods",
            "Ceramic coffee mug, 12oz capacity, dishwasher safe, matte white finish.",
            "A matte white ceramic mug, medium size, dishwasher safe, plain design."),
    Listing("L-1008", "Home Goods",
            "Stainless steel french press coffee maker, 34oz, double-wall insulated.",
            "A matte white ceramic mug sitting on a kitchen counter."),
]
