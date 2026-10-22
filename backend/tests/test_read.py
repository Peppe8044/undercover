import pytest


def test_list_claims(client):
    claims = client.get("/api/claims").json()
    assert [claim["claim_id"] for claim in claims] == [
        f"CLM-{number}" for number in range(1001, 1026)
    ]
    assert {claim["status"] for claim in claims} == {"waiting"}
    assert {claim["decision"] for claim in claims} == {None}
    assert claims[0] == {
        "claim_id": "CLM-1001",
        "customer_name": "Maya Patel",
        "claim_type": "trip_delay",
        "summary": "Flight home canceled by the airline, rebooked the next morning",
        "amount_claimed": 420.0,
        "submitted_on": "2026-06-24",
        "status": "waiting",
        "decision": None,
        "payout": None,
    }


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["story"].startswith("My flight home from Rome")
    assert len(claim["items"]) == 3
    assert sum(item["amount"] for item in claim["items"]) == 420.0
    assert len(claim["documents"]) == 4
    assert claim["status"] == "waiting"
    assert claim["decision"] is None
    assert claim["paid_amount"] is None
    assert claim["signed_off_by"] is None


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["plan_details"]["deductible"] == 50.0
    assert policy["add_on_details"] == []
    assert policy["deductible_applies_to"] == ["baggage", "emergency_medical"]


def test_get_policy_with_add_ons(client):
    policies = [
        client.get(f"/api/policies/POL-{number}").json() for number in range(2001, 2051)
    ]
    policy = next(policy for policy in policies if policy["add_ons"])
    assert [add_on["add_on"] for add_on in policy["add_on_details"]] == policy[
        "add_ons"
    ]


def test_get_customer(client):
    customer = client.get("/api/customers/CUS-3001").json()
    assert customer["name"] == "Maya Patel"
    assert [claim["claim_id"] for claim in customer["previous_claims"]] == ["CLM-0412"]


def test_list_handlers(client):
    handlers = client.get("/api/handlers").json()
    assert [handler["name"] for handler in handlers] == [
        "Dana Whitfield",
        "Marcus Oyelaran",
        "Priya Raman",
    ]


def test_get_instructions(client):
    text = client.get("/api/instructions").json()["text"]
    assert text.startswith("# The UnderCover Agent")
    assert "Version 2026.1" in text
    assert "manual" not in text.lower()


@pytest.mark.parametrize(
    "path",
    ["/api/claims/CLM-0000", "/api/policies/POL-0000", "/api/customers/CUS-0000"],
)
def test_unknown_ids(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["detail"].endswith("was not found.")
