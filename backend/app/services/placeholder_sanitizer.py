"""Attacker.com placeholder sanitizer for SKILL.md files."""

import re
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum

from app.models.skill import SkillFile


class PlaceholderType(str, Enum):
    C2_CALLBACK = "c2_callback"
    EXFILTRATION = "exfiltration"
    SHELL_CALLBACK = "shell_callback"
    BENIGN_DEMO = "benign_demo"
    UNKNOWN = "unknown"


class ReplacementDomain(str, Enum):
    ATTACKER_INVALID = "attacker.invalid"
    ATTACKER_EXAMPLE = "attacker.example"


@dataclass
class PlaceholderMatch:
    line_number: int
    column: int
    original_text: str
    placeholder_type: PlaceholderType
    replacement_domain: ReplacementDomain
    context_line: str


@dataclass
class FileSanitizationResult:
    file_path: str
    matches: List[PlaceholderMatch] = field(default_factory=list)
    modified: bool = False
    original_content: str = ""
    new_content: str = ""
    error: Optional[str] = None


@dataclass
class SanitizationResult:
    total_files: int
    files_with_placeholders: int
    total_replacements: int
    file_results: List[FileSanitizationResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class PlaceholderSanitizer:
    ATTACKER_COM_PATTERN = re.compile(r"attacker\.com", re.IGNORECASE)

    C2_PATTERNS = [
        re.compile(r"callback\s+(?:url|domain)?", re.IGNORECASE),
        re.compile(r"c2\s+(?:server|domain|host)", re.IGNORECASE),
        re.compile(r"\bc2\b", re.IGNORECASE),  # Match standalone "C2" or "c2"
        re.compile(r"command.?control", re.IGNORECASE),
        re.compile(r"beacon", re.IGNORECASE),
        re.compile(r"implant", re.IGNORECASE),
        re.compile(r"connect\s+to", re.IGNORECASE),
        re.compile(r"callback\s+to", re.IGNORECASE),
    ]

    EXFIL_PATTERNS = [
        re.compile(r"exfil(?:tration)?", re.IGNORECASE),
        re.compile(r"data.*exfil", re.IGNORECASE),
        re.compile(r"upload", re.IGNORECASE),
        re.compile(r"send.*data", re.IGNORECASE),
    ]

    SHELL_PATTERNS = [
        re.compile(r"(?:reverse|bind)\s+shell", re.IGNORECASE),
        re.compile(r"/dev/tcp/", re.IGNORECASE),
        re.compile(r"/dev/udp/", re.IGNORECASE),
        re.compile(r"\bnc\s+", re.IGNORECASE),
        re.compile(r"netcat", re.IGNORECASE),
        re.compile(r"bash\s+-i\s+>", re.IGNORECASE),
    ]

    BENIGN_PATTERNS = [
        re.compile(r"example\s+(?:url|domain|site)", re.IGNORECASE),
        re.compile(r"demo\s+(?:url|domain|site)", re.IGNORECASE),
        re.compile(r"placeholder\s+(?:url|domain)", re.IGNORECASE),
        re.compile(r"https?://", re.IGNORECASE),
    ]

    def __init__(self, skills_root: str = "Skills"):
        self.skills_root = Path(skills_root)

    def scan_skill_files(self) -> List[SkillFile]:
        skill_files = []
        if not self.skills_root.exists():
            return skill_files

        for skill_md in self.skills_root.rglob("SKILL.md"):
            try:
                content = skill_md.read_text(encoding="utf-8")
                rel_path = skill_md.relative_to(self.skills_root)
                category = rel_path.parts[0] if len(rel_path.parts) > 1 else "unknown"

                skill_files.append(SkillFile(
                    path=str(rel_path),
                    category=category,
                    raw_content=content,
                ))
            except Exception:
                continue

        return skill_files

    def _classify_placeholder(self, context: str) -> tuple[PlaceholderType, ReplacementDomain]:
        context_lower = context.lower()

        for pattern in self.C2_PATTERNS:
            if pattern.search(context_lower):
                return PlaceholderType.C2_CALLBACK, ReplacementDomain.ATTACKER_INVALID

        for pattern in self.EXFIL_PATTERNS:
            if pattern.search(context_lower):
                return PlaceholderType.EXFILTRATION, ReplacementDomain.ATTACKER_INVALID

        for pattern in self.SHELL_PATTERNS:
            if pattern.search(context_lower):
                return PlaceholderType.SHELL_CALLBACK, ReplacementDomain.ATTACKER_INVALID

        for pattern in self.BENIGN_PATTERNS:
            if pattern.search(context_lower):
                return PlaceholderType.BENIGN_DEMO, ReplacementDomain.ATTACKER_EXAMPLE

        return PlaceholderType.UNKNOWN, ReplacementDomain.ATTACKER_INVALID

    def _find_placeholders(self, content: str) -> List[PlaceholderMatch]:
        matches = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for match in self.ATTACKER_COM_PATTERN.finditer(line):
                # Context is the current line (for classification)
                context = line

                placeholder_type, replacement_domain = self._classify_placeholder(context)

                matches.append(PlaceholderMatch(
                    line_number=line_num,
                    column=match.start(),
                    original_text=match.group(),
                    placeholder_type=placeholder_type,
                    replacement_domain=replacement_domain,
                    context_line=line.strip(),
                ))

        return matches

    def _replace_placeholders(self, content: str, matches: List[PlaceholderMatch]) -> str:
        lines = content.split("\n")
        matches_by_line: dict[int, List[PlaceholderMatch]] = {}

        for match in matches:
            if match.line_number not in matches_by_line:
                matches_by_line[match.line_number] = []
            matches_by_line[match.line_number].append(match)

        for line_matches in matches_by_line.values():
            line_matches.sort(key=lambda m: m.column, reverse=True)

        for line_num, line_matches in matches_by_line.items():
            line_idx = line_num - 1
            if line_idx >= len(lines):
                continue

            line = lines[line_idx]
            for match in line_matches:
                replacement = match.replacement_domain.value
                line = line[:match.column] + replacement + line[match.column + len(match.original_text):]
            lines[line_idx] = line

        return "\n".join(lines)

    def sanitize_file(self, skill_file: SkillFile) -> FileSanitizationResult:
        matches = self._find_placeholders(skill_file.raw_content)

        if not matches:
            return FileSanitizationResult(
                file_path=skill_file.path,
                matches=[],
                modified=False,
                original_content=skill_file.raw_content,
                new_content=skill_file.raw_content,
            )

        new_content = self._replace_placeholders(skill_file.raw_content, matches)
        modified = new_content != skill_file.raw_content

        return FileSanitizationResult(
            file_path=skill_file.path,
            matches=matches,
            modified=modified,
            original_content=skill_file.raw_content,
            new_content=new_content,
        )

    def sanitize_all(self, dry_run: bool = True) -> SanitizationResult:
        skill_files = self.scan_skill_files()

        result = SanitizationResult(
            total_files=len(skill_files),
            files_with_placeholders=0,
            total_replacements=0,
        )

        for skill_file in skill_files:
            file_result = self.sanitize_file(skill_file)
            if file_result.matches:
                result.files_with_placeholders += 1
                result.total_replacements += len(file_result.matches)

            if file_result.modified and not dry_run:
                try:
                    file_path = self.skills_root / skill_file.path
                    file_path.write_text(file_result.new_content, encoding="utf-8")
                except Exception as e:
                    file_result.error = str(e)
                    result.errors.append(f"Failed to write {skill_file.path}: {e}")

            result.file_results.append(file_result)

        return result

    def generate_report(self, result: SanitizationResult) -> str:
        lines = [
            f"Placeholder Sanitization Report",
            f"=" * 50,
            f"Total files scanned: {result.total_files}",
            f"Files with placeholders: {result.files_with_placeholders}",
            f"Total replacements: {result.total_replacements}",
            f"",
        ]

        type_counts: dict[PlaceholderType, int] = {}
        domain_counts: dict[ReplacementDomain, int] = {}

        for file_result in result.file_results:
            for match in file_result.matches:
                type_counts[match.placeholder_type] = type_counts.get(match.placeholder_type, 0) + 1
                domain_counts[match.replacement_domain] = domain_counts.get(match.replacement_domain, 0) + 1

        if type_counts:
            lines.append("By placeholder type:")
            for ptype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {ptype.value}: {count}")

        if domain_counts:
            lines.append("")
            lines.append("By replacement domain:")
            for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {domain.value}: {count}")

        lines.append("")
        lines.append("Details:")
        for file_result in result.file_results:
            if file_result.matches:
                lines.append(f"  {file_result.file_path}:")
                for match in file_result.matches:
                    lines.append(f"    Line {match.line_number}: {match.placeholder_type.value} -> {match.replacement_domain.value}")
                    lines.append(f"      Context: {match.context_line[:100]}")

        if result.errors:
            lines.append("")
            lines.append("Errors:")
            for e in result.errors:
                lines.append(f"  - {e}")

        return "\n".join(lines)


def sanitize_placeholders(skills_root: str = "Skills", dry_run: bool = True) -> SanitizationResult:
    sanitizer = PlaceholderSanitizer(skills_root)
    return sanitizer.sanitize_all(dry_run)
