"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend import db

INSTRUCTIONS = Path(__file__).resolve().parent / "instructions.md"
POLICY_WORDING = db.DATA / "policy_wording.md"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not db.path().exists():
        db.seed()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


def record(connection: sqlite3.Connection, query: str, key: str) -> dict[str, Any]:
    """Return the JSON record a query finds by its key, or answer 404."""
    row = connection.execute(query, (key,)).fetchone()
    if row is None:
        raise HTTPException(404, f"{key} was not found.")
    return json.loads(row["record"])


def claim_row(connection: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    """Return a claim's row, or answer 404."""
    row = connection.execute(
        "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"{claim_id} was not found.")
    return row


def claim_out(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    """Return a claim as the API shows it: the record and where it stands."""
    signed_off_by = None
    if row["signed_off_by"]:
        handler = record(
            connection,
            "SELECT record FROM handlers WHERE handler_id = ?",
            row["signed_off_by"],
        )
        signed_off_by = {"handler_id": handler["handler_id"], "name": handler["name"]}
    return {
        **json.loads(row["record"]),
        "status": row["status"],
        "thread_id": row["thread_id"],
        "decision": row["decision"],
        "payout": row["payout"],
        "reason": row["reason"],
        "policy_section": row["policy_section"],
        "decided_at": row["decided_at"],
        "paid_amount": row["paid_amount"],
        "paid_at": row["paid_at"],
        "signed_off_by": signed_off_by,
        "signed_off_at": row["signed_off_at"],
    }


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims() -> list[dict[str, Any]]:
    """List every claim in the queue with where it stands."""
    with db.connect() as connection:
        names = {
            row["customer_id"]: json.loads(row["record"])["name"]
            for row in connection.execute("SELECT * FROM customers")
        }
        rows = connection.execute("SELECT * FROM claims ORDER BY claim_id").fetchall()
    claims = []
    for row in rows:
        claim = json.loads(row["record"])
        claims.append(
            {
                "claim_id": claim["claim_id"],
                "customer_name": names[claim["customer_id"]],
                "claim_type": claim["claim_type"],
                "summary": claim["summary"],
                "amount_claimed": claim["amount_claimed"],
                "submitted_on": claim["submitted_on"],
                "status": row["status"],
                "decision": row["decision"],
                "payout": row["payout"],
            }
        )
    return claims


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str) -> dict[str, Any]:
    """Get a claim in full: its story, items, documents, decision and payment."""
    with db.connect() as connection:
        return claim_out(connection, claim_row(connection, claim_id))


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str) -> dict[str, Any]:
    """Get a policy with its plan's limits and its add-ons."""
    with db.connect() as connection:
        policy = record(
            connection, "SELECT record FROM policies WHERE policy_id = ?", policy_id
        )
        plans = db.setting(connection, "plans")
    policy["plan_details"] = next(
        plan for plan in plans["plans"] if plan["plan"] == policy["plan"]
    )
    policy["add_on_details"] = [
        add_on for add_on in plans["add_ons"] if add_on["add_on"] in policy["add_ons"]
    ]
    policy["deductible_applies_to"] = plans["deductible_applies_to"]
    return policy


@app.get("/api/customers/{customer_id}", operation_id="get_customer")
def get_customer(customer_id: str) -> dict[str, Any]:
    """Get a customer with their earlier claims."""
    with db.connect() as connection:
        return record(
            connection,
            "SELECT record FROM customers WHERE customer_id = ?",
            customer_id,
        )


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers() -> list[dict[str, Any]]:
    """List the claims handlers."""
    with db.connect() as connection:
        rows = connection.execute("SELECT record FROM handlers ORDER BY handler_id")
        return [json.loads(row["record"]) for row in rows]


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> dict[str, str]:
    """Get the agent's instructions, which end with the policy wording."""
    text = INSTRUCTIONS.read_text(encoding="utf-8")
    wording = POLICY_WORDING.read_text(encoding="utf-8")
    return {"text": f"{text}\n{wording}"}


class StartIn(BaseModel):
    thread_id: str = Field(min_length=1)


class StepIn(BaseModel):
    kind: Literal["model", "tool_call", "tool_result"]
    content: str


class DecisionIn(BaseModel):
    decision: Literal["approve", "decline", "refer"]
    payout: float = Field(ge=0)
    reason: str = Field(min_length=1)
    policy_section: str = Field(min_length=1)


class PaymentIn(BaseModel):
    amount: float = Field(gt=0)


class SignOffIn(BaseModel):
    handler_id: str


def now() -> str:
    """Return the time now in UTC, to the second."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def money(amount: float) -> str:
    """Format an amount in US dollars, such as $1,250.00."""
    return f"${amount:,.2f}"


def approval_limit(connection: sqlite3.Connection) -> float:
    """Return the payout over which a handler must sign off."""
    return db.setting(connection, "company")["payout_approval_limit"]


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, start: StartIn) -> dict[str, Any]:
    """Start the agent's work on a waiting claim."""
    with db.connect() as connection:
        claim_row(connection, claim_id)
        updated = connection.execute(
            "UPDATE claims SET status = 'in_progress', thread_id = ? "
            "WHERE claim_id = ? AND status = 'waiting'",
            (start.thread_id, claim_id),
        )
        if updated.rowcount == 0:
            raise HTTPException(409, f"{claim_id} is not waiting.")
        return claim_out(connection, claim_row(connection, claim_id))


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, step: StepIn) -> dict[str, Any]:
    """Record a step of the agent's work on a claim."""
    with db.connect() as connection:
        claim_row(connection, claim_id)
        created_at = now()
        cursor = connection.execute(
            "INSERT INTO steps (claim_id, kind, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (claim_id, step.kind, step.content, created_at),
        )
    return {
        "step_id": cursor.lastrowid,
        "claim_id": claim_id,
        "kind": step.kind,
        "content": step.content,
        "created_at": created_at,
    }


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str) -> list[dict[str, Any]]:
    """List the steps of the agent's work on a claim, in order."""
    with db.connect() as connection:
        claim_row(connection, claim_id)
        rows = connection.execute(
            "SELECT * FROM steps WHERE claim_id = ? ORDER BY step_id", (claim_id,)
        )
        return [dict(row) for row in rows]


@app.post("/api/claims/{claim_id}/decision", operation_id="decide_claim")
def decide_claim(claim_id: str, decision: DecisionIn) -> dict[str, Any]:
    """Record the agent's decision on a claim in progress."""
    with db.connect() as connection:
        claim_row(connection, claim_id)
        if decision.decision != "approve" and decision.payout != 0:
            raise HTTPException(422, "A decline or a referral has a payout of 0.")
        payout = round(decision.payout, 2)
        held = decision.decision == "approve" and payout > approval_limit(connection)
        updated = connection.execute(
            "UPDATE claims SET status = ?, decision = ?, payout = ?, reason = ?, "
            "policy_section = ?, decided_at = ? "
            "WHERE claim_id = ? AND status = 'in_progress'",
            (
                "waiting_for_sign_off" if held else "decided",
                decision.decision,
                payout,
                decision.reason,
                decision.policy_section,
                now(),
                claim_id,
            ),
        )
        if updated.rowcount == 0:
            raise HTTPException(409, f"{claim_id} is not in progress.")
        return claim_out(connection, claim_row(connection, claim_id))


def check_payment(
    connection: sqlite3.Connection, row: sqlite3.Row, amount: float
) -> None:
    """Answer with an error unless the claim can be paid this amount now."""
    claim_id = row["claim_id"]
    if row["decision"] != "approve":
        raise HTTPException(409, f"{claim_id} is not approved.")
    if row["paid_at"]:
        raise HTTPException(409, f"{claim_id} has already been paid.")
    limit = approval_limit(connection)
    if row["payout"] > limit and not row["signed_off_by"]:
        raise HTTPException(
            403,
            f"A payout over {money(limit)} waits for a handler's sign-off. "
            "The payment is held.",
        )
    if round(amount, 2) != row["payout"]:
        raise HTTPException(
            422, f"The amount must be the approved payout, {money(row['payout'])}."
        )


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: PaymentIn) -> dict[str, Any]:
    """Pay an approved claim its payout; over the limit, only after sign-off."""
    with db.connect() as connection:
        check_payment(connection, claim_row(connection, claim_id), payment.amount)
        updated = connection.execute(
            "UPDATE claims SET paid_amount = payout, paid_at = ? "
            "WHERE claim_id = ? AND paid_at IS NULL",
            (now(), claim_id),
        )
        if updated.rowcount == 0:
            raise HTTPException(409, f"{claim_id} has already been paid.")
        return claim_out(connection, claim_row(connection, claim_id))


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str, sign_off: SignOffIn) -> dict[str, Any]:
    """Sign off a payout over the limit as a handler, which pays it."""
    with db.connect() as connection:
        claim_row(connection, claim_id)
        handler = record(
            connection,
            "SELECT record FROM handlers WHERE handler_id = ?",
            sign_off.handler_id,
        )
        if not handler["can_approve_over_limit"]:
            raise HTTPException(
                403, f"{handler['name']} cannot sign off payouts over the limit."
            )
        signed_at = now()
        updated = connection.execute(
            "UPDATE claims SET status = 'decided', signed_off_by = ?, "
            "signed_off_at = ?, paid_amount = payout, paid_at = ? "
            "WHERE claim_id = ? AND status = 'waiting_for_sign_off'",
            (sign_off.handler_id, signed_at, signed_at, claim_id),
        )
        if updated.rowcount == 0:
            raise HTTPException(409, f"{claim_id} is not waiting for sign-off.")
        return claim_out(connection, claim_row(connection, claim_id))
