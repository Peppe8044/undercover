import runpy
import sys

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main
from backend.main import app

client = TestClient(app)


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


def tool_call(name, **args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": name}])


def decision(claim_id, verdict, payout):
    return tool_call(
        "decide_claim",
        claim_id=claim_id,
        decision=verdict,
        payout=payout,
        reason="The wording covers it.",
        policy_section="Section 3, Trip Delay",
    )


def stub(*replies):
    return StubModel(messages=iter(replies))


def test_approve_and_pay():
    reply = main.run(
        "CLM-1001",
        "thread-1",
        stub(
            tool_call("get_claim", claim_id="CLM-1001"),
            decision("CLM-1001", "approve", 420),
            tool_call("pay_claim", claim_id="CLM-1001", amount=420),
            AIMessage(content="Approved, $420.00."),
        ),
    )
    assert reply == "Approved, $420.00."
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["thread_id"] == "thread-1"
    assert claim["paid_amount"] == 420.0
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [step["kind"] for step in steps] == [
        "tool_call",
        "tool_result",
        "tool_call",
        "tool_result",
        "tool_call",
        "tool_result",
        "model",
    ]
    assert steps[0]["content"] == 'get_claim {"claim_id": "CLM-1001"}'
    assert steps[1]["content"].startswith('get_claim: {"claim_id":"CLM-1001"')


def test_payment_over_the_limit_is_held():
    main.run(
        "CLM-1002",
        "thread-2",
        stub(
            decision("CLM-1002", "approve", 1150),
            tool_call("pay_claim", claim_id="CLM-1002", amount=1150),
            AIMessage(content="Approved, $1,150.00, waiting for sign-off."),
        ),
    )
    claim = client.get("/api/claims/CLM-1002").json()
    assert claim["status"] == "waiting_for_sign_off"
    assert claim["paid_amount"] is None
    results = [
        step["content"]
        for step in client.get("/api/claims/CLM-1002/steps").json()
        if step["kind"] == "tool_result"
    ]
    assert results[-1].startswith("pay_claim: Refused (403)")


def test_decline():
    main.run(
        "CLM-1003",
        "thread-3",
        stub(decision("CLM-1003", "decline", 0), AIMessage(content="Declined.")),
    )
    claim = client.get("/api/claims/CLM-1003").json()
    assert claim["status"] == "decided"
    assert claim["decision"] == "decline"
    assert claim["payout"] == 0


def test_tools_read_through_the_api():
    assert '"plan":"premium"' in main.get_policy.invoke({"policy_id": "POL-2001"})
    assert "Maya Patel" in main.get_customer.invoke({"customer_id": "CUS-3001"})
    assert main.get_claim.invoke({"claim_id": "CLM-0000"}) == (
        "Refused (404): CLM-0000 was not found."
    )


def test_work_queue_takes_waiting_claims(monkeypatch, capsys):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t"})
    worked = []
    monkeypatch.setattr(
        main, "run", lambda claim_id, thread_id: worked.append(claim_id) or "done"
    )
    main.work_queue([])
    assert worked == [f"CLM-{number}" for number in range(1002, 1026)]
    assert "CLM-1002: done" in capsys.readouterr().out


def test_command_takes_named_claims(monkeypatch):
    worked = []
    monkeypatch.setattr(main, "work_queue", worked.extend)
    monkeypatch.setattr(sys, "argv", ["agent", "CLM-1001", "CLM-1003"])
    runpy.run_module("agent", run_name="__main__")
    assert worked == ["CLM-1001", "CLM-1003"]


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    assert main.model().reasoning_effort == "low"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
