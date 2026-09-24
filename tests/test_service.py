import pytest

from attributes import conflicts, extract
from gen4 import KnowledgeBase, LLMClient, Memory
from service import SnapMatchService


@pytest.fixture
def svc():
    return SnapMatchService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))


def test_shades_in_same_family_are_not_conflicts():
    assert conflicts("Red leather jacket", "A crimson leather jacket") == []
    assert conflicts("Navy wool coat", "A blue wool coat") == []


def test_secondary_parts_do_not_count_as_product_colour():
    assert extract("Red leather jacket with silver zippers")["color"] == {"red"}


def test_high_overlap_colour_mismatch_is_held_with_policy_cited(svc):
    r = svc.check("b1", "Footwear", "Black leather ankle boots with a 2-inch heel",
                  "Brown leather ankle boots with a 2-inch heel")
    assert r["status"] == "hold_for_review" and not r["v1_would_flag"]
    assert r["trace"]["retrieval"][0]["heading"] == "Colour conflict"
    assert "black" in r["seller_message"] and "brown" in r["seller_message"]


def test_category_risk_orders_thresholds(svc):
    assert svc.threshold("Jackets", None)["hold_threshold"] < svc.threshold("Home Goods", None)["hold_threshold"]


def test_false_alarm_loosens_and_miss_tightens(svc):
    base = svc.threshold("Footwear", None)["hold_threshold"]
    r = svc.check("f1", "Footwear", "Black boots", "Brown boots")
    svc.review(r["decision_id"], "match")
    assert svc.threshold("Footwear", None)["hold_threshold"] > base
    r2 = svc.check("f2", "Footwear", "White canvas sneakers", "White canvas sneakers")
    svc.record_return(r2["decision_id"], "item_did_not_match_description")
    svc.record_return(r2["decision_id"], "item_did_not_match_description")
    assert svc.memory.param_history("offset:Footwear")[-1]["reason"].startswith("missed mismatch")


def test_offsets_are_bounded(svc):
    for k in range(30):
        r = svc.check(f"z{k}", "Jackets", "Black jacket", "Brown jacket")
        svc.review(r["decision_id"], "match")
    assert svc.memory.get_param("offset:Jackets") <= 0.15


def test_repeat_offender_seller_gets_stricter_threshold(svc):
    for k in range(2):
        r = svc.check(f"s{k}", "Jackets", "Black jacket", "Brown jacket", seller_id="acme")
        svc.review(r["decision_id"], "mismatch")
    assert svc.threshold("Jackets", "acme")["seller_penalty"] > 0
    assert svc.threshold("Jackets", "other")["seller_penalty"] == 0


def test_caption_required_offline(svc):
    with pytest.raises(ValueError):
        svc.check("x", "Jackets", "Black jacket", image_url="https://example.com/a.jpg")
