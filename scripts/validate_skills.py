"""Skill metadata regression guard: validates all SKILL.md have frontmatter and conforming description length."""

import sys
from pathlib import Path
from typing import List

from app.models.skill import SkillFile, SkillMetadata, SkillValidationStatus, SkillValidator


def main() -> int:
    """Validate all SKILL.md files and exit with error code if issues found."""
    skills_root = Path("Skills")
    if not skills_root.is_dir():
        print("ERROR: Skills/ directory not found", file=sys.stderr)
        return 1

    validator = SkillValidator(str(skills_root))
    result = validator.validate_all()

    exit_code = 0
    issues: List[str] = []

    if result.missing_frontmatter > 0:
        issues.append(
            f"{result.missing_frontmatter} skill{'s' if result.missing_frontmatter != 1 else ''} "
            f"missing frontmatter"
        )
        exit_code = 1

    if result.description_too_long > 0:
        issues.append(
            f"{result.description_too_long} skill{'s' if result.description_too_long != 1 else ''} "
            f"description exceeds 1024 characters"
        )
        exit_code = 1

    if result.attacker_placeholder > 0:
        issues.append(
            f"{result.attacker_placeholder} skill{'s' if result.attacker_placeholder != 1 else ''} "
            f"contains attacker.com placeholder"
        )
        exit_code = 1

    if result.invalid_yaml > 0:
        issues.append(
            f"{result.invalid_yaml} skill{'s' if result.invalid_yaml != 1 else ''} "
            f"has invalid YAML frontmatter"
        )
        exit_code = 1

    if result.missing_name > 0:
        issues.append(
            f"{result.missing_name} skill{'s' if result.missing_name != 1 else ''} "
            f"missing name in frontmatter"
        )
        exit_code = 1

    if result.missing_description > 0:
        issues.append(
            f"{result.missing_description} skill{'s' if result.missing_description != 1 else ''} "
            f"missing description in frontmatter"
        )
        exit_code = 1

    # Always print a summary
    print(f"Total skills validated: {result.total_files}")
    print(f"Valid: {result.valid}")
    print(f"Issues found: {result.total_files - result.valid}")

    if issues:
        print("\nProblems:")
        for issue in sorted(set(issues)):
            print(f"  - {issue}")

    if exit_code == 0:
        print("\nAll skills pass validation criteria.")
    else:
        print("\nValidation failures — CI build would fail.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
