# Status

The pilot is being built from `docs/PLAN.md`. Phases 1 and 2 of 6 are done.

## Built

- `backend/`: FastAPI on SQLite.
  - `backend/db.py` seeds the database from `data/`, leaving out `data/evals/` and `data/security/`.
  - The read operations: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers` and `get_instructions`.
  - The agent's instructions are in `backend/instructions.md`. The backend serves them with the policy wording appended.
  - The workflow: `start_claim`, `add_step`, `list_steps`, `decide_claim`, `pay_claim` and `sign_off_claim`.
  - A claim is `waiting`, `in_progress`, `waiting_for_sign_off` or `decided`, and a decision is final.
  - The $1,000 rule: `pay_claim` refuses a payout over the limit in `data/company.json` with 403 until a handler signs off, and the sign-off pays it.
- `agent/`: the hello-world skeleton, still to be built.
- `dashboard/`: the hello-world skeleton, still to be built.
- `e2e/`: one test of the skeleton page.

## Running it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- The database is `backend/undercover.db`, or the path in `UNDERCOVER_DB`. The backend seeds it on startup if it doesn't exist.
- `uv run -m backend.seed` resets the database from `data/`.
- `npm run check` runs every check.
