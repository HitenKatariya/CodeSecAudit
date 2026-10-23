export type Severity = "critical" | "high" | "medium" | "low";
export type GateStatus = "BLOCKED" | "PASSED" | "IN_REVIEW";
export type FindingStatus = "open" | "resolved" | "ignored";

export interface UserProfile {
  id: string;
  github_id: string;
  username: string;
  email: string | null;
  avatar_url: string | null;
  is_admin: boolean;
  active_organization_id: string;
  organization_name: string;
  organization_role: string;
  is_installed?: boolean;
}


export interface Finding {
  id: string;
  cwe_id: string;
  severity: Severity;
  title: string;
  file_path: string;
  line_number?: number;
  code_snippet?: string;
  suggested_fix?: string;
  why_it_matters?: string;
  attack_scenario?: string;
  owasp_category?: string;
  confidence?: number;
  security_principle?: string;
  reasoning_summary?: string;
  status?: FindingStatus;
  detected_at?: string;
  repository?: string;
}

export interface PullRequest {
  id: string;
  pr_number: number;
  title: string;
  repository: string;
  author: string;
  author_avatar?: string;
  security_score: number;
  findings_summary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  gate_status: GateStatus;
  scanned_at: string;
  commit_sha?: string;
  gate_reason?: string;
  findings: Finding[];
}

export interface Repository {
  id: string;
  name: string;
  full_name?: string;
  github_repo_id?: string;
  language: string;
  security_score: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  open_findings_count: number;
  last_scan: string;
  status: "Blocked" | "Protected" | "Warning" | "Passed";
  pr_count?: number;
  stars?: number;
}

export interface SecurityPolicy {
  block_critical: boolean;
  block_secrets: boolean;
  block_high: boolean;
  block_medium: boolean;
  min_security_score: number;
  confidence_threshold: number;
  secret_detection: boolean;
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: "Admin" | "Security Lead" | "Developer" | "Viewer";
  prs_reviewed: number;
  findings_resolved: number;
  last_active: string;
  avatar_url?: string;
}

export interface ReportSummary {
  period: string;
  repos_scanned: number;
  prs_scanned: number;
  vulnerabilities_detected: number;
  critical_vulnerabilities: number;
  resolved_vulnerabilities: number;
  avg_remediation_hours: {
    critical: number;
    high: number;
    medium_days: number;
  };
}

export interface ReviewRecord {
  id: string;
  repository_id: string;
  pr_number: number;
  commit_sha: string;
  risk_score: number;
  verdict: "APPROVE" | "WARNING" | "REQUEST_CHANGES";
  summary: string;
  guidance_available: boolean;
  created_at: string;
  findings: Finding[];
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  service: string;
}

export interface ScoreProgression {
  month: string;
  score: number;
}

export interface CWEDistribution {
  name: string;
  cwe_id: string;
  count: number;
  pct: string;
  color: string;
  barBg: string;
}

export interface GateVerdicts {
  passed_count: number;
  passed_pct: number;
  blocked_count: number;
  blocked_pct: number;
}

export interface AnalyticsTrends {
  security_score: number;
  critical_active: number;
  mttr_hours: number;
  gate_enforcement_pct: number;
  score_progression: ScoreProgression[];
  cwe_distribution: CWEDistribution[];
  gate_verdicts: GateVerdicts;
}
