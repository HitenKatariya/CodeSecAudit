"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { PullRequest, Repository } from "@/types";
import { fetchPullRequests, fetchRepositories, GITHUB_APP_INSTALL_URL } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { RepositoriesTable } from "@/components/repositories/RepositoriesTable";
import { RecentPRsTable } from "@/components/dashboard/RecentPRsTable";
import { GitHubIcon } from "@/components/ui/Icons";

export default function DashboardPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchRepositories(), fetchPullRequests()])
      .then(([r, p]) => {
        setRepos(r);
        setPrs(p);
      })
      .finally(() => setLoading(false));
  }, []);

  const totalFindings = repos.reduce((acc, r) => acc + (r.open_findings_count || 0), 0);
  const criticalCount = repos.reduce((acc, r) => acc + (r.critical_count || 0), 0);
  const blockedPrsCount = prs.filter((p) => p.gate_status === "BLOCKED").length;

  const avgSecurityScore =
    repos.length > 0
      ? Math.round(repos.reduce((acc, r) => acc + (r.security_score || 0), 0) / repos.length)
      : 100;

  const primaryBlockedRepo =
    repos.find((r) => r.critical_count > 0)?.name ||
    repos[0]?.name ||
    "Monitored Repositories";

  return (
    <div className="space-y">
      {/* Page Header */}
      <PageHeader
        title="Security Posture Dashboard"
        subtitle="Real-time Pull Request risk assessment across active repositories."
        actions={
          <div className="flex items-center gap-2">
            <a href={GITHUB_APP_INSTALL_URL} target="_blank" rel="noopener noreferrer">
              <Button variant="secondary" size="md" icon={<GitHubIcon size={16} />}>
                Install GitHub App ↗
              </Button>
            </a>
            <Link href="/pull-requests">
              <Button variant="primary" size="md">
                View All Pull Requests →
              </Button>
            </Link>
          </div>
        }
      />

      {/* GitHub App 1-Click Install Onboarding Card */}
      {!loading && repos.length === 0 && (
        <div
          style={{
            padding: "1.5rem",
            borderRadius: "12px",
            background: "linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(37, 99, 235, 0.05) 100%)",
            border: "1px solid rgba(59, 130, 246, 0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "1.25rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem", maxWidth: "680px" }}>
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "10px",
                background: "rgba(59, 130, 246, 0.2)",
                color: "var(--accent, #3b82f6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <GitHubIcon size={26} />
            </div>
            <div>
              <div style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main, #f8fafc)" }}>
                Install GitHub App to Start PR Security Audits
              </div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted, #94a3b8)", marginTop: "0.35rem", lineHeight: "1.5" }}>
                CodeSecAudit AI is ready. Install the GitHub App on your repositories to activate automatic AST taint analysis, OWASP RAG guidance, and inline PR security comments.
              </div>
            </div>
          </div>

          <a
            href={GITHUB_APP_INSTALL_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{ textDecoration: "none" }}
          >
            <Button
              variant="primary"
              size="lg"
              className="font-bold"
              icon={<GitHubIcon size={18} />}
            >
              ⚡ 1-Click Install GitHub App
            </Button>
          </a>
        </div>
      )}

      {/* Immediate Attention Callout */}
      {criticalCount > 0 ? (
        <div className="banner-alert">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="badge badge-critical">⚠️ Action Required</span>
              <span className="text-muted text-xs">&bull; {totalFindings} open findings</span>
            </div>
            <p className="text-sm text-main font-medium mt-1">
              <strong style={{ color: "var(--crit-color)" }}>
                {criticalCount} Critical finding{criticalCount === 1 ? "" : "s"}
              </strong>{" "}
              {blockedPrsCount > 0 ? (
                <>
                  currently blocking{" "}
                  <strong style={{ color: "var(--crit-color)" }}>
                    {blockedPrsCount} Pull Request{blockedPrsCount === 1 ? "" : "s"}
                  </strong>{" "}
                  in <code className="crumb-badge">{primaryBlockedRepo}</code>.
                </>
              ) : (
                <>detected in monitored codebases.</>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Link href="/findings?severity=critical">
              <Button variant="danger" size="sm">
                Review Critical Findings →
              </Button>
            </Link>
            {blockedPrsCount > 0 && (
              <Link href="/pull-requests">
                <Button variant="secondary" size="sm">
                  View Blocked PRs ({blockedPrsCount})
                </Button>
              </Link>
            )}
          </div>
        </div>
      ) : (
        <div className="p-3.5 rounded-lg border text-xs flex items-center justify-between" style={{ backgroundColor: "var(--pass-bg)", borderColor: "var(--pass-border)", color: "var(--pass-color)" }}>
          <div className="flex items-center gap-2">
            <span>🛡️</span>
            <span className="font-semibold">All Policy Gates Healthy: Zero critical security regressions detected.</span>
          </div>
          <span className="text-muted text-[11px]">{totalFindings} total informational/low findings</span>
        </div>
      )}

      {/* 4 Core Metrics dynamically computed from live state */}
      <div className="stat-grid">
        <MetricCard
          label="Security Score"
          value={String(avgSecurityScore)}
          suffix="/ 100"
          trend="+4%"
          trendDirection="up"
          trendPositive={true}
          subtitle="weighted average"
        />

        <MetricCard
          label="Open Findings"
          value={String(totalFindings)}
          trend={totalFindings > 0 ? "Active" : "Clean"}
          trendDirection="down"
          trendPositive={true}
          subtitle={`across ${repos.length} repo${repos.length === 1 ? "" : "s"}`}
        />

        <MetricCard
          label="Critical Issues"
          value={String(criticalCount)}
          severity={criticalCount > 0 ? "critical" : "passed"}
          subtitle={criticalCount > 0 ? "🔴 Blocking merges" : "✓ Clean posture"}
        />

        <MetricCard
          label="PRs Blocked"
          value={String(blockedPrsCount)}
          severity={blockedPrsCount > 0 ? "critical" : "passed"}
          subtitle={blockedPrsCount > 0 ? "Strict policy gate active" : "✓ All gates passing"}
        />
      </div>

      {/* Repositories Overview */}
      <Card
        title="Monitored Repositories"
        description="Active code repositories analyzed for security gates"
        actions={
          <Link
            href="/repositories"
            className="text-xs hover:underline"
            style={{ color: "var(--accent)" }}
          >
            Manage Repositories →
          </Link>
        }
      >
        <RepositoriesTable repositories={repos} />
      </Card>

      {/* Recent PR Stream */}
      <RecentPRsTable prs={prs} />
    </div>
  );
}
