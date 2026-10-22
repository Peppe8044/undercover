# Status

The pilot from `docs/SPEC.md` is built, following `docs/PLAN.md`. All six phases are done.

## Built

- `backend/`: FastAPI on SQLite.
  - `backend/db.py` seeds the database from `data/`, leaving out `data/evals/` and `data/security/`.
  - The read operations: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers` and `get_instructions`.
  - The workflow operations: `start_claim`, `add_step`, `list_steps`, `decide_claim`, `pay_claim` and `sign_off_claim`.
  - The agent's instructions are in `backend/instructions.md`. The backend serves them with the policy wording appended.
- `agent/`: the UnderCover Agent, built with LangChain's `create_agent` on OpenRouter.
  - Its tools call the API: `get_claim`, `get_policy`, `get_customer`, `decide_claim` and `pay_claim`. A refusal comes back to the model as text.
  - `run(claim_id, thread_id)` fetches the instructions, starts the claim, and posts each step to the backend as it works.
- `dashboard/`: React, Vite and TypeScript, styled to `docs/BRAND.md` in light and dark.
  - The queue at `#/`: counts by state, and every claim with its state, decision and payout. It refreshes every two seconds.
  - Each claim at `#/claims/CLM-1001`: the claim in full, the policy, the customer's earlier claims, the agent's decision and payment, and its steps. It refreshes every second.
  - A claim waiting for sign-off has a sign-off panel: pick a handler, then "Sign off and pay".
  - The agent's instructions at `#/instructions`, read only.
- `e2e/`: Playwright tests of the queue, a claim page, the agent's steps, an approval that gets paid, a sign-off, and the instructions.

## Claims and payments

A claim is `waiting`, `in_progress`, `waiting_for_sign_off` or `decided`. A decision is final.

The $1,000 rule:

- The agent records a decision, then pays an approval with `pay_claim`.
- Over the limit in `data/company.json`, `pay_claim` answers 403, and the claim waits for sign-off.
- A handler's sign-off pays the claim.

## Running it

- `npm run dev` starts the backend on port 8000 and the dashboard at http://localhost:5173.
- The database:
  - It is `backend/undercover.db`, or the path in `UNDERCOVER_DB`.
  - The backend seeds it on startup if it doesn't exist.
  - `uv run -m backend.seed` resets it from `data/`. A decided claim is final, so reset before working the queue again.
- The agent, with the backend running:
  - `uv run -m agent` works every waiting claim.
  - `uv run -m agent CLM-1001 CLM-1003` works only the claims named.
  - It uses `openai/gpt-6-luna` at low reasoning, or `MODEL_NAME` from `.env` if set, such as `openrouter/free`.
- `npm run check` runs every check.
  - The Playwright tests start their own backend on port 8001, with a freshly seeded `e2e/undercover-e2e.db`, and their own dashboard on port 5174. They don't touch the dev queue.
