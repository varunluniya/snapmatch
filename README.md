# SnapMatch

_Stops photo/description mismatches before a listing goes live, and learns how strict to be for each category and seller from reviews and returns._

[![ci](https://github.com/varunluniya/snapmatch/actions/workflows/ci.yml/badge.svg)](https://github.com/varunluniya/snapmatch/actions/workflows/ci.yml)

## What's new in v2: an intelligent, deployable service

| Layer | In SnapMatch |
|---|---|
| **Retrieval** | Review policy for the exact conflict found (type, colour or material) is cited and drives the seller message |
| **Context** | Category mismatch-return rate, seller strike count, and the resulting hold threshold |
| **Memory** | Every check, reviewer verdict, post-listing return, and seller record |
| **Feedback** | False alarms loosen a category and misses tighten it (bounded ±0.02 steps). Repeat-offender sellers get stricter checks |

**The intelligence gap v1 had:** TF-IDF passes mismatches that share most of their words. v2 adds attribute-level conflict detection (product type, colour family, material):

| | v1 | v2 |
|---|---|---|
| 15-listing eval set | 13/15 | **15/15** |
| "Black leather ankle boots…" vs photo of **brown** ones (similarity 0.75) | pass ✗ | **HOLD**: colour black→brown |
| "Stainless steel bottle…" vs photo of a **plastic** one (similarity 0.63) | pass ✗ | **HOLD**: material steel→plastic |
| crimson/red, navy/blue, olive/khaki | pass | pass (same colour family) |

Full framework write-up: [FRAMEWORK.md](FRAMEWORK.md).

## Run it

```bash
pip install -r requirements-dev.txt
uvicorn app:app --reload        # http://127.0.0.1:8000/docs
python -m pytest -q
python run_evals.py             # 16 cases x 3 runs, CI gate
python compare_v1_v2.py         # before/after proof
```

Docker: `docker build -t snapmatch . && docker run -p 8000:8000 -v snapmatch-data:/data snapmatch` · Render: `render.yaml` blueprint.
With `ANTHROPIC_API_KEY` set, you can send `image_url` instead of `image_caption`, and a live vision model captions the photo.

```bash
curl -X POST localhost:8000/check -H 'content-type: application/json' -d '{"listing_id":"L1","category":"Footwear","seller_id":"s9","description":"Black leather ankle boots, 2-inch heel","image_caption":"Brown leather ankle boots with a 2-inch heel"}'
```

| Endpoint | Purpose |
|---|---|
| `POST /check` · `POST /check/batch` | Publish or hold, with conflicts, risk, seller message, and trace |
| `POST /feedback/review` | Reviewer verdict on a held listing (`mismatch` / `match`) |
| `POST /feedback/return` | Post-listing return, with reason |
| `GET /categories` · `GET /metrics` | Live thresholds, review precision, missed mismatches |
| `GET /knowledge/search` · `/memory/facts` · `/params` · `/health` | Inspect each layer |

## Demo data

`python seed.py` fills `data/snapmatch.db` with synthetic history so every endpoint returns something meaningful on first run: 600 listings from 40 sellers over 6 months, reviewer verdicts on held listings, post-listing returns, learned per-category thresholds, and the sellers that tripped the repeat-offender rule.

```bash
python seed.py            # create data/snapmatch.db
python seed.py --reset    # rebuild it from scratch
```

The Docker image seeds `/data` on first boot (set `GEN4_SEED=0` to start empty). All of it is synthetic: no real customers, patients, tickets or model outputs. `GET /health` shows the dataset's counts.

---

## The original engine (v1)

The v1 demo still runs unchanged; the service wraps it.

_Flags product photo/description mismatches before listings go live._


Catches "item doesn't match the photo" *before* a product ever goes live —
instead of processing the resulting returns faster after a customer is
already disappointed. Runnable end to end:

```
pip install scikit-learn
python3 run_demo.py
```

### The reframe

An e-commerce team asked for an AI to "process return requests faster."
Taken at face value, that's a system that auto-approves straightforward
returns — it makes the same volume of returns move through the queue
quicker but does nothing about *why* they're happening. 70% of returns in
this scenario were logged as "item did not match description," which means
the real problem sits upstream, in the listing process, not the returns
process. This project is the upstream fix: flag mismatches between a
product's photo and its written description before the listing is
published.

### What it does

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

### Honest scope note

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

### Files

- `mismatch_detector.py` — the comparison + flagging logic.
- `sample_listings.py` — 8 sample product listings (4 mismatched, 4 matched).
- `historical_returns.py` — synthetic historical return log + category risk
  ranking.
- `run_demo.py` — runs both pieces and prints the full report.
- `run_output.txt` — captured output from an actual run.

### Why this exists

Most "process returns faster" projects optimize the wrong end of the pipeline — they speed up handling complaints instead of preventing them. The interesting move here is upstream: catch the mismatch before the listing ever goes live, and measure success by a drop in return volume, not by how fast tickets close. This repo is that idea, made runnable: identify the upstream cause, flag mismatches before listing, and be specific about what data (image-description pairs, historical return data) it takes to do it.
