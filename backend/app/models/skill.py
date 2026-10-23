from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SkillCategory(str, Enum):
    AI = "ai"
    AUTH = "auth"
    CICD = "cicd"
    CONTAINER = "container"
    CRYPTO = "crypto"
    EXPLOIT_DEV = "exploit-dev"
    FUZZING = "fuzzing"
    POST_EXPLOITATION = "post-exploitation"
    PRIVESC = "privesc"
    RECON = "recon"
    SOCIAL_ENGINEERING = "social-engineering"
    SUPPLY_CHAIN = "supply-chain"
    UTILITY = "utility"
    WEB = "web"
    WIRELESS = "wireless"
    ACTIVE_DIRECTORY = "active-directory"
    CLOUD = "cloud"
    IOT = "iot"
    MOBILE = "mobile"
    NETWORK = "network"
    FORENSICS = "forensics"
    API = "api"


class SkillValidationStatus(str, Enum):
    VALID = "valid"
    MISSING_FRONTMATTER = "missing_frontmatter"
    MISSING_NAME = "missing_name"
    MISSING_DESCRIPTION = "missing_description"
    DESCRIPTION_TOO_LONG = "description_too_long"
    INVALID_YAML = "invalid_yaml"
    ATTACKER_PLACEHOLDER = "attacker_placeholder"


class SkillMetadata(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field(..., min_length=1, max_length=1024)
    category: Optional[SkillCategory] = None
    tags: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0")
    author: Optional[str] = None

    @field_validator("description")
    @classmethod
    def validate_description_length(cls, v: str) -> str:
        if len(v) > 1024:
            raise ValueError(f"description exceeds 1024 characters (got {len(v)})")
        return v


class SkillFile(BaseModel):
    path: str
    category: str
    raw_content: str
    frontmatter: Optional[SkillMetadata] = None
    validation_status: SkillValidationStatus = SkillValidationStatus.VALID
    validation_errors: List[str] = Field(default_factory=list)
    has_attacker_com: bool = False
    attacker_com_locations: List[int] = Field(default_factory=list)


class SkillValidationResult(BaseModel):
    total_files: int
    valid: int
    missing_frontmatter: int
    missing_name: int
    missing_description: int
    description_too_long: int
    invalid_yaml: int
    attacker_placeholder: int
    skills: List[SkillFile]
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class SkillFixResult(BaseModel):
    file_path: str
    success: bool
    original_frontmatter: Optional[str] = None
    new_frontmatter: Optional[str] = None
    error: Optional[str] = None