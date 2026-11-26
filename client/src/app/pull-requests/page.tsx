"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { PullRequest } from "@/types";
import { fetchPullRequests, syncGitHubReviews } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { GateBadge, StatusDot } from "@/components/ui/Badge";
import { DataTable, Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";

export default function PullRequestsPage() {
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [filterGate, setFilterGate] = useState<string>("ALL");
  const [repoFilter, setRepoFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  const loadPrs = () =>
    fetchPullRequests()
      .then(setPrs)
      .finally(() => setLoading(false));

  useEffect(() => {
    loadPrs();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setSyncNotice(null);
    const res = await syncGitHubReviews();
    await loadPrs();
    setSyncing(false);
    setSyncNotice(
      res
        ? `Synced ${res.synced} new PR review(s) from GitHub (${res.skipped} already up to date).`
        : "GitHub sync could not complete right now."
    );
    setTimeout(() => setSyncNotice(null), 5000);
  };

  const repos = useMemo(() => Array.from(new Set(prs.map((p) => p.repository))), [prs]);

  const filtered = useMemo(() => {
    return prs.filter((pr) => {
      if (filterGate !== "ALL" && pr.gate_status !== filterGate) return false;
      if (repoFilter !== "ALL" && pr.repository !== repoFilter) return false;
      if (searchQuery && !pr.title.toLowerCase().includes(searchQuery.toLowerCase()) && !String(pr.pr_number).includes(searchQuery)) {
        return false;
      }
      return true;
    });
  }, [prs, filterGate, repoFilter, searchQuery]);

  const columns: Column<PullRequest>[] = [
    {
      key: "title",
      header: "Pull Request",
      render: (pr) => (
        <Link href={`/pull-requests/${pr.id}`} className="hover:underline block" style={{ color: "var(--text-main)" }}>
          <div className="font-medium flex items-center gap-1.5">
            <span className="font-mono text-xs" style={{ color: "var(--accent)" }}>#{pr.pr_number}</span>
            <span>{pr.title}</span>
          </div>
          <div className="text-[11px] font-mono text-dim mt-0.5">
            Commit {pr.commit_sha || "HEAD"} &middot; {pr.scanned_at}
          </div>
        </Link>
      ),
    },
    {
      key: "repository",
      header: "Repository",
      render: (pr) => <span className="font-mono text-xs text-muted">{pr.repository}</span>,
    },
    {
      key: "security_score",
      header: "CVSS / Score",
      render: (pr) => {
        const secScore = Math.max(0, Math.round(100 - pr.security_score * 10));
        const color = pr.security_score >= 7.0 ? "var(--crit-color)" : pr.security_score >= 4.0 ? "var(--med-color)" : "var(--pass-color)";
        return (
          <div className="font-mono text-xs">
            <span className="font-bold" style={{ color }}>{pr.security_score.toFixed(2)}</span>
            <span className="text-[11px] text-dim"> / 10</span>
            <span className="text-[11px] text-muted block">{secScore}/100 pts</span>
          </div>
        );
      },
    },
    {
      key: "findings",
      header: "Findings",
      render: (pr) => (
        <div className="flex items-center gap-2 text-xs font-mono">
          {pr.findings_summary.critical > 0 && <span style={{ color: "var(--crit-color)" }} className="font-bold flex items-center"><StatusDot color="var(--crit-color)" /> {pr.findings_summary.critical}C</span>}
          {pr.findings_summary.high > 0 && <span style={{ color: "var(--high-color)" }} className="font-semibold flex items-center"><StatusDot color="var(--high-color)" /> {pr.findings_summary.high}H</span>}
          {pr.findings_summary.medium > 0 && <span style={{ color: "var(--med-color)" }} className="flex items-center"><StatusDot color="var(--med-color)" /> {pr.findings_summary.medium}M</span>}
          {pr.findings_summary.critical === 0 && pr.findings_summary.high === 0 && pr.findings_summary.medium === 0 && (
            <span style={{ color: "var(--pass-color)" }} className="flex items-center"><StatusDot color="var(--pass-color)" /> Clean</span>
          )}
        </div>
      ),
    },
    {
      key: "gate_status",
      header: "Gate Verdict",
      render: (pr) => <GateBadge status={pr.gate_status} />,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (pr) => {
        const ghUrl = pr.pr_url || (pr.repository.includes("/") ? `https://github.com/${pr.repository}/pull/${pr.pr_number}` : undefined);
        return (
          <div className="flex items-center justify-end gap-2">
            {ghUrl && (
              <a href={ghUrl} target="_blank" rel="noopener noreferrer" className="text-xs hover:underline font-mono" style={{ color: "var(--accent)" }}>
                GitHub ↗
              </a>
            )}
            <Link href={`/pull-requests/${pr.id}`}>
              <Button variant="ghost" size="sm">Audit Details →</Button>
            </Link>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y">
      <PageHeader
        title="Pull Requests"
        subtitle="All CodeSecAudit security reviews synced from GitHub webhooks and repository history."
        actions={
          <Button variant="secondary" size="md" onClick={handleSync} loading={syncing}>
            Sync GitHub PRs
          </Button>
        }
      />
      {syncNotice && (
        <div className="p-3 rounded-lg border text-xs flex-between" style={{ backgroundColor: "var(--bg-surface-elevated)", borderColor: "var(--border-subtle)", color: "var(--text-main)" }}>
          <span>{syncNotice}</span>
          <button onClick={() => setSyncNotice(null)} className="text-muted hover:text-main">✕</button>
        </div>
      )}
      <div className="filter-bar flex-between">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-1">
            {["ALL", "BLOCKED", "WARNING", "PASSED"].map((g) => (
              <Button key={g} variant={filterGate === g ? "primary" : "secondary"} size="sm" onClick={() => setFilterGate(g)}>
                {g}
              </Button>
            ))}
          </div>
          <select value={repoFilter} onChange={(e) => setRepoFilter(e.target.value)} className="form-input">
            <option value="ALL">All Repositories</option>
            {repos.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <input
            type="text"
            placeholder="Search PR title or #number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="form-input"
            style={{ width: "220px" }}
          />
        </div>
        <span className="text-xs text-dim">Showing {filtered.length} pull requests</span>
      </div>
      <DataTable
        columns={columns}
        data={filtered}
        keyExtractor={(pr) => pr.id}
        loading={loading}
        emptyMessage="No pull requests match the selected filters."
      />
    </div>
  );
}
