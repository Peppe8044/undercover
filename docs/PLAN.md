# Plan: the claims pilot

The pilot from `docs/SPEC.md`. It has three parts:

- **A backend.** It holds the claims queue and enforces the $1,000 sign-off rule.
- **The UnderCover Agent.** It works the queue through the backend's API.
- **A dashboard.** Handlers use it to see the queue, each claim, the agent's steps and its instructions, and to sign off held payments.

The work is split into six phases, and each one builds on the last.

## Approach

### Claim states

A claim has one of four states, the ones the spec names:

| State | Label | Meaning |
|---|---|---|
| `waiting` | Waiting | Seeded from `data/claims.json`; the agent has not started it |
| `in_progress` | In progress | The agent is working on it |
| `waiting_for_sign_off` | Waiting for sign-off | The agent approved a payout over $1,000 and the payment waits for a handler |
| `decided` | Decided | Declined, referred, or approved and settled |

A decided claim is final. Running the agent on it again needs a reseed, `uv run -m backend.seed`.

- **Why:** these are the four states the team asked to see.
- **Why:** making decisions final keeps the rules simple and the history honest.

### The $1,000 rule is enforced in the backend, not in the prompt

The agent first records its decision with `decide_claim`. Paying is a separate operation, `pay_claim`, which takes the amount. The backend checks `pay_claim` against these rules:

- The claim must be approved.
- The amount must equal the approved payout.
- The claim must not have been paid already.
- If the payout is over the limit in `data/company.json` ($1,000.00), a handler must have signed off first. Otherwise the backend refuses the payment with 403.

A handler's sign-off, `sign_off_claim` with their handler id, pays the approved payout and settles the claim. The handler must be one whose `can_approve_over_limit` is true.

- **Why:** the spec says the system must block the payment "even if the agent tries to pay". A rule in the prompt can be ignored, but a rule in the API cannot.

### The agent reaches everything through the API

The agent fetches claims, policies, customers and its own instructions over HTTP. It never reads `data/`.

The instructions live in `backend/instructions.md`. The backend serves them with the policy wording from `data/policy_wording.md` appended, so the agent always has the wording in its prompt. The dashboard shows that same text, read only.

The claims manual is left out, as the spec asks.

- **Why:** the tech stack requires this.
- **Why:** it also means the dashboard shows exactly what the agent was told.

### The agent's steps

`run()` streams the agent's work and posts each step to the backend as it happens. A step is one of:

- a tool call, with its arguments
- a tool result
- the model's text

While a claim is in progress, the dashboard refreshes its steps every second.

- **Why:** the team needs to see what the agent is doing while it works.
- **Why:** polling a list of steps is the simplest way to do that, with no websockets.

### Storage

SQLite through Python's standard `sqlite3` module. Each source record keeps its original JSON in a column, next to the columns the workflow changes: status, decision, payment, sign-off and steps.

The database file is `backend/undercover.db`, or the path in the environment variable `UNDERCOVER_DB`. `*.db` is already in `.gitignore`.

On startup, the backend seeds the database if the file does not exist yet. `uv run -m backend.seed` resets it at any time.

The seed reads only these files:

- `claims.json`
- `policies.json`
- `customers.json`
- `plans.json`
- `handlers.json`
- `company.json`

It never reads `data/evals/` or `data/security/`.

- **Why:** this covers the pilot with no new dependency.

### Running the agent

`uv run -m agent` works through every waiting claim in order, giving each one a new thread id. `uv run -m agent CLM-1001 CLM-1003` works only the claims named.

The agent is not started from the dashboard, because the spec asks the team to see the work, not to start it.

### The dashboard

There are three views, reached by hash routes: `#/`, `#/claims/CLM-1001` and `#/instructions`. They use a small hook over `location.hash`, so no router package is needed.

Styling follows `docs/BRAND.md`:

- Instrument Sans, Instrument Serif and JetBrains Mono, from Google Fonts.
- Colors as CSS variables, with a light theme and a dark theme switched by `prefers-color-scheme`.
- Rounded panels with no outlines.
- Money shown as $1,250.00.

State badges use the brand order:

| State | Badge color | Text |
|---|---|---|
| Decided | Sea Green | Midnight |
| Waiting | Marigold | Midnight |
| Waiting for sign-off | Coral | Midnight |
| In progress | Cerulean | White |

### End-to-end tests run against their own backend and database

Playwright starts a backend on port 8001 with a freshly seeded `e2e/undercover-e2e.db`, and a dashboard on port 5174 that proxies to it. The tests do the agent's part through API calls, so they never call a model.

- **Why:** `npm run check` gives the same result whether or not `npm run dev` is running.
- **Why:** the tests never change the queue you work with.

### Not in the pilot

These are out, as the spec says:

- the claims manual
- sign-in
- real payments
- messages to customers

These are also out:

- scoring against `data/evals/`, which this build never opens
- `data/knowledge.json`
- the security claim

## The API

Every operation has an `operation_id` and a one-line docstring. None takes an optional input, and a test checks all three against the OpenAPI schema.

| Method and path | `operation_id` | Input | Notes |
|---|---|---|---|
| `GET /api/health` | `health` | | Exists today |
| `GET /api/claims` | `list_claims` | | One row per claim: id, customer name, type, summary, amount claimed, submitted date, state, decision, payout |
| `GET /api/claims/{claim_id}` | `get_claim` | | The full claim with its decision, payment and sign-off |
| `GET /api/policies/{policy_id}` | `get_policy` | | The policy with its plan's limits and its add-ons' details |
| `GET /api/customers/{customer_id}` | `get_customer` | | The customer with their earlier claims |
| `GET /api/handlers` | `list_handlers` | | The three handlers |
| `GET /api/instructions` | `get_instructions` | | `{"text": ...}`: the agent's instructions with the policy wording |
| `POST /api/claims/{claim_id}/start` | `start_claim` | `thread_id` | `waiting` to `in_progress`; 409 from any other state |
| `POST /api/claims/{claim_id}/steps` | `add_step` | `kind`, `content` | `kind` is `model`, `tool_call` or `tool_result` |
| `GET /api/claims/{claim_id}/steps` | `list_steps` | | In order, with times |
| `POST /api/claims/{claim_id}/decision` | `decide_claim` | `decision`, `payout`, `reason`, `policy_section` | Only from `in_progress`; see the rules below |
| `POST /api/claims/{claim_id}/payment` | `pay_claim` | `amount` | See the $1,000 rule above |
| `POST /api/claims/{claim_id}/sign-off` | `sign_off_claim` | `handler_id` | Only from `waiting_for_sign_off`; pays the payout and settles the claim |

Rules for `decide_claim`:

- A decline or a referral must have a payout of 0, or the backend answers 422. It then moves to `decided`.
- An approval of $1,000.00 or less moves to `decided`. The agent then pays.
- An approval over $1,000.00 moves to `waiting_for_sign_off`.

Errors:

- An unknown id answers 404.
- An operation in the wrong state answers 409.

## Phase 1: the backend's data and read operations

**What it builds:**

- `backend/db.py`: the connection, the schema and the seed logic.
- `backend/seed.py`: the reset command.
- The read operations: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers` and `get_instructions`.
- A first version of `backend/instructions.md`.
- Seeding on startup, when there is no database file yet.

**Why first:** everything else reads from this.

**Success criteria:**

- [x] `uv run -m backend.seed` creates `backend/undercover.db` and reports 25 claims, 50 policies, 49 customers and 3 handlers.
- [x] `GET /api/claims` returns 25 claims, CLM-1001 to CLM-1025. Every one is `waiting`, with no decision.
- [x] `GET /api/claims/CLM-1001` returns:
  - the story
  - three items totaling $420.00
  - four documents
  - state `waiting`
- [x] `GET /api/policies/POL-2001` returns the Premium plan with a $50.00 deductible.
- [x] `GET /api/customers/CUS-3001` returns Maya Patel, with earlier claim CLM-0412.
- [x] `GET /api/handlers` returns Dana Whitfield, Marcus Oyelaran and Priya Raman.
- [x] `GET /api/instructions` returns text that contains "Version 2026.1" from the policy wording. The text does not mention the claims manual.
- [x] An unknown claim, policy or customer id answers 404.
- [x] A test checks the OpenAPI schema. Every operation has an `operation_id`, a one-line description and only required inputs.
- [x] A test checks the seeded claim ids are exactly CLM-1001 to CLM-1025, so nothing from `data/evals/` or `data/security/` gets in.
- [x] Deleting the database file and starting the backend seeds it again.
- [x] `npm run check:python` passes with coverage of 80% or more.

## Phase 2: the claim workflow and the $1,000 rule

**What it builds:**

- These operations:
  - `start_claim`
  - `add_step`
  - `list_steps`
  - `decide_claim`
  - `pay_claim`
  - `sign_off_claim`
- The state changes and the rules described above.

**Why now:** the sign-off rule belongs to the backend. With the operations in place and tested, the agent and the dashboard build against a fixed contract.

**Success criteria:**

- [x] **Start.** `start_claim` moves a waiting claim to `in_progress` and records the thread id. A second call answers 409.
- [x] **Steps.** `add_step` then `list_steps` returns the steps in the order they were added, each with a time.
- [x] **Decline.** A decline with payout 0 moves the claim to `decided`. A decline with a payout answers 422.
- [x] **Approval up to the limit.**
  - An approval of $420.00 moves the claim to `decided`.
  - `pay_claim` with 420.00 records the payment.
  - A second payment answers 409.
  - A payment of the wrong amount answers 422.
- [x] **Exactly the limit.** An approval of exactly $1,000.00 moves the claim to `decided`, and paying it succeeds.
- [x] **Over the limit.**
  - An approval of $1,150.00 moves the claim to `waiting_for_sign_off`.
  - `pay_claim` answers 403, with a message that the payment waits for a handler's sign-off, and nothing is paid.
- [x] **Sign-off.**
  - `sign_off_claim` with HND-01 on that claim records Dana Whitfield, pays $1,150.00 and moves the claim to `decided`.
  - An unknown handler answers 404.
  - Signing off a claim that is not waiting for sign-off answers 409.
- [x] **Final decisions.** `decide_claim` on a decided claim answers 409.
- [x] **Reseed.** `uv run -m backend.seed` returns every claim to `waiting` and clears its steps.
- [x] `npm run check:python` passes with coverage of 80% or more.

## Phase 3: the UnderCover Agent

**What it builds:**

- **The instructions** in `backend/instructions.md`:
  - Read the claim, the policy and the customer's earlier claims.
  - Check them against the policy wording.
  - Decide to approve, decline or refer:
    - Refer when a document the wording asks for is missing, or when the claim needs judgment the wording does not settle.
  - Work out the payout as section 10 of the wording describes.
  - Record the decision with:
    - a reason of two or three sentences
    - the relevant policy section
  - Pay an approval.
  - Stop if the payment is held for sign-off.
- **The tools**, each a call to the API:
  - `get_claim`, `get_policy` and `get_customer`
  - `decide_claim` and `pay_claim`

  A refused call returns the backend's message to the model, so the agent learns that a payment is held. It does not crash.
- **`run(claim_id, thread_id)`**, which works one claim:
  1. Fetches the instructions.
  2. Starts the claim.
  3. Streams the agent and posts each step.
  4. Returns the final reply.
- **`agent/__main__.py`**, the queue runner.

**Why this way:** the model keeps the judgment: the decision, the payout and the reason. The backend keeps the controls. The pilot needs a simple agent loop with good tools, and the Week 1 Day 5 build will develop the harness.

**Success criteria:**

- [x] **Approval up to the limit.**
  - With a stub model scripted to read CLM-1001, approve $420.00 and pay, `run()` leaves the claim `decided` and paid.
  - Its steps show each tool call and result in order.
- [x] **Over the limit.**
  - With a stub model scripted to approve CLM-1002 at $1,150.00 and then pay, the payment is refused.
  - The refusal appears as a tool result in the steps, and the claim is `waiting_for_sign_off` and unpaid.
- [x] **Decline.** With a stub model scripted to decline, the claim is `decided` with payout 0.
- [x] **Queue runner.** With `run` replaced by a stub, `uv run -m agent` picks up only waiting claims, and named claim ids pick up only those.
- [x] **Model choice.** The default model is still `openai/gpt-6-luna` at low reasoning, and `MODEL_NAME` overrides it. The existing test keeps passing.
- [x] **No local data.** A search for `data/` in `agent/` finds nothing.
- [x] `npm run check:python` passes with coverage of 80% or more.

## Phase 4: the dashboard's queue and instructions

**What it builds:**

- The brand styles: fonts, color variables and light and dark themes.
- A header with links to the queue and the instructions.
- **The queue page:**
  - A count of claims in each state.
  - A table with id, customer, type, summary, amount claimed, submitted date, state badge, decision and payout.
  - Each row links to its claim.
  - The table refreshes every two seconds.
- **The instructions page:** the agent's instructions as read-only text.
- **Shared formatting:** money as $1,250.00, and labels for the claim types and states.

This replaces the health page.

**Why now:** the queue is the handlers' main screen, and it only needs the read operations.

**Success criteria:**

- [x] **Unit tests.** Vitest tests cover:
  - the queue rendering from a stubbed fetch
  - the state counts
  - money formatting
  - the instructions page
  - an error message when the backend is down
- [x] **Queue in the browser.** With `npm run dev` and a fresh seed, checked with the Playwright MCP server:
  - `http://localhost:5173` shows 25 claims, all Waiting.
  - CLM-1001 shows $420.00.
- [x] **Instructions in the browser.** `#/instructions` shows the instructions and the policy wording, with no way to edit them.
- [x] **Dark theme.** The page follows the brand in dark mode: background `#04232E` and black panels.
- [x] `npm run check:ts` passes with coverage of 80% or more.

## Phase 5: the dashboard's claim page, the agent's steps and sign-off

**What it builds:** the claim page, with these sections:

- **The claim:** id, state, customer, type, dates, location and amount claimed.
- **The story.**
- **The items** in a table.
- **The documents.**
- **The policy:** plan, add-ons, trip dates, trip cost and travelers.
- **The customer's earlier claims.**
- **The agent's decision:** the decision, the payout, the reason, the policy section, and the payment state, which is one of:
  - Paid
  - Waiting for sign-off
  - Not paid
- **The sign-off panel**, when the claim waits for sign-off. It has a handler picker and a "Sign off and pay" button.
- **The agent's steps.** They refresh every second while the claim is in progress.

**Why now:** this page needs the read operations and the write operations from Phase 2.

**Success criteria:**

- [x] **Unit tests.** Vitest tests cover:
  - a waiting claim
  - a decided claim with its reason
  - a claim waiting for sign-off that is signed off
  - the steps list
- [x] **Claim in the browser.** `#/claims/CLM-1001` shows:
  - the story
  - three items
  - four documents
  - the Premium policy
  - the earlier claim CLM-0412
- [x] **Steps while the agent works.** Calling the API as the agent does, the browser shows each step soon after it is added, with no reload:
  - start CLM-1001
  - add steps
  - approve $420.00
  - pay
- [x] **The finished claim.** The claim then shows Decided, the reason, the policy section and "Paid $420.00".
- [x] **Sign-off in the browser.**
  - Approve CLM-1002 at $1,150.00 through the API.
  - The page shows "Waiting for sign-off".
  - A payment through the API is refused.
  - Signing off as Priya Raman in the browser shows Decided, "Paid $1,150.00" and her name.
- [x] **Reseed.** `uv run -m backend.seed` resets the queue after these checks.
- [x] `npm run check:ts` passes with coverage of 80% or more.

## Phase 6: end-to-end tests, a live run and handover

**What it builds:**

- **Playwright's own servers.** Playwright starts a seeded backend on port 8001 and a dashboard on port 5174.
  - The vite proxy target comes from `UNDERCOVER_API_URL`, with `http://127.0.0.1:8000` as the default.
- **End-to-end tests,** which replace the health test. They cover:
  - the queue
  - a claim page
  - an approval up to the limit that the agent pays
  - an approval over the limit, refused for payment and signed off in the browser
  - the steps
  - the instructions
- **`docs/STATUS.md`:** what is built and how to run it.

**Why last:** the end-to-end tests check the whole flow once all the parts exist, and the live run checks the real model on real claims.

**Success criteria:**

- [ ] `npm run e2e` passes. It passes again on a second run, because each run starts from a fresh database.
- [ ] `npm run e2e` passes while `npm run dev` is also running, and the dev queue is unchanged.
- [ ] **Live run on the student's OpenRouter key.** This calls the model and costs a few cents.
  - Reseed, run `npm run dev`, then run `uv run -m agent CLM-1001 CLM-1003`.
  - The dashboard shows the steps as each claim is worked.
  - Each claim ends either `decided` or `waiting_for_sign_off`, with:
    - a decision
    - a reason of two or three sentences
    - a policy section
    - a payout when approved
  - Any approval over $1,000 shows a refused payment in its steps and waits for sign-off.
- [ ] **Reseed after the live run.** `uv run -m backend.seed` resets the queue afterwards.
- [ ] **Status file.** `docs/STATUS.md` describes:
  - the backend, the agent and the dashboard
  - the claim states and the sign-off rule
  - the commands `npm run dev`, `uv run -m agent`, `uv run -m backend.seed` and `npm run check`
- [ ] `npm run check` passes: ruff, pyright, pytest, ESLint, Prettier, tsc, vitest and Playwright.
