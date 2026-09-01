"""
Historical return data + pattern-mining.

Historical return data does
two jobs here -- (1) find which product categories have high
mismatch-driven return rates, so pre-listing review effort gets prioritized
where it matters most, and (2) serve as training/fine-tuning signal for the
detector itself (noted, not implemented -- would require a real labeled
image-description-return dataset, not available in this sandbox).

This module implements job (1): a synthetic-but-structured historical
return log, with a category risk ranking built from it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass
class ReturnRecord:
    product_category: str
    return_reason: str  # e.g. "item_did_not_match_description", "wrong_size", "changed_mind"


# Synthetic historical returns, weighted so "Jackets" and "Electronics" show
# a clearly higher mismatch-driven return rate than "Home Goods" -- this is
# what a real system would mine from actual order/return history.
HISTORICAL_RETURNS: list[ReturnRecord] = (
    [ReturnRecord("Jackets", "item_did_not_match_description")] * 42
    + [ReturnRecord("Jackets", "wrong_size")] * 18
    + [ReturnRecord("Jackets", "changed_mind")] * 10
    + [ReturnRecord("Footwear", "item_did_not_match_description")] * 20
    + [ReturnRecord("Footwear", "wrong_size")] * 35
    + [ReturnRecord("Footwear", "changed_mind")] * 15
    + [ReturnRecord("Electronics", "item_did_not_match_description")] * 30
    + [ReturnRecord("Electronics", "defective")] * 12
    + [ReturnRecord("Electronics", "changed_mind")] * 8
    + [ReturnRecord("Home Goods", "item_did_not_match_description")] * 6
    + [ReturnRecord("Home Goods", "changed_mind")] * 14
    + [ReturnRecord("Home Goods", "wrong_size")] * 2
)


def mismatch_return_rate_by_category(records: list[ReturnRecord]) -> dict:
    """For each category, what fraction of its returns are specifically
    'item did not match description'? Categories high on this list are
    where pre-listing review effort should be prioritized."""
    totals = defaultdict(int)
    mismatches = defaultdict(int)
    for r in records:
        totals[r.product_category] += 1
        if r.return_reason == "item_did_not_match_description":
            mismatches[r.product_category] += 1

    rates = {
        cat: round(mismatches[cat] / totals[cat], 3)
        for cat in totals
    }
    return dict(sorted(rates.items(), key=lambda kv: kv[1], reverse=True))
