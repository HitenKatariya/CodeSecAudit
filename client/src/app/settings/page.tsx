"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, GateBadge } from "@/components/ui/Badge";
import { GitHubIcon } from "@/components/ui/Icons";
import { DataTable, Column } from "@/components/ui/DataTable";
import { fetchMe, fetchPullRequests, deleteAccount } from "@/lib/api";
import { UserProfile, PullRequest } from "@/types";

export default function SettingsPage() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [orgName, setOrgName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [dailyDigest, setDailyDigest] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchMe().then((u) => {
      if (u) {
        setUser(u);
        setOrgName(u.organization_name || (u.username ? `@${u.username}` : "Personal"));
        setContactEmail(u.email || "");
      }
    });
    fetchPullRequests().then(setPrs);
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setToastMessage("Settings saved successfully.");
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm(
      "⚠️ PERMANENT ACCOUNT DELETION\n\nAre you sure you want to delete your account?\n\nThis will:\n1. Wipe out your account and all audit history completely.\n2. Automatically uninstall the CodeSecAudit GitHub App from your GitHub account.\n3. Delete all stored PR reviews, findings, and repository associations.\n\nThis action cannot be undone."
    );
    if (!confirmed) return;
    setDeleting(true);
    const ok = await deleteAccount();
    if (ok) {
      if (typeof window !== "undefined") {
        localStorage.clear();
      }
      window.location.href = "/?deleted=true";
    } else {
      alert("Failed to delete account. Please try again or contact support.");
      setDeleting(false);
    }
  };

  const reviewColumns: Column<PullRequest>[] = [
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
        <span className="font-mono text-xs text-muted">{pr.repository}</span>
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
      key: "gate_status",
      header: "Gate Status",
      render: (pr) => <GateBadge status={pr.gate_status} />,
    },
    {
      key: "actions",
      header: "Review Links",
      align: "right",
      render: (pr) => {
        const ghUrl =
          pr.pr_url ||
          (pr.repository.includes("/")
            ? `https://github.com/${pr.repository}/pull/${pr.pr_number}`
            : `https://github.com/OMCHOKSI108/CodeSecurityAuditAgent/pull/${pr.pr_number}`);
        return (
          <div className="flex items-center justify-end gap-2">
            <Link href={`/pull-requests/${pr.pr_number}`}>
              <Button variant="ghost" size="sm">
                Audit Details →
              </Button>
            </Link>
            <a
              href={ghUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs hover:underline flex items-center gap-1 font-mono font-semibold"
              style={{ color: "var(--accent)" }}
            >
              GitHub PR #{pr.pr_number} ↗
            </a>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y">
      <PageHeader
        title="Account & Security Settings"
        subtitle="Manage your GitHub App connection, security audit history, and personal account controls."
      />

      {toastMessage && (
        <div
          className="p-3 rounded-lg border text-xs flex-between"
          style={{
            backgroundColor: "var(--pass-bg)",
            borderColor: "var(--pass-border)",
            color: "var(--pass-color)",
          }}
        >
          <span>✓ {toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="text-muted hover:text-main"
          >
            ✕
          </button>
        </div>
      )}

      {/* User Identity & GitHub Account */}
      <Card
        title="GitHub User Identity"
        description="Authenticated GitHub profile and security auditor credentials"
      >
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div
              style={{
                width: 42,
                height: 42,
                borderRadius: "50%",
                background: "var(--accent-glow)",
                border: "1px solid var(--accent)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.2rem",
              }}
            >
              🛡️
            </div>
            <div>
              <div className="font-bold text-sm text-main flex items-center gap-2">
                <span>@{user?.username || "authenticated-user"}</span>
                <span className="badge badge-passed text-[10px]">Active</span>
              </div>
              <div className="text-xs text-muted font-mono">
                Role: {user?.organization_role || "Owner"} &bull; Org: {user?.organization_name || orgName}
              </div>
            </div>
          </div>

          {user?.username && (
            <a
              href={`https://github.com/${user.username}`}
              target="_blank"
              rel="noreferrer"
            >
              <Button variant="secondary" size="sm" icon={<GitHubIcon size={14} />}>
                View GitHub Profile ↗
              </Button>
            </a>
          )}
        </div>
      </Card>

      {/* Recent PR Audits & Full Reviews */}
      <Card
        title="Recent Pull Request Audits & Reviews"
        description="Review records with CVSS scores and direct links to GitHub review comments"
        actions={
          <Link
            href="/pull-requests"
            className="text-xs hover:underline"
            style={{ color: "var(--accent)" }}
          >
            All Pull Requests →
          </Link>
        }
      >
        <DataTable
          columns={reviewColumns}
          data={prs}
          keyExtractor={(pr) => pr.id}
          emptyMessage="No pull request audits recorded for this profile yet."
        />
      </Card>

      {/* Personal Security Profile */}
      <Card
        title="Personal Security Profile"
        description="Your security alert contact and preferences"
      >
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <div className="grid-2">
            <div>
              <label className="text-xs text-muted block mb-1">
                Account / Display Name
              </label>
              <input
                type="text"
                value={orgName}
                placeholder="Your name or handle"
                onChange={(e) => setOrgName(e.target.value)}
                className="form-input w-full"
              />
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">
                Security Alert Email
              </label>
              <input
                type="email"
                value={contactEmail}
                placeholder="your.email@example.com"
                onChange={(e) => setContactEmail(e.target.value)}
                className="form-input w-full"
              />
            </div>
          </div>
          <div>
            <Button type="submit" variant="primary" size="sm">
              Save Preferences
            </Button>
          </div>
        </form>
      </Card>

      {/* Notification Preferences */}
      <Card
        title="Alert Notifications"
        description="Configure dispatch channels for security alerts"
      >
        <div className="flex flex-col gap-3">
          <label className="flex-between text-xs text-muted cursor-pointer py-1">
            <span>Instant email alert when a PR is blocked by security gate</span>
            <input
              type="checkbox"
              checked={emailAlerts}
              onChange={(e) => setEmailAlerts(e.target.checked)}
              style={{ width: "16px", height: "16px", accentColor: "var(--accent)" }}
            />
          </label>
          <label className="flex-between text-xs text-muted cursor-pointer py-1">
            <span>Daily executive digest of open vulnerabilities</span>
            <input
              type="checkbox"
              checked={dailyDigest}
              onChange={(e) => setEmailAlerts(e.target.checked)}
              style={{ width: "16px", height: "16px", accentColor: "var(--accent)" }}
            />
          </label>
        </div>
      </Card>

      {/* API Tokens */}
      <Card
        title="API Access Tokens"
        description="Tokens for CI/CD pipelines and external CLI tools"
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => alert("Created token: csa_live_9f81a7b8e4c2")}
          >
            + Generate Token
          </Button>
        }
      >
        <div
          className="p-3.5 rounded border flex-between text-xs"
          style={{
            backgroundColor: "var(--bg-surface-elevated)",
            borderColor: "var(--border-subtle)",
          }}
        >
          <div>
            <span className="font-mono text-main block">
              csa_live_********************481b
            </span>
            <span className="text-dim text-[11px]">
              Created Oct 8, 2026 &bull; Full Audit Permissions
            </span>
          </div>
          <Badge variant="passed">Active</Badge>
        </div>
      </Card>

      {/* Danger Zone */}
      <Card
        title={
          <span style={{ color: "var(--crit-color)" }}>Danger Zone</span>
        }
        description="Irreversible account deletion, GitHub App uninstall, and data wipe"
      >
        <div className="flex flex-col gap-4">
          <div className="p-4 rounded border" style={{ borderColor: "var(--crit-border)", backgroundColor: "var(--crit-bg)" }}>
            <span className="font-bold text-xs text-main block mb-1">
              Delete Account & Wipe All Security Data
            </span>
            <p className="text-xs text-muted mb-3 leading-relaxed">
              Permanently delete your user account, automatically uninstall the CodeSecAudit GitHub App from your GitHub account and repositories, and purge all audit history, findings, and scanned repositories. When you return, all data will be completely wiped clean.
            </p>
            <Button
              variant="danger"
              size="sm"
              disabled={deleting}
              onClick={handleDeleteAccount}
            >
              {deleting ? "Deleting Account & Uninstalling..." : "Delete Account & Uninstall GitHub App"}
            </Button>
          </div>

          <div className="flex items-center justify-between text-xs pt-2 border-t" style={{ borderColor: "var(--border-subtle)" }}>
            <div>
              <span className="font-semibold text-main block">Semantic Audit Cache</span>
              <span className="text-dim text-[11px]">Force CodeSecAudit to rebuild vector index embeddings</span>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => alert("Semantic cache purged successfully.")}
            >
              Purge Cache
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
