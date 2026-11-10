# Changelog

## 1.4.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Enhanced
- Placeholder sanitizer: multi-line context support for accurate classification
  - Uses headings and descriptions from previous lines (up to 3 lines, stops at blank lines or other placeholders)
  - Prevents cross-contamination between adjacent placeholder lines
  - Fixes misclassification when context (e.g., "## C2 Callback Configuration") is on a separate line from the URL

### Tests
- Added 3 new test cases for multi-line context behavior
- All 54 backend tests pass (3 new + 51 existing)
## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Added
- Attacker.com placeholder sanitizer service: scans SKILL.md files for attacker.com references
- Context-aware classification: C2 callbacks, exfiltration, shell callbacks → attacker.invalid; benign demos → attacker.example
- Standalone PlaceholderSanitizer class with sanitize_file, sanitize_all, generate_report
- Dry-run and apply modes for safe preview before modification
- Comprehensive test coverage for placeholder sanitizer (17 tests)

### Tests
- All 51 backend tests pass (17 new + 34 existing)
- All 6 frontend tests pass

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Added
- Description length validator service: validates skill description <= 1024 characters
- Standalone DescriptionValidator class with validate_skill, validate_all, check_description_lengths
- Report generation for over-limit descriptions with character counts and previews
- Comprehensive test coverage for description validator (12 tests)

### Tests
- All 34 backend tests pass (12 new + 22 existing)

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

## [1.0.1] - 2026-10-30

### Added
- Frontmatter fixer service: scans Skills/**/SKILL.md, detects missing/incomplete frontmatter
- Legacy metadata extraction from **Skill Name** and ## Description sections
- Fallback to directory name for skill name extraction
- Frontmatter generation and file fixing (dry-run and write modes)
- Comprehensive test coverage for frontmatter fixer

### Fixed
- Handle incomplete frontmatter (missing name/description) with proper validation status
- Prefer legacy extraction over incomplete frontmatter when fixing files


## [1.0.0] - 2026-10-23

### Added
- FastAPI backend with skill validation engine
- React + TypeScript + Vite frontend with skill dashboard
- Skill validator service: parses SKILL.md, validates frontmatter, description length, attacker.com placeholders
- Legacy metadata extraction from ## Metadata sections
- Frontmatter generation for non-compliant skills
- REST API: /health, /api/skills/validate, /api/skills/list, /api/skills/fix, /api/skills/fix-all
- GitHub Actions CI workflow (backend pytest, frontend typecheck/build/test, Docker builds)
- Dockerfiles for backend and frontend with non-root users
- docker-compose.yaml with backend, frontend, and Keycloak services
- Portfolio.json with schema_version=1
- README with install/run/test steps, architecture diagram, API reference
- MIT LICENSE

### Security
- Localhost binding for development servers
- Non-root Docker users
- Server-side only LLM_API_KEY handling
- OIDC/Keycloak authentication framework (demo mode when unconfigured)
