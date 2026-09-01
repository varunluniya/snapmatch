# SnapMatch

_Flags product photo/description mismatches before listings go live._


Catches "item doesn't match the photo" *before* a product ever goes live —
instead of processing the resulting returns faster after a customer is
already disappointed. Runnable end to end:

```
pip install scikit-learn
python3 run_demo.py
```

## The reframe

An e-commerce team asked for an AI to "process return requests faster."
Taken at face value, that's a system that auto-approves straightforward
returns — it makes the same volume of returns move through the queue
quicker but does nothing about *why* they're happening. 70% of returns in
this scenario were logged as "item did not match description," which means
the real problem sits upstream, in the listing process, not the returns
process. This project is the upstream fix: flag mismatches between a
product's photo and its written description before the listing is
published.

## What it does

1. **`mismatch_detector.py`** — compares each listing's written description
   against a caption of its actual photo, using TF-IDF cosine similarity, and
   flags anything below a similarity threshold for human review before it
   goes live.
2. **`historical_returns.py`** — mines historical return data to rank product
   categories by how much of their return volume is specifically
   description-mismatch driven, so review effort gets prioritized where it
   actually pays off (see `run_demo.py`'s output — Jackets and Electronics
   run ~60% mismatch-driven vs. ~27-29% for Footwear and Home Goods).

Run `run_demo.py` and both pieces run together: 8 sample listings get
checked (4 deliberately mismatched, 4 matched, so the detector has real
signal to catch), then the category risk ranking prints below it.

## Honest scope note

A real deployment replaces the hand-written `image_caption` field with an
actual vision-language model's caption of the product photo (GPT-4V, Claude
with vision, LLaVA, etc.) — this sandbox has no image model available, so
`sample_listings.py` supplies pre-written captions standing in for what a VLM
would say. The comparison logic downstream (TF-IDF cosine similarity +
threshold) is real and provider-agnostic: swap in a real captioning call and
nothing else changes. Historical data's second job — training/fine-tuning
signal for the detector itself — is noted in `historical_returns.py` but not
implemented, since that needs a real labeled image/description/return
dataset this sandbox doesn't have.

## Files

- `mismatch_detector.py` — the comparison + flagging logic.
- `sample_listings.py` — 8 sample product listings (4 mismatched, 4 matched).
- `historical_returns.py` — synthetic historical return log + category risk
  ranking.
- `run_demo.py` — runs both pieces and prints the full report.
- `run_output.txt` — captured output from an actual run.

## Why this exists

Most "process returns faster" projects optimize the wrong end of the pipeline — they speed up handling complaints instead of preventing them. The interesting move here is upstream: catch the mismatch before the listing ever goes live, and measure success by a drop in return volume, not by how fast tickets close. This repo is that idea, made runnable: identify the upstream cause, flag mismatches before listing, and be specific about what data (image-description pairs, historical return data) it takes to do it.
