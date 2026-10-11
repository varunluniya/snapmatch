"""
Incremental-loading fix: metrics() backs the /metrics API endpoint (app.py), so it can
be polled on a schedule -- re-pulling and re-scanning every decision this
system has ever logged on every poll is the classic full-rescan mistake. These tests
prove the incremental replacement (running totals, merged from only the
NEW outcomes since the last watermark) matches a from-scratch recompute
and stays idempotent across repeated polls with nothing new.
"""
from gen4 import KnowledgeBase, LLMClient, Memory
from service import SnapMatchService


def _svc():
    return SnapMatchService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))


def test_metrics_is_idempotent_no_double_counting():
    svc = _svc()
    for k in range(6):
        r = svc.check(f"h{k}", "Footwear", "Black boots", "Brown boots")
        svc.review(r["decision_id"], "mismatch" if k < 2 else "match")
    for k in range(4):
        r = svc.check(f"p{k}", "Footwear", "White sneakers", "White sneakers")
        svc.record_return(r["decision_id"], "item_did_not_match_description" if k < 1 else "changed_mind")

    first = svc.metrics()
    second = svc.metrics()
    third = svc.metrics()
    assert first == second == third


def test_metrics_picks_up_new_outcomes_after_more_are_recorded():
    svc = _svc()
    for k in range(3):
        r = svc.check(f"h{k}", "Footwear", "Black boots", "Brown boots")
        svc.review(r["decision_id"], "match")
    first = svc.metrics()
    assert first["reviewed"] == 3

    for k in range(3, 7):
        r = svc.check(f"h{k}", "Footwear", "Black boots", "Brown boots")
        svc.review(r["decision_id"], "match")
    second = svc.metrics()
    assert second["reviewed"] == 7


def test_metrics_matches_a_from_scratch_recompute():
    """Cross-check the incremental totals against an independent, full
    re-derivation straight from memory.decisions() -- the thing metrics()
    used to do on every call -- to prove the fix is mathematically
    equivalent, not just internally consistent."""
    svc = _svc()
    for k in range(8):
        r = svc.check(f"h{k}", "Footwear", "Black boots", "Brown boots")
        svc.review(r["decision_id"], "mismatch" if k < 3 else "match")
    for k in range(5):
        r = svc.check(f"p{k}", "Footwear", "White sneakers", "White sneakers")
        svc.record_return(r["decision_id"], "item_did_not_match_description" if k < 2 else "changed_mind")

    incremental = svc.metrics()

    done = svc.memory.decisions(system="snapmatch", with_outcome=True)
    held = [d for d in done if d["output"]["status"] == "hold_for_review" and "review" in d["outcome"]]
    pub = [d for d in done if d["output"]["status"] == "publish" and "return_reason" in d["outcome"]]
    full_recompute = {
        "review_precision": round(sum(d["outcome"]["review"] == "mismatch" for d in held) / len(held), 4),
        "missed_mismatch_returns": sum(d["outcome"]["return_reason"] == "item_did_not_match_description"
                                       for d in pub),
        "reviewed": len(held), "published_with_returns": len(pub),
    }
    assert incremental == full_recompute
