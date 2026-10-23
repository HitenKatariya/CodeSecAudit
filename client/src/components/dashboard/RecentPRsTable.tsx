"use client";

import React from "react";
import Link from "next/link";
import { PullRequest } from "@/types";
import { Card } from "@/components/ui/Card";
import { DataTable, Column } from "@/components/ui/DataTable";
import { GateBadge } from "@/components/ui/Badge";

export function RecentPRsTable({ prs }: { prs: PullRequest[] }) {
  const columns: Column<PullRequest>[] = [
    {
      key: "title",
      header: "Pull Request",
      render: (pr) => (
        <Link
          href={`/pull-requests/${pr.pr_number}`}
          className="font-medium hover:underline flex items-center gap-1.5"
          style={{ color: "var(--text-main)" }}
        >
          <span className="font-mono text-xs" style={{ color: "var(--accent)" }}>
            #{pr.pr_number}
          </span>
          <span>{pr.title}</span>
        </Link>
      ),
    },
    {
      key: "repository",
      header: "Repository",
      render: (pr) => (
        <span className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>
          {pr.repository}
        </span>
      ),
    },
    {
      key: "author",
      header: "Author",
      render: (pr) => (
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {pr.author}
        </span>
      ),
    },
    {
      key: "security_score",
      header: "CVSS Risk",
      render: (pr) => (
        <span
          className="font-mono font-bold text-xs"
          style={{
            color:
              pr.security_score >= 7.0
                ? "var(--crit-color)"
                : pr.security_score >= 4.0
                ? "var(--med-color)"
                : "var(--pass-color)",
          }}
        >
          {pr.security_score.toFixed(2)} / 10.0
        </span>
      ),
    },
    {
      key: "findings",
      header: "Findings",
      render: (pr) => (
        <div className="flex items-center gap-2 text-xs font-mono">
          {pr.findings_summary.critical > 0 && (
            <span style={{ color: "var(--crit-color)" }} className="font-bold">
              🔴 {pr.findings_summary.critical} Crit
            </span>
          )}
          {pr.findings_summary.high > 0 && (
            <span style={{ color: "var(--high-color)" }} className="font-semibold">
              🟠 {pr.findings_summary.high} High
            </span>
          )}
          {pr.findings_summary.critical === 0 && pr.findings_summary.high === 0 && (
            <span style={{ color: "var(--pass-color)" }}>🟢 Clean</span>
          )}
        </div>
      ),
    },
    {
      key: "gate_status",
      header: "Gate Status",
      render: (pr) => <GateBadge status={pr.gate_status} />,
    },
    {
      key: "scanned_at",
      header: "Audited",
      render: (pr) => (
        <span className="text-xs" style={{ color: "var(--text-dim)" }}>
          {pr.scanned_at}
        </span>
      ),
    },
    {
      key: "github_link",
      header: "GitHub",
      align: "right",
      render: (pr) => {
        const ghUrl =
          pr.pr_url ||
          (pr.repository.includes("/")
            ? `https://github.com/${pr.repository}/pull/${pr.pr_number}`
            : undefined);
        return ghUrl ? (
          <a
            href={ghUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs hover:underline flex items-center gap-1 font-mono"
            style={{ color: "var(--accent)" }}
          >
            PR #{pr.pr_number} ↗
          </a>
        ) : null;
      },
    },
  ];

  return (
    <Card
      title="Recent Pull Request Audits"
      description="Automated gate verdicts for incoming pull requests"
      actions={
        <Link
          href="/pull-requests"
          className="text-xs hover:underline"
          style={{ color: "var(--accent)" }}
        >
          View all PRs →
        </Link>
      }
    >
      <DataTable
        columns={columns}
        data={prs}
        keyExtractor={(pr) => pr.id}
        emptyMessage="No pull request audits recorded yet."
      />
    </Card>
  );
}
