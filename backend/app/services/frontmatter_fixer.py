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
    SkillFixResult,
)


class FrontmatterFixer:
    FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
    DESCRIPTION_SECTION_PATTERN = re.compile(r"## Description\n(.*?)(?:\n## |\n# |\Z)", re.DOTALL)
    SKILL_NAME_PATTERN = re.compile(r"\*\*Skill Name\*\*?\s*:\s*([^\n]+)")

    def __init__(self, skills_root: str = "Skills"):
        self.skills_root = Path(skills_root)

    def scan_skill_files(self) -> List[SkillFile]:
        """Scan all SKILL.md files under the skills root."""
        skill_files = []
        if not self.skills_root.exists():
            return skill_files

        for skill_md in self.skills_root.rglob("SKILL.md"):
            try:
                raw_content = skill_md.read_text(encoding="utf-8")
                relative_path = skill_md.relative_to(self.skills_root)
                category_from_path = str(relative_path.parent.parent) if len(relative_path.parts) >= 2 else "unknown"

                skill_file = SkillFile(
                    path=str(relative_path),
                    category=category_from_path,
                    raw_content=raw_content,
                )
                self._parse_frontmatter(skill_file)
                self._check_attacker_placeholder(skill_file)
                self._determine_validation_status(skill_file)
                skill_files.append(skill_file)
            except Exception as e:
                skill_file = SkillFile(
                    path=str(skill_md.relative_to(self.skills_root)) if skill_md.is_relative_to(self.skills_root) else str(skill_md),
                    category="unknown",
                    raw_content="",
                    validation_status=SkillValidationStatus.INVALID_YAML,
                    validation_errors=[f"Failed to read file: {e}"],
                )
                skill_files.append(skill_file)

        return skill_files

    def _parse_frontmatter(self, skill_file: SkillFile) -> None:
        """Parse YAML frontmatter if present."""
        content = skill_file.raw_content
        match = self.FRONTMATTER_PATTERN.match(content)
        if match:
            try:
                fm_data = yaml.safe_load(match.group(1))
                if fm_data:
                    # Try to create SkillMetadata, but handle missing required fields
                    try:
                        skill_file.frontmatter = SkillMetadata(**fm_data)
                    except Exception as e:
                        # Partial frontmatter - create with what we have using model_construct to bypass validation
                        name = fm_data.get("name", "")
                        description = fm_data.get("description", "")
                        category = fm_data.get("category")
                        tags = fm_data.get("tags", [])
                        version = fm_data.get("version", "1.0.0")
                        author = fm_data.get("author")
                        skill_file.frontmatter = SkillMetadata.model_construct(
                            name=name,
                            description=description,
                            category=self._parse_category(category) if category else None,
                            tags=tags,
                            version=version,
                            author=author,
                        )
                        skill_file.validation_errors.append(f"Incomplete frontmatter: {e}")
            except Exception as e:
                skill_file.validation_errors.append(f"Invalid YAML: {e}")
                skill_file.validation_status = SkillValidationStatus.INVALID_YAML

    def _try_extract_legacy_metadata(self, skill_file: SkillFile) -> Optional[SkillMetadata]:
        """Extract name and description from legacy format (## Description, **Skill Name**)."""
        content = skill_file.raw_content

        # Try to extract name from **Skill Name** pattern
        name = None
        name_match = self.SKILL_NAME_PATTERN.search(content)
        if name_match:
            name = name_match.group(1).strip()
        else:
            # Fallback: extract from directory name (parent of SKILL.md)
            path_parts = skill_file.path.split("/")
            if len(path_parts) >= 2:
                name = path_parts[-2].replace("-", " ").replace("_", " ").title()

        # Try to extract description from ## Description section
        description = None
        desc_match = self.DESCRIPTION_SECTION_PATTERN.search(content)
        if desc_match:
            description = desc_match.group(1).strip()

        if name and description:
            return SkillMetadata(
                name=name,
                description=description,
                category=self._parse_category_from_path(skill_file.path),
            )
        return None

    def _parse_category(self, category_str: Optional[str]) -> Optional[SkillCategory]:
        if not category_str:
            return None
        try:
            return SkillCategory(category_str.lower())
        except ValueError:
            return None

    def _parse_category_from_path(self, path: str) -> Optional[SkillCategory]:
        parts = path.split("/")
        if len(parts) >= 2:
            cat_str = parts[0].lower()
            return self._parse_category(cat_str)
        return None

    def _check_attacker_placeholder(self, skill_file: SkillFile) -> None:
        """Check for attacker.com placeholders."""
        matches = list(re.finditer(r"attacker\.com", skill_file.raw_content, re.IGNORECASE))
        if matches:
            skill_file.has_attacker_com = True
            skill_file.attacker_com_locations = [m.start() for m in matches]

    def _determine_validation_status(self, skill_file: SkillFile) -> None:
        """Determine the validation status of a skill file."""
        if skill_file.frontmatter is None:
            skill_file.validation_status = SkillValidationStatus.MISSING_FRONTMATTER
            skill_file.validation_errors.append("Missing YAML frontmatter")
        elif skill_file.frontmatter and not skill_file.frontmatter.name:
            skill_file.validation_status = SkillValidationStatus.MISSING_NAME
            skill_file.validation_errors.append("Missing name in frontmatter")
        elif skill_file.frontmatter and not skill_file.frontmatter.description:
            skill_file.validation_status = SkillValidationStatus.MISSING_DESCRIPTION
            skill_file.validation_errors.append("Missing description in frontmatter")
        elif skill_file.has_attacker_com and skill_file.validation_status == SkillValidationStatus.VALID:
            skill_file.validation_status = SkillValidationStatus.ATTACKER_PLACEHOLDER
            skill_file.validation_errors.append("Contains attacker.com placeholder (should use RFC-reserved domains)")

    def validate_all(self) -> SkillValidationResult:
        """Validate all skill files."""
        skills = self.scan_skill_files()

        counts = {
            "valid": 0,
            "missing_frontmatter": 0,
            "missing_name": 0,
            "missing_description": 0,
            "description_too_long": 0,
            "invalid_yaml": 0,
            "attacker_placeholder": 0,
        }

        for skill in skills:
            if skill.validation_status == SkillValidationStatus.VALID:
                counts["valid"] += 1
            elif skill.validation_status == SkillValidationStatus.MISSING_FRONTMATTER:
                counts["missing_frontmatter"] += 1
            elif skill.validation_status == SkillValidationStatus.MISSING_NAME:
                counts["missing_name"] += 1
            elif skill.validation_status == SkillValidationStatus.MISSING_DESCRIPTION:
                counts["missing_description"] += 1
            elif skill.validation_status == SkillValidationStatus.DESCRIPTION_TOO_LONG:
                counts["description_too_long"] += 1
            elif skill.validation_status == SkillValidationStatus.INVALID_YAML:
                counts["invalid_yaml"] += 1
            elif skill.validation_status == SkillValidationStatus.ATTACKER_PLACEHOLDER:
                counts["attacker_placeholder"] += 1

        return SkillValidationResult(
            total_files=len(skills),
            valid=counts["valid"],
            missing_frontmatter=counts["missing_frontmatter"],
            missing_name=counts["missing_name"],
            missing_description=counts["missing_description"],
            description_too_long=counts["description_too_long"],
            invalid_yaml=counts["invalid_yaml"],
            attacker_placeholder=counts["attacker_placeholder"],
            skills=skills,
        )

    def generate_frontmatter(self, skill_file: SkillFile) -> str:
        """Generate YAML frontmatter for a skill file."""
        metadata = None

        # Use existing frontmatter only if it has both name and description
        if skill_file.frontmatter and skill_file.frontmatter.name and skill_file.frontmatter.description:
            metadata = skill_file.frontmatter
        else:
            # Try to extract from legacy content
            metadata = self._try_extract_legacy_metadata(skill_file)
            # If legacy extraction fails but we have partial frontmatter, use that as fallback
            if not metadata and skill_file.frontmatter:
                metadata = skill_file.frontmatter

        if not metadata:
            raise ValueError(f"Cannot generate frontmatter for {skill_file.path}: missing name or description")

        lines = ["---"]
        lines.append(f"name: \"{metadata.name}\"")
        lines.append(f"description: \"{metadata.description}\"")
        if metadata.category:
            lines.append(f"category: {metadata.category.value}")
        if metadata.tags:
            tags_str = ", ".join(f'"{tag}"' for tag in metadata.tags)
            lines.append(f"tags: [{tags_str}]")
        lines.append(f"version: \"{metadata.version}\"")
        if metadata.author:
            lines.append(f"author: \"{metadata.author}\"")
        lines.append("---")
        return "\n".join(lines) + "\n\n"

    def fix_skill_file(self, skill_file: SkillFile) -> Tuple[str, str]:
        """Generate fixed content for a skill file by adding/replacing frontmatter."""
        original_content = skill_file.raw_content

        # Check if frontmatter already exists
        fm_match = self.FRONTMATTER_PATTERN.match(original_content)
        if fm_match:
            # Replace existing frontmatter
            new_frontmatter = self.generate_frontmatter(skill_file)
            new_content = new_frontmatter + original_content[fm_match.end():]
        else:
            # Prepend frontmatter
            new_frontmatter = self.generate_frontmatter(skill_file)
            new_content = new_frontmatter + original_content

        return original_content, new_content

    def fix_all(self, dry_run: bool = True) -> List[SkillFixResult]:
        """Fix all skill files missing frontmatter."""
        results = []
        validation_result = self.validate_all()

        for skill in sorted(validation_result.skills, key=lambda s: s.path):
            if skill.validation_status in (
                SkillValidationStatus.MISSING_FRONTMATTER,
                SkillValidationStatus.MISSING_NAME,
                SkillValidationStatus.MISSING_DESCRIPTION,
            ):
                try:
                    original, fixed = self.fix_skill_file(skill)
                    new_frontmatter_match = self.FRONTMATTER_PATTERN.match(fixed)
                    new_frontmatter = new_frontmatter_match.group(0) if new_frontmatter_match else None

                    result = SkillFixResult(
                        file_path=skill.path,
                        success=True,
                        original_frontmatter=skill.raw_content[:skill.raw_content.find("---") + 3] if skill.raw_content.startswith("---") else None,
                        new_frontmatter=new_frontmatter,
                    )

                    if not dry_run:
                        skill_path = self.skills_root / skill.path
                        skill_path.write_text(fixed, encoding="utf-8")

                    results.append(result)
                except Exception as e:
                    results.append(SkillFixResult(
                        file_path=skill.path,
                        success=False,
                        error=str(e),
                    ))

        return results