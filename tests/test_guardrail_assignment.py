"""
Guide 4 Assignment 2 ("RAG with Guardrails") applied to SnapMatch's own
seller-note generator: one query that passes cleanly, one that fires the
guardrail, and one genuine edge case.
"""
import pytest

from gen4 import KnowledgeBase, LLMClient, Memory
from service import SnapMatchService


@pytest.fixture
def svc():
    return SnapMatchService(Memory(), KnowledgeBase.from_dir("knowledge"), LLMClient(provider="offline"))


def test_passing_query_note_for_a_genuinely_held_listing(svc):
    """A correctly-worded hold note (never claims the listing is live) clears unchanged."""
    draft = "Listing held before going live: the listing says red but the photo shows brown (color). Please correct."
    out = svc._guarded(draft, True, draft, passages=[])
    assert out == draft
    assert "guardrail replaced" not in out


def test_guardrail_fires_when_draft_claims_the_held_listing_is_live(svc):
    """The exact Air Canada failure shape: a fluent, confident statement that
    contradicts the real system state (here: the listing was held, not published)."""
    bad_draft = "Good news, your listing is now live and visible to buyers!"
    fallback = "Listing held before going live: please correct the photo or description, then resubmit."
    out = svc._guarded(bad_draft, True, fallback, passages=[])
    assert out != bad_draft
    assert "guardrail replaced" in out
    assert "held" in out.lower()


def test_edge_case_ambiguous_wording_that_implies_publication(svc):
    """Genuine edge case: the draft never says the word 'live', but 'is published'
    carries the same false implication for a listing that was actually held."""
    ambiguous_draft = "Your listing is published; a couple of small details need a follow-up edit."
    fallback = "Listing held before going live: please correct the photo or description, then resubmit."
    out = svc._guarded(ambiguous_draft, True, fallback, passages=[])
    assert out != ambiguous_draft
    assert "held" in out.lower()
