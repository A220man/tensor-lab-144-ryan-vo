# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

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