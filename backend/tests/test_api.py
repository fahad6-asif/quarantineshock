"""API smoke tests in replay mode (cache only, zero network). Needs a warmed cache: scripts/warm_cache.py."""
import json
import os
import tempfile

import pytest

os.environ["QS_DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="qs_test_"), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.agent.graph import NODE_NAMES  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.rag import sources  # noqa: E402

NOTICES = [n["id"] for n in sources.notices()]


@pytest.fixture(scope="module")
def client():
    settings.provider_mode = "replay"
    settings.replay_delay = 0
    with TestClient(app) as c:
        yield c
    settings.reload()


def _run_and_collect(client, notice_id):
    r = client.post("/api/runs", json={"notice_id": notice_id})
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    events = []
    with client.stream("GET", f"/api/runs/{run_id}/events") as s:
        kind = None
        for line in s.iter_lines():
            if line.startswith("event:"):
                kind = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and kind == "step":
                events.append(json.loads(line[5:].strip()))
            elif line.startswith("data:") and kind == "end":
                break
    return run_id, events


def test_health_and_settings(client):
    assert client.get("/api/health").json() == {"ok": True}
    s = client.get("/api/settings").json()
    assert s["provider_mode"] == "replay" and "modes" in s


def test_notices_list_shape(client):
    ns = client.get("/api/notices").json()
    assert [n["id"] for n in ns] == NOTICES
    assert all({"title", "effective_date", "processed", "stated_area_sq_mi"} <= n.keys() for n in ns)


def test_order_is_enforced(client):
    client.post("/api/demo/reset", json={})
    r = client.post("/api/runs", json={"notice_id": NOTICES[1]})
    assert r.status_code == 409


def test_sse_emits_all_ten_nodes_in_order_and_endpoints(client):
    client.post("/api/demo/reset", json={})
    for nid in NOTICES[:5]:  # through June 18
        run_id, events = _run_and_collect(client, nid)
        done = [e["node"] for e in events if e["status"] == "done" and e["node"] != "run"]
        started = [e["node"] for e in events if e["status"] == "started" and e["node"] != "run"]
        assert started == NODE_NAMES, started
        assert done == NODE_NAMES, done
        assert events[-1]["node"] == "run" and events[-1]["status"] == "done"

    run = client.get(f"/api/runs/{run_id}").json()
    assert run["status"] == "done" and run["result"]["counts"]["newly_flagged"] == 4

    st = client.get(f"/api/state?notice_id={NOTICES[4]}").json()
    assert st["processed"] and st["zones"]["type"] == "FeatureCollection" and len(st["shipments"]) == 25
    by_id = {s["id"]: s for s in st["shipments"]}
    assert by_id["SR-1007"]["status"] == "REVIEW" and by_id["SR-1007"]["changed"]
    assert by_id["SR-1015"]["status"] == "UNCLEAR"
    assert by_id["SR-1011"]["status"] == "NOT_HOST"

    d = client.get(f"/api/shipments/SR-1007?notice_id={NOTICES[4]}").json()
    assert d["pack"] and d["evidence"]
    assert any(e["verification"] and e["verification"]["verified"] for e in d["evidence"])

    r = client.post("/api/shipments/SR-1007/decision", json={"decision": "hold", "notice_id": NOTICES[4], "note": "test"})
    assert r.status_code == 200 and r.json()["decision"] == "hold"
    assert "decision" in client.get("/api/audit.csv").text

    nd = client.get(f"/api/notices/{NOTICES[4]}").json()
    assert nd["extract"]["stated_area_sq_mi"] == 111 and nd["highlights"]

    src = client.get("/api/sources/cdfa_3417%23002").json()
    assert "4.5 mile radius" in src["text"]

    ev = client.post("/api/evals/run").json()
    assert ev["runs_evaluated"] == 5 and ev["grounding"]["total"] > 0


def test_chat_streams_answer_with_citations(client):
    with client.stream("POST", "/api/chat", json={"question": "Can I ship frozen avocado pulp from El Cajon?"}) as s:
        kind, done = None, None
        for line in s.iter_lines():
            if line.startswith("event:"):
                kind = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and kind == "done":
                done = json.loads(line[5:].strip())
    assert done and done["citations"]
    assert all(q["verified"] for q in done["quotes"])
    assert not done["certainty_warning"]


def test_unknown_provider_mode_rejected(client):
    assert client.post("/api/settings/provider", json={"mode": "nope"}).status_code == 400
