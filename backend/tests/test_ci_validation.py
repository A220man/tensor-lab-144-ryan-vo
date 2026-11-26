"""CI regression guards test for skill metadata validation.

Tests the SkillValidator class directly, which is the core of the CI
regression guards that validate SKILL.md frontmatter, description length,
attacker.com placeholders, and other metadata requirements.
"""

from pathlib import Path

import pytest

from app.services.skill_validator import SkillValidator
from app.models.skill import SkillValidationStatus


class TestCIReggressionGuards:
    """Tests for CI regression guards that validate skill metadata."""

    @pytest.fixture
    def validator(self, tmp_path):
        skills_dir = tmp_path / "Skills"
        skills_dir.mkdir()
        return SkillValidator(str(skills_dir))

    def _write_and_validate(self, validator, content: str, category: str = "web"):
        """Write a skill file, scan, and validate. Returns the validation result."""
        cat_dir = Path(validator.skills_root) / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        skill_file = cat_dir / "SKILL.md"
        skill_file.write_text(content, encoding="utf-8")

        validator.scan_skill_files()
        result = validator.validate_all()
        # Find the skill we just wrote (last one scanned in this category)
        skill = next((s for s in result.skills if "SKILL.md" in s.path), None)
        return result, skill

    def test_ci_valid_skill_with_frontmatter_and_description_passes(self, validator):
        """A skill with frontmatter containing name, description passes CI validation."""
        content = (
            "---\n"
            "name: Cross-Site Scripting\n"
            "category: web\n"
            "description: A cross-site scripting vulnerability.\n"
            "version: \"1.0.0\"\n"
            "---\n"
            "# SKILL: Cross-Site Scripting (XSS)\n"
            "## Description\n"
            "A cross-site scripting vulnerability allows attackers to execute\n"
            "arbitrary JavaScript in a victim's browser.\n"
            "## Methodology\n"
            "XSS attacks typically involve injecting malicious scripts into\n"
            "web pages through user input that is not properly sanitized.\n"
            "## Remediation\n"
            "Implement output encoding and Content Security Policy to prevent\n"
            "XSS attacks.\n"
        )
        result, skill = self._write_and_validate(validator, content)
        assert skill is not None
        # With frontmatter having description field, should be VALID
        assert skill.validation_status == SkillValidationStatus.VALID, (
            f"Expected VALID, got {skill.validation_status}: {skill.validation_errors}"
        )

    def test_ci_missing_frontmatter_fails(self, validator):
        """A skill without YAML frontmatter fails CI validation."""
        content = (
            "# SKILL: Cross-Site Scripting (XSS)\n"
            "## Description\n"
            "A cross-site scripting vulnerability allows attackers to execute\n"
            "arbitrary JavaScript in a victim's browser.\n"
        )
        result, skill = self._write_and_validate(validator, content)
        assert skill is not None
        assert skill.validation_status == SkillValidationStatus.MISSING_FRONTMATTER, (
            f"Expected MISSING_FRONTMATTER, got {skill.validation_status}: {skill.validation_errors}"
        )

    def test_ci_description_too_long_in_frontmatter_fails(self, validator):
        """A skill with description exceeding 1024 chars in frontmatter fails CI validation."""
        long_desc = "x" * 1500
        content = (
            "---\n"
            "name: Test Skill\n"
            "category: web\n"
            f"description: {long_desc}\n"
            "version: \"1.0.0\"\n"
            "---\n"
            "# SKILL: Test Skill\n"
            "## Description\n"
            "Some short description.\n"
        )
        result, skill = self._write_and_validate(validator, content)
        assert skill is not None
        assert skill.validation_status == SkillValidationStatus.DESCRIPTION_TOO_LONG, (
            f"Expected DESCRIPTION_TOO_LONG, got {skill.validation_status}: {skill.validation_errors}"
        )

    def test_ci_attacker_com_placeholder_fails(self, validator):
        """A skill containing attacker.com placeholder fails CI validation."""
        content = (
            "---\n"
            "name: Test Skill\n"
            "category: web\n"
            "description: A test skill description.\n"
            "version: \"1.0.0\"\n"
            "---\n"
            "# SKILL: Test Skill\n"
            "## Description\n"
            "This uses attacker.com for C2 callbacks.\n"
        )
        result, skill = self._write_and_validate(validator, content)
        assert skill is not None
        assert skill.has_attacker_com is True, f"Expected has_attacker_com=True, got {skill.has_attacker_com}"
        # When frontmatter is present with description, attacker.com detection
        # should set status to ATTACKER_PLACEHOLDER
        assert skill.validation_status == SkillValidationStatus.ATTACKER_PLACEHOLDER, (
            f"Expected ATTACKER_PLACEHOLDER, got {skill.validation_status}: {skill.validation_errors}"
        )

    def test_ci_missing_name_in_frontmatter_fails(self, validator):
        """A skill with frontmatter missing name fails CI validation."""
        content = (
            "---\n"
            "category: web\n"
            "description: A test description.\n"
            "version: \"1.0.0\"\n"
            "---\n"
            "# SKILL: Test Skill\n"
            "## Description\n"
            "A test skill description.\n"
        )
        result, skill = self._write_and_validate(validator, content)
        assert skill is not None
        # Without name in frontmatter, the error should mention name
        assert any("name" in e.lower() for e in skill.validation_errors), (
            f"Expected error mentioning 'name': {skill.validation_errors}"
        )

    def test_ci_missing_description_in_frontmatter_fails(self, validator):
        """A skill with frontmatter missing description fails CI validation."""
        content = (
            "---\n"
            "name: Test Skill\n"
            "category: web\n"
            "version: \"1.0.0\"\n"
            "---\n"
            "# SKILL: Test Skill\n"
            "## Description\n"
            "A test skill description.\n"
        )
        result, skill = self._write_and_validate(validator, content)
        assert skill is not None
        # Frontmatter present but missing description field
        assert skill.validation_status == SkillValidationStatus.MISSING_DESCRIPTION, (
            f"Expected MISSING_DESCRIPTION, got {skill.validation_status}: {skill.validation_errors}"
        )

    def test_ci_invalid_yaml_frontmatter_fails(self, validator):
        """A skill with invalid YAML frontmatter fails CI validation."""
        content = (
            "---\n"
            "name: Invalid YAML\n"
            "this is not valid yaml: [unclosed\n"
            "---\n"
            "# SKILL: Invalid YAML\n"
            "## Description\n"
            "A skill with broken frontmatter.\n"
        )
        result, skill = self._write_and_validate(validator, content)
        assert skill is not None
        assert skill.validation_status == SkillValidationStatus.INVALID_YAML, (
            f"Expected INVALID_YAML, got {skill.validation_status}: {skill.validation_errors}"
        )
        assert any("Invalid YAML" in e for e in skill.validation_errors), (
            f"Expected 'Invalid YAML' in errors: {skill.validation_errors}"
        )
