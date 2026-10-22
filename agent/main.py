"""The UnderCover Agent."""

import json
import os
import uuid
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

BACKEND_URL = "http://localhost:8000"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=10)


def call(method: str, path: str, body: dict[str, Any] | None = None) -> str:
    """Call the backend for a tool, and return its reply or its refusal as text."""
    with backend() as client:
        response = client.request(method, path, json=body)
    if response.is_error:
        return f"Refused ({response.status_code}): {response.json()['detail']}"
    return response.text


@tool
def get_claim(claim_id: str) -> str:
    """Get a claim: the customer's story, the items claimed and the documents."""
    return call("GET", f"/api/claims/{claim_id}")


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy: its plan and limits, add-ons, covered trip and travelers."""
    return call("GET", f"/api/policies/{policy_id}")


@tool
def get_customer(customer_id: str) -> str:
    """Get a customer with their earlier claims."""
    return call("GET", f"/api/customers/{customer_id}")


@tool
def decide_claim(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    reason: str,
    policy_section: str,
) -> str:
    """Record your decision on a claim, with the payout (0 unless you approve),
    a reason of two or three sentences and the relevant policy section."""
    return call(
        "POST",
        f"/api/claims/{claim_id}/decision",
        {
            "decision": decision,
            "payout": payout,
            "reason": reason,
            "policy_section": policy_section,
        },
    )


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim its payout. Over $1,000 it waits for a sign-off."""
    return call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})


TOOLS = [get_claim, get_policy, get_customer, decide_claim, pay_claim]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def steps(message: BaseMessage) -> list[tuple[str, str]]:
    """Describe a message in the agent's work as steps for the dashboard."""
    if isinstance(message, ToolMessage):
        return [("tool_result", f"{message.name}: {message.text}")]
    found: list[tuple[str, str]] = [("model", message.text)] if message.text else []
    if isinstance(message, AIMessage):
        found += [
            ("tool_call", f"{tool_call['name']} {json.dumps(tool_call['args'])}")
            for tool_call in message.tool_calls
        ]
    return found


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim and return its final reply."""
    with backend() as client:
        instructions = client.get("/api/instructions").raise_for_status().json()
        client.post(
            f"/api/claims/{claim_id}/start", json={"thread_id": thread_id}
        ).raise_for_status()
        agent = create_agent(
            llm or model(), tools=TOOLS, system_prompt=instructions["text"]
        )
        reply = ""
        for update in agent.stream(
            {"messages": [{"role": "user", "content": f"Decide claim {claim_id}."}]},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            messages = [m for node in update.values() for m in node["messages"]]
            for message in messages:
                for kind, content in steps(message):
                    client.post(
                        f"/api/claims/{claim_id}/steps",
                        json={"kind": kind, "content": content},
                    ).raise_for_status()
                if isinstance(message, AIMessage):
                    reply = message.text
    return reply


def work_queue(claim_ids: list[str]) -> None:
    """Run the agent on the claims named, or on every waiting claim in order."""
    if not claim_ids:
        with backend() as client:
            claims = client.get("/api/claims").raise_for_status().json()
        claim_ids = [c["claim_id"] for c in claims if c["status"] == "waiting"]
    for claim_id in claim_ids:
        print(f"{claim_id}: {run(claim_id, str(uuid.uuid4()))}")
