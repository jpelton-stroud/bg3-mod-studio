#!/usr/bin/env python3
"""
test_skills_installer.py
------------------------
Unit tests for packaging, discovery, and studio deployment of agent skills.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from bg3_core.skills_installer import (
    discover_bundled_skills,
    get_default_skills_target,
    install_agent_skills,
)


class TestSkillsInstaller(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.target_dir = Path(self.temp_dir) / ".agents" / "skills"

    def tearDown(self):
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_discover_bundled_skills_discovers_all_fifteen(self):
        skills = discover_bundled_skills()
        self.assertEqual(len(skills), 15, f"Expected 15 skills, found {len(skills)}: {list(skills.keys())}")
        for name, meta in skills.items():
            self.assertTrue(meta["source_path"].is_dir(), f"Skill directory missing: {meta['source_path']}")
            self.assertTrue(meta["skill_md"].is_file(), f"SKILL.md missing for {name}")

    def test_skills_package_allocations(self):
        skills = discover_bundled_skills()
        core_skills = {k for k, v in skills.items() if v["package"] == "bg3-core"}
        authoring_skills = {k for k, v in skills.items() if v["package"] == "bg3-authoring"}
        theorycraft_skills = {k for k, v in skills.items() if v["package"] == "bg3-theorycraft"}

        expected_core = {
            "bg3-create-modio-collection",
            "bg3-document-mods",
            "bg3-document-single-mod",
            "bg3-manage-load-order",
            "bg3-search-mods",
            "bg3-update-mod-documentation",
            "bg3-update-single-mod",
        }
        expected_authoring = {
            "bg3-check-mod-conflicts",
            "bg3-create-mod",
            "bg3-diagnose-mod",
            "bg3-post-release",
            "bg3-release-prep",
            "bg3-test-mod",
        }
        expected_theorycraft = {
            "bg3-create-build-guide",
            "bg3-query-gear",
        }

        self.assertEqual(core_skills, expected_core)
        self.assertEqual(authoring_skills, expected_authoring)
        self.assertEqual(theorycraft_skills, expected_theorycraft)

    def test_install_agent_skills_to_target_directory(self):
        res = install_agent_skills(target_dir=self.target_dir, force=True)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["installed"]), 15)
        self.assertEqual(len(res["errors"]), 0)

        for skill_name in res["installed"]:
            skill_folder = self.target_dir / skill_name
            self.assertTrue(skill_folder.is_dir(), f"Missing installed folder: {skill_folder}")
            self.assertTrue((skill_folder / "SKILL.md").is_file(), f"Missing SKILL.md in: {skill_folder}")

    def test_install_agent_skills_idempotent_update(self):
        # Initial install
        first_run = install_agent_skills(target_dir=self.target_dir, force=True)
        self.assertEqual(len(first_run["installed"]), 15)

        # Subsequent run updates existing folders
        second_run = install_agent_skills(target_dir=self.target_dir, force=True)
        self.assertTrue(second_run["success"])
        self.assertEqual(len(second_run["updated"]), 15)
        self.assertEqual(len(second_run["errors"]), 0)

    def test_install_preserves_subdirectories(self):
        install_agent_skills(target_dir=self.target_dir, force=True)
        create_mod_dir = self.target_dir / "bg3-create-mod"
        self.assertTrue((create_mod_dir / "references" / "grill_me_interview_protocol.md").is_file())
        self.assertTrue((create_mod_dir / "resources" / "subagent_templates.md").is_file())

    def test_default_skills_target(self):
        custom_studio = Path("/tmp/custom_studio")
        target = get_default_skills_target(studio_dir=custom_studio)
        self.assertEqual(target, custom_studio / ".agents" / "skills")


if __name__ == "__main__":
    unittest.main()
