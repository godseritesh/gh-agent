# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merged with project-specific
instructions for the Autonomous Agent System.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work")
require constant clarification.

---

## 5. Project: Autonomous Agent System

### 5.1 Mission

An AI agent that **proactively maintains and improves** the godseritesh GitHub organization.
It works like a silent staff engineer who, every day:
- **Researches** one repo deeply — reads the codebase, runs linters, analyzes structure
- **Suggests** improvements — missing tests, error handling gaps, security issues, feature gaps
- **Implements** the best suggestion — writes production code, adds tests, runs them
- **Ships** via automated PR + auto-merge (deployment handled by target repo CI)

No human triggers needed. The agent initiates everything itself: research → plan → code → test → PR → merge.

### 5.2 Target Repositories

Active repos under godseritesh (agent proactively researches and improves these):

| Repo | Stack | Focus |
|---|---|---|
| SkyLink | Java, Spring Boot, MySQL, REST, JUnit | Airline reservation system |
| nss-platform | Spring Boot, React, PostgreSQL, JWT, Docker | Event polling & blood donation |
| Map_My_Ganapati | Next.js, Firebase, Leaflet, OpenStreetMap | Festival navigation app |
| Intelligent_Traffic_Manager_Agent | Python, GNN, RL, SUMO | ML traffic optimization |
| godseritesh.github.io | React, TypeScript, Tailwind, Framer Motion | Portfolio website |

Archived repos (monitor-only; no active changes):
File_uploader, Criminal_Management_System, AWS_Rekognition_Video_Indexing, Resume_Parser,
Fastagminiature, HandRX, Car_Management_System, Handwritten_Digits_Recognizer,
Car_Rental_Website

### 5.3 Model & Infrastructure

| Component | Choice | Justification |
|---|---|---|
| Primary LLM | GitHub Models GPT-4o-mini (via GH_TOKEN, free tier) | Zero cost, better code quality |
| Fallback Model | Groq (llama-3.3-70b, llama-4-scout, qwen3-32b) → HF router (depleted) | Graceful degradation |
| Orchestration | GitHub Actions (free tier, event-driven) | No recurring cost |
| State | JSON file on dedicated `agent-state` branch | Zero infra, transparent |
| Per-repo config | `.agent-config.yaml` files per repo | Explicit, DRY |

Cost model: **Zero.** No API keys, no paid tiers, no cloud compute.

### 5.4 Architecture Decisions (Agreed)

| Area | Decision |
|---|---|
| Pipeline | Modular sub-agents (separate GitHub Action workflows per step) |
| Triggering | Event-driven: `on: [push, issues, pull_request, schedule(daily)]` |
| State persistence | JSON state file on `agent-state` branch in target repo |
| API error handling | Retry with exponential backoff (3 attempts), fallback to smaller model |
| Test loop | Max 3 iterations per subtask, then escalate via GitHub Issue |
| PR body | Template-based (Problem, Change, Testing, Risk) — no raw LLM output |
| Context | Only changed files per run (`last_checked_commit` in state) |
| Rate limits | Check `x-ratelimit-remaining`, sleep if <100 remaining |
| Git clone caching | GitHub Actions `actions/cache` for daily runs |
| Daily token budget | Tracked in state file — stop when exceeded, resume next day |
| Agent testing | Unit tests for all modules with mocked API responses |
| Failure mode tests | Corrupt state, invalid config, 429, timeout, 500, git conflict |

### 5.5 Workflow Pipeline

#### Step 1: Deep Repo Research
- Clone the repo
- Build file tree with line counts, detect test files, identify tech stack
- Read key files (README, build files, configs, CI workflows)
- Run linter to get current code quality snapshot
- LLM analyzes the full codebase structure and returns improvement suggestions

#### Step 2: Suggestion Scoring
- Score each suggestion by: impact (user-facing value), effort (implementation cost)
- Filter by effort budget (max "medium" per day)
- Pick highest-impact suggestion that fits budget
- One change per day max

#### Step 3: Implementation Planning
- LLM produces a step-by-step plan from the selected suggestion
- Plan format: `[{step, verify, files}]`
- Max 3 subtasks per change

#### Step 4: Implementation (Test-in-the-Loop)
For each subtask (max 3 iterations):
1. LLM generates the implementation code
2. Apply the patch
3. Run test suite (if `test_framework` is set in config)
4. Run linter
5. If tests fail, output logged for later human review

If no test framework: lint-only, no auto-merge.

#### Step 5: PR & Auto-Merge
- Commit to a feature branch (`agent-{category}-{repo}-{timestamp}`)
- Create PR via `gh pr create` with structured template
- CI runs automatically
- Enable auto-merge: `gh pr merge --auto --squash`
- PR merges when all required checks pass

#### Step 6: Daily Cadence
- GitHub Actions `schedule` trigger (weekdays 8am UTC)
- Research one repo per day (round-robin)
- At most one PR per day — focused, minimal, tested

### 5.6 Engineering Rules (Per-Repo)

- Follow existing conventions (naming, imports, framework usage)
- Before writing code, read surrounding context to understand patterns
- Prefer editing existing files over creating new ones
- After changes: remove imports/variables YOUR changes made unused
- After changes: run linters and type-checkers if available
- Per-repo config defines: `test_framework`, `build_command`, `lint_command`
- If `test_framework` is null → lint-only, no auto-merge

### 5.7 Success Criteria

System is working if:
- Each run produces at most one PR with a minimal, focused change
- No unnecessary files or code appear in diffs
- All tests pass before merge (when applicable)
- Clarifying questions come before implementation, not after
- Monthly GitHub Actions usage stays under 500 minutes
- API cost: $0

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to
overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Progress

### Done
- CLAUDE.md created with behavioral guidelines + full agent spec
- Architecture review: modular sub-agents over monolithic pipeline
- All core Python modules: config.py, state.py, sync_state.py, hf_client.py, scanner.py, planner.py, coder.py, pr.py, main.py
- GitHub Actions main workflow: agent-main.yml (schedule-driven, weekdays 8am UTC)
- 48 unit tests across 8 test files, all passing (ruff lint: clean)
- Repo pushed to https://github.com/godseritesh/gh-agent (public)
- agent-state branch created for state persistence
- HF_TOKEN secret set in "prod" environment
- First workflow run completed: all 5 active repos cloned & analyzed
- Pipeline: reactive → proactive (research → plan → implement)
- **AGENTS.md system** (`agent/agents_md.py`): per-repo context cache stored on agent-state branch. First run writes AGENTS-<repo>.md via deep analysis; subsequent runs load cached context (skip full re-scan if no new commits). Shipped features appended after each PR.
- **EOD Email Notification** (`agent/notify.py`): SMTP daily summary (weekdays 1:30pm UTC = 6:30pm IST) via `agent-eod-summary.yml` workflow. Summarizes repos researched, changes shipped, PR URLs, token usage. Requires SMTP_HOST/PORT/USER/PASS/TO secrets.
- **State tracking**: `shipped_today` + `repos_seen_today` in agent-state.json for EOD summary; auto-reset daily.
- **sync_state.py** handles AGENTS-*.md files alongside agent-state.json.
- **GitHub Models API** (`agent/hf_client.py`): `_call_github_models()` using GH_TOKEN at `https://models.github.ai/inference/chat/completions`. Reordered provider priority: GitHub Models → Groq → HF router.
- **`models: read` permission** added to agent-main.yml for GitHub Models API access.
- **Pre-commit build verification** (`agent/main.py`): runs build_command from config before committing; fails fast, skips PR.
- **Deployment removed** from pipeline — handled by target repo CI.
- **AST-aware RAG index** (`agent/indexer.py`, `agent/parsers/`): weekly-built code index with semantic chunks using libCST (Python), regex fallbacks (Java/TS/Kotlin), and subprocess hooks for Spoon (Java) and ts-morph (TypeScript). Stored as `INDEX-<repo>.json` on agent-state branch.
- **Weekly index build workflow** (`.github/workflows/agent-index-build.yml`): Sundays 10:00 UTC.
- **`sync_state.py`** now handles `INDEX-*.json` alongside `AGENTS-*.md`.
- **RAG-enhanced context** (`agent/scanner.py`): `to_context()` appends AST-derived code snippets matching the repo domain, improving LLM understanding without full re-scan.

### In Progress
- *(none)*

### Blocked
- Groq TPM rate limit (6000/min on llama-3.1-8b-instant) — hits 429 after ~3-4 calls. 2s throttle insufficient. Fallback models 2-4 have unknown limits; HF router is dead (402 credits depleted).
- LLM still hallucinating code despite build context — SecurityConfig completely rewritten, ProfileController got javax.annotation.Nullable, PollController got newIllegalArgumentException. Coder prompt hardened but not yet runner-verified after pipeline changes.
- Windows encoding trap documented — PowerShell `>` redirection writes UTF-16 LE BOM. Must use `cmd /c "git show ... > ..."` or `[System.IO.File]::WriteAllText()` for clean UTF-8.
