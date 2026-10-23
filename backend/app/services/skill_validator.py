import re
import yaml
from pathlib import Path
from typing import Optional, List, Tuple
from app.models.skill import (
     SkillMetadata,
     SkillFile,
     SkillValidationResult,
     SkillValidationStatus,
     SkillCategory,
 )


class SkillValidator:
    FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
    DESCRIPTION_SECTION_PATTERN = re.compile(r"## Description\n(.*?)(?:\n## |\n# |\Z)", re.DOTALL)
    SKILL_NAME_PATTERN = re.compile(r"\*\*Skill Name\*\*?\s*:\s*(\S+)")
    ATTACKER_COM_PATTERN = re.compile(r"attacker\.com", re.IGNORECASE)

    def __init__(self, skills_root: str = "Skills"):
        self.skills_root = Path(skills_root)

    def scan_skill_files(self) -> List[SkillFile]:
        skill_files = []
        if not self.skills_root.exists():
            return skill_files

        for skill_md in self.skills_root.rglob("SKILL.md"):
            relative_path = skill_md.relative_to(self.skills_root)
            category = relative_path.parts[0] if len(relative_path.parts) > 1 else "unknown"

            content = skill_md.read_text(encoding="utf-8")
            skill_file = SkillFile(
                path=str(relative_path),
                category=category,
                raw_content=content,
            )

            self._parse_frontmatter(skill_file)
            self._check_attacker_placeholder(skill_file)
            self._determine_validation_status(skill_file)

            skill_files.append(skill_file)

        return skill_files

    def _parse_frontmatter(self, skill_file: SkillFile) -> None:
        content = skill_file.raw_content
        match = self.FRONTMATTER_PATTERN.match(content)

        if not match:
            skill_file.validation_status = SkillValidationStatus.MISSING_FRONTMATTER
            skill_file.validation_errors.append("Missing YAML frontmatter")
            self._try_extract_legacy_metadata(skill_file)
            # If legacy extraction succeeded, update status to VALID
            if skill_file.frontmatter is not None:
                skill_file.validation_status = SkillValidationStatus.VALID
            return

        try:
            frontmatter_data = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter_data, dict):
                skill_file.validation_status = SkillValidationStatus.INVALID_YAML
                skill_file.validation_errors.append("Frontmatter is not a valid YAML mapping")
                return

            name = frontmatter_data.get("name")
            description = frontmatter_data.get("description")

            if not name:
                skill_file.validation_status = SkillValidationStatus.MISSING_NAME
                skill_file.validation_errors.append("Missing required field: name")

            if not description:
                skill_file.validation_status = SkillValidationStatus.MISSING_DESCRIPTION
                skill_file.validation_errors.append("Missing required field: description")
            elif len(description) > 1024:
                skill_file.validation_status = SkillValidationStatus.DESCRIPTION_TOO_LONG
                skill_file.validation_errors.append(f"Description exceeds 1024 characters (got {len(description)})")

            if name and description and len(description) <= 1024:
                skill_file.frontmatter = SkillMetadata(
                    name=name,
                    description=description,
                    category=self._parse_category(frontmatter_data.get("category")),
                    tags=frontmatter_data.get("tags", []),
                    version=frontmatter_data.get("version", "1.0.0"),
                    author=frontmatter_data.get("author"),
                )

        except yaml.YAMLError as e:
            skill_file.validation_status = SkillValidationStatus.INVALID_YAML
            skill_file.validation_errors.append(f"Invalid YAML: {e}")

    def _try_extract_legacy_metadata(self, skill_file: SkillFile) -> None:
        content = skill_file.raw_content

        name_match = self.SKILL_NAME_PATTERN.search(content)
        desc_match = self.DESCRIPTION_SECTION_PATTERN.search(content)

        extracted_name = name_match.group(1).strip() if name_match else None
        extracted_description = desc_match.group(1).strip() if desc_match else None

        if extracted_name and extracted_description:
            skill_file.frontmatter = SkillMetadata(
                name=extracted_name,
                description=extracted_description[:1024],
                category=self._parse_category_from_path(skill_file.path),
            )
            skill_file.validation_errors.append("Extracted from legacy ## Metadata section (needs frontmatter)")

    def _parse_category(self, category_str: Optional[str]) -> Optional[SkillCategory]:
        if not category_str:
            return None
        try:
            return SkillCategory(category_str.lower().replace("-", "_"))
        except ValueError:
            return None

    def _parse_category_from_path(self, path: str) -> Optional[SkillCategory]:
        parts = path.split("/")
        if len(parts) >= 1:
            cat_str = parts[0].lower().replace("-", "_")
            try:
                return SkillCategory(cat_str)
            except ValueError:
                return None
        return None

    def _check_attacker_placeholder(self, skill_file: SkillFile) -> None:
        matches = list(self.ATTACKER_COM_PATTERN.finditer(skill_file.raw_content))
        if matches:
            skill_file.has_attacker_com = True
            skill_file.attacker_com_locations = [m.start() for m in matches]

    def _determine_validation_status(self, skill_file: SkillFile) -> None:
        if skill_file.has_attacker_com and skill_file.validation_status == SkillValidationStatus.VALID:
            skill_file.validation_status = SkillValidationStatus.ATTACKER_PLACEHOLDER
            skill_file.validation_errors.append("Contains attacker.com placeholder (should use RFC-reserved domains)")

    def validate_all(self) -> SkillValidationResult:
        skills = self.scan_skill_files()

        return SkillValidationResult(
            total_files=len(skills),
            valid=sum(1 for s in skills if s.validation_status == SkillValidationStatus.VALID),
            missing_frontmatter=sum(1 for s in skills if s.validation_status == SkillValidationStatus.MISSING_FRONTMATTER),
            missing_name=sum(1 for s in skills if s.validation_status == SkillValidationStatus.MISSING_NAME),
            missing_description=sum(1 for s in skills if s.validation_status == SkillValidationStatus.MISSING_DESCRIPTION),
            description_too_long=sum(1 for s in skills if s.validation_status == SkillValidationStatus.DESCRIPTION_TOO_LONG),
            invalid_yaml=sum(1 for s in skills if s.validation_status == SkillValidationStatus.INVALID_YAML),
            attacker_placeholder=sum(1 for s in skills if s.validation_status == SkillValidationStatus.ATTACKER_PLACEHOLDER),
            skills=skills,
        )

    def generate_frontmatter(self, skill_file: SkillFile) -> str:
        if not skill_file.frontmatter:
            raise ValueError("No frontmatter data available")

        fm = skill_file.frontmatter
        lines = [
            "---",
            f"name: {fm.name}",
            f"description: {fm.description}",
        ]
        if fm.category:
            lines.append(f"category: {fm.category.value}")
        if fm.tags:
            lines.append(f"tags: {fm.tags}")
        if fm.version != "1.0.0":
            lines.append(f"version: {fm.version}")
        if fm.author:
            lines.append(f"author: {fm.author}")
        lines.append("---")
        return "\n".join(lines) + "\n\n"

    def fix_skill_file(self, skill_file: SkillFile) -> Tuple[str, str]:
        original_content = skill_file.raw_content
        new_frontmatter = self.generate_frontmatter(skill_file)

        if self.FRONTMATTER_PATTERN.match(original_content):
            new_content = self.FRONTMATTER_PATTERN.sub(new_frontmatter, original_content, count=1)
        else:
            new_content = new_frontmatter + original_content

        return original_content, new_content