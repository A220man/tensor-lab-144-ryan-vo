"""Tests for description length validator."""

import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.description_validator import (
    DescriptionValidator,
    DescriptionValidationIssue,
    DescriptionValidationResult,
    check_description_lengths,
    report_over_limit,
)
from app.models.skill import SkillFile, SkillMetadata, SkillCategory, SkillValidationStatus


class TestDescriptionValidator:
    @pytest.fixture
    def validator(self):
        return DescriptionValidator()

    def _make_skill(self, name: str, description: str, category: str = "web") -> SkillFile:
        """Create a SkillFile with given name and description."""
        # Bypass SkillMetadata validation by using model_construct
        metadata = SkillMetadata.model_construct(name=name, description=description)
        return SkillFile(
            path=f"Skills/{category}/{name}/SKILL.md",
            category=category,
            raw_content="",
            frontmatter=metadata,
            validation_status=SkillValidationStatus.VALID,
        )

    def test_valid_description(self, validator):
        """Test that descriptions within limit pass."""
        skill = self._make_skill("XSS", "A short description of XSS.")
        issue = validator.validate_skill(skill)
        assert issue is None

    def test_exact_limit(self, validator):
        """Test that description at exactly 1024 chars passes."""
        desc = "x" * 1024
        skill = self._make_skill("Test", desc)
        issue = validator.validate_skill(skill)
        assert issue is None

    def test_over_limit(self, validator):
        """Test that descriptions over 1024 chars fail."""
        desc = "x" * 1025
        skill = self._make_skill("Test", desc)
        issue = validator.validate_skill(skill)
        assert issue is not None
        assert issue.description_length == 1025
        assert issue.skill_name == "Test"

    def test_validate_all_mixed(self, validator):
        """Test validating mix of valid and invalid skills."""
        skills = [
            self._make_skill("Valid1", "Short desc"),
            self._make_skill("Invalid1", "x" * 1025),
            self._make_skill("Valid2", "Another short one"),
            self._make_skill("Invalid2", "y" * 2000),
        ]
        result = validator.validate_all(skills)
        assert result.total_skills == 4
        assert result.valid_count == 2
        assert result.over_limit_count == 2
        assert len(result.issues) == 2

    def test_validate_all_empty(self, validator):
        """Test validating empty list."""
        result = validator.validate_all([])
        assert result.total_skills == 0
        assert result.valid_count == 0
        assert result.over_limit_count == 0
        assert result.all_valid

    def test_report_over_limit(self, validator):
        """Test report generation."""
        skills = [
            self._make_skill("Valid", "OK"),
            self._make_skill("Invalid", "x" * 1500),
        ]
        report = report_over_limit(skills)
        assert "Over limit" in report
        assert "1500" in report
        assert "Invalid" in report

    def test_report_all_valid(self, validator):
        """Test report when all valid."""
        skills = [self._make_skill("Valid", "OK")]
        report = report_over_limit(skills)
        assert "All 1 skills have valid description lengths" in report

    def test_no_frontmatter(self, validator):
        """Test skill without frontmatter is skipped."""
        skill = SkillFile(
            path="Skills/web/test/SKILL.md",
            category="web",
            raw_content="",
            frontmatter=None,
            validation_status=SkillValidationStatus.MISSING_FRONTMATTER,
        )
        issue = validator.validate_skill(skill)
        assert issue is None

    def test_custom_limit(self):
        """Test custom limit parameter."""
        validator = DescriptionValidator()
        validator.MAX_DESCRIPTION_LENGTH = 100
        skill = self._make_skill("Test", "x" * 101)
        issue = validator.validate_skill(skill)
        assert issue is not None
        assert issue.limit == 100

    def test_check_description_lengths_function(self):
        """Test convenience function."""
        skills = [self._make_skill("Test", "x" * 2000)]
        result = check_description_lengths(skills, limit=1000)
        assert result.over_limit_count == 1
        assert result.issues[0].limit == 1000

    def test_issue_preview_truncation(self, validator):
        """Test that long descriptions are truncated in preview."""
        long_desc = "x" * 1500
        skill = self._make_skill("Test", long_desc)
        issue = validator.validate_skill(skill)
        assert issue is not None
        assert len(issue.description_preview) <= 203  # 200 + "..."
        assert issue.description_preview.endswith("...")

    def test_issue_contains_required_fields(self, validator):
        """Test that validation issue has all required fields."""
        skill = self._make_skill("SQLi", "x" * 1100)
        issue = validator.validate_skill(skill)
        assert issue.file_path == skill.path
        assert issue.category == skill.category
        assert issue.skill_name == "SQLi"
        assert issue.description_length == 1100
        assert issue.limit == 1024
