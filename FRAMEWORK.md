# SnapMatch — FDE Framework Build Notes

## Part 1 — Problem Reframing

| Step | Output |
|---|---|
| Ordinary problem | "Process return requests faster." |
| Lever 1: Data liquidity | Return reasons sit in the returns system. Listing photos and descriptions sit in the catalogue. Nobody joins them. Seller track records are never used at listing time. |
| Lever 2: Network effect | Every reviewer verdict and every return adjusts the strictness of its category and seller. More listings mean sharper per-category thresholds and faster detection of repeat-offender sellers. |
| Lever 3: Algorithmic leverage | Attribute-level conflict detection (type, colour family, material) layered on text similarity. It catches the mismatches that share 60–75% of their words, which is exactly where word-overlap methods fail. |
| Lever 4: First principles × JTBD | The buyer's job is "receive what the photo promised". A return is a failure already paid for twice (shipping and trust). The cheapest fix is before publication. |
| Extraordinary problem | **Stop mismatched listings from going live** by checking that the photo and the description agree attribute by attribute, and **learn how strict to be** per category and per seller from what actually gets returned. |
| Rating | 5 / 5. It moves the system from speeding up returns to preventing them. |

## Part 2 — Design the Eval

**Outcome of intelligence**
- Zero missed mismatches on the curated set, including high-overlap mismatches (black vs brown boots, steel vs plastic bottle).
- Zero false holds on genuine matches phrased differently (crimson/red, navy/blue, olive/khaki).
- In production: a lower `missed_mismatch_returns` count and higher review precision (`GET /metrics`).

**EQ(PRE)**
| Angle | Hypothesis |
|---|---|
| Causal | Word overlap is used as a stand-in for "same product", but one differing attribute is what causes the return. |
| Context | One global threshold ignores that jackets and electronics carry about twice the mismatch-return share of footwear and home goods. |
| Consistency | A VLM caption varies run to run, so attribute extraction must be deterministic on whatever caption it gets. |

**EQ(POST), cheapest first**
1. Prompt: the VLM caption prompt asks for type, colour and material explicitly.
2. Context/retrieval: colour families and material lexicons, category-risk thresholds, and seller strikes.
3. Feedback: returns and reviewer verdicts move per-category offsets (±0.02 per step, bounded between −0.20 and +0.15).

**Executable:** `python run_evals.py` runs 16 cases × 3 runs across four segments (samples, v1_blind_spot, no_overflag, learning). CI fails below 100%.

## Part 3 — Gen-4 Architecture

| Layer | What SnapMatch does |
|---|---|
| Retrieval | `knowledge/listing_review_policy.md`. The section for the specific conflict found (type, colour or material) is cited and drives the seller message. |
| Context | Category mismatch-return rate (seeded from historical returns), the seller's confirmed-mismatch strikes, and the resulting hold threshold (Jackets and Electronics 0.21; Footwear and Home Goods about 0.34). |
| Memory | Every check, every reviewer verdict, every return, and seller strike counts as knowledge-graph facts. |
| Feedback | A false alarm loosens the category one step. A missed mismatch tightens it and adds a strike to the seller. Return mix updates the category risk. Every change is logged in `param_history`. |

The model: with `ANTHROPIC_API_KEY` set, pass `image_url` and a live vision model captions the photo. Without the key, the caller supplies `image_caption`. Either way, the attribute logic is deterministic.

## Part 4 — Implementation Plan

| Component | Priority | Estimate | Status |
|---|---|---|---|
| Attribute extractor + conflict rules | MVP | 0.5 day | done |
| Risk fusion (conflicts + low similarity) | MVP | 0.25 day | done |
| Category risk from return history, seller strikes | MVP | 0.5 day | done |
| Bounded feedback from reviews and returns | MVP | 0.5 day | done |
| Vision captioning via live model (optional) | MVP | 0.25 day | done |
| API, Docker, CI eval gate | MVP | 0.5 day | done |
| Size/fit attribute (the largest non-mismatch return reason) | nice-to-have | 1 day | future |
| LLM attribute extraction for long-tail vocabulary | nice-to-have | 1 day | future |
| Catalogue webhook integration (block publish until checked) | future | 2 days | future |

## Part 5 — Prove It

**Visible change** (`python compare_v1_v2.py`, output in `run_output_v1_vs_v2.txt`):

| | v1 (TF-IDF only) | v2 (intelligent) |
|---|---|---|
| Correct on 15 listings | 13 / 15 | **15 / 15** |
| High-overlap mismatches caught (black→brown boots, sim 0.75; steel→plastic bottle, sim 0.63) | 0 / 2 | **2 / 2** |
| False holds on synonym or shade matches | 0 | 0 |
| Tells the seller what to fix | no | yes: "listing says black but the photo shows brown (colour)" |

An outside observer would see the listings v1 let through, the ones that become "item did not match" returns, now held with a specific fix request. Strictness also tightens by itself in categories and for sellers where returns keep happening.
