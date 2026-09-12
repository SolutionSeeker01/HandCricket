# Hand Cricket — Sprint Log

## Sprint Metadata

* **Project**: Hand Cricket Web Game
* **Sprint Duration**: Strict 2-day development sprint
* **Goal**: Build, verify, and ship a real, deployed, playable Hand Cricket web game.
* **Deployment Target**: AWS EC2 (Ubuntu 24.04 LTS) + Docker Compose + Caddy Reverse Proxy (HTTPS/WSS via `sslip.io` + Let's Encrypt).
* **Source of Truth**: [`implementation_plan.md`](file:///d:/PYTHON/Cricket/implementation_plan.md)
* **Legacy Reference**: [`Cric.py`](file:///d:/PYTHON/Cricket/Cric.py) (Historical CLI reference implementation preserving original game logic and intent).

---

## Working Agreement Summary

1. **One vertical slice at a time**: Implement only the approved slice; test, review, and confirm before proceeding.
2. **Vertical-slice workflow**: Define scope $\rightarrow$ Implement minimum code $\rightarrow$ Run automated tests $\rightarrow$ Review $\rightarrow$ Approve.
3. **No scope creep**: Do not pull features from future slices.
4. **Antigravity's role**: Implement the requested slice, report file changes and test results, and stop for review.
5. **Testing philosophy**: Meaningful rule, boundary, state transition, failure-path, and integration tests (no arbitrary 100% line coverage chasing).
6. **Project principle**: Ship a reliable, simple, publicly playable product on AWS within 48 hours.

---

## Slice Status Board

| Slice | Title | Description | Status |
| :--- | :--- | :--- | :--- |
| **Slice 1** | Project Skeleton & Baseline Test Harness | Directory layout (`backend/`, `frontend/`, `deploy/`), exact pinned dependencies, `pytest` setup, verified frontend build | **APPROVED** |
| **Slice 2** | Single Ball Resolution Engine | Pure function `resolve_ball(bat, bowl) -> BallResult` (1–6 matching rules) | **APPROVED** |
| **Slice 3** | Batsman Lifecycle & Score Tracking | Runs, balls faced, status (`NOT_OUT`, `OUT`), batsman transition | **APPROVED** |
| **Slice 4** | Over & Innings Progression | 6 balls/over, 5 overs max (30 legal balls), 10 wickets all-out limit | **COMPLETED (Awaiting Review)** |
| **Slice 5** | Bowler Quota Enforcement | 1 over max per bowler (requires 5 unique bowlers across 5 overs) | NOT STARTED |
| **Slice 6** | Full Match & Target Chasing | Innings 1 sets target; Innings 2 chase with early finish termination | NOT STARTED |
| **Slice 7** | Predefined Teams & Toss Mechanics | 4 teams & 11 players each, coin toss A/B, Bat/Bowl decision | NOT STARTED |
| **Slice 8** | Headless Computer Player (Bot) | Bot choosing 1–6 and picking bowlers; 100-match automated Bot vs Bot simulation | NOT STARTED |
| **Slice 9** | Backend HTTP & WebSocket Foundation | FastAPI app, `/health`, room generation (`POST /api/rooms`), WebSocket connection | NOT STARTED |
| **Slice 10** | WebSocket Game Protocol & 5s Turn Timer | Simultaneous blind inputs, 5-second countdown timer, auto-pick fallback | NOT STARTED |
| **Slice 11** | EC2 Deployment of Walking Skeleton | Launch EC2 `t3.small`, Docker + Caddy SSL, verify public `wss://` on phone | NOT STARTED |
| **Slice 12** | Minimal Playable Arena UI | Vite + React + Tailwind minimal arena (Scoreboard, Keypad, Bot Mode) | NOT STARTED |
| **Slice 13** | Pre-Match Flows | Landing, room lobby link sharing, team selection, toss, bowler modal | NOT STARTED |
| **Slice 14** | Polish, Animations & Edge Cases | Coin flip animation, 5s countdown bar, ball reveal cards, auto-pick badge | NOT STARTED |
| **Slice 15** | Friend Mode E2E Testing & Final Ship | End-to-end multi-device verification (phone + desktop), final sign-off | NOT STARTED |

---

## Execution Log

### Slice 1: Project Skeleton & Baseline Test Harness

* **Status**: COMPLETED (Awaiting Review)
* **Timestamp**: 2026-09-12T22:37:00+05:30
* **What was implemented**:
  * Established project boundaries (`backend/`, `frontend/`, `deploy/`).
  * Created root `.gitignore` covering Python bytecode, caches, virtual environments, node modules, build outputs (`dist/`), and IDE artifacts.
  * Pinned exact `==` backend dependencies in `backend/requirements.txt` (`fastapi==0.111.0`, `uvicorn[standard]==0.29.0`, `websockets==12.0`, `pydantic==2.7.1`, `pytest==8.2.0`, and `httpx==0.27.0`). Documented why `httpx` is required by FastAPI `TestClient`.
  * Created baseline FastAPI app in `backend/app/main.py` with `/health` endpoint.
  * Created root `pytest.ini` with test discovery (`testpaths = backend/tests`). Verified that pytest automatically traverses to root from subdirectories; removed redundant `backend/pytest.ini`.
  * Created baseline test suite in `backend/tests/test_sanity.py` testing environment validity (Python 3.11+), FastAPI app initialization, and `/health` response.
  * Configured frontend skeleton (`frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/index.html`, `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/src/index.css`).
  * Reviewed and removed `lucide-react` from `frontend/package.json` as it is not needed in Slice 1.
  * Added required `tailwind.config.js` and `postcss.config.js` to support `@tailwind` directives in `src/index.css`.
  * Executed `npm install` and `npm run build` in `frontend/`, verifying that the TypeScript compiler and Vite production build succeed completely.
  * Created deployment reverse proxy blueprint in `deploy/Caddyfile`.
* **Files Created / Maintained**:
  * `.gitignore`
  * `pytest.ini`
  * `backend/requirements.txt` (exact `==` pinned)
  * `backend/app/__init__.py`
  * `backend/app/main.py`
  * `backend/tests/__init__.py`
  * `backend/tests/test_sanity.py`
  * `deploy/Caddyfile`
  * `frontend/package.json` (lucide-react removed)
  * `frontend/package-lock.json`
  * `frontend/tsconfig.json`
  * `frontend/vite.config.ts`
  * `frontend/tailwind.config.js`
  * `frontend/postcss.config.js`
  * `frontend/index.html`
  * `frontend/src/index.css`
  * `frontend/src/App.tsx`
  * `frontend/src/main.tsx`
* **Tests & Builds Executed**:
  * Command 1: `pytest -v` from repository root $\rightarrow$ PASS (3 passed in 1.17s).
  * Command 2: `pytest -v` from `backend/` directory $\rightarrow$ PASS (3 passed in 1.15s).
  * Command 3: `npm run build` from `frontend/` $\rightarrow$ PASS (TypeScript checked, Vite production bundle generated in 1.50s into `frontend/dist/`).
* **Decisions Made**:
  * Used exact `==` version pinning for all backend dependencies.
  * Removed `lucide-react` from `package.json` to keep Slice 1 strictly minimal.
  * Removed redundant `backend/pytest.ini` after verifying that root `pytest.ini` is cleanly resolved from child directories.
  * Added `tailwind.config.js` and `postcss.config.js` to ensure the frontend build pipeline functions without error.
* **Deviations from Plan**: None.
* **Unresolved Issues**: None.

### Slice 2: Single Ball Resolution Engine

* **Status**: COMPLETED (Awaiting Review)
* **Timestamp**: 2026-09-12T22:47:00+05:30
* **What was implemented**:
  * Pure deterministic game engine module in `backend/app/engine/ball.py`.
  * Implemented `BallResult` frozen dataclass with `batsman_choice`, `bowler_choice`, `runs`, and `is_wicket`.
  * Implemented `validate_choice()` enforcing integer values between 1 and 6, explicitly rejecting booleans and non-integers.
  * Implemented `InvalidBallChoiceError(ValueError)` domain exception for invalid inputs.
  * Implemented `resolve_ball(batsman_choice, bowler_choice)` adhering strictly to frozen Hand Cricket ball resolution rules:
    * `batsman_choice == bowler_choice` $\rightarrow$ Wicket (`runs=0`, `is_wicket=True`).
    * `batsman_choice != bowler_choice` $\rightarrow$ Runs (`runs=batsman_choice`, `is_wicket=False`).
  * Created unit test suite in `backend/tests/test_ball_engine.py` covering:
    * All 36 combinations (6x6 matrix of 1..6 vs 1..6).
    * Canonical runs and wickets examples from product specification.
    * Out-of-bounds inputs (<1, >6).
    * Non-integer type rejection (strings, floats, None, bools, lists, dicts).
    * Player role identification in error messages.
    * Determinism and object immutability.
* **Files Created**:
  * `backend/app/engine/__init__.py`
  * `backend/app/engine/ball.py`
  * `backend/tests/test_ball_engine.py`
* **Tests Executed**:
  * Command: `pytest -v` from repository root $\rightarrow$ PASS (58 passed in 1.37s). All 3 previous Slice 1 sanity tests + 55 Slice 2 engine tests passed cleanly.
* **Decisions Made**:
  * Defined `BallResult` as an immutable frozen dataclass (`@dataclass(frozen=True)`) to ensure ball resolution results are safe, read-only value objects.
  * Subclassed `ValueError` for `InvalidBallChoiceError` to provide clear domain context while maintaining idiomatic Python error hierarchy.
  * Explicitly rejected `bool` types before integer checks because `isinstance(True, int)` evaluates to `True` in Python.
* **Deviations from Plan**: None.
* **Unresolved Issues**: None.

### Slice 3: Batsman Lifecycle & Score Tracking

* **Status**: APPROVED
* **Timestamp**: 2026-09-12T22:52:00+05:30
* **What was implemented**:
  * Pure domain model `BattingState` in `backend/app/engine/batting.py`.
  * Initial innings state initialized with batsman 1 on strike, batsman 2 as non-striker, next batsman as 3, 0 runs, 0 wickets, and 0 balls processed.
  * Score accumulation logic in `record_ball(ball_result: BallResult)`:
    * Runs scored added to current striker's individual score and team total.
    * Odd runs (1, 3, 5): striker and non-striker swap ends.
    * Even runs (2, 4, 6): striker and non-striker remain in place.
  * Wicket lifecycle:
    * Striker dismissed and appended to `dismissed_batsmen`.
    * Wickets tally incremented.
    * Next available batsman enters as the new active striker; non-striker remains in place.
  * Robust lifecycle protection and domain exceptions:
    * `BattingLifecycleError`: Base domain exception.
    * `NoAvailableBatsmanError`: Raised when processing a ball when no striker is available.
    * `InvalidBatsmanError`: Raised on invalid batsman identifiers or roster bounds.
  * Defensive immutability:
    * Property accessors return copies of `individual_scores`, `balls_faced`, and `dismissed_batsmen` to prevent external mutation.
  * Created unit test suite in `backend/tests/test_batting_engine.py` (32 tests) covering:
    * Initial state verification.
    * Scoring updates for 1, 2, 4, 6 runs.
    * Odd-run swapping for 1, 3, 5 runs.
    * Even-run retention for 2, 4, 6 runs.
    * Wicket dismissal, next batsman entry, and consecutive wickets.
    * Realistic multi-ball sequential match progression.
    * Roster exhaustion boundary and `NoAvailableBatsmanError`.
    * Invalid operations (invalid IDs, invalid team sizes, invalid ball types).
    * Immutability and state isolation.
* **Files Created**:
  * `backend/app/engine/batting.py`
  * `backend/tests/test_batting_engine.py`
* **Tests Executed**:
  * Command: `pytest -v` from repository root $\rightarrow$ PASS (90 passed in 1.42s). All 3 Slice 1 sanity tests + 55 Slice 2 ball tests + 32 Slice 3 batting tests passed cleanly.
* **Decisions Made**:
  * Modeled `BattingState` as an encapsulated domain entity tracking individual runs and balls faced per batsman.
  * Ensured single authoritative wicket mutation pathway strictly via `record_ball(ball_result)`. Removed arbitrary dismissal API.
  * Decoupled batting progression from over limits, innings termination, and match rules (kept strictly for Slices 4 and 6).
  * Maintained defensive copies on all dictionary and list property getters.
* **Deviations from Plan**: None.
* **Unresolved Issues**: None.

### Slice 4: Over & Innings Progression

* **Status**: COMPLETED (Awaiting Review)
* **Timestamp**: 2026-09-12T23:01:00+05:30
* **What was implemented**:
  * Pure domain model `Innings` in `backend/app/engine/innings.py`.
  * Over and ball tracking:
    * 1-indexed `current_over` (initial=1, max=5).
    * `balls_in_current_over` (0 to 5; resets to 0 after 6 valid balls).
    * `total_balls` completed (0 to 30).
  * Encapsulates `BattingState` and delegates single-ball scoring, wickets, and strike rotation to it.
  * Single authoritative mutation entry point `record_ball(ball_result: BallResult)`:
    1. Guard: Rejects any ball if innings is complete by raising `InningsCompleteError`.
    2. Type Validation: Validates `ball_result` is an instance of `BallResult` (raises `TypeError` otherwise).
    3. Batting State Mutation: Passes `ball_result` to `batting_state.record_ball()`.
    4. Counter Increments: Increments `balls_in_current_over` and `total_balls`.
    5. Innings Completion Check: Evaluates `total_balls == max_balls (30)` OR `batting_state.striker is None` (all-out) $\rightarrow$ sets `innings_complete = True`.
    6. Over Completion Check: If `balls_in_current_over == balls_per_over (6)`, resets `balls_in_current_over = 0` and increments `current_over += 1` if and only if the innings is not complete.
  * Domain boundaries & invariant guarantees:
    * No 6th over is created: on the 30th ball (over 5, ball 6), `current_over` remains 5.
    * Wickets count as legal completed balls for both over and innings tallies.
    * Wicket on ball 30 counts as ball 30 and marks the innings complete.
    * Premature all-out (when no striker remains) immediately completes the innings.
    * Calls to `record_ball()` after innings completion are rejected with `InningsCompleteError`.
    * No automatic strike rotation at over end: striker and non-striker ends are preserved across over boundaries unless swapped by odd runs or wickets in `BattingState`.
  * Read-only properties exposed:
    * `current_over`, `balls_in_current_over`, `total_balls`, `max_overs`, `balls_per_over`, `max_balls`.
    * `innings_complete`, `is_completed`.
    * `over_complete` & `is_over_complete`: Semantics clarified: True if the most recently recorded ball completed an over (does not mean the currently active over is complete).
    * `batting_state` and delegating properties `striker`, `non_striker`, `total_runs`, `wickets`.
  * Comprehensive test suite in `backend/tests/test_innings_engine.py` (37 tests) covering initial state, 1-ball, 6-ball over, 7th ball, 12 balls, 14 balls, 30 balls, wickets as legal balls, all-out boundaries, post-completion rejection, sequential integration, boundary limits, strict retention of strike at over ends, instance isolation, clarified `over_complete` semantics, and type safety.
* **Files Created / Modified**:
  * `backend/app/engine/innings.py`
  * `backend/tests/test_innings_engine.py`
* **Tests Executed**:
  * Command: `pytest -v` from repository root $\rightarrow$ PASS (127 passed in 1.66s). All 3 Slice 1 sanity tests + 55 Slice 2 ball tests + 32 Slice 3 batting tests + 37 Slice 4 innings tests passed cleanly.
* **Decisions Made**:
  * `Innings` encapsulates `BattingState` and does not duplicate batting scores, wickets, or striker rotation.
  * Used exact `==` checks for `total_balls == max_balls` and `balls_in_current_over == balls_per_over` invariants.
  * Documented and tested `over_complete` semantics: signifies the event that the ball just recorded completed an over.
  * Kept strike rotation strictly governed by `BattingState` (odd runs and wickets). Explicitly prohibited automatic strike swaps merely because an over ended.
  * Subclassed `InningsCompleteError` from `InningsError(ValueError)` for domain-specific error handling.
  * Allowed optional dependency injection of `BattingState` in `Innings.__init__` while defaulting to standard 11-player lineup.
* **Deviations from Plan**: None.
* **Unresolved Issues**: None.



