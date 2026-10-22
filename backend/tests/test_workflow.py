import pytest

from backend import db


def start(client, claim_id):
    return client.post(f"/api/claims/{claim_id}/start", json={"thread_id": "t-1"})


def decide(client, claim_id, decision, payout):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "reason": "The wording covers it.",
            "policy_section": "Section 3, Trip Delay",
        },
    )


def pay(client, claim_id, amount):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def sign_off(client, claim_id, handler_id):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def approve(client, claim_id, payout):
    start(client, claim_id)
    return decide(client, claim_id, "approve", payout)


def test_start(client):
    response = start(client, "CLM-1001")
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["thread_id"] == "t-1"
    assert start(client, "CLM-1001").status_code == 409


def test_steps(client):
    for kind, content in [("tool_call", "get_claim"), ("tool_result", "{}")]:
        response = client.post(
            "/api/claims/CLM-1001/steps", json={"kind": kind, "content": content}
        )
        assert response.status_code == 200
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [(step["kind"], step["content"]) for step in steps] == [
        ("tool_call", "get_claim"),
        ("tool_result", "{}"),
    ]
    assert all(step["created_at"] for step in steps)
    assert client.get("/api/claims/CLM-0000/steps").status_code == 404


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_decline_or_refer(client, decision):
    start(client, "CLM-1001")
    assert decide(client, "CLM-1001", decision, 50).status_code == 422
    response = decide(client, "CLM-1001", decision, 0)
    assert response.json()["status"] == "decided"
    assert response.json()["decision"] == decision
    assert pay(client, "CLM-1001", 10).status_code == 409


def test_decide_needs_a_claim_in_progress(client):
    assert decide(client, "CLM-1001", "decline", 0).status_code == 409
    assert decide(client, "CLM-0000", "decline", 0).status_code == 404


def test_approve_up_to_the_limit(client):
    response = approve(client, "CLM-1001", 420)
    assert response.json()["status"] == "decided"
    assert response.json()["payout"] == 420.0
    assert pay(client, "CLM-1001", 400).status_code == 422
    paid = pay(client, "CLM-1001", 420)
    assert paid.status_code == 200
    assert paid.json()["paid_amount"] == 420.0
    assert paid.json()["paid_at"]
    assert pay(client, "CLM-1001", 420).status_code == 409


def test_approve_exactly_the_limit(client):
    assert approve(client, "CLM-1002", 1000).json()["status"] == "decided"
    assert pay(client, "CLM-1002", 1000).status_code == 200


def test_payment_over_the_limit_is_held(client):
    response = approve(client, "CLM-1002", 1150)
    assert response.json()["status"] == "waiting_for_sign_off"
    refused = pay(client, "CLM-1002", 1150)
    assert refused.status_code == 403
    assert "sign-off" in refused.json()["detail"]
    assert client.get("/api/claims/CLM-1002").json()["paid_amount"] is None


def test_sign_off_pays(client):
    approve(client, "CLM-1002", 1150)
    response = sign_off(client, "CLM-1002", "HND-01")
    assert response.status_code == 200
    claim = response.json()
    assert claim["status"] == "decided"
    assert claim["paid_amount"] == 1150.0
    assert claim["signed_off_by"] == {"handler_id": "HND-01", "name": "Dana Whitfield"}
    assert claim["signed_off_at"]
    assert pay(client, "CLM-1002", 1150).status_code == 409
    assert sign_off(client, "CLM-1002", "HND-01").status_code == 409


def test_sign_off_errors(client):
    approve(client, "CLM-1002", 1150)
    assert sign_off(client, "CLM-1002", "HND-99").status_code == 404
    assert sign_off(client, "CLM-1001", "HND-01").status_code == 409
    with db.connect() as connection:
        connection.execute(
            "UPDATE handlers SET record = json_set(record, "
            "'$.can_approve_over_limit', json('false')) WHERE handler_id = 'HND-03'"
        )
    refused = sign_off(client, "CLM-1002", "HND-03")
    assert refused.status_code == 403
    assert refused.json()["detail"].startswith("Priya Raman")


def test_a_decided_claim_is_final(client):
    approve(client, "CLM-1001", 420)
    assert decide(client, "CLM-1001", "decline", 0).status_code == 409
    assert start(client, "CLM-1001").status_code == 409


def test_reseed_resets_the_queue(client):
    approve(client, "CLM-1001", 420)
    client.post("/api/claims/CLM-1001/steps", json={"kind": "model", "content": "x"})
    db.seed()
    assert client.get("/api/claims/CLM-1001").json()["status"] == "waiting"
    assert client.get("/api/claims/CLM-1001/steps").json() == []
