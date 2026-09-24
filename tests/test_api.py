import os
import tempfile

os.environ["GEN4_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["GEN4_LLM_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

c = TestClient(app)


def test_check_review_return_flow():
    r = c.post("/check", json={"listing_id": "L1", "category": "Jackets", "seller_id": "s1",
                               "description": "Maroon suede jacket", "image_caption": "A red leather jacket"}).json()
    assert r["status"] == "hold_for_review"
    assert c.post("/feedback/review", json={"decision_id": r["decision_id"], "verdict": "mismatch"}).status_code == 200
    ok = c.post("/check", json={"listing_id": "L2", "category": "Jackets",
                                "description": "Red leather jacket", "image_caption": "A red leather jacket"}).json()
    assert ok["status"] == "publish"
    assert c.post("/feedback/return", json={"decision_id": ok["decision_id"]}).status_code == 200
    assert c.get("/metrics").json()["missed_mismatch_returns"] == 1


def test_errors_and_catalog():
    assert c.post("/check", json={"listing_id": "L3", "category": "Jackets", "description": "x"}).status_code == 422
    assert c.post("/feedback/review", json={"decision_id": "nope", "verdict": "match"}).status_code == 404
    assert {x["category"] for x in c.get("/categories").json()} >= {"Jackets", "Footwear"}
    assert c.get("/health").json()["status"] == "ok"
