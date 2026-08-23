#!/usr/bin/env python3
"""Bootstrap another project's AI harness from `templates/`.

Deterministic on purpose: no model, no network, no judgement. Same input, same
output, every time.

    python3 scripts/init-project.py ../my-project
    python3 scripts/init-project.py ../my-project --dry-run
    python3 scripts/init-project.py ../my-project --check     # audit, write nothing

Works on an empty directory and on a project that already has a `Makefile`, a
`CLAUDE.md` and a `.claude/` — the harder case, and the one that decides whether the
harness is actually wired or merely present. Each file carries the merge strategy it
can survive:

    whole   write when absent, never touch when present (LICENSE, docs, AGENTS.md)
    block   append one delimited block, once (.gitignore, .env.example)
    make    append only the Makefile targets the project does not already define
    json    merge keys, keeping what is there (.claude/settings.json, .mcp.json)
    import  guarantee `@AGENTS.md` on line 1 (CLAUDE.md, copilot-instructions.md)
    advise  cannot be merged safely — print what to add by hand (pre-commit)

Nothing is ever overwritten, truncated or deleted. `--check` audits CONTENT, not the
presence of a path: a `Makefile` with no `sync-check`, or a `settings.json` that never
calls the hooks, is reported incomplete and exits 1.

What it deliberately does NOT do — because only a human or a model can: fill the
`TODO:` markers, detect the stack, write the sensor commands. That is the job of
`/bootstrap-ai-harness`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TEMPLATES = HERE / "templates"

# Seed names for the one-of-each examples. Renaming them is the project's first task;
# they exist so CTX-03, SKL-01 and AGT-01 pass from the first commit.
EXAMPLE_AGENT = "example-specialist"
EXAMPLE_SKILL = "example-procedure"
EXAMPLE_RULE = "example-area"
EXAMPLE_SPEC = "example-capability"
FIRST_ADR = "0001-record-architecture-decisions"

LANGS = ("pt-br", "en-us")
SOURCE_LANG = "pt-br"

BLOCK_OPEN = "harness-bootstrap >>>"
BLOCK_CLOSE = "harness-bootstrap <<<"


@dataclass(frozen=True)
class Item:
    """One template and the only way it can reach the target without breaking it."""

    template: str
    dest: str
    mode: str = "whole"
    executable: bool = False
    # Used when `dest` is already taken by something the project owns and the two
    # cannot be merged: a workflow file next to the project's own, not inside it.
    alt_dest: str | None = None
    # `--check`: substrings that must appear in the destination for the harness to be
    # wired. Empty means existence is the whole requirement.
    requires: tuple[str, ...] = ()


MANIFEST: list[Item] = [
    # contract and adapters
    Item("contract/agents.md.tpl", "AGENTS.md"),
    Item("contract/claude.md.tpl", "CLAUDE.md", mode="import", requires=("@AGENTS.md",)),
    Item("contract/copilot-instructions.md.tpl", ".github/copilot-instructions.md",
         mode="import", requires=("@AGENTS.md",)),
    # harness: hygiene and orientation
    Item("harness/readme.md.tpl", "README.md"),
    Item("harness/license-mit.tpl", "LICENSE"),
    Item("harness/gitignore.tpl", ".gitignore", mode="block",
         requires=(".env", "*.pem")),
    Item("harness/env.example.tpl", ".env.example", mode="block"),
    Item("harness/harness-score.json.tpl", ".harness-score.json"),
    Item("harness/mcp.json.tpl", ".mcp.json", mode="json"),
    # harness: sensors, CI, hooks
    Item("harness/makefile.tpl", "Makefile", mode="make",
         requires=("sync-check:", "lint-file:")),
    Item("harness/ci.yml.tpl", ".github/workflows/ci.yml",
         alt_dest=".github/workflows/harness.yml", requires=("sync-check",)),
    Item("harness/pre-commit-config.yaml.tpl", ".pre-commit-config.yaml", mode="advise",
         requires=("sync-ai-surfaces.py --check",)),
    Item("harness/settings.json.tpl", ".claude/settings.json", mode="json",
         requires=("gate-write.sh", "gate-bash.sh", "feedback-edit.sh")),
    Item("harness/hooks/gate-write.sh", ".claude/hooks/gate-write.sh", executable=True),
    Item("harness/hooks/gate-bash.sh", ".claude/hooks/gate-bash.sh", executable=True),
    Item("harness/hooks/feedback-edit.sh", ".claude/hooks/feedback-edit.sh", executable=True),
    # the generator
    Item("sync-ai-surfaces.py", "scripts/sync-ai-surfaces.py", executable=True),
    # authored sources: one example of each, so every surface has something to project
    Item("authored/agent.md.tpl", f".claude/agents/{EXAMPLE_AGENT}.md"),
    Item("authored/skill.md.tpl", f"skills/{EXAMPLE_SKILL}/SKILL.md"),
    Item("authored/rule.md.tpl", f".claude/rules/{EXAMPLE_RULE}.md"),
    Item("authored/memory.md.tpl", "memory/MEMORY.md"),
    # docs index (language-neutral)
    Item("docs/readme.md.tpl", "docs/README.md"),
]

# Documents that exist once per language subtree.
DOCS: list[tuple[str, str, str]] = [
    ("docs/architecture/01-context.md.tpl", "architecture/01-context.md", "Contexto"),
    ("docs/architecture/02-container.md.tpl", "architecture/02-container.md", "Containers"),
    ("docs/architecture/03-component.md.tpl", "architecture/03-component.md", "Componentes"),
    ("docs/architecture/04-code.md.tpl", "architecture/04-code.md", "Código"),
    ("docs/specs/spec.md.tpl", f"specs/{EXAMPLE_SPEC}.md", EXAMPLE_SPEC),
    ("docs/decisions/0000-adr.md.tpl", f"decisions/{FIRST_ADR}.md", "Registrar decisões de arquitetura"),
    ("docs/manual/index.md.tpl", "manual/index.md", "Manual"),
]

PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")
# A Makefile target: `name:` at line start. `:=` is a variable, not a target.
TARGET_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:(?!=)", re.M)


def substitute(text: str, values: dict[str, str]) -> str:
    """
    Replace only known placeholders, one by one. Never a blanket `{{...}}` sweep:
    `${{ vars.HARNESS_MIN_LEVEL }}` is GitHub Actions syntax and must survive.
    """
    for key, value in values.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def leftovers(text: str) -> list[str]:
    """
    Placeholders the caller left unresolved. GitHub Actions expressions are safe by
    construction: `${{ vars.X }}` carries spaces and lowercase, which `[A-Z_]+` in
    PLACEHOLDER cannot match.
    """
    return sorted(set(PLACEHOLDER.findall(text)))


# --- merge strategies ------------------------------------------------------


def wrap_block(body: str) -> str:
    """
    The template content as a delimited block. The markers go in even when the file is
    created from scratch — that is what makes the second run a no-op instead of
    appending the same block again, and what keeps a hand edit inside the block from
    ever being reverted. Every destination of this mode (.gitignore, .env.example,
    Makefile) comments with `#`.
    """
    return f"# {BLOCK_OPEN}\n{body.strip()}\n# {BLOCK_CLOSE}\n"


def merge_block(existing: str, body: str) -> tuple[str, str]:
    if BLOCK_OPEN in existing:
        return existing, "block present"
    if not existing.strip():
        return wrap_block(body), "block added"
    return existing.rstrip("\n") + "\n\n" + wrap_block(body), "block added"


def merge_makefile(existing: str, template: str) -> tuple[str, str]:
    """
    Append only the targets the project does not define. Appending all of them would
    silently override the project's own `test:` — make keeps the last recipe and only
    warns, which is the worst of both outcomes.
    """
    have = set(TARGET_RE.findall(existing))
    blocks: list[str] = []
    added: list[str] = []
    for para in template.split("\n\n"):
        m = TARGET_RE.search(para)
        if not m or m.group(1) in have:
            continue
        blocks.append(para.rstrip())
        added.append(m.group(1))
    if not blocks:
        return existing, "targets present"

    parts: list[str] = []
    # `$(TODO)` is what makes an unfilled sensor fail loudly instead of passing.
    if "TODO =" not in existing and any("$(TODO)" in b for b in blocks):
        parts.append("TODO = @printf 'TODO: fill the `%s` target in the Makefile.\\n' $@ && exit 1")
    parts.append(".PHONY: " + " ".join(added))
    parts.extend(blocks)
    merged = existing.rstrip("\n") + "\n\n" + wrap_block("\n\n".join(parts))
    return merged, "targets added: " + ", ".join(added)


def hook_commands(node: object) -> set[str]:
    """Every `command` string reachable inside a hooks entry list."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "command" and isinstance(value, str):
                found.add(value)
            else:
                found |= hook_commands(value)
    elif isinstance(node, list):
        for value in node:
            found |= hook_commands(value)
    return found


def merge_json(existing_text: str, template_text: str) -> tuple[str, str]:
    """
    Add what is missing, change nothing that is there. Hook lists are matched on the
    `command` string, so re-running never registers the same hook twice.
    """
    try:
        current = json.loads(existing_text or "{}")
    except json.JSONDecodeError as exc:
        return existing_text, f"left alone (not valid JSON: {exc.msg})"
    incoming = json.loads(template_text)
    if not isinstance(current, dict):
        return existing_text, "left alone (top level is not an object)"

    changes: list[str] = []

    def merge(dst: dict, src: dict, trail: str = "") -> None:
        for key, value in src.items():
            path = f"{trail}.{key}" if trail else key
            if key not in dst:
                if value not in ({}, []):
                    dst[key] = value
                    changes.append(path)
                continue
            if isinstance(dst[key], dict) and isinstance(value, dict):
                merge(dst[key], value, path)
            elif isinstance(dst[key], list) and isinstance(value, list):
                known = hook_commands(dst[key])
                for entry in value:
                    if not (hook_commands(entry) & known):
                        dst[key].append(entry)
                        changes.append(path)

    merge(current, incoming)
    if not changes:
        return existing_text, "already merged"
    return json.dumps(current, indent=2, ensure_ascii=False) + "\n", "merged: " + ", ".join(
        sorted(set(changes))
    )


def merge_import(existing: str, template: str) -> tuple[str, str]:
    """
    Guarantee the canonical import on line 1. Without it Claude Code reads a contract
    that never mentions `AGENTS.md`, and the project has two sources of truth — the
    exact failure this repository exists to prevent.
    """
    first = template.strip().splitlines()[0].strip()  # `@AGENTS.md`
    if first in existing:
        return existing, "import present"
    note = (
        f"{first}\n\n"
        "<!-- harness-bootstrap: AGENTS.md is canonical; anything that also applies to\n"
        "     Codex or Copilot belongs there, not here. -->\n\n"
    )
    return note + existing.lstrip("\n"), "import added"


def satisfies(path: Path, requires: tuple[str, ...]) -> bool:
    """Whether the file already contains everything the harness needs from it."""
    if not requires or not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return all(need in text for need in requires)


# --- bootstrap -------------------------------------------------------------


@dataclass
class Result:
    dest: str
    state: str


class Bootstrap:
    def __init__(self, target: Path, project: str, holder: str, year: str) -> None:
        self.target = target
        self.base_values = {"PROJECT": project, "YEAR": year, "COPYRIGHT_HOLDER": holder}
        self.results: list[Result] = []
        self.unresolved: dict[str, list[str]] = {}
        self.advice: list[tuple[str, str]] = []

    # --- writing ---------------------------------------------------------

    def rendered(self, item: Item, extra: dict[str, str] | None = None) -> str:
        src = TEMPLATES / item.template
        if not src.is_file():
            raise SystemExit(f"missing template: {src.relative_to(HERE)}")
        return substitute(src.read_text(encoding="utf-8"), {**self.base_values, **(extra or {})})

    def emit(self, item: Item, extra: dict[str, str] | None = None, *, write: bool) -> None:
        content = self.rendered(item, extra)
        dest = item.dest
        out = self.target / dest

        if not out.exists():
            state = "created"
            new_text = wrap_block(content) if item.mode in ("block", "make") else content
        elif (
            item.alt_dest
            and not (self.target / item.alt_dest).exists()
            and not satisfies(out, item.requires)
        ):
            # Cannot be merged (a workflow's YAML jobs are not appendable), so it goes
            # beside the project's file instead of fighting it for the name. Skipped
            # when the file already answers the requirement — including the run that
            # wrote it, which would otherwise get a duplicate on the next pass.
            dest, out = item.alt_dest, self.target / item.alt_dest
            state, new_text = "created (beside existing)", content
        elif item.mode == "block":
            new_text, state = merge_block(out.read_text(encoding="utf-8"), content)
        elif item.mode == "make":
            new_text, state = merge_makefile(out.read_text(encoding="utf-8"), content)
        elif item.mode == "json":
            new_text, state = merge_json(out.read_text(encoding="utf-8"), content)
        elif item.mode == "import":
            new_text, state = merge_import(out.read_text(encoding="utf-8"), content)
        elif item.mode == "advise":
            self.advice.append((dest, content))
            self.results.append(Result(dest, "exists — see the note below"))
            return
        else:
            self.results.append(Result(dest, "exists"))
            return

        remaining = leftovers(new_text)
        if remaining and state.startswith("created"):
            self.unresolved[dest] = remaining

        self.results.append(Result(dest, state))
        if not write or new_text == (out.read_text(encoding="utf-8") if out.exists() else None):
            return
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(new_text, encoding="utf-8")
        if item.executable:
            out.chmod(0o755)

    def run(self, *, write: bool) -> None:
        extra = {"AGENT_NAME": EXAMPLE_AGENT, "SKILL_NAME": EXAMPLE_SKILL, "RULE_NAME": EXAMPLE_RULE}
        for item in MANIFEST:
            self.emit(item, extra, write=write)

        # Source-language docs carry the real skeleton; every other language gets a
        # pointer stub, so the parity check comes back empty from the first commit.
        for template, rel, title in DOCS:
            self.emit(
                Item(template, f"docs/{SOURCE_LANG}/{rel}"),
                {"CAPABILITY": title, "DECISION_TITLE": title, "TITLE": title},
                write=write,
            )
            for lang in LANGS:
                if lang == SOURCE_LANG:
                    continue
                self.emit(
                    Item("docs/translation-stub.md.tpl", f"docs/{lang}/{rel}"),
                    {"TITLE": title, "RELATIVE_PATH": rel},
                    write=write,
                )

    # --- auditing --------------------------------------------------------

    def audit(self) -> list[Result]:
        """
        Check what the harness needs to be WIRED, not which paths exist. A hook script
        on disk that no `settings.json` calls is a dead file; a `Makefile` without
        `sync-check` cannot answer the CI job that invokes it.
        """
        findings: list[Result] = []
        for item in MANIFEST:
            candidates = [item.dest] + ([item.alt_dest] if item.alt_dest else [])
            present = [c for c in candidates if (self.target / c).exists()]
            if not present:
                findings.append(Result(item.dest, "missing"))
                continue
            if not item.requires:
                findings.append(Result(present[0], "ok"))
                continue
            # Any one of the candidate paths may satisfy the requirement.
            best: tuple[int, str, list[str]] | None = None
            for path in present:
                text = (self.target / path).read_text(encoding="utf-8", errors="replace")
                absent = [need for need in item.requires if need not in text]
                if best is None or len(absent) < best[0]:
                    best = (len(absent), path, absent)
            assert best is not None
            _, path, absent = best
            findings.append(
                Result(path, "ok" if not absent else "incomplete — needs " + ", ".join(absent))
            )
        for template, rel, _ in DOCS:
            for lang in LANGS:
                dest = f"docs/{lang}/{rel}"
                findings.append(Result(dest, "ok" if (self.target / dest).exists() else "missing"))
        return findings

    # --- reporting -------------------------------------------------------

    def report(self, mode: str) -> None:
        rows = self.audit() if mode == "check" else self.results
        for row in rows:
            label = row.state if mode != "dry-run" else row.state.replace("created", "would create")
            print(f"  {label:34} {row.dest}")

        if mode == "check":
            broken = [r for r in rows if r.state != "ok"]
            print(f"\n{len(rows) - len(broken)} wired, {len(broken)} missing or incomplete.")
        else:
            touched = [r for r in rows if r.state != "exists" and not r.state.startswith("exists")]
            print(f"\n{len(touched)} written or merged, {len(rows) - len(touched)} left untouched.")

        if self.unresolved:
            print("\nPlaceholders still open (fill before committing):")
            for path, keys in sorted(self.unresolved.items()):
                print(f"  {path}: {', '.join(keys)}")

        for dest, content in self.advice:
            print(f"\n{dest} already exists and YAML cannot be merged blind — a second")
            print("`repos:` key would break the file. Add this hook to it by hand:")
            block = content.split("- repo: local", 1)
            snippet = ("  - repo: local" + block[1]).rstrip() if len(block) > 1 else content
            for line in snippet.splitlines():
                if line.strip().startswith("# TODO"):
                    break
                print(f"    {line}")


def detect_stack(target: Path) -> str:
    manifests = {
        "package.json": "node",
        "pyproject.toml": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "composer.json": "php",
        "wp-config.php": "wordpress",
    }
    found = [name for path, name in manifests.items() if (target / path).exists()]
    found += ["dotnet"] if list(target.glob("*.csproj")) else []
    return ", ".join(sorted(set(found))) or "TODO (no manifest found)"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("target", help="project root to bootstrap")
    ap.add_argument("--project", help="project name for the banners (default: target directory name)")
    ap.add_argument("--holder", help="copyright holder in LICENSE (default: git config user.name)")
    ap.add_argument("--year", help="copyright year (default: current year)")
    ap.add_argument("--dry-run", action="store_true", help="write nothing; list what would change")
    ap.add_argument("--check", action="store_true",
                    help="audit an existing project's wiring; write nothing; exit 1 if incomplete")
    ap.add_argument("--no-sync", action="store_true", help="skip running the surface generator at the end")
    args = ap.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        raise SystemExit(f"target is not a directory: {target}")
    if target == HERE:
        raise SystemExit("refusing to bootstrap this repository over itself.")

    mode = "check" if args.check else "dry-run" if args.dry_run else "write"
    project = args.project or target.name
    year = args.year or str(_dt.date.today().year)
    holder = args.holder or git_user(target) or "{{COPYRIGHT_HOLDER}}"

    brownfield = any((target / p).exists() for p in ("CLAUDE.md", "AGENTS.md", ".claude", "Makefile"))
    print(f"{'audit' if mode == 'check' else 'bootstrap'}: {target}")
    print(
        f"project: {project} | stack: {detect_stack(target)} | "
        f"languages: {', '.join(LANGS)} | {'existing harness' if brownfield else 'from scratch'}\n"
    )

    boot = Bootstrap(target, project, holder, year)
    if mode != "check":
        boot.run(write=(mode == "write"))
    boot.report(mode)

    if mode == "check":
        return 1 if any(r.state != "ok" for r in boot.audit()) else 0
    if mode == "dry-run":
        return 0

    generator = target / "scripts/sync-ai-surfaces.py"
    code = 0
    if not args.no_sync and generator.is_file():
        print("\nprojecting AI surfaces:", flush=True)  # flush: the child writes to the same stdout
        code = subprocess.run([sys.executable, str(generator)], cwd=target, check=False).returncode

    print(
        "\nNext, in order:\n"
        "  1. Fill the TODO markers, starting with AGENTS.md (stack, commands, pitfalls).\n"
        "  2. Fill the four sensor targets in the Makefile and add the tool config —\n"
        "     that is what unlocks L3/L4 in harness-score, not the hooks.\n"
        "  3. Rename the example agent, skill and rule to something this project needs.\n"
        "  4. pre-commit install\n"
        "  5. python3 scripts/init-project.py . --check   # is it actually wired?\n"
        "  6. npx harness-score                           # baseline"
    )
    if code == 2:
        print(
            "\nThe generator found a hand-authored file at a path one of the seeded\n"
            "sources projects onto, and wrote nothing there. Rename either side."
        )
    if not shutil.which("git") or not (target / ".git").exists():
        print("\nNote: the target is not a git repository yet — `git init` before committing.")
    return 0


def git_user(target: Path) -> str | None:
    if not shutil.which("git"):
        return None
    out = subprocess.run(
        ["git", "config", "user.name"], cwd=target, capture_output=True, text=True, check=False
    )
    return out.stdout.strip() or None


if __name__ == "__main__":
    sys.exit(main())
