#!/usr/bin/env python3
"""Remove from a project what `init-project.py` put there — and nothing else.

    python3 scripts/uninstall-project.py ../my-project --dry-run
    python3 scripts/uninstall-project.py ../my-project
    python3 scripts/uninstall-project.py ../my-project --force   # modified files too

Uninstalling is the harder direction: the bootstrap merges into files the project
owns, so a blind `rm` of the manifest would take the project's `Makefile` with it.
Each mode is reversed by the inverse of the merge that wrote it:

    whole   delete the file only when it is byte-identical to the rendered template
    block   strip the delimited block; delete the file if nothing else was in it
    make    same block, same rule — the appended targets live inside it
    json    drop only the keys whose value still equals the template's
    import  drop the `@AGENTS.md` line and the note that came with it
    advise  nothing was ever written; nothing to undo

A file the project edited after the bootstrap is NOT ours to delete: it is reported
as `modified — kept` and left alone. `--force` removes those too, and is the only
mode that can destroy work. Generated AI surfaces are matched by the generator's own
`managed-by:` banner, so a hand-authored file under `.claude/commands/` survives.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def _load_bootstrap():
    """Import the bootstrap as a module: one manifest, one renderer, one truth."""
    spec = importlib.util.spec_from_file_location("init_project", HERE / "scripts/init-project.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: @dataclass resolves annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


boot = _load_bootstrap()

# Roots the surface generator owns entirely. Kept in sync with the same tuple in
# `templates/sync-ai-surfaces.py`; the banner test below is what actually decides.
GENERATED_ROOTS = (
    ".claude/skills",
    ".claude/commands",
    ".agents/skills",
    ".github/prompts",
    ".github/instructions",
    ".codex",
)
BANNER_MARK = "managed-by:"
BANNER_TOOL = "sync-ai-surfaces"

# Directories the harness introduces. Removed only when empty, deepest first, so a
# project that keeps its own `scripts/` or `docs/` never loses it.
OWNED_DIRS = (
    ".claude/hooks", ".claude/agents", ".claude/rules", ".claude/skills", ".claude/commands",
    ".claude", ".agents/skills", ".agents", ".codex/agents", ".codex/prompts", ".codex",
    "skills", "memory", "scripts", ".github/workflows", ".github/prompts",
    ".github/instructions", ".github",
    "docs/pt-br/architecture", "docs/pt-br/specs", "docs/pt-br/decisions", "docs/pt-br/manual",
    "docs/pt-br", "docs/en-us/architecture", "docs/en-us/specs", "docs/en-us/decisions",
    "docs/en-us/manual", "docs/en-us", "docs",
)


class Uninstall:
    def __init__(self, target: Path, project: str, holder: str, year: str, *, force: bool) -> None:
        self.target = target
        self.force = force
        self.render = boot.Bootstrap(target, project, holder, year)
        self.results: list[tuple[str, str]] = []
        self.kept = 0

    # --- helpers ---------------------------------------------------------

    def note(self, dest: str, state: str) -> None:
        if state.endswith("kept"):
            self.kept += 1
        self.results.append((dest, state))

    def delete(self, path: Path, dest: str, state: str, *, write: bool) -> None:
        if write:
            path.unlink()
        self.note(dest, state)

    def rewrite(self, path: Path, text: str, dest: str, state: str, *, write: bool) -> None:
        if not text.strip():
            self.delete(path, dest, state + " — file now empty", write=write)
            return
        if write:
            path.write_text(text, encoding="utf-8")
        self.note(dest, state)

    # --- per-mode reversal -----------------------------------------------

    def strip_block(self, text: str) -> tuple[str, bool]:
        """Drop `# harness-bootstrap >>> … <<<` and the blank line that preceded it."""
        lines = text.splitlines(keepends=True)
        out: list[str] = []
        inside = False
        found = False
        for line in lines:
            if boot.BLOCK_OPEN in line:
                inside, found = True, True
                while out and not out[-1].strip():
                    out.pop()
                continue
            if inside:
                if boot.BLOCK_CLOSE in line:
                    inside = False
                continue
            out.append(line)
        return "".join(out), found

    def unmerge_json(self, current: object, template: object, *, top: bool = False) -> None:
        """
        Remove what the template contributed, key by key: a scalar that still equals
        the template's, a hook entry matched by `command`, a branch that came back
        empty. One guard on top of that — a file the project owns is never reduced to
        `{}`. Its last container stays, because `{"mcpServers": {}}` is very likely
        what the merge found, and an empty file is not a restoration.
        """
        if not isinstance(current, dict) or not isinstance(template, dict):
            return

        def drop(key: str) -> None:
            if not (top and len(current) == 1):
                del current[key]

        for key, value in list(template.items()):
            if key not in current:
                continue
            mine = current[key]
            if isinstance(mine, dict) and isinstance(value, dict):
                self.unmerge_json(mine, value)
                if not mine:
                    drop(key)
            elif isinstance(mine, list) and isinstance(value, list):
                for entry in value:
                    # Hooks are matched the way the merge matched them: by `command`.
                    commands = boot.hook_commands(entry)
                    mine[:] = [
                        kept
                        for kept in mine
                        if not (kept == entry or (commands and boot.hook_commands(kept) & commands))
                    ]
                if not mine:
                    drop(key)
            elif mine == value:
                drop(key)

    def unmerge_import(self, text: str, template: str) -> tuple[str, bool]:
        first = template.strip().splitlines()[0].strip()  # `@AGENTS.md`
        if first not in text:
            return text, False
        out: list[str] = []
        dropping = False
        for line in text.splitlines(keepends=True):
            if line.strip() == first:
                continue
            if line.lstrip().startswith("<!-- harness-bootstrap:"):
                dropping = "-->" not in line
                continue
            if dropping:
                dropping = "-->" not in line
                continue
            out.append(line)
        return "".join(out).lstrip("\n"), True

    # --- the pass --------------------------------------------------------

    def surfaces(self, *, write: bool) -> None:
        """Generated files, matched by the generator's banner — never by path alone."""
        removed = 0
        for root in GENERATED_ROOTS:
            base = self.target / root
            if not base.exists():
                continue
            for path in sorted(base.rglob("*")):
                if not path.is_file():
                    continue
                head = path.read_text(encoding="utf-8", errors="replace")[:400]
                if BANNER_MARK not in head or BANNER_TOOL not in head:
                    self.note(str(path.relative_to(self.target)), "hand-authored — kept")
                    continue
                if write:
                    path.unlink()
                removed += 1
        if removed:
            print(f"  {'generated surfaces removed':34} {removed} file(s)")

    def item(self, item, extra: dict[str, str] | None = None, *, write: bool) -> None:
        content = self.render.rendered(item, extra)
        for dest in [item.dest] + ([item.alt_dest] if item.alt_dest else []):
            path = self.target / dest
            if not path.exists():
                if dest == item.dest:
                    self.note(dest, "absent")
                continue

            # What a from-scratch install would have written. When the file still
            # matches it byte for byte, the bootstrap owns the whole file — no mode
            # needs reversing, and this is the only case that also covers `advise`
            # and `import`, which write the template whole when the path is free.
            pristine = boot.wrap_block(content) if item.mode in ("block", "make") else content
            if path.read_text(encoding="utf-8", errors="replace") == pristine:
                self.delete(path, dest, "remove", write=write)
            elif item.mode == "advise":
                self.note(dest, "written by hand — kept")
            elif item.mode in ("block", "make"):
                stripped, found = self.strip_block(path.read_text(encoding="utf-8"))
                if found:
                    self.rewrite(path, stripped, dest, "strip the harness block", write=write)
                else:
                    self.note(dest, "no harness block — kept")
            elif item.mode == "json":
                try:
                    current = json.loads(path.read_text(encoding="utf-8") or "{}")
                except json.JSONDecodeError:
                    self.note(dest, "not valid JSON — kept")
                    continue
                self.unmerge_json(current, json.loads(content), top=True)
                # Never deleted here: the file did not match the template above, so
                # the project owns it. An empty `{}` left behind is its own — the
                # bootstrap found it that way.
                self.rewrite(
                    path, json.dumps(current, indent=2, ensure_ascii=False) + "\n",
                    dest, "remove the merged keys", write=write,
                )
            elif item.mode == "import":
                text, found = self.unmerge_import(path.read_text(encoding="utf-8"), content)
                if not found:
                    self.note(dest, "no harness import — kept")
                elif not text.strip():
                    self.delete(path, dest, "remove", write=write)
                else:
                    self.rewrite(path, text, dest, "remove the import line", write=write)
            elif self.force:
                # `whole`, and the pristine test above already failed: the file was
                # edited, or it was the project's from the start. Only --force gets here.
                self.delete(path, dest, "remove (forced)", write=write)
            else:
                self.note(dest, "differs from the template — kept")

    def run(self, *, write: bool) -> None:
        self.surfaces(write=write)
        extra = {
            "AGENT_NAME": boot.EXAMPLE_AGENT,
            "SKILL_NAME": boot.EXAMPLE_SKILL,
            "RULE_NAME": boot.EXAMPLE_RULE,
        }
        for entry in boot.MANIFEST:
            self.item(entry, extra, write=write)
        for template, rel, title in boot.DOCS:
            self.item(
                boot.Item(template, f"docs/{boot.SOURCE_LANG}/{rel}"),
                {"CAPABILITY": title, "DECISION_TITLE": title, "TITLE": title},
                write=write,
            )
            for lang in boot.LANGS:
                if lang == boot.SOURCE_LANG:
                    continue
                self.item(
                    boot.Item("docs/translation-stub.md.tpl", f"docs/{lang}/{rel}"),
                    {"TITLE": title, "RELATIVE_PATH": rel},
                    write=write,
                )
        if write:
            self.prune_dirs()

    def prune_dirs(self) -> None:
        """
        Deepest first, and only under a root the harness introduces: an empty
        `skills/<name>/` is ours to drop, an empty directory the project keeps
        somewhere else is not.
        """
        candidates: list[Path] = []
        for rel in OWNED_DIRS:
            root = self.target / rel
            if not root.is_dir():
                continue
            candidates.append(root)
            candidates += [p for p in root.rglob("*") if p.is_dir()]
        for path in sorted(set(candidates), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()

    # Every reverting state is written as a verb, so a dry-run reads as a plan and a
    # real run reads as a record, from the same string.
    PAST = {
        "remove": "removed",
        "remove (forced)": "removed (forced)",
        "strip the harness block": "harness block stripped",
        "remove the merged keys": "merged keys removed",
        "remove the import line": "import line removed",
    }

    def report(self, *, write: bool) -> None:
        for dest, state in self.results:
            if state == "absent":
                continue
            head, _, tail = state.partition(" — file now empty")
            label = (self.PAST[head] if write else "would " + head) + tail if head in self.PAST else state
            print(f"  {label:34} {dest}")
        gone = sum(1 for _, st in self.results if st.partition(" — ")[0] in self.PAST)
        print(f"\n{gone} reverted, {self.kept} kept because the project changed them.")
        if self.kept and not self.force:
            print("Re-run with --force to delete the modified files too — that destroys work.")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("target", help="project root to clean")
    ap.add_argument("--project", help="the name used at install time (default: target's name)")
    ap.add_argument("--holder", help="the LICENSE holder used at install time")
    ap.add_argument("--year", help="the LICENSE year used at install time")
    ap.add_argument("--dry-run", action="store_true", help="list what it would revert")
    ap.add_argument("--force", action="store_true",
                    help="delete files the project modified after the bootstrap")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    if not target.is_dir():
        raise SystemExit(f"uninstall: {target} is not an existing directory")
    if target == HERE:
        raise SystemExit("uninstall: refusing to run over itself")

    # The same default the bootstrap used, read in the same place: a different
    # holder renders a different LICENSE, and the file would look modified.
    holder = args.holder or boot.git_user(target) or "{{COPYRIGHT_HOLDER}}"
    year = args.year or str(_dt.date.today().year)
    job = Uninstall(target, args.project or target.name, holder, year, force=args.force)

    print(f"uninstall: {target}")
    print(f"project: {job.render.base_values['PROJECT']} | mode: "
          f"{'dry-run' if args.dry_run else 'write'}\n")
    job.run(write=not args.dry_run)
    job.report(write=not args.dry_run)
    return 0



if __name__ == "__main__":
    sys.exit(main())
