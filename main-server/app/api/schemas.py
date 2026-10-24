"""API Request and Response Pydantic schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    postgres: str
    redis: str
    rag_service: str


class VersionResponse(BaseModel):
    service: str = "main-server"
    version: str
    git_sha: str


class UserMeResponse(BaseModel):
    id: str
    github_id: str
    username: str
    email: Optional[str]
    avatar_url: Optional[str]
    is_admin: bool
    active_organization_id: str
    organization_name: str
    organization_role: str
    is_installed: bool = False
    github_app_slug: Optional[str] = None
    github_app_install_url: Optional[str] = None



class LoginRequest(BaseModel):
    username: str = "omchoksi"
    email: Optional[str] = "om@codesec.ai"
    organization_name: Optional[str] = None


class FindingItem(BaseModel):
    id: str
    cwe_id: str
    severity: str
    title: str
    file_path: str
    line_number: Optional[int]
    code_snippet: Optional[str]
    suggested_fix: Optional[str]
    status: Optional[str] = "open"
    review_id: Optional[str] = None


class UpdateFindingStatusRequest(BaseModel):
    status: str


class ReviewDetailResponse(BaseModel):
    id: str
    repository_id: str
    repo_full_name: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: int
    commit_sha: str
    risk_score: float = 0.0
    verdict: str
    summary: str
    guidance_available: bool
    created_at: str
    findings: list[FindingItem] = Field(default_factory=list)


class ManualReviewRequest(BaseModel):
    repository_id: str
    code_content: str = Field(min_length=1)
    file_path: str = "manual_scan.py"


class LogEntry(BaseModel):
    id: str
    timestamp: str
    level: str
    message: str
    service: str


class RepositoryResponse(BaseModel):
    id: str
    name: str
    full_name: str
    github_repo_id: str
    is_private: bool = False
    language: str = "TypeScript / Python"
    security_score: int = 100
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    open_findings_count: int = 0
    pr_count: int = 0
    last_scan: str = "Recent"
    status: str = "Protected"


class SecurityPolicySchema(BaseModel):
    block_critical: bool = True
    block_secrets: bool = True
    block_high: bool = True
    block_medium: bool = False
    min_security_score: int = 80
    confidence_threshold: int = 70
    secret_detection: bool = True


class TeamMemberResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    avatar: str
    last_active: str


class ScoreProgressionItem(BaseModel):
    month: str
    score: int


class CWEDistributionItem(BaseModel):
    name: str
    cwe_id: str
    count: int
    pct: str
    color: str
    barBg: str


class GateVerdictsItem(BaseModel):
    passed_count: int
    passed_pct: float
    blocked_count: int
    blocked_pct: float


class AnalyticsTrendsResponse(BaseModel):
    security_score: int
    critical_active: int
    mttr_hours: float
    gate_enforcement_pct: float
    score_progression: list[ScoreProgressionItem]
    cwe_distribution: list[CWEDistributionItem]
    gate_verdicts: GateVerdictsItem


class ReportSummaryResponse(BaseModel):
    period: str
    repos_scanned: int
    prs_scanned: int
    vulnerabilities_detected: int
    critical_vulnerabilities: int
    resolved_vulnerabilities: int
    avg_remediation_hours: dict[str, float]

