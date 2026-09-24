#!/usr/bin/env python3
"""
SnapMatch eval gate. Segments:
  samples          the 8 original sample listings (4 mismatched, 4 matched)
  v1_blind_spot    mismatches with high word overlap that TF-IDF alone passes
  no_overflag      genuine matches phrased differently (synonyms, shades)
  learning         missed-mismatch returns tighten the category threshold
"""

from gen4 import KnowledgeBase, LLMClient, Memory
from gen4.evals import EvalCase, gate, print_and_exit, run_eval
from hard_cases import HARD_CASES
from sample_listings import LISTINGS
from service import SnapMatchService

MISMATCHED = {"L-1002", "L-1004", "L-1006", "L-1008"}


def fresh():
    return SnapMatchService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))


def cases():
    out = [EvalCase(l.listing_id, ("check", l.listing_id, l.product_category, l.description, l.image_caption),
                    l.listing_id in MISMATCHED, "samples") for l in LISTINGS]
    for hid, cat, d, c, bad in HARD_CASES:
        out.append(EvalCase(hid, ("check", hid, cat, d, c), bad, "v1_blind_spot" if bad else "no_overflag"))
    out.append(EvalCase("learn-tightens", ("learn",), True, "learning"))
    return out


def system(inp):
    svc = fresh()
    if inp[0] == "check":
        _, lid, cat, d, c = inp
        return svc.check(lid, cat, d, c)["status"] == "hold_for_review"
    before = svc.threshold("Home Goods", None)["hold_threshold"]
    for k in range(3):
        r = svc.check(f"x{k}", "Home Goods", "Bamboo cutting board", "A bamboo cutting board", seller_id="s1")
        svc.record_return(r["decision_id"], "item_did_not_match_description")
    t = svc.threshold("Home Goods", "s1")
    return t["hold_threshold"] < before and t["seller_penalty"] > 0


if __name__ == "__main__":
    report = run_eval(cases(), system, runs=3)
    ok, why = gate(report, min_accuracy=1.0, min_consistency=1.0)
    print_and_exit("SnapMatch", report, ok, why)
