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

Build an automated agent powered by Hugging Face Inference API (free tier) that:
- Monitors repos in the godseritesh GitHub organization
- Detects bugs, issues, and feature opportunities
- Evaluates business and audience relevance
- Plans fixes/features, breaks them into subtasks
- Implements changes following strict engineering rules
- Tests changes, creates PRs, auto-merges to master
- Triggers deployment and verifies correctness post-deploy

### 5.2 Target Repositories

Active repos under godseritesh:

| Repo | Stack | Focus |
|---|---|---|
| SkyLink | Java, Spring Boot, MySQL, REST, JUnit | Airline reservation system |
| nss-platform | Spring Boot, React, PostgreSQL, JWT, Docker | Event polling & blood donation |
| Map_My_Ganapati | Next.js, Firebase, Leaflet, OpenStreetMap | Festival navigation app |
| OptiHeart | Python, TensorFlow, Keras, Streamlit | CNN-based health prediction |
| Intelligent_Traffic_Manager_Agent | Python, GNN, RL, SUMO | ML traffic optimization |
| godseritesh.github.io | React, TypeScript, Tailwind, Framer Motion | Portfolio website |

Archived repos (monitor-only; no active changes):
File_uploader, Criminal_Management_System, AWS_Rekognition_Video_Indexing, Resume_Parser,
Fastagminiature, HandRX, Car_Management_System, Handwritten_Digits_Recognizer,
Car_Rental_Website

### 5.3 Model & Infrastructure

| Component | Choice | Justification |
|---|---|---|
| Primary LLM | HF Inference API free tier (Qwen3-27B, Phi-4, Gemma 4) | Zero cost, permissive licenses |
| Fallback Model | Smaller HF model if primary rate-limited | Graceful degradation |
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

#### Step 1: Repository Inventory & CI Audit
- Use `GET /orgs/{org}/repos` to list repos
- Check `.github/workflows/`, `.travis.yml`, `.gitlab-ci.yml`, `Jenkinsfile`
- Detect code quality tools (CodeQL, etc.)
- Output: inventory, tech stacks, CI/quality tooling

#### Step 2: Issue Detection (Event-Driven)
- On push: compare `last_checked_commit` to HEAD, analyze changed files only
- On issue opened: classify issue, check relevance
- On PR opened: review diff with LLM
- On schedule: full scan of repos without recent events

#### Step 3: Prioritization & Planning
- Score by: business impact, security risk, user-reported severity, component visibility
- LLM proposes plan with subtasks in format: `[task] → verify: [check]`
- Surface tradeoffs if multiple approaches exist

#### Step 4: Implementation (Test-in-the-Loop)
For each subtask (max 3 iterations):
1. Generate a failing test that reproduces the bug
2. Prompt LLM to produce minimal code change
3. Run the test suite (if `test_framework` is set in config)
4. If tests fail, analyze failure and refine patch
5. If tests pass, proceed
6. Run linters as additional QA gate

If no test framework: lint-only + AI review, no auto-merge.

#### Step 5: PR & Auto-Merge
- Commit to feature branch
- Create PR via `gh pr create`
- CI runs automatically
- Enable auto-merge: `gh pr merge --auto --squash`
- PR merges when all required checks pass

#### Step 6: Deployment & Monitoring
- Post-merge: build/publish or run smoke tests
- HTTP health checks, API call verification
- LLM-based evaluation (small model) to judge change quality
- Log results to GitHub Actions output

#### Step 7: Daily Cadence
- GitHub Actions `schedule` trigger (daily backup)
- Run on repos without recent events
- One high-priority change max per day

### 5.6 Engineering Rules (Per-Repo)

- Follow existing conventions (naming, imports, framework usage)
- Before writing code, read surrounding context to understand patterns
- Prefer editing existing files over creating new ones
- After changes: remove imports/variables YOUR changes made unused
- After changes: run linters and type-checkers if available
- Per-repo config defines: `test_framework`, `build_command`, `lint_command`, `deploy_command`
- If `test_framework` is null → lint-only, no auto-merge

### 5.7 Success Criteria

System is working if:
- Each run produces at most one PR with a minimal, focused change
- No unnecessary files or code appear in diffs
- All tests pass before merge (when applicable)
- Post-deploy smoke tests confirm no regression
- Clarifying questions come before implementation, not after
- Monthly GitHub Actions usage stays under 500 minutes
- API cost: $0

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to
overcomplication, and clarifying questions come before implementation rather than after mistakes.
