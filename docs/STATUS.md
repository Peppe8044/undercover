# Status

The pilot is being built from `docs/PLAN.md`. Phases 1 to 4 of 6 are done.

## Built

- `backend/`: FastAPI on SQLite.
  - `backend/db.py` seeds the database from `data/`, leaving out `data/evals/` and `data/security/`.
  - The read operations: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers` and `get_instructions`.
  - The agent's instructions are in `backend/instructions.md`. The backend serves them with the policy wording appended.
  - The workflow: `start_claim`, `add_step`, `list_steps`, `decide_claim`, `pay_claim` and `sign_off_claim`.
  - A claim is `waiting`, `in_progress`, `waiting_for_sign_off` or `decided`, and a decision is final.
  - The $1,000 rule: `pay_claim` refuses a payout over the limit in `data/company.json` with 403 until a handler signs off, and the sign-off pays it.
- `agent/`: the UnderCover Agent, LangChain's `create_agent` on OpenRouter.
  - Its tools call the API: `get_claim`, `get_policy`, `get_customer`, `decide_claim` and `pay_claim`. A refusal comes back to the model as text.
  - `run(claim_id, thread_id)` fetches the instructions, starts the claim, and posts each step to the backend as it works.
  - `uv run -m agent` works every waiting claim; `uv run -m agent CLM-1001 CLM-1003` works the claims named.
- `dashboard/`: React, Vite and TypeScript, styled to `docs/BRAND.md` in light and dark.
  - The queue at `#/`: counts by state and every claim with its state, decision and payout, refreshed every two seconds.
  - The agent's instructions at `#/instructions`, read only.
- `e2e/`: one test that the dashboard opens on the queue.

## Running it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- The database is `backend/undercover.db`, or the path in `UNDERCOVER_DB`. The backend seeds it on startup if it doesn't exist.
- `uv run -m backend.seed` resets the database from `data/`. A decided claim is final, so run it before working the queue again.
- `uv run -m agent` works the queue with the backend running. It uses `MODEL_NAME` from `.env` if set, such as `openrouter/free`.
- `npm run check` runs every check.
