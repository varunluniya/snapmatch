"""
SnapMatch intelligent service — pre-listing mismatch detection with Gen-4 layers.

    Retrieval  review policy for the specific conflict found (what to do about it)
    Context    category return-risk, seller track record, threshold in force
    Memory     every check, reviewer verdicts, post-listing returns, seller record
    Feedback   returns + reviewer verdicts move per-category thresholds in small,
               bounded, logged steps (low stakes, so no human approval needed)

v1 compared description and photo caption with TF-IDF only. v2 keeps that
signal and adds attribute-level conflicts (type, colour family, material),
which catch mismatches that share most of their words: black vs brown boots,
stainless vs plastic bottle.
"""

from __future__ import annotations

import os
from pathlib import Path

from attributes import conflicts as attribute_conflicts
from gen4 import Context, KnowledgeBase, LLMClient, Memory, Trace
from gen4 import feedback as fb
from historical_returns import HISTORICAL_RETURNS
from mismatch_detector import MISMATCH_THRESHOLD, _similarity

SYSTEM = "snapmatch"
HERE = Path(__file__).parent
CONFLICT_RISK = {"type": 0.9, "color": 0.6, "material": 0.5}
LOW_SIM_WEIGHT = 0.5
STEP = 0.02
OFFSET_BOUNDS = (-0.2, 0.15)
SELLER_STRIKES = 3
SELLER_RATE = 0.25
SELLER_PENALTY = 0.10
POLICY_HEADINGS = {"type": "Product type conflict", "color": "Colour conflict",
                   "material": "Material conflict"}


class SnapMatchService:
    def __init__(self, memory: Memory | None = None, kb: KnowledgeBase | None = None,
                 llm: LLMClient | None = None):
        self.memory = memory or Memory(os.environ.get("GEN4_DB", HERE / "data" / f"{SYSTEM}.db"))
        self.kb = kb or KnowledgeBase.from_dir(HERE / "knowledge")
        self.llm = llm or LLMClient()
        self._seed_category_risk()

    # -- knowledge graph seed: historical returns -> category risk -------------
    def _seed_category_risk(self) -> None:
        if self.memory.facts(predicate="return_counts"):
            return
        counts: dict[str, dict] = {}
        for r in HISTORICAL_RETURNS:
            c = counts.setdefault(r.product_category, {"mismatch": 0, "other": 0})
            c["mismatch" if r.return_reason == "item_did_not_match_description" else "other"] += 1
        for cat, c in counts.items():
            self.memory.add_fact(f"category:{cat}", "return_counts", c, source="historical_returns")

    def category_risk(self, category: str) -> float:
        c = self.memory.fact(f"category:{category}", "return_counts")
        if not c:
            all_c = [f["object"] for f in self.memory.facts(predicate="return_counts")]
            m = sum(x["mismatch"] for x in all_c)
            t = sum(x["mismatch"] + x["other"] for x in all_c)
            return round(m / t, 4) if t else 0.35
        return round(c["mismatch"] / max(1, c["mismatch"] + c["other"]), 4)

    def seller_strikes(self, seller_id: str) -> int:
        return int(self.memory.fact(f"seller:{seller_id}", "confirmed_mismatches", 0) or 0)

    def repeat_offender(self, seller_id: str) -> bool:
        """At least SELLER_STRIKES confirmed mismatches AND a confirmed-mismatch
        rate of SELLER_RATE or more across the seller's listings -- so a big,
        careful seller isn't penalised just for volume."""
        strikes = self.seller_strikes(seller_id)
        listings = max(1, len(self.memory.history(f"seller:{seller_id}", limit=10_000)))
        return strikes >= SELLER_STRIKES and strikes / listings >= SELLER_RATE

    def threshold(self, category: str, seller_id: str | None) -> dict:
        risk = self.category_risk(category)
        base = max(0.15, min(0.45, 0.45 - 0.4 * risk))
        offset = self.memory.get_param(f"offset:{category}", 0.0)
        penalty = SELLER_PENALTY if seller_id and self.repeat_offender(seller_id) else 0.0
        return {"category_mismatch_rate": risk, "base": round(base, 4), "learned_offset": offset,
                "seller_penalty": penalty, "hold_threshold": round(max(0.1, base + offset - penalty), 4)}

    # -- the check ----------------------------------------------------------------
    def check(self, listing_id: str, category: str, description: str,
              image_caption: str | None = None, image_url: str | None = None,
              seller_id: str | None = None) -> dict:
        trace = Trace()
        caption = image_caption
        if not caption and image_url:
            caption = self.llm.describe_image(
                image_url, "Describe this product photo in one sentence: product type, colour, material.",
                offline=lambda: "")
        if not caption:
            raise ValueError("image_caption is required unless a live vision model is configured "
                             "(set ANTHROPIC_API_KEY and pass image_url)")
        trace.model = {"caption_provider": "given" if image_caption else self.llm.last_provider}

        sim = round(_similarity(description, caption), 3)
        found = attribute_conflicts(description, caption)
        parts = [CONFLICT_RISK[c["attribute"]] for c in found]
        low_sim = max(0.0, (MISMATCH_THRESHOLD - sim) / MISMATCH_THRESHOLD) * LOW_SIM_WEIGHT
        if low_sim:
            parts.append(low_sim)
        keep = 1.0
        for p in parts:
            keep *= (1 - p)
        risk = round(1 - keep, 3)

        t = self.threshold(category, seller_id)
        trace.params = t
        hold = risk >= t["hold_threshold"]
        ctx = (Context()
               .add("category", category)
               .add("category_mismatch_rate", t["category_mismatch_rate"], "share of returns that are mismatches")
               .add("seller_strikes", self.seller_strikes(seller_id) if seller_id else None,
                    f">= {SELLER_STRIKES} confirmed mismatches and >= {SELLER_RATE:.0%} of listings tightens the threshold"))
        trace.context = ctx.as_dict()
        trace.memory = {"seller_history": len(self.memory.history(f"seller:{seller_id}")) if seller_id else 0}

        queries = [POLICY_HEADINGS[c["attribute"]] for c in found] or (
            ["Low text similarity with no attribute conflict"] if low_sim else ["Category risk"])
        passages = []
        for q in queries:
            passages += self.kb.search(q, k=1)
        trace.cite(passages)

        v1_flag = sim < MISMATCH_THRESHOLD
        seller_msg = self._seller_message(found, low_sim > 0) if hold else ""
        out = {"listing_id": listing_id, "status": "hold_for_review" if hold else "publish",
               "mismatch_risk": risk, "similarity": sim, "conflicts": found,
               "v1_would_flag": v1_flag, "seller_message": seller_msg, "image_caption": caption}
        did = self.memory.record_decision(SYSTEM, f"seller:{seller_id}" if seller_id else listing_id,
                                          {"category": category, "seller_id": seller_id,
                                           "listing_id": listing_id}, out)
        return {"decision_id": did, **out, "trace": trace.as_dict()}

    def _seller_message(self, found: list[dict], low_sim: bool) -> str:
        def offline():
            if not found:
                return ("Your description and photo share little detail. Please add the product type, "
                        "colour and material to the description so buyers know what they will receive.")
            bits = [f"the listing says {', '.join(c['listing_says'])} but the photo shows "
                    f"{', '.join(c['photo_shows'])} ({c['attribute']})" for c in found]
            return "Listing held before going live: " + "; ".join(bits) + \
                   ". Please correct the photo or the description, then resubmit."
        return self.llm.complete(f"Write a short, polite note to a seller. Conflicts: {found}. "
                                 f"Low similarity: {low_sim}. Ask them to fix photo or description.",
                                 offline=offline, max_tokens=120)

    # -- feedback --------------------------------------------------------------------
    def _load(self, decision_id: str) -> dict:
        d = self.memory.get_decision(decision_id)
        if not d:
            raise KeyError(decision_id)
        return d

    def _move(self, category: str, direction: int, reason: str) -> float:
        cur = self.memory.get_param(f"offset:{category}", 0.0)
        new = round(max(OFFSET_BOUNDS[0], min(OFFSET_BOUNDS[1], cur + direction * STEP)), 4)
        if new != cur:
            self.memory.set_param(f"offset:{category}", new, reason)
        return new

    def _strike(self, seller_id: str | None) -> None:
        if seller_id:
            self.memory.add_fact(f"seller:{seller_id}", "confirmed_mismatches",
                                 self.seller_strikes(seller_id) + 1)

    def review(self, decision_id: str, verdict: str) -> dict:
        """Reviewer verdict on a held listing: 'mismatch' (correct hold) or 'match' (false alarm)."""
        d = self._load(decision_id)
        cat, seller = d["features"]["category"], d["features"]["seller_id"]
        self.memory.record_outcome(decision_id, {"review": verdict})
        if verdict == "match":
            new = self._move(cat, +1, f"false alarm on {d['features']['listing_id']}")
            learned = "false alarm: category threshold loosened one step"
        else:
            self._strike(seller)
            new = self.memory.get_param(f"offset:{cat}", 0.0)
            learned = "confirmed mismatch: seller strike recorded"
        return {"learned": learned, "category_offset": new, "threshold": self.threshold(cat, seller)}

    def record_return(self, decision_id: str, reason: str) -> dict:
        """A published listing came back. Mismatch returns on published listings are misses."""
        d = self._load(decision_id)
        cat, seller = d["features"]["category"], d["features"]["seller_id"]
        self.memory.record_outcome(decision_id, {"return_reason": reason})
        counts = self.memory.fact(f"category:{cat}", "return_counts") or {"mismatch": 0, "other": 0}
        is_mismatch = reason == "item_did_not_match_description"
        counts["mismatch" if is_mismatch else "other"] += 1
        self.memory.add_fact(f"category:{cat}", "return_counts", counts)
        learned = "category return mix updated"
        if is_mismatch and d["output"]["status"] == "publish":
            self._move(cat, -1, f"missed mismatch on {d['features']['listing_id']}")
            self._strike(seller)
            learned = "missed mismatch: category threshold tightened one step, seller strike recorded"
        return {"learned": learned, "threshold": self.threshold(cat, seller)}

    def categories(self) -> list[dict]:
        cats = sorted(f["subject"].split(":", 1)[1] for f in self.memory.facts(predicate="return_counts"))
        return [{"category": c, **self.threshold(c, None)} for c in cats]

    def metrics(self) -> dict:
        done = self.memory.decisions(system=SYSTEM, with_outcome=True)
        held = [d for d in done if d["output"]["status"] == "hold_for_review" and "review" in d["outcome"]]
        pub = [d for d in done if d["output"]["status"] == "publish" and "return_reason" in d["outcome"]]
        return {"review_precision": fb.rate(sum(d["outcome"]["review"] == "mismatch" for d in held), len(held)),
                "missed_mismatch_returns": sum(d["outcome"]["return_reason"] == "item_did_not_match_description"
                                               for d in pub),
                "reviewed": len(held), "published_with_returns": len(pub)}
