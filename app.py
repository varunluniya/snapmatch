"""
SnapMatch API.   uvicorn app:app --reload    ->  http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from gen4.api import common_router
from service import SnapMatchService

service = SnapMatchService()
app = FastAPI(title="SnapMatch", version="2.0.0",
              description="Catch photo/description mismatches before a listing goes live, and learn "
                          "per-category and per-seller strictness from reviews and returns.")
app.include_router(common_router(service, "snapmatch"))


class ListingIn(BaseModel):
    listing_id: str
    category: str
    description: str
    image_caption: str | None = None
    image_url: str | None = None
    seller_id: str | None = None


class ReviewIn(BaseModel):
    decision_id: str
    verdict: Literal["mismatch", "match"]


class ReturnIn(BaseModel):
    decision_id: str
    reason: str = "item_did_not_match_description"


@app.get("/", tags=["ops"])
def root():
    return {"service": "SnapMatch", "docs": "/docs",
            "flow": "POST /check -> POST /feedback/review (held) or /feedback/return (published)"}


@app.post("/check", tags=["decision"])
def check(body: ListingIn):
    try:
        return service.check(**body.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/check/batch", tags=["decision"])
def check_batch(body: list[ListingIn]):
    return [check(b) for b in body]


@app.post("/feedback/review", tags=["feedback"])
def review(body: ReviewIn):
    try:
        return service.review(body.decision_id, body.verdict)
    except KeyError:
        raise HTTPException(404, "unknown decision_id")


@app.post("/feedback/return", tags=["feedback"])
def returned(body: ReturnIn):
    try:
        return service.record_return(body.decision_id, body.reason)
    except KeyError:
        raise HTTPException(404, "unknown decision_id")


@app.get("/categories", tags=["feedback"])
def categories():
    return service.categories()


@app.get("/metrics", tags=["feedback"])
def metrics():
    return service.metrics()
