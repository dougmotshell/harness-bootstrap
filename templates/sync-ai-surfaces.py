#!/usr/bin/env python3
"""AI surface generator (template).

One authored source -> every AI surface. Copy this file to
`scripts/sync-ai-surfaces.py` in the target project; it needs no edits, since the
banner takes the repository root's directory name.

Sources (authored, versioned, hand-editable):

    .claude/agents/<n>.md      agents, Claude's native format
    skills/<n>/SKILL.md        skills, Agent Skills format (portable)
    .claude/rules/<n>.md       path-scoped rules, `paths:` frontmatter

Outputs (generated, versioned on purpose so a fresh clone works without running
anything, and NEVER hand-edited):

    .claude/skills/<n>/SKILL.md                skill in the directory Claude reads
    .claude/commands/<n>.md                    slash command (skills and agents)
    .agents/skills/<n>/SKILL.md                neutral surface
    .github/prompts/<n>.prompt.md              Copilot prompt
    .codex/prompts/<n>.md                      Codex prompt
    .codex/agents/<n>.toml                     agent in Codex's format
    .github/instructions/<n>.instructions.md   Copilot path-scoped rule

Usage:
    python3 scripts/sync-ai-surfaces.py            write the outputs
    python3 scripts/sync-ai-surfaces.py --check     write nothing; exit 1 on drift
    python3 scripts/sync-ai-surfaces.py --dry-run   write nothing; list what would change
    python3 scripts/sync-ai-surfaces.py --prune      also delete orphaned outputs

`--check` is for CI: it fails when someone hand-edited an output or forgot to run
the generator after touching a source.

Translations (`<n>.en-US.md`, `SKILL.en-US.md`) are skipped: they exist for
readers, not so the model loads the same skill twice.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Project name in the banner. The root directory name by default; replace with a
# fixed string if a clone's directory may be named differently.
PROJECT = ROOT.name

BANNER = f"<!-- managed-by:{PROJECT}/sync-ai-surfaces — do not edit by hand -->"
TOML_BANNER = f"# managed-by:{PROJECT}/sync-ai-surfaces — do not edit by hand"

AGENTS_DIR = ROOT / ".claude/agents"
SKILLS_DIR = ROOT / "skills"
RULES_DIR = ROOT / ".claude/rules"

# Roots owned entirely by this generator. Anything here without a matching source
# is an orphan — leftover from a rename.
GENERATED_ROOTS = (
    ".claude/skills",
    ".claude/commands",
    ".agents/skills",
    ".github/prompts",
    ".github/instructions",
    ".codex",
)

# All prose in these projects exists in pt-BR and en-US. The source is the file
# with no suffix (pt-BR, the source of truth); the translation is a sibling with a
# language suffix — `adr.en-US.md`, `SKILL.en-US.md`. Only the source is projected:
# a projected translation would become a duplicate skill or rule with the same
# `name`.
TRANSLATION_SUFFIX = re.compile(r"\.[a-z]{2}-[A-Z]{2}$")


def is_translation(path: Path) -> bool:
    return bool(TRANSLATION_SUFFIX.search(path.stem))


# --- frontmatter -----------------------------------------------------------


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """
    Return (fields, body). Deliberately minimal parser: root-level keys with
    scalar values, plus `- x` list items captured as raw text. Avoids depending on
    PyYAML, which these projects do not require.
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw, body = text[4:end], text[end + 5 :]

    fields: dict[str, str] = {}
    current = None
    for line in raw.splitlines():
        if m := re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line):
            current, value = m.group(1), m.group(2).strip()
            fields[current] = value
        elif current and line.strip().startswith("- "):
            item = line.strip()[2:].strip().strip('"').strip("'")
            fields[current] = f"{fields[current]},{item}".lstrip(",")
        elif current and line.startswith(" "):
            fields[current] = f"{fields[current]} {line.strip()}".strip()
    return fields, body


def as_list(value: str) -> list[str]:
    return [p.strip().strip('"').strip("'") for p in value.split(",") if p.strip()]


def toml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def toml_block(body: str) -> str:
    """
    Long body as a multiline TOML string.

    Prefers the literal form, which interprets no escapes — a `\\` in the agent's
    text would break the basic form. Falls back to the basic form, with escaping,
    only when the body contains the literal delimiter itself.
    """
    body = body.strip()
    literal = "'" * 3
    if literal not in body:
        return f"{literal}\n{body}\n{literal}"
    escaped = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'"""\n{escaped}\n"""'


def md_document(frontmatter: dict[str, str], source: str, body: str) -> str:
    """
    Markdown output with the banner. The banner sits right after the closing `---`,
    never above it: a parser only recognises frontmatter that starts on line 1.
    Files with no frontmatter carry the banner on line 1.
    """
    head = ""
    if frontmatter:
        fields = "\n".join(f"{k}: {v}" for k, v in frontmatter.items() if v)
        head = f"---\n{fields}\n---\n"
    return f"{head}{BANNER}\n<!-- source: {source} -->\n{body}"


# --- collection ------------------------------------------------------------


def collect_skills() -> list[tuple[str, dict[str, str], str, Path]]:
    items = []
    for skill in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        if is_translation(skill):
            continue
        fields, body = split_frontmatter(skill.read_text(encoding="utf-8"))
        if not fields.get("name") or not fields.get("description"):
            raise SystemExit(
                f"{skill.relative_to(ROOT)}: frontmatter needs `name:` and `description:`."
            )
        items.append((fields["name"], fields, body, skill.parent))
    return items


def collect_agents() -> list[tuple[str, dict[str, str], str]]:
    items = []
    for agent in sorted(AGENTS_DIR.glob("*.md")):
        if is_translation(agent):
            continue
        fields, body = split_frontmatter(agent.read_text(encoding="utf-8"))
        name = fields.get("name") or agent.stem
        if not fields.get("description"):
            raise SystemExit(f"{agent.relative_to(ROOT)}: frontmatter needs `description:`.")
        items.append((name, fields, body))
    return items


def collect_rules() -> list[tuple[str, dict[str, str], str]]:
    items = []
    for rule in sorted(RULES_DIR.glob("*.md")):
        if is_translation(rule):
            continue
        fields, body = split_frontmatter(rule.read_text(encoding="utf-8"))
        if not fields.get("paths"):
            raise SystemExit(f"{rule.relative_to(ROOT)}: frontmatter needs `paths:`.")
        items.append((rule.stem, fields, body))
    return items


# --- projection ------------------------------------------------------------


def project() -> dict[Path, bytes]:
    """Return {relative path: content} for everything that must exist generated."""
    out: dict[Path, bytes] = {}

    def put(rel: str, content: str) -> None:
        out[Path(rel)] = content.encode("utf-8")

    for name, fields, body, skill_dir in collect_skills():
        desc = fields["description"]
        hint = fields.get("argument-hint", "")
        source = f"skills/{skill_dir.name}/SKILL.md"
        # A skill that takes arguments needs the placeholder in the surfaces that
        # inject them; one that does not must never grow a stray `$ARGUMENTS`.
        args = "\n\n$ARGUMENTS\n" if hint else ""

        skill_md = md_document({"name": name, "description": desc}, source, body)
        put(f".claude/skills/{skill_dir.name}/SKILL.md", skill_md)
        put(f".agents/skills/{skill_dir.name}/SKILL.md", skill_md)

        # Companion files of the skill (references/, scripts/, data) travel with it.
        for extra in sorted(skill_dir.rglob("*")):
            if not extra.is_file() or extra.name == "SKILL.md" or is_translation(extra):
                continue
            rel = extra.relative_to(skill_dir)
            for base in (".claude/skills", ".agents/skills"):
                out[Path(f"{base}/{skill_dir.name}/{rel}")] = extra.read_bytes()

        put(
            f".claude/commands/{skill_dir.name}.md",
            md_document(
                {"description": desc, "argument-hint": hint}, source, body + args
            ),
        )
        # `agent:` is the current key; the old `mode:` is deprecated.
        put(
            f".github/prompts/{skill_dir.name}.prompt.md",
            md_document(
                {"name": name, "description": desc, "agent": "agent",
                 "argument-hint": hint},
                source,
                body + args,
            ),
        )
        put(f".codex/prompts/{skill_dir.name}.md", md_document({}, source, body))

    agent_names = []
    for name, fields, body in collect_agents():
        agent_names.append(name)
        source = f".claude/agents/{name}.md"
        tools = as_list(fields.get("tools", ""))

        lines = [
            TOML_BANNER,
            f"# source: {source}",
            "",
            f"name = {toml_quote(name)}",
            f"description = {toml_quote(fields['description'])}",
        ]
        if tools:
            lines.append("tools = [" + ", ".join(toml_quote(t) for t in tools) + "]")
        lines += ["", "instructions = " + toml_block(body), ""]
        out[Path(f".codex/agents/{name}.toml")] = "\n".join(lines).encode("utf-8")

        # Slash command that delegates to the subagent, for CLIs where the agent
        # is not directly invocable.
        put(
            f".claude/commands/{name}.md",
            md_document(
                {"description": fields["description"],
                 "argument-hint": "[task for this specialist]"},
                source,
                f"\nDelegate the task below to the `{name}` specialist defined in "
                f"@{source}.\n\n$ARGUMENTS\n\nUse the Agent tool with subagent_type "
                f"`{name}` when subagents are available; otherwise adopt that "
                "agent's instructions yourself and execute them directly.\n",
            ),
        )

    for name, fields, body in collect_rules():
        put(
            f".github/instructions/{name}.instructions.md",
            md_document(
                {"applyTo": toml_quote(",".join(as_list(fields["paths"])))},
                f".claude/rules/{name}.md",
                body,
            ),
        )

    return out


# --- execution -------------------------------------------------------------


def find_orphans(expected: dict[Path, bytes]) -> list[Path]:
    """Generated output with no matching source: leftover from a rename."""
    orphans: list[Path] = []
    for generated_root in GENERATED_ROOTS:
        base = ROOT / generated_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.relative_to(ROOT) not in expected:
                orphans.append(path.relative_to(ROOT))
    return sorted(orphans)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 on drift (for CI)")
    ap.add_argument("--dry-run", action="store_true",
                    help="write nothing; list what would change")
    ap.add_argument("--prune", action="store_true",
                    help="delete orphaned outputs instead of only reporting them")
    args = ap.parse_args()
    read_only = args.check or args.dry_run

    expected = project()
    drifted: list[tuple[str, Path]] = []

    for rel, content in sorted(expected.items()):
        target = ROOT / rel
        current = target.read_bytes() if target.is_file() else None
        if current == content:
            continue
        drifted.append(("stale" if current is not None else "missing", rel))
        if not read_only:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    orphans = find_orphans(expected)
    if orphans and args.prune and not read_only:
        for rel in orphans:
            (ROOT / rel).unlink()
        for generated_root in GENERATED_ROOTS:
            base = ROOT / generated_root
            for path in sorted(base.rglob("*"), reverse=True) if base.exists() else []:
                if path.is_dir() and not any(path.iterdir()):
                    path.rmdir()

    for state, rel in drifted:
        print(f"  {state:9} {rel}")
    for rel in orphans:
        tail = "removed" if args.prune and not read_only else "no source — use --prune"
        print(f"  {'orphan':9} {rel}  ({tail})")

    if args.check:
        if drifted or orphans:
            print(f"\n--check failed: {len(drifted)} drifted, {len(orphans)} orphaned.")
            print("Run: python3 scripts/sync-ai-surfaces.py")
            return 1
        print(f"{len(expected)} generated file(s) up to date.")
        return 0

    if args.dry_run:
        print(f"\n{len(drifted)} of {len(expected)} file(s) would be written.")
        return 0

    print(f"\n{len(drifted)} written, {len(expected)} total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
