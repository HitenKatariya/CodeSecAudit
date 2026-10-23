"use client";

import React, { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

import { fetchMe } from "@/lib/api";

export default function SettingsPage() {
  const [orgName, setOrgName] = useState("Acme Engineering");
  const [contactEmail, setContactEmail] = useState("security@acme.corp");
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [dailyDigest, setDailyDigest] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  React.useEffect(() => {
    fetchMe().then((user) => {
      if (user?.organization_name) setOrgName(user.organization_name);
      if (user?.email) setContactEmail(user.email);
    });
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setToastMessage("Settings saved successfully.");
    setTimeout(() => setToastMessage(null), 3000);
  };

  return (
    <div className="space-y">
      <PageHeader
        title="Organization Settings"
        subtitle="Manage your workspace configuration, security keys, and alerts."
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

      {/* Workspace Profile */}
      <Card
        title="Workspace Profile"
        description="Core organization identifiers for automated security audits"
      >
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <div className="grid-2">
            <div>
              <label className="text-xs text-muted block mb-1">
                Organization Name
              </label>
              <input
                type="text"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="form-input w-full"
              />
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">
                Security Contact Email
              </label>
              <input
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                className="form-input w-full"
              />
            </div>
          </div>
          <div>
            <Button type="submit" variant="primary" size="sm">
              Save Profile
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
        description="Irreversible maintenance and cache actions"
      >
        <p className="text-xs text-muted mb-3 leading-relaxed">
          Flushing the audit cache will force CodeSecAudit to perform full semantic re-indexing on all repositories.
        </p>
        <Button
          variant="danger"
          size="sm"
          onClick={() => alert("Cache purged successfully.")}
        >
          Purge Semantic Audit Cache
        </Button>
      </Card>
    </div>
  );
}
