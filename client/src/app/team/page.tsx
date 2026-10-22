"use client";

import React, { useEffect, useState } from "react";
import { TeamMember } from "@/types";
import { fetchTeamMembers } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function TeamPage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"Developer" | "Security Lead" | "Viewer">("Developer");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => { fetchTeamMembers().then(setMembers); }, []);

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail) return;
    const newMember: TeamMember = {
      id: `tm-${Date.now()}`,
      name: inviteEmail.split("@")[0],
      email: inviteEmail,
      role: inviteRole,
      prs_reviewed: 0,
      findings_resolved: 0,
      last_active: "Invited",
    };
    setMembers([...members, newMember]);
    setShowInviteModal(false);
    setInviteEmail("");
    setToastMessage(`Invitation sent to ${inviteEmail} as ${inviteRole}.`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const columns: Column<TeamMember>[] = [
    {
      key: "name",
      header: "Member",
      render: (m) => (
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0" style={{ backgroundColor: "rgba(56, 189, 248, 0.2)", color: "var(--accent)" }}>
            {m.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <span className="font-semibold text-main text-xs block">{m.name}</span>
            <span className="text-[11px] text-muted font-mono">{m.email}</span>
          </div>
        </div>
      ),
    },
    {
      key: "role",
      header: "Role",
      render: (m) => <Badge variant={m.role === "Security Lead" ? "low" : m.role === "Admin" ? "critical" : "passed"}>{m.role}</Badge>,
    },
    {
      key: "prs_reviewed",
      header: "PRs Audited",
      render: (m) => <span className="font-mono text-xs text-main">{m.prs_reviewed}</span>,
    },
    {
      key: "findings_resolved",
      header: "Resolved",
      render: (m) => <span className="font-mono text-xs font-bold" style={{ color: "var(--pass-color)" }}>{m.findings_resolved}</span>,
    },
    {
      key: "last_active",
      header: "Last Active",
      render: (m) => <span className="text-xs text-dim">{m.last_active}</span>,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (m) => (
        <Button variant="ghost" size="sm" onClick={() => alert(`Manage permissions for ${m.name}`)}>
          Edit Role
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y">
      <PageHeader
        title="Team & Access Controls"
        subtitle="Manage organization members, RBAC permissions, and DevSecOps activity."
        badge={<span className="crumb-badge text-xs">Seats: {members.length} / 10</span>}
        actions={<Button variant="primary" size="md" onClick={() => setShowInviteModal(true)}>+ Invite Member</Button>}
      />

      {toastMessage && (
        <div className="p-3 rounded-lg border text-xs flex-between" style={{ backgroundColor: "var(--pass-bg)", borderColor: "var(--pass-border)", color: "var(--pass-color)" }}>
          <span>✓ {toastMessage}</span>
          <button onClick={() => setToastMessage(null)} className="text-muted hover:text-main">✕</button>
        </div>
      )}

      <DataTable columns={columns} data={members} keyExtractor={(m) => m.id} />

      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: "rgba(0, 0, 0, 0.75)" }}>
          <div className="p-6 rounded-xl border max-w-md w-full" style={{ backgroundColor: "var(--bg-surface)", borderColor: "var(--border-subtle)" }}>
            <h2 className="text-base font-bold text-main mb-3">Invite New Team Member</h2>
            <form onSubmit={handleInvite} className="flex flex-col gap-3">
              <div>
                <label className="text-xs text-muted block mb-1">Email Address</label>
                <input type="email" required placeholder="colleague@company.com" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="form-input w-full" />
              </div>
              <div>
                <label className="text-xs text-muted block mb-1">Role &amp; Permissions</label>
                <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as any)} className="form-input w-full">
                  <option value="Developer">Developer (Resolve findings)</option>
                  <option value="Security Lead">Security Lead (Approve policy gates)</option>
                  <option value="Viewer">Viewer (Read-only reports)</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowInviteModal(false)}>Cancel</Button>
                <Button type="submit" variant="primary" size="sm">Send Invitation</Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
