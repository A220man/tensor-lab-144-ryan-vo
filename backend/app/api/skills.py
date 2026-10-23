from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.skill_validator import SkillValidator
from app.models.skill import SkillValidationResult, SkillFile, SkillFixResult, SkillValidationStatus

router = APIRouter(prefix="/api/skills", tags=["skills"])

_validator: Optional[SkillValidator] = None


def get_validator() -> SkillValidator:
    global _validator
    if _validator is None:
        _validator = SkillValidator("Skills")
    return _validator


@router.get("/validate", response_model=SkillValidationResult)
async def validate_skills():
    """Validate all SKILL.md files in the Skills directory."""
    validator = get_validator()
    return validator.validate_all()


@router.get("/list", response_model=List[SkillFile])
async def list_skills(
    status: Optional[SkillValidationStatus] = Query(None, description="Filter by validation status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    has_attacker_com: Optional[bool] = Query(None, description="Filter by attacker.com presence"),
):
    """List all skills with optional filters."""
    validator = get_validator()
    result = validator.validate_all()

    skills = result.skills
    if status:
        skills = [s for s in skills if s.validation_status == status]
    if category:
        skills = [s for s in skills if s.category.lower() == category.lower()]
    if has_attacker_com is not None:
        skills = [s for s in skills if s.has_attacker_com == has_attacker_com]

    return skills


@router.post("/fix/{skill_path:path}", response_model=SkillFixResult)
async def fix_skill(skill_path: str):
    """Generate fixed frontmatter for a skill file (dry-run by default)."""
    validator = get_validator()
    result = validator.validate_all()

    skill_file = next((s for s in result.skills if s.path == skill_path), None)
    if not skill_file:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_path}")

    if not skill_file.frontmatter:
        raise HTTPException(status_code=400, detail="Cannot fix: no frontmatter data available (legacy extraction failed)")

    original, fixed = validator.fix_skill_file(skill_file)

    return SkillFixResult(
        file_path=skill_path,
        success=True,
        original_frontmatter=original[:500] + "..." if len(original) > 500 else original,
        new_frontmatter=fixed[:500] + "..." if len(fixed) > 500 else fixed,
    )


@router.post("/fix-all", response_model=List[SkillFixResult])
async def fix_all_skills(apply: bool = Query(False, description="Actually write changes to disk")):
    """Fix all skills missing frontmatter."""
    validator = get_validator()
    result = validator.validate_all()

    fixes = []
    for skill_file in result.skills:
        if skill_file.validation_status in (
            SkillValidationStatus.MISSING_FRONTMATTER,
            SkillValidationStatus.MISSING_NAME,
            SkillValidationStatus.MISSING_DESCRIPTION,
        ) and skill_file.frontmatter:
            original, fixed = validator.fix_skill_file(skill_file)
            if apply:
                skill_path = Path("Skills") / skill_file.path
                skill_path.write_text(fixed, encoding="utf-8")
            fixes.append(SkillFixResult(
                file_path=skill_file.path,
                success=True,
                original_frontmatter=original[:500] + "..." if len(original) > 500 else original,
                new_frontmatter=fixed[:500] + "..." if len(fixed) > 500 else fixed,
            ))

    return fixes


from pathlib import Path