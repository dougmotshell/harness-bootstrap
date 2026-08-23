#!/usr/bin/env python3
"""Golden tests for the bootstrap and the surface generator.

Stdlib only: this repository must be testable in a fresh clone with no install step.

Two fixtures, because the two cases fail differently. A greenfield run is judged on
completeness — 36 files, every placeholder resolved. A brownfield run is judged on
what it did NOT break: the project's own `test:` recipe, its own hook, its own CI
file. Both are judged on idempotence, which is the only property that makes a
bootstrap safe to re-run.

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INIT = REPO / "scripts/init-project.py"


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def bootstrap(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run(str(INIT), str(target), *extra)


def sync(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run("scripts/sync-ai-surfaces.py", *extra, cwd=target)


def tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git/" not in str(p.relative_to(root))
    }


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name) / "project"
        self.target.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def read(self, rel: str) -> str:
        return (self.target / rel).read_text(encoding="utf-8")

    def write(self, rel: str, text: str) -> None:
        path = self.target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def assertIdempotent(self, runs: int = 2) -> None:
        before = tree(self.target)
        for _ in range(runs):
            bootstrap(self.target)
        self.assertEqual(before, tree(self.target), "a re-run changed the tree")


class Greenfield(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.proc = bootstrap(self.target)

    def test_writes_the_whole_harness(self) -> None:
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        for rel in (
            "AGENTS.md",
            "CLAUDE.md",
            "Makefile",
            ".gitignore",
            ".claude/settings.json",
            ".claude/hooks/gate-write.sh",
            "scripts/sync-ai-surfaces.py",
            "skills/example-procedure/SKILL.md",
            "docs/pt-br/architecture/01-context.md",
            "docs/en-us/architecture/01-context.md",
            ".github/workflows/ci.yml",
        ):
            self.assertTrue((self.target / rel).is_file(), f"missing {rel}")

    def test_hooks_are_executable(self) -> None:
        for hook in sorted((self.target / ".claude/hooks").glob("*.sh")):
            self.assertTrue(hook.stat().st_mode & 0o111, f"{hook.name} is not executable")

    def test_surfaces_are_projected_and_in_sync(self) -> None:
        self.assertEqual(sync(self.target, "--check").returncode, 0)

    def test_audit_passes(self) -> None:
        self.assertEqual(bootstrap(self.target, "--check").returncode, 0)

    def test_idempotent(self) -> None:
        self.assertIdempotent(runs=3)


class Brownfield(Fixture):
    """A project that already has its own contract, sensors, hooks and CI."""

    def setUp(self) -> None:
        super().setUp()
        self.write("package.json", '{"name": "legacy", "scripts": {"test": "vitest"}}\n')
        self.write("CLAUDE.md", "# Legacy\n\nSempre rode `npm test`.\n")
        self.write("Makefile", ".PHONY: test build\ntest:\n\tnpm test\n\nbuild:\n\tnpm run build\n")
        self.write(".gitignore", "node_modules/\n")
        self.write(".pre-commit-config.yaml", "repos:\n  - repo: local\n    hooks: []\n")
        self.write(
            ".claude/settings.json",
            json.dumps(
                {
                    "permissions": {"allow": ["Bash(npm test)"]},
                    "hooks": {
                        "PreToolUse": [
                            {"matcher": "Bash", "hooks": [{"type": "command", "command": "./own-gate.sh"}]}
                        ]
                    },
                },
                indent=2,
            )
            + "\n",
        )
        self.write(".claude/skills/deploy/SKILL.md", "---\nname: deploy\n---\n\nÀ mão.\n")
        self.write(".github/workflows/ci.yml", "name: ci\non: push\njobs: {}\n")
        self.proc = bootstrap(self.target)

    def test_contract_gains_the_canonical_import(self) -> None:
        claude = self.read("CLAUDE.md")
        self.assertTrue(claude.startswith("@AGENTS.md"), "CLAUDE.md must import AGENTS.md first")
        self.assertIn("Sempre rode `npm test`.", claude, "the project's own rules survived")

    def test_makefile_keeps_its_targets_and_gains_the_missing_ones(self) -> None:
        makefile = self.read("Makefile")
        self.assertIn("npm test", makefile)
        self.assertIn("npm run build", makefile)
        self.assertIn("sync-check:", makefile)
        self.assertIn("lint-file:", makefile)
        # One definition of `test`, and it is still the project's.
        self.assertEqual(makefile.count("\ntest:"), 1)
        plan = subprocess.run(
            ["make", "-n", "test"], cwd=self.target, capture_output=True, text=True, check=False
        )
        self.assertIn("npm test", plan.stdout)

    def test_settings_keeps_its_hook_and_gains_the_three_gates(self) -> None:
        data = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(data["permissions"], {"allow": ["Bash(npm test)"]})
        commands = json.dumps(data["hooks"])
        for expected in ("own-gate.sh", "gate-write.sh", "gate-bash.sh", "feedback-edit.sh"):
            self.assertIn(expected, commands)

    def test_gitignore_gains_credential_hygiene(self) -> None:
        ignored = self.read(".gitignore")
        self.assertIn("node_modules/", ignored)
        self.assertIn(".env", ignored)
        self.assertIn("*.pem", ignored)

    def test_workflow_lands_beside_the_project_ci(self) -> None:
        self.assertEqual(self.read(".github/workflows/ci.yml"), "name: ci\non: push\njobs: {}\n")
        self.assertIn("sync-check", self.read(".github/workflows/harness.yml"))

    def test_unmergeable_yaml_is_advised_not_touched(self) -> None:
        self.assertEqual(self.read(".pre-commit-config.yaml"), "repos:\n  - repo: local\n    hooks: []\n")
        self.assertIn("sync-ai-surfaces.py --check", self.proc.stdout)

    def test_hand_authored_skill_survives(self) -> None:
        self.assertIn("À mão.", self.read(".claude/skills/deploy/SKILL.md"))

    def test_audit_reports_the_one_thing_left_by_hand(self) -> None:
        audit = bootstrap(self.target, "--check")
        self.assertEqual(audit.returncode, 1)
        self.assertIn("incomplete", audit.stdout)
        self.assertIn(".pre-commit-config.yaml", audit.stdout)

    def test_audit_catches_unwired_hooks(self) -> None:
        """The failure that used to pass: hook scripts on disk that nothing calls."""
        data = json.loads(self.read(".claude/settings.json"))
        del data["hooks"]
        self.write(".claude/settings.json", json.dumps(data, indent=2) + "\n")
        audit = bootstrap(self.target, "--check")
        self.assertEqual(audit.returncode, 1)
        self.assertIn("gate-write.sh", audit.stdout)

    def test_idempotent(self) -> None:
        self.assertIdempotent(runs=3)


class Generator(Fixture):
    """Ownership rules of the surface generator, on a project it did not create."""

    def setUp(self) -> None:
        super().setUp()
        bootstrap(self.target)

    def test_foreign_file_survives_prune(self) -> None:
        self.write(".claude/skills/deploy/SKILL.md", "---\nname: deploy\n---\n\nÀ mão.\n")
        self.write(".claude/skills/deploy/notes.md", "anotações\n")
        proc = sync(self.target, "--prune")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("foreign", proc.stdout)
        self.assertTrue((self.target / ".claude/skills/deploy/SKILL.md").is_file())
        self.assertTrue((self.target / ".claude/skills/deploy/notes.md").is_file())

    def test_real_orphan_is_pruned(self) -> None:
        orphan = self.target / ".claude/commands/renamed.md"
        orphan.write_text(
            "<!-- managed-by:x/sync-ai-surfaces — do not edit by hand -->\nstale\n", encoding="utf-8"
        )
        proc = sync(self.target, "--prune")
        self.assertIn("orphan", proc.stdout)
        self.assertFalse(orphan.exists(), "a bannered leftover must be prunable")

    def test_collision_refuses_to_overwrite(self) -> None:
        # A hand-authored file exactly where a source projects.
        clash = self.target / ".claude/skills/example-procedure/SKILL.md"
        clash.write_text("escrito à mão\n", encoding="utf-8")
        proc = sync(self.target)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("conflict", proc.stdout)
        self.assertEqual(clash.read_text(encoding="utf-8"), "escrito à mão\n")
        # --force is the documented way through.
        self.assertEqual(sync(self.target, "--force").returncode, 0)
        self.assertIn("managed-by", clash.read_text(encoding="utf-8"))

    def test_companion_assets_keep_syncing(self) -> None:
        asset = self.target / "skills/example-procedure/references/api.md"
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text("v1\n", encoding="utf-8")
        sync(self.target)
        copy = self.target / ".claude/skills/example-procedure/references/api.md"
        self.assertEqual(copy.read_text(encoding="utf-8"), "v1\n")
        asset.write_text("v2\n", encoding="utf-8")
        sync(self.target)
        self.assertEqual(copy.read_text(encoding="utf-8"), "v2\n", "a raw asset must still update")

    def test_check_is_clean_after_a_sync(self) -> None:
        self.assertEqual(sync(self.target).returncode, 0)
        self.assertEqual(sync(self.target, "--check").returncode, 0)


@unittest.skipUnless(shutil.which("make"), "make not available")
class Refusals(Fixture):
    def test_refuses_to_bootstrap_itself(self) -> None:
        proc = bootstrap(REPO)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("over itself", proc.stderr + proc.stdout)

    def test_refuses_a_missing_target(self) -> None:
        proc = bootstrap(self.target / "nope")
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
