"use client";

import React, { useEffect, useState } from "react";
import { SecurityPolicy, PullRequest } from "@/types";
import { fetchSecurityPolicy, saveSecurityPolicy, fetchPullRequests } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { PolicyForm } from "@/components/policies/PolicyForm";
import { ShieldCheckIcon } from "@/components/ui/Icons";

export default function PoliciesPage() {
  const [policy, setPolicy] = useState<SecurityPolicy | null>(null);
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ ok: boolean; msg: string } | null>(null);

  useEffect(() => {
    fetchSecurityPolicy().then((p) =>
      setPolicy({ ...p, warn_security_score: p.warn_security_score ?? Math.min(100, p.min_security_score + 10) })
    );
    fetchPullRequests().then(setPrs);
  }, []);

  const handleSave = async () => {
    if (!policy) return;
    setSaving(true);
    const ok = await saveSecurityPolicy(policy);
    if (ok) {
      const refreshed = await fetchPullRequests();
      setPrs(refreshed);
      setToast({
        ok: true,
        msg: `Policy saved (${policy.min_security_score}/100 block gate) and synchronized across ${refreshed.length} PR(s).`,
      });
    } else {
      setToast({ ok: false, msg: "Failed to save policy. Please ensure you are signed in and try again." });
    }
    setSaving(false);
    setTimeout(() => setToast(null), 5000);
  };

  if (!policy) {
    return (
      <div className="py-16 text-center text-muted text-xs">
        <span className="btn-spinner mr-2" />
        Loading policy rules...
      </div>
    );
  }

  return (
    <div className="space-y">
      <PageHeader
        title="Security Policies"
        subtitle="Define dynamic score threshold bars and automated blocking criteria for CI/CD Pull Request gates."
      />

      {toast && (
        <div
          className="p-3 rounded-lg border text-xs flex-between"
          style={{
            backgroundColor: toast.ok ? "var(--pass-bg)" : "var(--crit-bg)",
            borderColor: toast.ok ? "var(--pass-border)" : "var(--crit-border)",
            color: toast.ok ? "var(--pass-color)" : "var(--crit-color)",
          }}
        >
          <span>{toast.ok ? "✓" : "!"} {toast.msg}</span>
          <button onClick={() => setToast(null)} className="btn-dismiss" aria-label="Dismiss notification">✕</button>
        </div>
      )}

      <div
        className="p-4 rounded-xl border flex items-center justify-between"
        style={{ backgroundColor: "var(--bg-surface)", borderColor: "var(--border-subtle)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            style={{ backgroundColor: "rgba(56, 189, 248, 0.15)", color: "var(--accent)" }}
          >
            <ShieldCheckIcon size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-main">Active Enforcement Gate</span>
              <span className="badge badge-passed">LIVE THRESHOLDS</span>
            </div>
            <p className="text-xs text-muted mt-0.5">
              Blocks PRs scoring &lt; {policy.min_security_score}/100 &middot; warns &lt;{" "}
              {policy.warn_security_score ?? policy.min_security_score}/100 &middot; confidence &ge;{" "}
              {policy.confidence_threshold}%.
            </p>
          </div>
        </div>
      </div>

      <PolicyForm policy={policy} onChange={setPolicy} onSave={handleSave} saving={saving} recentPrs={prs} />
    </div>
  );
}
