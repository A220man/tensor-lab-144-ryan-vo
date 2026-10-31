import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.frontmatter_fixer import FrontmatterFixer
from app.models.skill import SkillValidationStatus, SkillCategory


class TestFrontmatterFixer:
    @pytest.fixture
    def fixer(self, tmp_path):
        skills_dir = tmp_path / "Skills"
        skills_dir.mkdir()
        return FrontmatterFixer(str(skills_dir))

    def _write_skill(self, skills_dir: str, category: str, name: str, content: str):
        cat_dir = Path(skills_dir) / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        skill_dir = cat_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    def test_valid_frontmatter(self, fixer, tmp_path):
        content = """---
name: "SQL Injection"
description: "Exploit SQL injection vulnerabilities"
category: web
tags: ["sqli", "injection"]
version: "1.0.0"
author: "Test Author"
---
## Description
Exploit SQL injection vulnerabilities in web applications.
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "sql-injection", content)

        result = fixer.validate_all()

        assert result.total_files == 1
        assert result.valid == 1
        skill = result.skills[0]
        assert skill.frontmatter is not None
        assert skill.frontmatter.name == "SQL Injection"
        assert skill.frontmatter.description == "Exploit SQL injection vulnerabilities"
        assert skill.frontmatter.category == SkillCategory.WEB
        assert "sqli" in skill.frontmatter.tags
        assert skill.validation_status == SkillValidationStatus.VALID

    def test_missing_frontmatter(self, fixer, tmp_path):
        content = """# SKILL: Cross-Site Scripting (XSS)

## Description
Exploit XSS vulnerabilities in web applications.
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "xss", content)

        result = fixer.validate_all()

        assert result.total_files == 1
        assert result.missing_frontmatter == 1
        skill = result.skills[0]
        assert skill.frontmatter is None
        assert skill.validation_status == SkillValidationStatus.MISSING_FRONTMATTER
        assert "Missing YAML frontmatter" in skill.validation_errors

    def test_missing_name_in_frontmatter(self, fixer, tmp_path):
        content = """---
description: "Missing name"
category: web
---
## Description
Missing name.
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "missing-name", content)

        result = fixer.validate_all()

        assert result.total_files == 1
        assert result.missing_name == 1
        skill = result.skills[0]
        assert skill.frontmatter is not None
        assert skill.frontmatter.name == ""
        assert skill.validation_status == SkillValidationStatus.MISSING_NAME

    def test_missing_description_in_frontmatter(self, fixer, tmp_path):
        content = """---
name: "Test Skill"
category: web
---
## Description
Missing description.
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "missing-desc", content)

        result = fixer.validate_all()

        assert result.total_files == 1
        assert result.missing_description == 1
        skill = result.skills[0]
        assert skill.frontmatter is not None
        assert skill.frontmatter.description == ""
        assert skill.validation_status == SkillValidationStatus.MISSING_DESCRIPTION

    def test_legacy_metadata_extraction(self, fixer, tmp_path):
        content = """# SKILL: SQL Injection

**Skill Name**: SQL Injection

## Description
Exploit SQL injection vulnerabilities in web applications.

## Usage
sqlmap -u \"target\"
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "sql-injection", content)

        result = fixer.validate_all()

        assert result.total_files == 1
        assert result.missing_frontmatter == 1
        skill = result.skills[0]
        assert skill.validation_status == SkillValidationStatus.MISSING_FRONTMATTER

        # Test extraction
        extracted = fixer._try_extract_legacy_metadata(skill)
        assert extracted is not None
        assert extracted.name == "SQL Injection"
        assert "SQL injection" in extracted.description

    def test_generate_frontmatter_from_legacy(self, fixer, tmp_path):
        content = """# SKILL: XSS

**Skill Name**: Cross-Site Scripting

## Description
Exploit XSS vulnerabilities.
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "xss", content)

        result = fixer.validate_all()
        skill = result.skills[0]

        frontmatter = fixer.generate_frontmatter(skill)
        assert frontmatter.startswith("---\n")
        assert "name: \"Cross-Site Scripting\"" in frontmatter
        assert "description: \"Exploit XSS vulnerabilities.\"" in frontmatter
        assert "category: web" in frontmatter
        assert frontmatter.endswith("---\n\n")

    def test_fix_skill_file_adds_frontmatter(self, fixer, tmp_path):
        content = """# SKILL: XSS

**Skill Name**: Cross-Site Scripting

## Description
Exploit XSS vulnerabilities.
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "xss", content)

        result = fixer.validate_all()
        skill = result.skills[0]

        original, fixed = fixer.fix_skill_file(skill)
        assert original == content
        assert fixed.startswith("---\n")
        assert "name: \"Cross-Site Scripting\"" in fixed
        assert "description: \"Exploit XSS vulnerabilities.\"" in fixed
        assert fixed.endswith(content)

    def test_fix_skill_file_replaces_invalid_frontmatter(self, fixer, tmp_path):
        # Frontmatter with missing name - should be filled from legacy content
        content = """---
description: "Old description"
---
# SKILL: New Skill Name

## Description
New description from legacy.
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "test", content)

        result = fixer.validate_all()
        skill = result.skills[0]

        # Should have missing_name status
        assert skill.validation_status == SkillValidationStatus.MISSING_NAME

        original, fixed = fixer.fix_skill_file(skill)
        # Should have new name from legacy content
        assert "New Skill Name" in fixed
        assert "New description from legacy" in fixed
        assert "Old description" not in fixed
        assert fixed.count("---") == 2  # opening and closing

    def test_fix_all_dry_run(self, fixer, tmp_path):
        # Valid skill
        content1 = """---
name: "Valid Skill"
description: "Valid description"
category: web
---
## Description
Valid description.
"""
        # Missing frontmatter
        content2 = """# SKILL: Missing FM

## Description
Missing frontmatter.
"""
        # Missing name
        content3 = """---
description: "Missing name"
category: web
---
## Description
Missing name.
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "valid", content1)
        self._write_skill(str(tmp_path / "Skills"), "web", "missing-fm", content2)
        self._write_skill(str(tmp_path / "Skills"), "web", "missing-name", content3)

        results = fixer.fix_all(dry_run=True)

        assert len(results) == 2  # only missing-fm and missing-name
        assert results[0].success is True
        assert results[0].file_path == "web/missing-fm/SKILL.md"
        assert results[1].success is True
        assert results[1].file_path == "web/missing-name/SKILL.md"
        assert results[0].new_frontmatter is not None
        assert "name: \"Missing Fm\"" in results[0].new_frontmatter

    def test_fix_all_writes_files(self, fixer, tmp_path):
        content = """# SKILL: Test

## Description
Test description.
"""
        self._write_skill(str(tmp_path / "Skills"), "web", "test", content)

        results = fixer.fix_all(dry_run=False)

        assert len(results) == 1
        assert results[0].success is True

        # Verify file was written
        skill_path = tmp_path / "Skills" / "web" / "test" / "SKILL.md"
        written = skill_path.read_text(encoding="utf-8")
        assert written.startswith("---\n")
        assert "name: \"Test\"" in written
        assert "description: \"Test description.\"" in written

    def test_category_from_path(self, fixer):
        # Test category parsing from various paths
        cat = fixer._parse_category_from_path("web/sql-injection/SKILL.md")
        assert cat == SkillCategory.WEB

        cat = fixer._parse_category_from_path("recon/port-scanning/SKILL.md")
        assert cat == SkillCategory.RECON

        cat = fixer._parse_category_from_path("unknown/test/SKILL.md")
        assert cat is None

    def test_no_skills_directory(self, tmp_path):
        # Skills directory doesn't exist
        fixer = FrontmatterFixer(str(tmp_path / "NonExistent"))
        result = fixer.validate_all()
        assert result.total_files == 0
        assert result.skills == []