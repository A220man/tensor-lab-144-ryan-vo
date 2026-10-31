# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

skill-frontmatter-fixer

## Roadmap

### skeleton-and-core-workflow — Runnable FastAPI/React skeleton with skill validation workflow

Status: done

Acceptance:
- FastAPI backend with /health and /api/skills endpoints
- React + TypeScript + Vite frontend with skill list view
- Skill validation engine: parses SKILL.md files, extracts frontmatter, validates required fields
- CI workflow running backend pytest and frontend build/test
- Dockerfiles for backend and frontend with compose.yaml
- README with install/run/test steps
- portfolio.json at root with schema_version=1

Implementation: `backend/app/main.py`, `backend/app/api/skills.py`, `backend/app/services/skill_validator.py`, `backend/app/models/skill.py`, `backend/tests/test_skill_validator.py`, `backend/requirements.txt`, `frontend/package.json`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/components/SkillList.tsx`, `frontend/vite.config.ts`, `.github/workflows/ci.yml`, `docker-compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`, `README.md`, `portfolio.json`

Tests: `backend/tests/test_skill_validator.py`, `frontend/src/components/SkillList.test.tsx`

### skill-frontmatter-fixer — Automated frontmatter repair for 28 legacy SKILL.md files

Status: done

Acceptance:
- CLI tool scans Skills/**/SKILL.md and detects missing frontmatter
- Extracts name from directory and description from ## Description section
- Writes proper YAML frontmatter to files lacking it
- Validates all 78 skills have conforming frontmatter

Implementation: `backend/app/services/frontmatter_fixer.py`, `backend/app/api/fixer.py`

Tests: `backend/tests/test_frontmatter_fixer.py`

### description-length-validator — Description length validator for 1024-char spec limit

Status: planned

Acceptance:
- Validates description field <= 1024 characters
- Reports all 18 over-limit skills with character counts
- CI check fails on over-limit descriptions

Implementation: `backend/app/services/description_validator.py`

Tests: `backend/tests/test_description_validator.py`

### attacker-placeholder-sanitizer — Attacker.com placeholder replacement with RFC-reserved domains

Status: planned

Acceptance:
- Scans all SKILL.md files for attacker.com references
- Replaces C2/exfil/shell callbacks with attacker.invalid
- Replaces benign URL demos with attacker.example
- Preserves legitimate content

Implementation: `backend/app/services/placeholder_sanitizer.py`

Tests: `backend/tests/test_placeholder_sanitizer.py`

### ci-regression-guards — CI regression guards for skill metadata

Status: planned

Acceptance:
- GitHub Action validates all SKILL.md have frontmatter
- Validates description length <= 1024
- Validates skill count matches README badge
- Fails build on any regression

Implementation: `.github/workflows/skill-validation.yml`, `scripts/validate_skills.py`

Tests: `backend/tests/test_ci_validation.py`

