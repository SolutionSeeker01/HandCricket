# Hand Cricket Web Game — Architecture & EC2 Deployment Plan

This document freezes our technical architecture, formalizes **AWS EC2 + Ubuntu + Docker Compose + Caddy** as our official production target, outlines the networking flow and pedagogical deployment blueprint, and defines our strict **one-thing-at-a-time vertical slice roadmap**.

---

## Development Rules & Working Agreement

This agreement governs all development across the 48-hour sprint:

1. **One vertical slice at a time**
   * We implement only the current approved slice.
   * Do not begin the next slice until the current slice has been tested, reviewed, and explicitly approved.

2. **Vertical-slice workflow**
   For every slice:
   * Define the scope and acceptance criteria.
   * Implement only that scope.
   * Run automated tests.
   * Manually inspect/review the result.
   * Fix issues if necessary.
   * Explicitly approve the slice.
   * Only then move to the next slice.

3. **No scope creep**
   * Do not add features from future slices just because they are convenient to implement now.
   * If an architectural issue or dependency from a future slice is discovered, document it and discuss it before changing scope.

4. **Antigravity's role**
   * Implement the specific task we give it.
   * Do not autonomously proceed to later slices.
   * Report files changed, tests run, results, and important implementation decisions.
   * Stop after completing the requested slice/task and wait for review.

5. **Our review process**
   * ChatGPT and the developer/user will review the implementation after each slice.
   * We will verify both correctness and architectural quality before approval.

6. **Testing philosophy**
   * Prioritize meaningful tests for game rules, boundaries, state transitions, failure paths, and integration points.
   * Do not chase arbitrary 100% code coverage.

7. **Project principle**
   * The objective is to ship a working, publicly playable Hand Cricket game within the two-day sprint.
   * Prefer simple, reliable solutions over unnecessary engineering complexity.
   * However, do not avoid worthwhile engineering work merely because it is difficult; the priority is shipping a real working product.

8. **Decision authority**
   * The implementation plan is the source of truth for frozen architecture, scope, and roadmap.
   * Any change to frozen decisions must be explicitly discussed and approved before implementation.

---

## Legacy Reference: Cric.py

* `Cric.py` is the original CLI implementation of the Hand Cricket game.
* It is preserved as a historical/reference implementation.
* The new web game must preserve the core game rules established there where they match the newly frozen product requirements.
* The new architecture must NOT directly reuse its blocking `input()`/`print()` flow, global mutable state, or CLI control structure.
* The new game engine will independently model the game using explicit match state and server-authoritative state transitions.
* Where the new frozen product requirements differ from `Cric.py`, the frozen product requirements take precedence.

### Explicitly Recorded Differences
* **Over / Ball Limits**: Legacy game uses 120 balls / 20 overs; new game uses 30 balls / 5 overs per innings.
* **Execution Model**: Legacy implementation is CLI/input driven; new implementation is browser/WebSocket driven.
* **State Isolation**: Legacy implementation uses global mutable dictionaries; new implementation must isolate state per match/room.
* **Computer Opponent**: Legacy implementation has a computer opponent directly inside the terminal loop; the new architecture treats the computer as a server-side player/bot.
* **Strike and Player Flow**: Legacy implementation's internal strike/state handling should not be blindly copied; it must be evaluated against the newly frozen game rules.

> “Cric.py preserves the original game's historical logic and intent; the new engine preserves the applicable rules while redesigning the implementation for a server-authoritative web application.”

---

## 1. Frozen System Architecture

```
                                  PUBLIC INTERNET
                                         │
                   HTTPS (:443) / WSS (:443) / HTTP (:80 redirect)
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                        AWS EC2 INSTANCE (Ubuntu 24.04 LTS)                        |
|   Elastic IP attached • Security Group: Inbound 22 (SSH), 80 (HTTP), 443 (HTTPS)  |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                       CADDY CONTAINER (Reverse Proxy)                       |  |
|  | - Listens on ports 80 & 443                                                 |  |
|  | - Automatically provisions & renews Let's Encrypt SSL using IP-encoded       |  |
|  |   hostname resolution (e.g., <elastic-ip>.sslip.io maps to <elastic-ip>)    |  |
|  | - Terminates HTTPS and WSS                                                  |  |
|  | - Transparently proxies WebSocket upgrades: `reverse_proxy app:8000`        |  |
|  +-----------------------------------------------------------------------------+  |
|                                        │                                          |
|                          Internal Docker Bridge Network                           |
|                                        │                                          |
|                                        ▼                                          |
|  +-----------------------------------------------------------------------------+  |
|  |                     APPLICATION CONTAINER (FastAPI + React)                 |  |
|  | - Listens internally on port 8000 (not exposed to public internet)          |  |
|  | - Multi-stage build: Vite React SPA compiled into static files               |  |
|  | - FastAPI serves static UI files on `/` and `/assets`                       |  |
|  | - FastAPI manages real-time WebSocket traffic on `/ws/{room_code}`         |  |
|  | - In-memory ephemeral game rooms with asyncio 5s decision timers           |  |
|  | - Pure Python authoritative cricket game engine                             |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### Why this architecture is ideal for a DevOps student:
1. **Real-world DevOps practice**: You configure security groups, Elastic IPs, SSH keys, Linux daemon processes, Docker Compose networking, reverse proxies, and TLS certificate lifecycle.
2. **Minimal complexity**: Zero enterprise bloat. No Kubernetes, no multi-VPC routing, no redundant load balancers. Everything runs reliably on a single virtual server.
3. **Budget safe**: Uses an EC2 `t3.small` instance (~$0.0208/hour). A full 48-hour sprint consumes ~**$1.00**, seamlessly covered by your ~$100 student credits.

---

## 2. Networking & Traffic Flow Explained

Understanding the packet path prevents "black box" confusion during setup and debugging:

```
[User on Mobile / Desktop Browser]
             │
             │ 1. Browser queries DNS for `54-xx-xx-xx.sslip.io`
             ▼
[DNS Resolver returns EC2 Elastic IP `54.xx.xx.xx`]
             │
             │ 2. Browser initiates TCP connection on port 443 (HTTPS/WSS)
             ▼
[AWS EC2 Security Group Firewall]
             │ (Inspects packet: Is port 443 open? YES -> Pass traffic to OS)
             ▼
[Ubuntu Kernel / Docker Port Forwarding]
             │ (Routes host:443 to Caddy container:443)
             ▼
[Caddy Reverse Proxy]
             │ 3. Performs TLS handshake using Let's Encrypt certificate.
             │ 4. Decrypts HTTPS/WSS payload into raw HTTP/1.1 or WebSocket frame.
             │ 5. Inspects HTTP headers:
             │    - If standard GET / -> forwards to `app:8000`
             │    - If `Upgrade: websocket` -> maintains persistent TCP tunnel to `app:8000`
             ▼
[FastAPI Application (Uvicorn)]
             │ 6. Dispatches to static file router (HTML/JS/CSS) or WebSocket endpoint.
             ▼
[In-Memory Game Room / Engine]
```

---

## 3. The 22-Point EC2 Deployment Master Guide (DevOps Blueprint)

When we reach **Slice 11 (Deployment of Walking Skeleton)**, we will walk through every step with full pedagogical explanations:

1. **Creating the Instance**: Navigating AWS EC2 Console, choosing the optimal region (e.g., `us-east-1` or closest to you for lowest ping).
2. **OS Image**: Selecting **Ubuntu 24.04 LTS (HVM), SSD Volume Type** (64-bit x86)—industry standard, massive community support.
3. **Instance Sizing**: Choosing **`t3.small`** (2 vCPUs, 2 GB RAM)—provides comfortable memory for building Docker images and running Caddy + Python simultaneously without out-of-memory (OOM) crashes.
4. **Security Group Configuration**: Creating `hand-cricket-sg`.
5. **Ports & Whitelisting**:
   * Port `22` (SSH): For terminal administration.
   * Port `80` (HTTP): Mandatory for ACME HTTP-01 challenge (Let's Encrypt validation) and redirecting users to HTTPS.
   * Port `443` (HTTPS/WSS): Encrypted web and WebSocket traffic.
   * *Why port 8000 is NOT exposed*: Internal security best practice. FastAPI is isolated inside the private Docker network; only Caddy can reach it.
6. **SSH Key Pair Creation**: Creating `hand-cricket-key.pem` (RSA or ED25519) and securely storing it.
7. **Connecting from Windows**: Setting Windows file permissions (`icacls` or PowerShell) and using native OpenSSH:
   `ssh -i path\to\key.pem ubuntu@<elastic-ip>`
8. **System Maintenance**: Updating package indices: `sudo apt update && sudo apt upgrade -y`.
9. **Installing Docker**: Installing official Docker Engine via the Docker apt repository.
10. **Installing Docker Compose**: Enabling `docker compose` plugin for declarative multi-container management.
11. **Git Repository Setup**: Cloning the GitHub repository directly onto the EC2 server.
12. **Docker Compose Architecture**: Defining `docker-compose.yml` with two services (`app` and `caddy`) sharing an internal bridge network `web_net`.
13. **Caddy Configuration**: Writing `Caddyfile` using an IP-encoded hostname (e.g. `<elastic-ip>.sslip.io`, where sslip.io resolves the encoded IP directly to your EC2 Elastic IP). Caddy automatically uses this public hostname to obtain a Let's Encrypt TLS certificate via standard ACME HTTP-01 challenge:
    ```caddyfile
    YOUR_ELASTIC_IP.sslip.io {
        reverse_proxy app:8000
    }
    ```
14. **Automated SSL Lifecycle**: How Caddy talks to Let's Encrypt over ACME, passes the HTTP-01 challenge, issues certificates, and auto-renews.
15. **WebSocket Termination in Caddy**: Why Caddy automatically handles `Connection: Upgrade` and `Upgrade: websocket` without manual proxy headers.
16. **Starting Services**: `docker compose up -d --build` (running in detached mode).
17. **Verification**: Checking container health with `docker compose ps` and `curl -I https://<ip>.sslip.io/health`.
18. **Observability & Logs**: Viewing live logs with `docker compose logs -f app` and `docker compose logs -f caddy`.
19. **Restarting Services**: Graceful restarts using `docker compose restart`.
20. **Zero-Downtime Updates (CI/CD flow)**: Pulling new code: `git pull && docker compose up -d --build`.
21. **Teardown & Cost Management**: Releasing Elastic IPs and stopping or terminating instances from the AWS console to prevent credit burn when finished.
22. **Troubleshooting Matrix**: Resolving common issues (port conflicts, permission denied, Docker OOM, DNS propagation delays, TLS handshake timeouts).

---

## 4. Vertical-Slice Development Roadmap

We adhere strictly to our **one-thing-at-a-time** rule. Each slice has a single capability, automated verification, and explicit review before advancing.

```
+-------------------------------------------------------------------------+
|                  CORE GAME ENGINE & LOGIC (DAY 1 - PART 1)              |
+-------------------------------------------------------------------------+
  Slice 1: Project Skeleton & Baseline Test Harness
     │
     v
  Slice 2: Single Ball Resolution Engine (1-6 matching rules)
     │
     v
  Slice 3: Batsman Lifecycle & Score Tracking (Runs, balls, OUT status)
     │
     v
  Slice 4: Over & Innings Progression (6 balls/over, 5 overs, 10 wickets)
     │
     v
  Slice 5: Bowler Quota Enforcement (1 over max per bowler, 5 unique bowlers)
     │
     v
  Slice 6: Full Match & Target Chasing (2 innings + early finish check)
     │
     v
  Slice 7: Predefined Teams & Toss Mechanics (4 teams, A/B coin toss)
     │
     v
  Slice 8: Headless Computer Player (100-match automated Bot vs. Bot test)

+-------------------------------------------------------------------------+
|               BACKEND, WEBSOCKETS & DEPLOYMENT (DAY 1 - PART 2)          |
+-------------------------------------------------------------------------+
  Slice 9: Backend HTTP & WebSocket Foundation ("Walking Skeleton")
     │
     v
  Slice 10: WebSocket Game Protocol & 5-Second Turn Timer
     │
     v
  Slice 11: Production Deployment of Backend Walking Skeleton to AWS EC2
            (Launch EC2, configure Security Group, Elastic IP, Docker & Caddy.
             Deploy backend walking skeleton and verify HTTP /health & public WSS
             connectivity from phone/browser. The full React UI will be integrated in Slice 12).

+-------------------------------------------------------------------------+
|               FRONTEND & FULL-STACK INTEGRATION (DAY 2)                 |
+-------------------------------------------------------------------------+
  Slice 12: Minimal Playable Arena UI (Vite + React + Tailwind + Bot Mode)
     │
     v
  Slice 13: Pre-Match Flows (Landing, Team Select, Toss, Bowler Select)
     │
     v
  Slice 14: Polish, Edge Cases & Animations (Coin flip, Wicket alert, Auto-pick badge)
     │
     v
  Slice 15: Friend Mode E2E Testing, Multi-Device Verification & Final Ship
```

---

## 5. Testing Philosophy & Acceptance Criteria for Slice 1

### Testing Philosophy Across the Project:
We do **not** enforce dogmatic 100% arbitrary line-coverage metrics. Instead, our testing focuses on high-value, meaningful coverage:
- Core game rule mechanics (runs, wickets, strike, bowler limits).
- Boundary conditions (30 balls completed, 10 wickets, 0 runs, target ties).
- State transition integrity and failure paths (invalid numbers, timeouts, auto-picks).
- Integration points (WebSocket ping/pong, room creation, turn timer expiry).

### Slice 1 Acceptance Criteria:
* **Directory Structure**: Clear separation between `backend/`, `frontend/`, and `deploy/` with `.gitignore` configured.
* **Dependencies**: Python backend requirements pinned (`fastapi`, `uvicorn`, `websockets`, `pydantic`, `pytest`).
* **Test Harness**: A sanity test file (`test_sanity.py`) verifying the testing environment.
* **Verification Command**: Executing `pytest` succeeds with all tests passing (exit code 0).
