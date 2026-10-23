"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Repository, PullRequest, Finding } from "@/types";
import { fetchRepositoryById, fetchPullRequests, fetchFindings } from "@/lib/api";
import { ArrowLeftIcon, RepoIcon, ShieldCheckIcon, GitHubIcon } from "@/components/ui/Icons";
import { GateBadge } from "@/components/ui/Badge";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card } from "@/components/ui/Card";
import { DataTable, Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { SecurityFindingCard } from "@/components/ui/SecurityFindingCard";

export default function RepositoryDetailPage() {
  const params = useParams();
  const repoName = typeof params?.id === "string" ? params.id : "payment-api";
  const [repo, setRepo] = useState<Repository | null>(null);
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);

  useEffect(() => {
    fetchRepositoryById(repoName).then((data) => { if (data) setRepo(data); });
    fetchPullRequests().then((d) => setPrs(d.filter((p) => p.repository === repoName)));
    fetchFindings().then((d) => setFindings(d.filter((f) => f.repository === repoName)));
  }, [repoName]);

  if (!repo) {
    return (
      <div className="py-16 text-center text-muted text-xs">
        <span className="btn-spinner mr-2" />Loading repository details...
      </div>
    );
  }

  const prColumns: Column<PullRequest>[] = [
    {
      key: "title",
      header: "Pull Request",
      render: (p) => (
        <Link href={`/pull-requests/${p.pr_number}`} className="font-medium hover:underline flex items-center gap-1.5" style={{ color: "var(--text-main)" }}>
          <span className="font-mono text-xs" style={{ color: "var(--accent)" }}>#{p.pr_number}</span>
          <span>{p.title}</span>
        </Link>
      ),
    },
    {
      key: "author",
      header: "Author",
      render: (p) => <span className="text-xs text-muted">{p.author}</span>,
    },
    {
      key: "security_score",
      header: "Score",
      render: (p) => (
        <span className="font-mono font-bold text-xs" style={{ color: p.security_score >= 85 ? "var(--pass-color)" : "var(--crit-color)" }}>
          {p.security_score}/100
        </span>
      ),
    },
    {
      key: "gate_status",
      header: "Gate Verdict",
      render: (p) => <GateBadge status={p.gate_status} />,
    },
    {
      key: "scanned_at",
      header: "Audited",
      render: (p) => <span className="text-xs text-dim">{p.scanned_at}</span>,
    },
  ];

  return (
    <div className="space-y">
      <div className="flex items-center gap-2 text-xs">
        <Link href="/repositories" className="text-muted hover:text-main flex items-center gap-1 font-medium">
          <ArrowLeftIcon size={14} /><span>Repositories</span>
        </Link>
        <span className="text-dim">/</span>
        <span className="crumb-badge font-mono">{repo.name}</span>
      </div>

      <div className="flex-between items-start gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center border" style={{ backgroundColor: "var(--bg-surface-elevated)", borderColor: "var(--border-subtle)", color: "var(--accent)" }}>
            <RepoIcon size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="page-title mb-0">{repo.name}</h1>
              <span className="crumb-badge text-xs">{repo.language}</span>
            </div>
            <p className="text-xs text-muted mt-0.5">
              Branch: <code className="text-main font-mono">main</code> &bull; Webhook: <span style={{ color: "var(--pass-color)" }}>Active</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="badge badge-passed"><ShieldCheckIcon size={14} className="mr-1" />Branch Protection Active</span>
          <a href={`https://github.com/${repo.name}`} target="_blank" rel="noreferrer">
            <Button variant="secondary" size="sm" icon={<GitHubIcon size={14} />}>Open in GitHub ↗</Button>
          </a>
        </div>
      </div>

      <div className="stat-grid">
        <MetricCard label="Security Score" value={repo.security_score} suffix="/ 100" severity={repo.security_score >= 85 ? "passed" : "medium"} subtitle="Continuous gate posture" />
        <MetricCard label="PRs Audited" value={repo.pr_count ?? prs.length} subtitle="Live repository pull requests" />
        <MetricCard label="Open Vulnerabilities" value={repo.open_findings_count} severity={repo.open_findings_count > 0 ? "critical" : "passed"} subtitle="Require developer fix" />
        <MetricCard
          label="Resolved Findings"
          value={findings.filter((f) => f.status === "resolved").length}
          severity="passed"
          subtitle="Fixed security issues"
        />
      </div>

      <Card title="Pull Request Audit History" description="Automated security assessments for incoming code branches">
        <DataTable columns={prColumns} data={prs} keyExtractor={(p) => p.id} emptyMessage="No PR audits recorded for this repository." />
      </Card>

      {findings.length > 0 && (
        <div>
          <h2 className="text-sm font-bold text-main mb-3">Active Repository Vulnerabilities ({findings.length})</h2>
          <div className="flex flex-col gap-3">
            {findings.map((f) => <SecurityFindingCard key={f.id} finding={f} />)}
          </div>
        </div>
      )}
    </div>
  );
}
