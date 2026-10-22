"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { PullRequest } from "@/types";
import { fetchPullRequestById } from "@/lib/api";
import { GateBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { SecurityFindingCard } from "@/components/ui/SecurityFindingCard";
import { ArrowLeftIcon, GitHubIcon } from "@/components/ui/Icons";

export default function PRDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const [pr, setPr] = useState<PullRequest | null>(null);

  useEffect(() => {
    if (id) {
      fetchPullRequestById(id).then(setPr);
    }
  }, [id]);

  if (!pr) {
    return (
      <div className="py-16 text-center text-muted text-xs">
        <span className="btn-spinner mr-2" />
        Loading PR Security Audit...
      </div>
    );
  }

  const isBlocked = pr.gate_status === "BLOCKED";

  return (
    <div className="space-y">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-xs">
        <Link
          href="/pull-requests"
          className="text-muted hover:text-main flex items-center gap-1 font-medium"
        >
          <ArrowLeftIcon size={14} />
          <span>Pull Requests</span>
        </Link>
        <span className="text-dim">/</span>
        <span className="crumb-badge">PR #{pr.pr_number}</span>
      </div>

      {/* Header */}
      <div className="flex-between items-start gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3 mb-1.5">
            <span className="font-mono text-xl font-bold" style={{ color: "var(--accent)" }}>
              #{pr.pr_number}
            </span>
            <h1 className="page-title mb-0">{pr.title}</h1>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted flex-wrap">
            <span className="crumb-badge">{pr.repository}</span>
            <span>
              Author: <strong className="text-main">{pr.author}</strong>
            </span>
            <span>
              Commit: <code className="text-main font-mono">{pr.commit_sha || "HEAD"}</code>
            </span>
            <span>Audited: {pr.scanned_at}</span>
          </div>
        </div>

        <a
          href={`https://github.com/example/${pr.repository}/pull/${pr.pr_number}`}
          target="_blank"
          rel="noreferrer"
        >
          <Button variant="secondary" size="md" icon={<GitHubIcon size={16} />}>
            Open in GitHub ↗
          </Button>
        </a>
      </div>

      {/* 3 Metric Cards */}
      <div className="stat-grid">
        <div className="metric-card">
          <span className="metric-card-label">Security Gate Verdict</span>
          <div className="mt-1">
            <GateBadge status={pr.gate_status} />
          </div>
          <span className="metric-card-trend text-dim">
            {isBlocked
              ? "Merge blocked in GitHub branch checks."
              : "All security criteria satisfied."}
          </span>
        </div>

        <MetricCard
          label="Security Score"
          value={pr.security_score}
          suffix="/ 100"
          severity={
            pr.security_score >= 85
              ? "passed"
              : pr.security_score >= 70
              ? "medium"
              : "critical"
          }
          subtitle="Based on severity weights"
        />

        <div className="metric-card">
          <span className="metric-card-label">Findings Summary</span>
          <div className="flex items-center gap-2 text-xs font-mono mt-1">
            <span style={{ color: "var(--crit-color)" }} className="font-bold">
              🔴 {pr.findings_summary.critical} Crit
            </span>
            <span style={{ color: "var(--high-color)" }} className="font-bold">
              🟠 {pr.findings_summary.high} High
            </span>
            <span style={{ color: "var(--med-color)" }} className="font-bold">
              🟡 {pr.findings_summary.medium} Med
            </span>
          </div>
          <span className="metric-card-trend text-dim">
            Total {pr.findings.length} detected security items
          </span>
        </div>
      </div>

      {/* Gate Reason Callout: Always clear why PR was blocked */}
      <div
        className="p-4 rounded-lg border text-xs"
        style={{
          backgroundColor: isBlocked
            ? "var(--crit-bg)"
            : "var(--pass-bg)",
          borderColor: isBlocked
            ? "var(--crit-border)"
            : "var(--pass-border)",
        }}
      >
        <span className="font-bold uppercase tracking-wider block mb-1 text-main">
          Security Gate Evaluation
        </span>
        <p className="text-muted leading-relaxed">
          <strong className="text-main">Reason:</strong>{" "}
          {pr.gate_reason || "Evaluated by CodeSecAudit CI webhook policy."}
        </p>
      </div>

      {/* Findings List */}
      <div>
        <h2 className="text-sm font-bold text-main mb-3">
          Vulnerabilities in this PR ({pr.findings.length})
        </h2>
        {pr.findings.length === 0 ? (
          <Card>
            <div className="py-8 text-center text-xs" style={{ color: "var(--pass-color)" }}>
              ✓ Zero security vulnerabilities detected in modified lines.
            </div>
          </Card>
        ) : (
          <div className="flex flex-col gap-3">
            {pr.findings.map((f) => (
              <SecurityFindingCard key={f.id} finding={f} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
