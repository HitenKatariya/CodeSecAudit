"use client";

import React, { useEffect, useState } from "react";
import { SecurityPolicy } from "@/types";
import { fetchSecurityPolicy, saveSecurityPolicy } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { PolicyForm } from "@/components/policies/PolicyForm";
import { ShieldCheckIcon } from "@/components/ui/Icons";

export default function PoliciesPage() {
  const [policy, setPolicy] = useState<SecurityPolicy | null>(null);
  const [saving, setSaving] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchSecurityPolicy().then((p) => setPolicy(p));
  }, []);

  const handleSave = async () => {
    if (!policy) return;
    setSaving(true);
    await saveSecurityPolicy(policy);
    setSaving(false);
    setToastMessage(
      "Security policy successfully updated and synchronized with GitHub check runs."
    );
    setTimeout(() => setToastMessage(null), 4000);
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
        subtitle="Define automated guardrails and blocking criteria for CI/CD Pull Request gates."
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

      {/* Active Gate status banner */}
      <div
        className="p-4 rounded-xl border flex items-center justify-between"
        style={{
          backgroundColor: "var(--bg-surface)",
          borderColor: "var(--border-subtle)",
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
            style={{
              backgroundColor: "rgba(56, 189, 248, 0.15)",
              color: "var(--accent)",
            }}
          >
            <ShieldCheckIcon size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-main">
                Active Enforcement Gate: Strict Mode
              </span>
              <span className="badge badge-passed">LIVE IN PRODUCTION</span>
            </div>
            <p className="text-xs text-muted mt-0.5">
              Blocking merge on Critical &amp; High vulnerabilities, hardcoded
              secrets, and scores &lt; {policy.min_security_score}.
            </p>
          </div>
        </div>
      </div>

      {/* Policy Configuration Form */}
      <PolicyForm
        policy={policy}
        onChange={setPolicy}
        onSave={handleSave}
        saving={saving}
      />
    </div>
  );
}
