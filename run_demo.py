"""
Run the full demo: check every sample listing for a description/image
mismatch, then rank product categories by historical mismatch-driven
return rate to show where pre-listing review should be prioritized.
"""

from mismatch_detector import check_batch
from sample_listings import LISTINGS
from historical_returns import HISTORICAL_RETURNS, mismatch_return_rate_by_category


def main():
    print("=" * 78)
    print("PRE-LISTING MISMATCH CHECK")
    print("=" * 78)
    results = check_batch(LISTINGS)
    for r in results:
        status = "FLAGGED FOR REVIEW" if r.flagged else "ok"
        print(f"[{status:^18}] {r.listing_id}  similarity={r.similarity:.2f}")
        print(f"    description: {r.description}")
        print(f"    image shows: {r.image_caption}")
        print()

    flagged = [r for r in results if r.flagged]
    print(f"-> {len(flagged)}/{len(results)} listings flagged before going live.\n")

    print("=" * 78)
    print("HISTORICAL MISMATCH-RETURN RATE BY CATEGORY (review prioritization)")
    print("=" * 78)
    rates = mismatch_return_rate_by_category(HISTORICAL_RETURNS)
    for category, rate in rates.items():
        print(f"  {category:15s} {rate:.1%} of returns are description mismatches")

    print()
    top_category = next(iter(rates))
    print(f"-> Prioritize pre-listing review capacity on '{top_category}' first -- "
          f"it has the highest historical mismatch-driven return rate.")


if __name__ == "__main__":
    main()
