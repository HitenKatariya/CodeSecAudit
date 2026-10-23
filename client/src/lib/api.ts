import {
  AnalyticsTrends,
  Finding,
  LogEntry,
  PullRequest,
  ReportSummary,
  Repository,
  ReviewRecord,
  SecurityPolicy,
  TeamMember,
  UserProfile,
} from "@/types";

export const GITHUB_APP_NAME =
  process.env.NEXT_PUBLIC_GITHUB_APP_NAME || "codesecaudit-ai";
export const GITHUB_APP_INSTALL_URL = `https://github.com/apps/${GITHUB_APP_NAME}/installations/new`;

export async function fetchMe(): Promise<UserProfile | null> {
  try {
    const res = await fetch("/api/auth/me", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      if (data && data.id) {
        return data;
      }
    }
  } catch {}
  return null;
}

export async function loginUser(credentials?: {
  username?: string;
  email?: string;
  organization_name?: string;
}): Promise<UserProfile | null> {
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(credentials || { username: "admin" }),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error("Login failed:", err);
  }
  return null;
}

export async function logoutUser(): Promise<boolean> {
  try {
    if (typeof window !== "undefined") {
      localStorage.removeItem("codesec_app_installed");
    }
    const res = await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    });
    return res.ok;
  } catch (err) {
    console.error("Logout failed:", err);
    return false;
  }
}


export async function fetchReviews(): Promise<ReviewRecord[]> {
  try {
    const res = await fetch("/api/reviews", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) return data;
    }
  } catch {}
  return [];
}

export async function fetchReviewDetail(id: string): Promise<ReviewRecord | null> {
  try {
    const res = await fetch(`/api/reviews/${id}`, { credentials: "include" });
    if (res.ok) return await res.json();
  } catch {}
  return null;
}

export async function fetchPullRequests(): Promise<PullRequest[]> {
  const reviews = await fetchReviews();
  if (reviews.length > 0) {
    const allFindings = await fetchFindings();
    const livePrs: PullRequest[] = reviews.map((r) => {
      const rFindings = r.findings && r.findings.length > 0
        ? r.findings
        : allFindings.filter((f) => (f as any).review_id === r.id);
      const crit = rFindings.filter((f) => f.severity === "critical").length;
      const high = rFindings.filter((f) => f.severity === "high").length;
      const med = rFindings.filter((f) => f.severity === "medium").length;
      const low = rFindings.filter((f) => f.severity === "low").length;
      const repoFullName = r.repo_full_name || r.repository_id || "OMCHOKSI108/CodeSecurityAuditAgent";
      const prUrl = r.pr_url || (repoFullName.includes("/") ? `https://github.com/${repoFullName}/pull/${r.pr_number}` : undefined);
      return {
        id: r.id,
        pr_number: r.pr_number || 1,
        title: `Security Audit PR #${r.pr_number || 1}`,
        repository: repoFullName,
        repo_full_name: repoFullName,
        pr_url: prUrl,
        author: "GitHub Author",
        security_score: Number(r.risk_score != null ? r.risk_score : 0),
        findings_summary: { critical: crit, high, medium: med, low },
        gate_status: r.verdict === "APPROVE" ? "PASSED" : "BLOCKED",
        scanned_at: new Date(r.created_at).toLocaleDateString(),
        commit_sha: r.commit_sha ? r.commit_sha.slice(0, 7) : "HEAD",
        gate_reason: r.summary,
        findings: rFindings,
      };
    });
    return livePrs;
  }
  return [];
}

export async function fetchPullRequestById(id: string): Promise<PullRequest | null> {
  const review = await fetchReviewDetail(id);
  if (review) {
    const crit = review.findings.filter((f) => f.severity === "critical").length;
    const high = review.findings.filter((f) => f.severity === "high").length;
    const med = review.findings.filter((f) => f.severity === "medium").length;
    const low = review.findings.filter((f) => f.severity === "low").length;
    const repoFullName = review.repo_full_name || review.repository_id || "OMCHOKSI108/CodeSecurityAuditAgent";
    const prUrl = review.pr_url || (repoFullName.includes("/") ? `https://github.com/${repoFullName}/pull/${review.pr_number}` : undefined);
    return {
      id: review.id,
      pr_number: review.pr_number || 1,
      title: `Security Audit PR #${review.pr_number || 1}`,
      repository: repoFullName,
      repo_full_name: repoFullName,
      pr_url: prUrl,
      author: "GitHub Author",
      security_score: Number(review.risk_score != null ? review.risk_score : 0),
      findings_summary: { critical: crit, high, medium: med, low },
      gate_status: review.verdict === "APPROVE" ? "PASSED" : "BLOCKED",
      scanned_at: new Date(review.created_at).toLocaleDateString(),
      commit_sha: review.commit_sha ? review.commit_sha.slice(0, 7) : "HEAD",
      gate_reason: review.summary,
      findings: review.findings as any,
    };
  }
  const all = await fetchPullRequests();
  return all.find((p) => p.id === id || String(p.pr_number) === id) || null;
}

export async function fetchRepositories(): Promise<Repository[]> {
  try {
    const res = await fetch("/api/repositories", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) return data;
    }
  } catch {}
  return [];
}

export async function fetchRepositoryById(id: string): Promise<Repository | null> {
  try {
    const res = await fetch(`/api/repositories/${id}`, { credentials: "include" });
    if (res.ok) return await res.json();
  } catch {}
  const all = await fetchRepositories();
  return all.find((r) => r.id === id || r.name === id) || null;
}

export async function fetchFindings(): Promise<Finding[]> {
  try {
    const res = await fetch("/api/findings", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) return data;
    }
  } catch {}
  return [];
}

export async function fetchFindingById(id: string): Promise<Finding | null> {
  try {
    const res = await fetch(`/api/findings/${id}`, { credentials: "include" });
    if (res.ok) return await res.json();
  } catch {}
  const all = await fetchFindings();
  return all.find((f) => f.id === id) || null;
}

export async function updateFindingStatus(
  findingId: string,
  status: "open" | "resolved" | "ignored"
): Promise<boolean> {
  try {
    const res = await fetch(`/api/findings/${findingId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
      credentials: "include",
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchSecurityPolicy(): Promise<SecurityPolicy> {
  try {
    const res = await fetch("/api/policies", { credentials: "include" });
    if (res.ok) return await res.json();
  } catch {}
  return {
    block_critical: true,
    block_secrets: true,
    block_high: true,
    block_medium: false,
    min_security_score: 80,
    confidence_threshold: 70,
    secret_detection: true,
  };
}

export async function saveSecurityPolicy(policy: SecurityPolicy): Promise<boolean> {
  try {
    const res = await fetch("/api/policies", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(policy),
      credentials: "include",
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchTeamMembers(): Promise<TeamMember[]> {
  try {
    const res = await fetch("/api/team", { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) {
        return data.map((m: any) => ({
          id: m.id,
          name: m.name,
          email: m.email,
          role: m.role as any,
          prs_reviewed: 0,
          findings_resolved: 0,
          last_active: m.last_active || "Active now",
          avatar_url: m.avatar,
        }));
      }
    }
  } catch {}
  return [];
}

export async function fetchAnalyticsTrends(): Promise<AnalyticsTrends | null> {
  try {
    const res = await fetch("/api/analytics/trends", { credentials: "include" });
    if (res.ok) return await res.json();
  } catch {}
  return null;
}

export async function fetchReportSummary(): Promise<ReportSummary | null> {
  try {
    const res = await fetch("/api/reports/summary", { credentials: "include" });
    if (res.ok) return await res.json();
  } catch {}
  return null;
}

export async function fetchLogs(
  service: "main-server" | "client-server" | "rag-server",
  limit = 50
): Promise<LogEntry[]> {
  try {
    const res = await fetch(`/api-logs/${service}-logs?limit=${limit}`, { credentials: "include" });
    if (res.ok) return await res.json();
  } catch {}
  return [];
}
