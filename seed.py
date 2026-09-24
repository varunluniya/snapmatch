#!/usr/bin/env python3
"""
Seed SnapMatch's memory with 6 months of synthetic listing history.

    python seed.py [--reset] [--if-empty]

600 listings from 40 sellers across the four categories, run through the
real service in date order. Each listing's photo caption either agrees with
the description (sometimes using a different shade in the same colour
family) or genuinely conflicts on one attribute. Held listings get a
reviewer verdict; published listings sometimes come back as returns. Four
sellers are sloppy and mismatch three times as often, so the seller-strike
memory has something to find. All data is synthetic.
"""

from pathlib import Path

from attributes import COLOR_FAMILIES
from gen4 import Memory
from gen4.seedkit import already_seeded, args, iso, mark
from service import SnapMatchService

N, DAYS = 600, 180
CATALOG = {
    "Jackets": {"types": ["jacket", "blazer", "coat", "parka"], "materials": ["leather", "suede", "denim", "wool", "polyester"],
                "extras": ["with zip front", "with two side pockets", "slim fit", "with button closure"], "mismatch": 0.18},
    "Footwear": {"types": ["sneakers", "boots", "sandals"], "materials": ["leather", "canvas", "suede"],
                 "extras": ["with rubber sole", "lace-up", "with cushioned insole", "ankle height"], "mismatch": 0.08},
    "Electronics": {"types": ["headphones", "speaker", "earphones", "soundbar"], "materials": ["plastic"],
                    "extras": ["wireless, 30-hour battery", "bluetooth 5.3", "with noise cancelling", "with USB-C charging"],
                    "mismatch": 0.15},
    "Home Goods": {"types": ["mug", "plate", "bottle", "cup"], "materials": ["ceramic", "steel", "glass", "plastic"],
                   "extras": ["dishwasher safe", "500 ml", "set of two", "matte finish"], "mismatch": 0.06},
}
COLORS = ["black", "white", "red", "blue", "brown", "grey", "green", "beige", "maroon", "pink"]
SELLERS = [f"S-{k:03d}" for k in range(1, 41)]
SLOPPY = {"S-007", "S-019", "S-026", "S-033"}


def shade(rng, family):
    return rng.choice(sorted(COLOR_FAMILIES[family]))


def make(rng, i):
    cat = rng.choice(list(CATALOG))
    spec = CATALOG[cat]
    seller = rng.choice(SELLERS)
    typ, mat, col, extra = rng.choice(spec["types"]), rng.choice(spec["materials"]), rng.choice(COLORS), rng.choice(spec["extras"])
    p_bad = spec["mismatch"] * (3 if seller in SLOPPY else 1)
    bad = rng.random() < p_bad
    c_typ, c_mat, c_col = typ, mat, shade(rng, col) if rng.random() < 0.3 else col
    changed = None
    if bad:
        changed = rng.choices(["color", "material", "type"], [0.5, 0.3, 0.2])[0]
        if changed == "material" and len(spec["materials"]) == 1:
            changed = "color"
        if changed == "color":
            c_col = rng.choice([c for c in COLORS if c != col])
        elif changed == "material":
            c_mat = rng.choice([m for m in spec["materials"] if m != mat])
        else:
            c_typ = rng.choice([t for t in spec["types"] if t != typ])
    desc = f"{col.title()} {mat} {typ} {extra}."
    cap = rng.choice([f"A {c_col} {c_mat} {c_typ} photographed on a plain background.",
                      f"{c_col.title()} {c_mat} {c_typ}, front view.",
                      f"Product photo of a {c_col} {c_typ} made of {c_mat}."])
    return {"listing_id": f"L-{20000 + i}", "category": cat, "seller_id": seller,
            "description": desc, "image_caption": cap}, bad, changed


def main():
    a, rng = args("data/snapmatch.db", "Seed SnapMatch with synthetic listing history")
    Path(a.db).parent.mkdir(parents=True, exist_ok=True)
    mem = Memory(a.db)
    if a.if_empty and already_seeded(mem):
        print(f"{a.db} already has data -- skipping seed")
        return
    svc = SnapMatchService(memory=mem)
    c = {"listings": 0, "true_mismatches": 0, "held": 0, "held_correct": 0, "false_alarms": 0,
         "published": 0, "returns_mismatch": 0, "returns_other": 0}
    for i in range(N):
        days_ago = DAYS - i * DAYS / N
        listing, bad, _ = make(rng, i)
        r = svc.check(**listing)
        c["listings"] += 1
        c["true_mismatches"] += bad
        outcome_ts = None
        if r["status"] == "hold_for_review":
            c["held"] += 1
            svc.review(r["decision_id"], "mismatch" if bad else "match")
            c["held_correct" if bad else "false_alarms"] += 1
            outcome_ts = iso(days_ago - 0.5)
        else:
            c["published"] += 1
            p_ret = 0.45 if bad else 0.07
            if rng.random() < p_ret:
                reason = "item_did_not_match_description" if (bad or rng.random() < 0.12) else \
                    rng.choice(["wrong_size", "changed_mind", "defective"])
                svc.record_return(r["decision_id"], reason)
                c["returns_mismatch" if reason == "item_did_not_match_description" else "returns_other"] += 1
                outcome_ts = iso(max(0.1, days_ago - rng.uniform(5, 20)))
        mem.backdate(r["decision_id"], iso(days_ago), outcome_ts)
    mark(mem, "snapmatch", a.seed, c)
    print(f"seeded {a.db}: {c}")
    print("thresholds:", {x["category"]: x["hold_threshold"] for x in svc.categories()})
    print("repeat-offender sellers:", [x for x in SELLERS if svc.repeat_offender(x)],
          "(truly sloppy:", sorted(SLOPPY), ")")


if __name__ == "__main__":
    main()
