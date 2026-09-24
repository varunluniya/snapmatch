"""
Attribute-level comparison: the reason v2 catches mismatches v1 misses.

TF-IDF similarity measures word overlap, so "Black leather ankle boots with
a 2-inch heel" vs a photo of *brown* leather ankle boots scores 0.75 and
passes. The words agree on everything except the one attribute the customer
returns the item for. This module extracts normalised attributes (product
type, colour family, material) from both texts and reports conflicts.

Lexicons are deliberately small and editable; a live VLM/LLM extractor can
replace `extract()` without changing callers.
"""

from __future__ import annotations

import re

COLOR_FAMILIES = {
    "red": {"red", "crimson", "scarlet", "cherry"},
    "maroon": {"maroon", "burgundy", "wine", "oxblood"},
    "blue": {"blue", "navy", "cobalt", "azure", "indigo", "teal"},
    "black": {"black", "jet", "onyx"},
    "white": {"white", "ivory", "snow"},
    "brown": {"brown", "tan", "chocolate", "camel", "cognac"},
    "grey": {"grey", "gray", "charcoal", "slate"},
    "green": {"green", "olive", "khaki", "emerald"},
    "pink": {"pink", "rose", "blush"},
    "yellow": {"yellow", "mustard"},
    "beige": {"beige", "cream", "sand"},
    "purple": {"purple", "violet", "lavender"},
    "orange": {"orange", "rust"},
}
MATERIALS = {
    "leather": {"leather", "cowhide", "lambskin"},
    "suede": {"suede", "nubuck"},
    "canvas": {"canvas"},
    "denim": {"denim"},
    "wool": {"wool", "woollen", "woolen", "merino", "cashmere"},
    "cotton": {"cotton"},
    "polyester": {"polyester", "nylon"},
    "ceramic": {"ceramic", "porcelain", "stoneware"},
    "steel": {"steel", "stainless"},
    "glass": {"glass"},
    "plastic": {"plastic", "acrylic"},
    "wood": {"wood", "wooden", "bamboo", "oak"},
}
PRODUCT_TYPES = {
    "jacket": {"jacket", "blazer"},
    "coat": {"coat", "overcoat", "parka", "trench"},
    "sneaker": {"sneaker", "trainer"},
    "boot": {"boot"},
    "sandal": {"sandal", "flip-flop"},
    "headphones": {"headphone", "headset", "earphone"},
    "speaker": {"speaker", "soundbar"},
    "mug": {"mug", "cup"},
    "french_press": {"french press", "cafetiere", "coffee maker"},
    "plate": {"plate", "dish"},
    "bottle": {"bottle", "flask"},
}
# words that describe secondary parts, whose colour/material should not be read
# as the product's own (e.g. "silver zippers", "rubber sole")
SECONDARY = {"zipper", "zip", "sole", "button", "lace", "strap", "trim", "lining", "detail", "cup",
             "desk", "counter", "table", "floor", "background", "jeans", "model"}


def _stem(w: str) -> str:
    if w.endswith("es") and w[:-2].endswith(("ss", "sh", "ch")):
        return w[:-2]
    return w[:-1] if w.endswith("s") and not w.endswith("ss") and len(w) > 3 else w


def _words(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z][a-z\-]*", text.lower())]


def _match(words: list[str], text: str, table: dict, skip_secondary: bool) -> set[str]:
    found = set()
    joined = " ".join(words)
    for family, terms in table.items():
        for term in terms:
            if " " in term:
                if term in joined:
                    found.add(family)
                continue
            for i, w in enumerate(words):
                if w == term:
                    nxt = words[i + 1] if i + 1 < len(words) else ""
                    if skip_secondary and (nxt in SECONDARY):
                        continue
                    found.add(family)
    return found


def extract(text: str) -> dict:
    words = _words(text)
    return {
        "type": _match(words, text, PRODUCT_TYPES, skip_secondary=False),
        "color": _match(words, text, COLOR_FAMILIES, skip_secondary=True),
        "material": _match(words, text, MATERIALS, skip_secondary=True),
    }


def conflicts(description: str, caption: str) -> list[dict]:
    """A conflict = both texts name an attribute and share no value for it.
    Silence on one side is not a conflict (photos often omit material)."""
    d, c = extract(description), extract(caption)
    out = []
    for attr in ("type", "color", "material"):
        if d[attr] and c[attr] and not (d[attr] & c[attr]):
            # the secondary-object guard: "mug on a kitchen counter" should not
            # make "counter" a product; only disjoint *product* sets count.
            out.append({"attribute": attr, "listing_says": sorted(d[attr]), "photo_shows": sorted(c[attr])})
    return out
