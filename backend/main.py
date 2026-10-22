"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

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
