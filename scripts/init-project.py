#!/usr/bin/env python3
"""Bootstrap another project's AI harness from `templates/`.

Deterministic on purpose: no model, no network, no judgement. It copies templates,
substitutes placeholders, seeds one example of each authored artifact, builds the
`docs/` trees in both languages and runs the surface generator. Same input, same
output, every time.

    python3 scripts/init-project.py ../my-project
    python3 scripts/init-project.py ../my-project --dry-run
    python3 scripts/init-project.py ../my-project --check     # audit, write nothing

Non-destructive without exception: an existing file is reported as skipped and never
overwritten, truncated or deleted. Run it twice and the second run writes nothing.

What it deliberately does NOT do — because only a human or a model can:
fill the `TODO:` markers, detect the stack, write the sensor commands into the
Makefile, decide whether the project has end users. That is the job of
`/bootstrap-ai-harness`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import shutil
import subprocess
import sys
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

# (template, destination, executable)
MANIFEST: list[tuple[str, str, bool]] = [
    # contract and adapters
    ("contract/agents.md.tpl", "AGENTS.md", False),
    ("contract/claude.md.tpl", "CLAUDE.md", False),
    ("contract/copilot-instructions.md.tpl", ".github/copilot-instructions.md", False),
    # harness: hygiene and orientation
    ("harness/readme.md.tpl", "README.md", False),
    ("harness/license-mit.tpl", "LICENSE", False),
    ("harness/gitignore.tpl", ".gitignore", False),
    ("harness/env.example.tpl", ".env.example", False),
    ("harness/harness-score.json.tpl", ".harness-score.json", False),
    ("harness/mcp.json.tpl", ".mcp.json", False),
    # harness: sensors, CI, hooks
    ("harness/makefile.tpl", "Makefile", False),
    ("harness/ci.yml.tpl", ".github/workflows/ci.yml", False),
    ("harness/pre-commit-config.yaml.tpl", ".pre-commit-config.yaml", False),
    ("harness/settings.json.tpl", ".claude/settings.json", False),
    ("harness/hooks/gate-write.sh", ".claude/hooks/gate-write.sh", True),
    ("harness/hooks/gate-bash.sh", ".claude/hooks/gate-bash.sh", True),
    ("harness/hooks/feedback-edit.sh", ".claude/hooks/feedback-edit.sh", True),
    # the generator
    ("sync-ai-surfaces.py", "scripts/sync-ai-surfaces.py", True),
    # authored sources: one example of each, so every surface has something to project
    ("authored/agent.md.tpl", f".claude/agents/{EXAMPLE_AGENT}.md", False),
    ("authored/skill.md.tpl", f"skills/{EXAMPLE_SKILL}/SKILL.md", False),
    ("authored/rule.md.tpl", f".claude/rules/{EXAMPLE_RULE}.md", False),
    ("authored/memory.md.tpl", "memory/MEMORY.md", False),
    # docs index (language-neutral)
    ("docs/readme.md.tpl", "docs/README.md", False),
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


def substitute(text: str, values: dict[str, str]) -> str:
    """
    Replace only known placeholders, one by one. Never a blanket `{{...}}` sweep:
    `${{ vars.HARNESS_MIN_LEVEL }}` is GitHub Actions syntax and must survive.
    """
    for key, value in values.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def leftovers(text: str) -> list[str]:
    return sorted({m for m in PLACEHOLDER.findall(text) if "${{" not in text[: text.find(m)][-3:]})


class Bootstrap:
    def __init__(self, target: Path, project: str, holder: str, year: str) -> None:
        self.target = target
        self.base_values = {
            "PROJECT": project,
            "YEAR": year,
            "COPYRIGHT_HOLDER": holder,
        }
        self.created: list[str] = []
        self.skipped: list[str] = []
        self.unresolved: dict[str, list[str]] = {}

    # --- writing ---------------------------------------------------------

    def emit(self, template: str, dest: str, executable: bool, extra: dict[str, str] | None = None,
             *, write: bool) -> None:
        src = TEMPLATES / template
        if not src.is_file():
            raise SystemExit(f"missing template: {src.relative_to(HERE)}")

        out = self.target / dest
        if out.exists():
            self.skipped.append(dest)
            return

        content = substitute(src.read_text(encoding="utf-8"), {**self.base_values, **(extra or {})})
        remaining = leftovers(content)
        if remaining:
            self.unresolved[dest] = remaining

        self.created.append(dest)
        if not write:
            return
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        if executable:
            out.chmod(0o755)

    def run(self, *, write: bool) -> None:
        for template, dest, executable in MANIFEST:
            extra = {
                "AGENT_NAME": EXAMPLE_AGENT,
                "SKILL_NAME": EXAMPLE_SKILL,
                "RULE_NAME": EXAMPLE_RULE,
            }
            self.emit(template, dest, executable, extra, write=write)

        # Source-language docs carry the real skeleton; every other language gets a
        # pointer stub, so the parity check comes back empty from the first commit.
        for template, rel, title in DOCS:
            self.emit(
                template,
                f"docs/{SOURCE_LANG}/{rel}",
                False,
                {"CAPABILITY": title, "DECISION_TITLE": title, "TITLE": title},
                write=write,
            )
            for lang in LANGS:
                if lang == SOURCE_LANG:
                    continue
                self.emit(
                    "docs/translation-stub.md.tpl",
                    f"docs/{lang}/{rel}",
                    False,
                    {"TITLE": title, "RELATIVE_PATH": rel},
                    write=write,
                )

    # --- reporting -------------------------------------------------------

    def report(self, mode: str) -> None:
        verb = {"write": "created", "dry-run": "would create", "check": "missing"}[mode]
        for path in self.created:
            print(f"  {verb:12} {path}")
        for path in self.skipped:
            print(f"  {'exists':12} {path}")

        print(f"\n{len(self.created)} {verb}, {len(self.skipped)} left untouched.")

        if self.unresolved:
            print("\nPlaceholders still open (fill before committing):")
            for path, keys in sorted(self.unresolved.items()):
                print(f"  {path}: {', '.join(keys)}")


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
    ap.add_argument("--holder", help="copyright holder in LICENSE (default: leave the placeholder open)")
    ap.add_argument("--year", help="copyright year (default: current year)")
    ap.add_argument("--dry-run", action="store_true", help="write nothing; list what would be created")
    ap.add_argument("--check", action="store_true",
                    help="audit an existing project; write nothing; exit 1 if anything is missing")
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

    print(f"{'audit' if mode == 'check' else 'bootstrap'}: {target}")
    print(f"project: {project} | stack: {detect_stack(target)} | languages: {', '.join(LANGS)}\n")

    boot = Bootstrap(target, project, args.holder or "{{COPYRIGHT_HOLDER}}", year)
    boot.run(write=(mode == "write"))
    boot.report(mode)

    if mode == "check":
        return 1 if boot.created else 0
    if mode == "dry-run":
        return 0

    generator = target / "scripts/sync-ai-surfaces.py"
    if not args.no_sync and generator.is_file():
        print("\nprojecting AI surfaces:", flush=True)  # flush: the child writes to the same stdout
        subprocess.run([sys.executable, str(generator)], cwd=target, check=False)

    print(
        "\nNext, in order:\n"
        "  1. Fill the TODO markers, starting with AGENTS.md (stack, commands, pitfalls).\n"
        "  2. Fill the four sensor targets in the Makefile and add the tool config —\n"
        "     that is what unlocks L3/L4 in harness-score, not the hooks.\n"
        "  3. Rename the example agent, skill and rule to something this project needs.\n"
        "  4. pre-commit install\n"
        "  5. npx harness-score        # baseline\n"
        "  6. make sync-check          # must pass before the first commit"
    )
    if not shutil.which("git") or not (target / ".git").exists():
        print("\nNote: the target is not a git repository yet — `git init` before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
