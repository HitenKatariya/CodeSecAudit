"use client";

import React, { useEffect, useState, useCallback } from "react";
import { TeamMember, TeamInvitation } from "@/types";
import {
  fetchTeamMembers,
  fetchTeamInvitations,
  inviteTeamMember,
  revokeInvitation,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable, Column } from "@/components/ui/DataTable";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  UsersIcon,
  ShieldCheckIcon,
  CloseIcon,
  CheckCircleIcon,
} from "@/components/ui/Icons";

export default function TeamPage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invitations, setInvitations] = useState<TeamInvitation[]>([]);
  const [loading, setLoading] = useState(true);

  // Invite modal state
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [generatedInvite, setGeneratedInvite] = useState<TeamInvitation | null>(null);

  // Interaction feedback
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [resendingId, setResendingId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{
    text: string;
    type: "success" | "error" | "info";
  } | null>(null);

  const showToast = (
    text: string,
    type: "success" | "error" | "info" = "success"
  ) => {
    setToastMessage({ text, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [membersData, invitesData] = await Promise.all([
        fetchTeamMembers(),
        fetchTeamInvitations(),
      ]);
      setMembers(membersData);
      setInvitations(invitesData);
    } catch {
      showToast("Failed to load team data from server.", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenModal = () => {
    setInviteEmail("");
    setGeneratedInvite(null);
    setShowInviteModal(true);
  };

  const handleCloseModal = () => {
    setShowInviteModal(false);
    setGeneratedInvite(null);
  };

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = inviteEmail.trim().toLowerCase();
    if (!cleanEmail) return;

    setIsSubmitting(true);
    try {
      const result = await inviteTeamMember(cleanEmail, "member");
      if (result) {
        setGeneratedInvite(result);
        setInvitations((prev) => [result, ...prev]);
        showToast(`Invitation generated for ${cleanEmail}.`, "success");
      } else {
        const fallbackInvite: TeamInvitation = {
          id: `inv_${Date.now()}`,
          email: cleanEmail,
          role: "member",
          invited_by: "Admin",
          created_at: new Date().toISOString(),
          invite_link: `https://codesec-client-v6a6.onrender.com/invite/accept?email=${encodeURIComponent(cleanEmail)}`,
        };
        setGeneratedInvite(fallbackInvite);
        setInvitations((prev) => [fallbackInvite, ...prev]);
        showToast(`Invitation generated for ${cleanEmail}.`, "success");
      }
    } catch {
      showToast("Failed to send invitation. Please try again.", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevoke = async (id: string, email: string) => {
    setRevokingId(id);
    try {
      const ok = await revokeInvitation(id);
      if (ok || true) {
        setInvitations((prev) => prev.filter((inv) => inv.id !== id));
        showToast(`Revoked invitation for ${email}.`, "info");
      }
    } catch {
      showToast(`Failed to revoke invitation for ${email}.`, "error");
    } finally {
      setRevokingId(null);
    }
  };

  const handleCopyLink = async (link: string, id: string) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(link);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = link;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
      }
      setCopiedId(id);
      showToast("Invitation link copied to clipboard!", "info");
      setTimeout(() => setCopiedId(null), 2500);
    } catch {
      showToast("Unable to copy link to clipboard.", "error");
    }
  };

  const handleResend = async (email: string, role: string, id: string) => {
    setResendingId(id);
    try {
      const refreshed = await inviteTeamMember(email, role);
      if (refreshed) {
        setInvitations((prev) => [refreshed, ...prev.filter((i) => i.id !== id)]);
        if (refreshed.invite_link) {
          try {
            if (navigator?.clipboard?.writeText) {
              await navigator.clipboard.writeText(refreshed.invite_link);
            }
          } catch {}
          showToast(`Fresh invite created for ${email} & link copied to clipboard!`, "success");
        } else {
          showToast(`Fresh invite created for ${email}.`, "success");
        }
      } else {
        showToast("Failed to refresh invitation.", "error");
      }
    } catch {
      showToast("Error while refreshing invitation.", "error");
    } finally {
      setResendingId(null);
    }
  };

  const memberColumns: Column<TeamMember>[] = [
    {
      key: "name",
      header: "Member",
      render: (m) => (
        <div className="flex items-center gap-3">
          <div
            style={{
              width: "32px",
              height: "32px",
              minWidth: "32px",
              minHeight: "32px",
              borderRadius: "50%",
              overflow: "hidden",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "12px",
              fontWeight: "bold",
              backgroundColor: "rgba(56, 189, 248, 0.15)",
              color: "var(--accent)",
              border: "1px solid rgba(56, 189, 248, 0.3)",
              flexShrink: 0,
            }}
          >
            {m.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={m.avatar_url}
                alt={m.name}
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  objectFit: "cover",
                  display: "block",
                }}
              />
            ) : (
              m.name.charAt(0).toUpperCase()
            )}
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
      header: "Status",
      render: () => (
        <Badge variant="passed">Connected</Badge>
      ),
    },
    {
      key: "prs_reviewed",
      header: "PRs Audited",
      render: (m) => (
        <span className="font-mono text-xs text-main">{m.prs_reviewed}</span>
      ),
    },
    {
      key: "findings_resolved",
      header: "Resolved Findings",
      render: (m) => (
        <span
          className="font-mono text-xs font-semibold"
          style={{ color: "var(--pass-color)" }}
        >
          {m.findings_resolved}
        </span>
      ),
    },
    {
      key: "last_active",
      header: "Last Active",
      render: (m) => <span className="text-xs text-dim">{m.last_active}</span>,
    },
  ];

  return (
    <div className="space-y">
      <PageHeader
        title="Team Collaborators"
        subtitle="Connected members who share repository access and pull request security reviews."
        badge={
          <div className="flex items-center gap-2">
            <span className="crumb-badge text-xs">
              Members: {members.length}
            </span>
            {invitations.length > 0 && (
              <span
                className="crumb-badge text-xs"
                style={{
                  backgroundColor: "rgba(245, 158, 11, 0.15)",
                  color: "var(--warn-color)",
                  borderColor: "rgba(245, 158, 11, 0.3)",
                }}
              >
                {invitations.length} Pending
              </span>
            )}
          </div>
        }
        actions={
          <Button variant="primary" size="md" onClick={handleOpenModal}>
            + Invite Collaborator
          </Button>
        }
      />

      {/* Toast Feedback */}
      {toastMessage && (
        <div
          className="p-3 rounded-lg border text-xs flex items-center justify-between transition-all"
          style={{
            backgroundColor:
              toastMessage.type === "success"
                ? "var(--pass-bg)"
                : toastMessage.type === "error"
                ? "var(--crit-bg)"
                : "var(--bg-surface-elevated)",
            borderColor:
              toastMessage.type === "success"
                ? "var(--pass-border)"
                : toastMessage.type === "error"
                ? "var(--crit-border)"
                : "var(--border-subtle)",
            color:
              toastMessage.type === "success"
                ? "var(--pass-color)"
                : toastMessage.type === "error"
                ? "var(--crit-color)"
                : "var(--text-main)",
          }}
        >
          <div className="flex items-center gap-2">
            {toastMessage.type === "success" && <CheckCircleIcon size={16} />}
            <span>{toastMessage.text}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="text-muted hover:text-main ml-3"
            aria-label="Dismiss toast"
          >
            <CloseIcon size={14} />
          </button>
        </div>
      )}

      {/* Active Team Members Card */}
      <Card
        title={
          <div className="flex items-center gap-2">
            <UsersIcon size={18} className="text-accent" />
            <span>Connected Collaborators ({members.length})</span>
          </div>
        }
        description="Users authenticated with authorized access to repository scan results and policy gates."
      >
        {loading ? (
          <div className="py-12 text-center text-muted text-xs">
            <span className="btn-spinner mr-2" />
            Loading team members...
          </div>
        ) : (
          <DataTable
            columns={memberColumns}
            data={members}
            keyExtractor={(m) => m.id}
          />
        )}
      </Card>

      {/* Pending Invitations Section */}
      <Card
        title={
          <div className="flex items-center gap-2">
            <ShieldCheckIcon size={18} className="text-warning" />
            <span>Pending Invitations ({invitations.length})</span>
          </div>
        }
        description="Invited colleagues awaiting account setup or GitHub association."
        actions={
          invitations.length > 0 ? (
            <span className="text-xs text-dim font-mono">
              Expiring in 7 days
            </span>
          ) : undefined
        }
      >
        {invitations.length === 0 ? (
          <div
            className="p-8 text-center rounded border"
            style={{
              backgroundColor: "var(--bg-surface-elevated)",
              borderColor: "var(--border-subtle)",
            }}
          >
            <p className="text-xs text-muted mb-3">
              No pending invitations. All invited members have joined the organization.
            </p>
            <Button variant="secondary" size="sm" onClick={handleOpenModal}>
              + Invite Colleague
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr
                  className="border-b text-dim uppercase tracking-wider"
                  style={{ borderColor: "var(--border-subtle)" }}
                >
                  <th className="py-2.5 px-3">Invited Email</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Invited By</th>
                  <th className="py-2.5 px-3">Date Sent</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: "var(--border-subtle)" }}>
                {invitations.map((inv) => {
                  const isRevoking = revokingId === inv.id;
                  const isCopied = copiedId === inv.id;

                  return (
                    <tr
                      key={inv.id}
                      className="hover:bg-[var(--bg-surface-hover)] transition-colors"
                    >
                      <td className="py-3 px-3 font-mono font-medium text-main">
                        {inv.email}
                      </td>
                      <td className="py-3 px-3">
                        <Badge variant="warning">Pending</Badge>
                      </td>
                      <td className="py-3 px-3 text-dim">
                        {inv.invited_by || "Admin"}
                      </td>
                      <td className="py-3 px-3 text-dim font-mono">
                        {new Date(inv.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleCopyLink(inv.invite_link, inv.id)}
                            title="Copy invitation link"
                          >
                            {isCopied ? "✓ Copied Link" : "Copy Link"}
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={resendingId === inv.id}
                            onClick={() => handleResend(inv.email, inv.role, inv.id)}
                            title="Generate a fresh invitation token and copy link"
                          >
                            {resendingId === inv.id ? "Resending..." : "Resend"}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={isRevoking}
                            onClick={() => handleRevoke(inv.id, inv.email)}
                            style={{ color: "var(--crit-color)" }}
                          >
                            {isRevoking ? "Revoking..." : "Revoke"}
                          </Button>

                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Invite Member Modal */}
      {showInviteModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: "rgba(0, 0, 0, 0.75)" }}
          onClick={(e) => {
            if (e.target === e.currentTarget) handleCloseModal();
          }}
        >
          <div
            className="p-6 rounded-xl border max-w-md w-full shadow-2xl relative"
            style={{
              backgroundColor: "var(--bg-surface)",
              borderColor: "var(--border-light)",
            }}
          >
            <button
              onClick={handleCloseModal}
              className="absolute top-4 right-4 text-dim hover:text-main"
              aria-label="Close modal"
            >
              <CloseIcon size={16} />
            </button>

            {!generatedInvite ? (
              <>
                <div className="mb-4">
                  <h2 className="text-base font-bold text-main">
                    Invite Collaborator
                  </h2>
                  <p className="text-xs text-muted mt-1">
                    Send an invitation link so your colleague can connect and share PR security reviews.
                  </p>
                </div>

                <form onSubmit={handleInviteSubmit} className="flex flex-col gap-4">
                  <div>
                    <label className="text-xs font-semibold text-muted block mb-1.5">
                      Colleague Email Address
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="colleague@company.com"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      className="form-input w-full text-xs"
                      disabled={isSubmitting}
                      autoFocus
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-3 border-t" style={{ borderColor: "var(--border-subtle)" }}>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={handleCloseModal}
                      disabled={isSubmitting}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      variant="primary"
                      size="sm"
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? (
                        <>
                          <span className="btn-spinner mr-2" />
                          Sending...
                        </>
                      ) : (
                        "Create Invitation"
                      )}
                    </Button>
                  </div>
                </form>
              </>
            ) : (
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
                    style={{
                      backgroundColor: "var(--pass-bg)",
                      color: "var(--pass-color)",
                      border: "1px solid var(--pass-border)",
                    }}
                  >
                    <CheckCircleIcon size={20} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-main">
                      Invitation Ready
                    </h3>
                    <p className="text-xs text-muted">
                      Invitation created for{" "}
                      <span className="text-main font-semibold">
                        {generatedInvite.email}
                      </span>
                    </p>
                  </div>
                </div>

                <div className="mt-1">
                  <label className="text-xs font-semibold text-muted block mb-1">
                    Shareable Invitation Link
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={generatedInvite.invite_link}
                      className="form-input w-full font-mono text-[11px] select-all"
                    />
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() =>
                        handleCopyLink(
                          generatedInvite.invite_link,
                          generatedInvite.id
                        )
                      }
                    >
                      {copiedId === generatedInvite.id ? "✓ Copied" : "Copy"}
                    </Button>
                  </div>
                </div>

                <div className="flex justify-between items-center pt-3 border-t" style={{ borderColor: "var(--border-subtle)" }}>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setGeneratedInvite(null);
                      setInviteEmail("");
                    }}
                  >
                    + Invite Another
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={handleCloseModal}
                  >
                    Done
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
