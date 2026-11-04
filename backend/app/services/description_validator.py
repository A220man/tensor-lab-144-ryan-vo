"""Description length validator for SKILL.md files.

Validates that description fields in skill frontmatter do not exceed 1024 characters.
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

from app.models.skill import SkillFile, SkillValidationStatus


@dataclass
class DescriptionValidationIssue:
    """Represents a description length violation."""
    file_path: str
    category: str
    skill_name: str
    description_length: int
    description_preview: str
    limit: int = 1024


@dataclass
class DescriptionValidationResult:
    """Result of description length validation across all skills."""
    total_skills: int
    valid_count: int
    over_limit_count: int
    issues: List[DescriptionValidationIssue] = field(default_factory=list)
    skills_processed: List[SkillFile] = field(default_factory=list)

    @property
    def all_valid(self) -> bool:
        return self.over_limit_count == 0


class DescriptionValidator:
    """Validates description field length in skill frontmatter."""

    MAX_DESCRIPTION_LENGTH = 1024

    def __init__(self, skills_root: str = "Skills"):
        self.skills_root = Path(skills_root)

    def validate_skill(self, skill_file: SkillFile) -> Optional[DescriptionValidationIssue]:
        """Validate a single skill's description length.

        Returns None if valid, otherwise returns the validation issue.
        """
        if skill_file.frontmatter is None:
            return None

        description = skill_file.frontmatter.description
        length = len(description)

        if length > self.MAX_DESCRIPTION_LENGTH:
            preview = description[:200] + ("..." if len(description) > 200 else "")
            return DescriptionValidationIssue(
                file_path=skill_file.path,
                category=skill_file.category,
                skill_name=skill_file.frontmatter.name,
                description_length=length,
                description_preview=preview,
                limit=self.MAX_DESCRIPTION_LENGTH,
            )
        return None

    def validate_all(self, skill_files: Optional[List[SkillFile]] = None) -> DescriptionValidationResult:
        """Validate description length for all skill files."""
        if skill_files is None:
            skill_files = self._load_skill_files()

        result = DescriptionValidationResult(
            total_skills=len(skill_files),
            valid_count=0,
            over_limit_count=0,
            skills_processed=skill_files,
        )

        for skill in skill_files:
            issue = self.validate_skill(skill)
            if issue:
                result.issues.append(issue)
                result.over_limit_count += 1
            else:
                result.valid_count += 1

        return result

    def _load_skill_files(self) -> List[SkillFile]:
        """Load skill files from the skills directory."""
        # This would normally use the FrontmatterFixer to scan, but we'll keep it simple
        # and assume the caller provides the skill files
        return []


def check_description_lengths(skill_files: List[SkillFile], limit: int = 1024) -> DescriptionValidationResult:
    """Convenience function to validate description lengths."""
    validator = DescriptionValidator()
    validator.MAX_DESCRIPTION_LENGTH = limit
    return validator.validate_all(skill_files)


def report_over_limit(skill_files: List[SkillFile]) -> str:
    """Generate a human-readable report of over-limit descriptions."""
    result = check_description_lengths(skill_files)

    if result.all_valid:
        return f"All {result.total_skills} skills have valid description lengths (<= {DescriptionValidator.MAX_DESCRIPTION_LENGTH} chars)."

    lines = [
        f"Description Length Validation Report",
        f"=====================================",
        f"Total skills: {result.total_skills}",
        f"Valid: {result.valid_count}",
        f"Over limit (> {DescriptionValidator.MAX_DESCRIPTION_LENGTH} chars): {result.over_limit_count}",
        f"",
        f"Over-limit skills:",
    ]

    for issue in result.issues:
        lines.append(
            f"  - {issue.file_path} ({issue.category}/{issue.skill_name}): "
            f"{issue.description_length} chars"
        )
        lines.append(f"    Preview: {issue.description_preview}")

    return "\n".join(lines)
