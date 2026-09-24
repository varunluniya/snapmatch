#!/usr/bin/env python3
"""Prove-It: v1 (TF-IDF only) vs v2 (TF-IDF + attribute conflicts + category risk)
on the 8 original samples plus 7 hard cases."""

from gen4 import KnowledgeBase, LLMClient, Memory
from hard_cases import HARD_CASES
from mismatch_detector import Listing, check_listing
from sample_listings import LISTINGS
from service import SnapMatchService

MISMATCHED = {"L-1002", "L-1004", "L-1006", "L-1008"}
svc = SnapMatchService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))
rows = [(l.listing_id, l.product_category, l.description, l.image_caption, l.listing_id in MISMATCHED)
        for l in LISTINGS] + list(HARD_CASES)
v1_ok = v2_ok = 0
print(f"{'id':<7}{'truth':<10}{'sim':>6}  {'v1':<8}{'v2':<8}conflicts")
for lid, cat, d, c, bad in rows:
    v1 = check_listing(Listing(lid, cat, d, c)).flagged
    r = svc.check(lid, cat, d, c)
    v2 = r["status"] == "hold_for_review"
    v1_ok += v1 == bad
    v2_ok += v2 == bad
    conf = ", ".join(f"{x['attribute']}:{'/'.join(x['listing_says'])}->{'/'.join(x['photo_shows'])}" for x in r["conflicts"])
    print(f"{lid:<7}{'mismatch' if bad else 'match':<10}{r['similarity']:>6.2f}  "
          f"{('HOLD' if v1 else 'pass') + ('' if v1 == bad else '✗'):<8}{('HOLD' if v2 else 'pass') + ('' if v2 == bad else '✗'):<8}{conf}")
print(f"\nv1 correct: {v1_ok}/{len(rows)}   v2 correct: {v2_ok}/{len(rows)}")
