# Contributing to Meridian

First — thanks for your interest. Meridian is built in the open and we welcome
contributions of all sizes. This document covers what you need to know to get
your changes merged quickly.

> Read **`AGENTS.md`** before opening a non-trivial PR. It documents the
> non-negotiable architectural rules (Kafka-only event bus, MERGE on Neo4j,
> SHAP for every risk score, etc.) that reviewers will check against.

---

## Table of contents

1. [Code of conduct](#code-of-conduct)
2. [Project status & phases](#project-status--phases)
3. [Setting up your environment](#setting-up-your-environment)
4. [Pick something to work on](#pick-something-to-work-on)
5. [Development workflow](#development-workflow)
6. [Code standards](#code-standards)
7. [Testing](#testing)
8. [Documentation requirements](#documentation-requirements)
9. [Submitting your PR](#submitting-your-pr)
10. [Reporting bugs & security issues](#reporting-bugs--security-issues)

---

## Code of conduct

Be excellent to each other. See `CODE_OF_CONDUCT.md` for the full text.
Harassment, discrimination, or trolling will result in immediate removal from
the project.

## Project status & phases

| Phase | Scope | Status |
| ----- | ----- | ------ |
| 1 | Kafka ingestion (GDELT / ACLED / AIS) | ✅ Stable |
| 2 | Entity resolution + Neo4j knowledge graph | 🔄 In progress |
| 3 | Intelligence engine (BERT / XGBoost / NER) | 🟡 Built, needs ML tests |
| 4 | Simulation + alerting (Monte Carlo / BFS / Slack) | 🟡 Built, partial tests |
| 5 | Frontend dashboard + JWT auth | 🟡 Functional, needs polish |
| 6 | Production deployment (Terraform / CI/CD) | 🟡 IaC complete, untested in cloud |

If you're new, start with `good first issue` labels — these are scoped to a
single file or function and have clear acceptance criteria.

## Setting up your environment

### Prerequisites

- Python 3.11 or 3.12 (3.13 is **not** supported yet — pandas wheel issue)
- Docker Desktop
- Node 20+ (for the React frontend)
- Make (optional, but used by `make` targets)

### One-time setup

```bash
git clone https://github.com/askmy-stack/meridian.git
cd meridian

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Validate env config
cp .env.example .env
# edit .env to fill in your local secrets
python scripts/validate_env.py --env-file .env

# Frontend
cd frontend && npm install && cd ..

# Local infra
docker compose up -d
```

### Daily dev loop

```bash
make dev          # start API + frontend with hot reload
make test         # full pytest run
make test-unit    # unit tests only (fast, no services)
make lint         # black + ruff
make seed         # populate Neo4j with ports / chokepoints
```

## Pick something to work on

1. Check the [good first issue](https://github.com/askmy-stack/meridian/labels/good%20first%20issue)
   list.
2. Comment on the issue saying "I'd like to take this".
3. Wait for a maintainer to assign it (usually < 24h).
4. Open a draft PR early so we can discuss approach before you go deep.

If you have an idea that doesn't have an issue yet, open a feature request
issue first using the template in `.github/ISSUE_TEMPLATE/feature_request.md`.

## Development workflow

We use trunk-based development with short-lived feature branches.

```text
main          ← protected, deployable at any time
 ├─ feat/xxx  ← your work
 └─ fix/xxx
```

1. Branch from `main`: `git checkout -b feat/your-thing`.
2. Make focused commits with conventional-commit style messages
   (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
3. Keep your branch rebased on `main`.
4. Open a PR with the template filled out.

## Code standards

- **Type hints on every function.** No `# type: ignore` without justification.
- **Docstrings on every public class / function.** Keep them short and useful.
- **No `print()`** — use `structlog` (`logger = structlog.get_logger(__name__)`).
- **No hardcoded secrets** — use `os.getenv()` with fail-fast defaults.
- **No new untracked files** — every code path needs to be reachable from
  `src/`, `tests/`, `frontend/src/`, or a documented script.
- **No bypassing the architectural rules in `AGENTS.md`.**

### Architectural non-negotiables

| Rule | Why |
| ---- | --- |
| All inter-service comms via Kafka | One event bus, easy replay, no retries-of-retries |
| Neo4j is the source of truth for relationships | No graph logic in app code |
| MERGE, not CREATE, for Neo4j writes | Idempotency for reprocessed events |
| MLflow for every ML experiment | No untracked model versions |
| SHAP explanation for every risk score | No black-box outputs |
| Monte Carlo runs ≥ 1000 iterations | Never point estimates |

## Testing

We split tests into two suites:

```bash
pytest tests/unit/         # fast, mocked, no Docker required
pytest tests/integration/  # requires docker compose up -d
```

Rules:

- **Every bug fix gets a regression test.** No exceptions.
- **Don't delete or weaken tests** without an explicit note in the PR.
- **Fail fast.** Tests should not require the network unless they're under
  `tests/integration/external/`.
- Coverage is enforced per-module — keep it green.

Running a subset:

```bash
pytest tests/unit/test_producers.py::TestGDELTProducer -v
pytest tests/integration/test_api_endpoints.py -v
```

## Documentation requirements

Update these alongside code changes when relevant:

- `ARCHITECTURE.md` — for any new module or major data-flow change
- `DECISIONS.md` — for architectural decisions (new ADR entry)
- `SESSIONS.md` — only maintainers append; describes what shipped each session
- `MISTAKES.md` — when you introduce or discover a non-obvious gotcha
- `README.md` — for user-facing capability changes

PRs that change behavior without updating docs will be sent back.

## Submitting your PR

Before requesting review, confirm:

- [ ] `make lint` passes
- [ ] `make test` passes locally
- [ ] You've added a test that fails without your change
- [ ] Docs updated (see above list)
- [ ] No new hardcoded secrets / credentials / wildcards
- [ ] Conventional commit message in the PR title
- [ ] PR description references the issue (`Closes #123`)

A maintainer will review within 3 business days. Squash-merge is the default.

## Reporting bugs & security issues

- Non-security bugs → use the bug report issue template.
- **Security vulnerabilities → email security@meridian.dev** (see `SECURITY.md`).
  Do not file public issues for vulnerabilities.

---

Thanks again. Welcome aboard. 🚢
