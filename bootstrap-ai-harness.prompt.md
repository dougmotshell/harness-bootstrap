---
name: "bootstrap-ai-harness"
description: "Bootstrap the current project's AI harness: run the deterministic init script, then do the part only a model can — detect the stack, wire the sensors, fill the contract from real evidence, and verify with harness-score. Idempotent and non-destructive."
agent: agent
---

# /bootstrap-ai-harness

Takes no arguments: it acts on the current workspace root, in pt-BR and en-US.

The copying is not your job. `TEMPLATES_REPO/scripts/init-project.py` owns it —
deterministic, idempotent, non-destructive, and already tested. Your job is what a
script cannot do: read the project and turn its `TODO:` markers into facts.

`TEMPLATES_REPO` = TODO absolute path of the templates repository on this machine.

## What the script already did

35 files: `AGENTS.md` and the two thin adapters, `README.md`, `LICENSE`, `Makefile`,
`.gitignore`, `.env.example`, `.mcp.json`, `.harness-score.json`,
`.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `.claude/settings.json` with
three hooks, `scripts/sync-ai-surfaces.py`, one example agent / skill / rule,
`memory/MEMORY.md`, and `docs/` in `pt-br` and `en-us` with the four trees. Then it ran
the surface generator.

That lands the project at **L2 · Guided, 83/106** on
[harness-score](https://github.com/paladini/harness-score). Everything below is the
climb to L4, and none of it can be templated.

## Step 0 — Run it, or audit

```bash
python3 TEMPLATES_REPO/scripts/init-project.py . --dry-run   # see the plan
python3 TEMPLATES_REPO/scripts/init-project.py .             # write
python3 TEMPLATES_REPO/scripts/init-project.py . --check     # audit; exit 1 if incomplete
```

An existing file is never overwritten — the script reports it as `exists` and moves on.
If the project already has a contract, run `--check` and report the gap instead of
scaffolding over it. Migrating is a separate, explicit request.

If only `CLAUDE.md` exists, offer the built-ins first: `/init` (with
`CLAUDE_CODE_NEW_INIT=1`) reads `AGENTS.md`, Cursor and Copilot rules; `/import` carries
over another CLI's commands, subagents, skills and MCP servers.

## Step 1 — Wire the sensors (this is the whole game)

20 of the 23 missing points are `SNS-01..05`, and `sensors ≥ 60%` is what gates L3.
Detect the stack from manifests only, then fill the four `Makefile` targets **and** add
the tool config the check actually looks for:

| Target | Needs on disk | Python | Node/TS | Go |
|---|---|---|---|---|
| `test` | runner config + ≥1 test file | `pytest` | `vitest run` | `go test ./...` |
| `lint` | linter config | `ruff check .` | `eslint .` | `golangci-lint run` |
| `typecheck` | strict config | `mypy --strict .` | `tsc --noEmit` | native |
| `format` | formatter config | `ruff format .` | `prettier -w .` | `gofmt -w .` |

Also fill `lint-file` / `format-file` — the `PostToolUse` hook stays silent until they
leave their TODO stub. No manifest ⇒ leave the targets failing and say so; a sensor that
passes in silence is worse than no sensor.

Then remove `continue-on-error: true` from the `sensors` job in `ci.yml`, and add the
setup step for the stack.

## Step 2 — Fill the contract

`AGENTS.md`: stack, commands, conventions that differ from tool defaults, pitfalls.
Only what the manifests and the code prove. Unknowns stay `TODO:` — never a guess.

Budget: `AGENTS.md` + `CLAUDE.md` under 200 lines together (`@AGENTS.md` is an import;
it does not free context), `AGENTS.md` under 32 KiB, `SKILL.md` under 5,000 words,
`memory/MEMORY.md` under 200 lines. Over budget, move content to what loads on demand —
a skill, a path-scoped rule, the matching `docs/` tree, or a nested `AGENTS.md` — never
into another import.

Rename `example-specialist`, `example-procedure` and `example-area` to something this
project needs, then run `python3 scripts/sync-ai-surfaces.py --prune`.

Decide whether `docs/*/manual/` applies. No end users ⇒ delete the tree and declare the
absence, with the reason, in `docs/README.md`.

## Step 3 — Never

Overwrite, truncate or delete an authored file · touch `.git/` · stage or commit ·
write a secret, token, real hostname, PII or customer name · edit a file whose banner
says `managed-by:` (edit its source and run the generator) · invent architecture,
decisions or user steps.

## Step 4 — Verify with real output

Paste the command output. Never assert a check you did not run.

```bash
make sync-check                                   # surfaces in sync
wc -l AGENTS.md CLAUDE.md ; wc -c AGENTS.md       # under 200 lines / 32768 bytes
find docs -type d -name '*[A-Z]*'                 # must be empty: docs dirs are lowercase
diff <(cd docs/pt-br && find . -type f | sort) \
     <(cd docs/en-us && find . -type f | sort)    # empty, or every gap an explicit TODO
make test lint typecheck                          # the sensors you just wired
npx harness-score                                 # target: L4, 106/106
```

## Step 5 — Report

1. What the script created vs. what already existed.
2. What you wired: stack detected, sensor commands, configs added.
3. The verification output above, pass or fail, with the harness-score level and score.
4. Remaining `TODO:` markers, grouped by file.
5. What is left for a human: the lockfile (`HYG-07`) if dependencies are not installed
   yet, `pre-commit install`, and the `HARNESS_MIN_LEVEL` repository variable — `3` once
   the sensors are real, `4` once the hooks are in use.
