# gh-agent

Autonomous GitHub agent for the [godseritesh](https://github.com/godseritesh) organization. Monitors repos, detects bugs/issues, plans fixes, implements changes, creates PRs, auto-merges, and deploys — all on the **free tier** using Hugging Face Inference API.

**Cost: $0.** No API keys needed.

---

## Quick Start

### 1. Create a new repo for the agent

```bash
# Create a new repo on GitHub called "gh-agent" (private or public)
# Then run:
git init
git remote add origin https://github.com/godseritesh/gh-agent.git
git add .
git commit -m "initial commit: gh-agent"
git branch -M master
git push -u origin master
```

### 2. Initialize the state branch

```bash
git checkout --orphan agent-state
git rm -rf .
echo '{"last_checked_commit": {}, "in_progress": null, "token_budget": {"date": "", "tokens_used": 0, "daily_limit": 30000}}' > agent-state.json
git add agent-state.json
git commit -m "init state"
git push origin agent-state
git checkout master
```

### 3. Set GitHub Actions Secrets

Go to `https://github.com/godseritesh/gh-agent/settings/secrets/actions` and add:

| Secret | Value | Required? |
|---|---|---|
| `HF_TOKEN` | Your Hugging Face API token from [hf.co/settings/tokens](https://huggingface.co/settings/tokens) | Yes — needed for LLM inference |
| `GH_PAT` | GitHub Personal Access Token with `repo` + `workflow` scopes | Recommended — needed for auto-merge and state branch pushes |

> **Note:** `GITHUB_TOKEN` is auto-provided but has limitations (can't push to protected branches, can't auto-merge PRs it creates). For full functionality, create a PAT and store it as `GH_PAT`.

### 4. Update Target Repo Config

Edit `.agent-config.yaml` to point to your target repos. The config is already set up for all 6 active godseritesh repos.

```yaml
repos:
  SkyLink:
    test_framework: junit
    build_command: mvn clean compile
    lint_command: mvn checkstyle:check
    deploy_command: null
    active: true
```

Fields:
- `test_framework` — `null` means lint-only, no auto-merge
- `build_command` — run before tests (can be `null`)
- `lint_command` — run after changes (can be `null`)
- `deploy_command` — run post-merge (can be `null`)
- `active` — `false` = skip this repo

### 5. Verify Setup

Manually trigger a workflow:

```bash
gh workflow run "Agent - Daily Scan"
# or trigger via the GitHub web UI: Actions → Agent - Daily Scan → Run workflow
```

Check workflow logs in GitHub Actions for any errors.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  GitHub Actions (free tier)                  │
│                                                             │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │ Inventory │   │ Issue Detect │   │   Daily Scan       │  │
│  │ (weekly)  │   │ (on event)   │   │  (weekdays 8am)    │  │
│  └────┬─────┘   └──────┬───────┘   └─────────┬──────────┘  │
│       │                │                     │             │
│       └────────────────┼─────────────────────┘             │
│                        ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              agent/ (Python 3.13)                   │   │
│  │  config → state → scanner → planner → coder → pr    │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │                                          │
│                 ▼                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Hugging Face Inference API (free tier)       │   │
│  │  Qwen3-27B → Gemma 4-4B → Phi-4 (fallback chain)    │   │
│  └─────────────────────────────────────────────────────┘   │
│                 │                                          │
│                 ▼                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Target Repos (godseritesh/*)                 │   │
│  │  SkyLink │ nss-platform │ Map_My_Ganapati │ ...     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `agent-daily.yml` | Schedule (weekdays 8am) + manual | Full scan of all active repos, one change max |
| `agent-inventory.yml` | Schedule (weekly Sunday) | Audit all repos: CI configs, tech stacks, code quality |
| `agent-issue-detection.yml` | Push, Issues, PRs, manual | React to events: review diffs, classify issues |

### Model Fallback Chain

The agent tries models in order. If one is rate-limited, it falls through:

1. **Qwen3-27B** — Apache 2.0, strong coding, primary model
2. **Gemma 4-4B** — Apache 2.0, fast fallback for simple tasks
3. **Phi-4** — MIT license, small reasoning model, last resort

---

## How the Agent Works

### 1. Repo Inventory & CI Audit
- Scans all active repos for CI configs (GitHub Actions, Travis, Jenkins)
- Detects tech stack from build files
- Reports findings to GitHub Actions log

### 2. Issue Detection
- **On push:** compares `last_checked_commit` to HEAD, analyzes only changed files
- **On issue opened:** classifies issue priority and category
- **On PR opened:** reviews the diff for problems
- **On schedule:** full scan of repos without recent events

### 3. Prioritization & Planning
- LLM scores each issue by: business impact, security risk, component visibility
- Produces a plan with subtasks in format: `[step] → verify: [check]`
- Max **3 subtasks** per run

### 4. Implementation (Test-in-the-Loop)
For each subtask (max 3 iterations):
1. LLM analyzes the code and produces a fix
2. Applies the patch
3. Runs test and lint commands (if configured)
4. If tests fail and iterations remain, refines the patch
5. If no test framework configured → lint-only, no auto-merge

### 5. PR & Auto-Merge
- Creates a feature branch with changes
- Opens a PR with a structured template (Problem/Change/Testing/Risk)
- Enables auto-merge (`gh pr merge --auto --squash`)
- PR merges when all required checks pass

### 6. State Persistence
- State is stored on the `agent-state` branch as `agent-state.json`
- Survives across GitHub Action runs
- Tracks: last checked commit per repo, daily token budget, in-progress tasks
- Token budget resets daily (30k tokens/day)

---

## Token Budget

The Hugging Face Inference API free tier has a **30k input tokens/minute** limit. The agent tracks usage per day and stops when the budget is exceeded:

```json
{
  "token_budget": {
    "date": "2026-06-15",
    "tokens_used": 12500,
    "daily_limit": 30000
  }
}
```

Budget resets at midnight UTC. If you hit the limit, the agent skips remaining repos and resumes the next day.

---

## Adding a New Repo

1. Add the repo to `.agent-config.yaml`:
```yaml
repos:
  NewRepo:
    test_framework: pytest
    build_command: null
    lint_command: ruff check .
    deploy_command: null
    active: true
```

2. Ensure the repo is under the `godseritesh` GitHub organization.

3. The agent picks it up automatically on the next run.

---

## Common Issues

| Problem | Fix |
|---|---|
| `HFApiError: 503` | Hugging Face model is loading. Retry in 30s. |
| `Rate limit: 429` | Wait a minute. Budget resets daily. |
| `gh pr merge --auto` fails | Set `GH_PAT` secret (not enough with `GITHUB_TOKEN`). |
| State branch not found | Run `git checkout --orphan agent-state` and push. |
| `pip install -e ".[dev]"` fails | Update `pyproject.toml` dependency versions. |

---

## Project Structure

```
gh-agent/
├── CLAUDE.md                    # Full project spec & behavioral guidelines
├── README.md                    # This file
├── pyproject.toml               # Python project config
├── .agent-config.yaml           # Per-repo configurations
├── .gitignore
├── .github/workflows/
│   ├── agent-daily.yml          # Daily scan (weekdays)
│   ├── agent-inventory.yml      # Weekly inventory
│   └── agent-issue-detection.yml # Event-driven detection
├── agent/
│   ├── __init__.py
│   ├── config.py                # Config loader & validator
│   ├── state.py                 # State management (branch-persisted)
│   ├── sync_state.py            # Git branch sync for state
│   ├── hf_client.py             # Hugging Face Inference API client
│   ├── scanner.py               # Repo CI / stack detection
│   ├── planner.py               # Issue classification & planning
│   ├── coder.py                 # Code generation & test runner
│   ├── pr.py                    # PR creation & auto-merge
│   └── main.py                  # Orchestration
└── tests/
    ├── test_config.py
    ├── test_state.py
    ├── test_hf_client.py
    ├── test_planner.py
    ├── test_coder.py
    ├── test_pr.py
    └── test_failure_modes.py
    └── fixtures/
```
