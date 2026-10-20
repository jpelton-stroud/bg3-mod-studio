"""Unit tests for agent skills defined in .agents/skills/.

Validates compliance with Antigravity specifications and industry best practices:
- Kebab-case naming convention (folder and frontmatter name)
- YAML frontmatter completeness and validity
- Path portability (zero hardcoded user paths)
- Markdown link and file reference integrity
- Subagent model inheritance ('inherit')
- Tool discovery and registry integration
"""

import os
from pathlib import Path
import re
import unittest
import yaml

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = WORKSPACE_ROOT / ".agents" / "skills"


class TestAgentSkills(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.skill_files = sorted(list(SKILLS_DIR.glob("*/SKILL.md"))) if SKILLS_DIR.is_dir() else []
        cls.all_skill_md_files = sorted(list(SKILLS_DIR.rglob("*.md"))) if SKILLS_DIR.is_dir() else []
        cls.all_skill_files = sorted(list(SKILLS_DIR.rglob("*.md")) + list(SKILLS_DIR.rglob("*.json"))) if SKILLS_DIR.is_dir() else []

    def test_skills_exist(self):
        """Verify that agent skills are discovered in .agents/skills/."""
        self.assertGreaterEqual(
            len(self.skill_files),
            15,
            f"Expected at least 15 skills, found {len(self.skill_files)}"
        )

    def test_skill_kebab_case_naming(self):
        """Verify that skill directory names follow kebab-case (lowercase and hyphenated)."""
        kebab_pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
        non_kebab = []
        for sf in self.skill_files:
            dir_name = sf.parent.name
            if not re.match(kebab_pattern, dir_name):
                non_kebab.append(dir_name)
        self.assertEqual(
            non_kebab,
            [],
            f"The following skill directories are not kebab-case: {non_kebab}"
        )

    def test_skill_yaml_frontmatter(self):
        """Verify that SKILL.md begins with valid YAML frontmatter containing matching name and description."""
        kebab_pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
        errors = []
        for sf in self.skill_files:
            content = sf.read_text(encoding="utf-8")
            match = re.match(r"^---\n(.*?)\n---(?:\n|$)", content, re.DOTALL)
            if not match:
                errors.append(f"{sf.parent.name}: missing YAML frontmatter delimited by '---'")
                continue
            try:
                fm = yaml.safe_load(match.group(1))
            except Exception as e:
                errors.append(f"{sf.parent.name}: YAML parse error: {e}")
                continue
            if not isinstance(fm, dict):
                errors.append(f"{sf.parent.name}: frontmatter is not a mapping")
                continue

            name = fm.get("name")
            if not name:
                errors.append(f"{sf.parent.name}: frontmatter missing 'name'")
            elif name != sf.parent.name:
                errors.append(f"{sf.parent.name}: frontmatter name '{name}' does not match directory '{sf.parent.name}'")
            elif not re.match(kebab_pattern, name):
                errors.append(f"{sf.parent.name}: frontmatter name '{name}' is not kebab-case")

            desc = fm.get("description")
            if not desc:
                errors.append(f"{sf.parent.name}: frontmatter missing 'description'")
            elif len(desc.strip()) < 40:
                errors.append(f"{sf.parent.name}: description is too short ({len(desc.strip())} chars)")

        self.assertEqual(errors, [], f"Frontmatter errors found:\n" + "\n".join(errors))

    def test_skill_path_portability(self):
        """Verify that skills do not contain user-specific absolute paths (/home/ or C:\\Users\\)."""
        violations = []
        for sf in self.skill_files:
            content = sf.read_text(encoding="utf-8")
            user_paths = re.findall(r"(?:/home/|C:[/\\]Users[/\\])[a-zA-Z0-9_\-\.]+", content)
            if user_paths:
                violations.append(f"{sf.parent.name}: found user paths {set(user_paths)}")
        self.assertEqual(
            violations,
            [],
            f"Hardcoded user paths detected in skills:\n" + "\n".join(violations)
        )

    def test_skill_link_integrity(self):
        """Verify that relative and local file markdown links in all skill files resolve to existing files."""
        broken_links = []
        for sf in self.all_skill_md_files:
            content = sf.read_text(encoding="utf-8")
            links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
            rel_path = sf.relative_to(SKILLS_DIR)
            for text, target in links:
                if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
                    continue
                if target.startswith("#"):
                    continue
                if target in ("profile_url", "..."):
                    broken_links.append(f"{rel_path}: placeholder link [{text}]({target})")
                    continue
                clean = target[7:] if target.startswith("file://") else target
                clean = clean.split("#")[0]
                if not clean:
                    continue
                resolved = Path(clean) if os.path.isabs(clean) else (sf.parent / clean).resolve()
                if not resolved.exists():
                    broken_links.append(f"{rel_path}: broken link [{text}]({target}) -> {resolved}")

        self.assertEqual(broken_links, [], f"Broken links detected in skills:\n" + "\n".join(broken_links))

    def test_subagent_model_inheritance(self):
        """Verify that subagent launch payloads specify Model: 'inherit' per AGY guidelines."""
        illegal_models = []
        for sf in self.all_skill_files:
            content = sf.read_text(encoding="utf-8")
            model_matches = re.findall(r'["\']Model["\']\s*:\s*["\']([^"\']+)["\']', content)
            rel_path = sf.relative_to(SKILLS_DIR)
            for m in model_matches:
                if m != "inherit":
                    illegal_models.append(f"{rel_path}: Model '{m}' (must be 'inherit')")
        self.assertEqual(
            illegal_models,
            [],
            f"Non-inherited subagent models found:\n" + "\n".join(illegal_models)
        )

    def test_skill_discovery_guidance(self):
        """Verify that skills include tool discovery guidance (bg3 tools)."""
        missing_discovery = []
        for sf in self.skill_files:
            content = sf.read_text(encoding="utf-8")
            has_discovery = (
                "bg3 tools" in content
                or "scripts/bg3.py tools" in content
                or "tools.py" in content
                or "registry" in content.lower()
            )
            if not has_discovery:
                missing_discovery.append(sf.parent.name)
        self.assertEqual(
            missing_discovery,
            [],
            f"Skills missing tool discovery guidance: {missing_discovery}"
        )

    def test_skills_conform_to_canonical_standards(self):
        """Verify that all skills pass validate_rule_or_skill.py with zero errors and zero warnings."""
        import json
        import subprocess

        validator_path = Path.home() / ".agents" / "skills-global" / "create-agent-rules-and-skills" / "scripts" / "validate_rule_or_skill.py"
        if not validator_path.exists():
            validator_path = Path.home() / ".gemini" / "config" / "skills" / "create-agent-rules-and-skills" / "scripts" / "validate_rule_or_skill.py"

        if not validator_path.exists():
            self.skipTest(f"Validator script not found at {validator_path}")

        failures = []
        for sf in self.skill_files:
            res = subprocess.run(
                ["python3", str(validator_path), "-f", str(sf), "-t", "skill", "--json"],
                capture_output=True,
                text=True
            )
            data = json.loads(res.stdout) if res.stdout else {}
            if not data.get("valid", False) or data.get("errors") or data.get("warnings"):
                failures.append(
                    f"{sf.parent.name}: errors={data.get('errors')}, warnings={data.get('warnings')}"
                )

        self.assertEqual(
            failures,
            [],
            f"Skills failed canonical pre-flight validation:\n" + "\n".join(failures)
        )


if __name__ == "__main__":
    unittest.main()

