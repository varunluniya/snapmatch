"""
Pre-Listing Mismatch Detector

Catches image/description mismatches on product listings BEFORE they go
live, instead of processing the resulting "item did not match description"
returns faster after the fact. This is the extraordinary reframe: the
upstream cause of the return volume is the listing process, not the
returns process, so that's where the AI system goes.

Real deployment note: a production version would use a vision-language
model (e.g. GPT-4V, Claude with vision, LLaVA) to generate a caption
directly from the product photo, then compare that caption to the listed
description. This sandbox has no image model available, so
`image_caption` below is a stand-in for "what a VLM would say the photo
shows" -- supplied as text for each sample listing. The comparison logic
downstream (TF-IDF cosine similarity + threshold) is real and provider-
agnostic: swap in an actual VLM captioning call and everything else is
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


MISMATCH_THRESHOLD = 0.35  # similarity below this -> flag for review


@dataclass
class Listing:
    listing_id: str
    product_category: str
    description: str
    image_caption: str  # stand-in for VLM-generated caption of the actual photo


@dataclass
class MismatchResult:
    listing_id: str
    similarity: float
    flagged: bool
    description: str
    image_caption: str


def _similarity(description: str, image_caption: str) -> float:
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf = vectorizer.fit_transform([description, image_caption])
    except ValueError:
        # one or both texts were entirely stopwords / empty after vectorization
        return 0.0
    return float(cosine_similarity(tfidf[0], tfidf[1])[0][0])


def check_listing(listing: Listing) -> MismatchResult:
    sim = _similarity(listing.description, listing.image_caption)
    return MismatchResult(
        listing_id=listing.listing_id,
        similarity=round(sim, 3),
        flagged=sim < MISMATCH_THRESHOLD,
        description=listing.description,
        image_caption=listing.image_caption,
    )


def check_batch(listings: list[Listing]) -> list[MismatchResult]:
    return [check_listing(l) for l in listings]
