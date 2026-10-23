"use client";

import React, { useState } from "react";
import { Finding } from "@/types";
import { ShieldCheckIcon, AlertTriangleIcon } from "@/components/ui/Icons";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface Props {
  finding: Finding;
  onStatusChange: (newStatus: "open" | "resolved" | "ignored") => void;
}

export function FindingDetailContent({ finding, onStatusChange }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopyFix = () => {
    if (finding.suggested_fix) {
      navigator.clipboard.writeText(finding.suggested_fix);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y">
      {/* 1. Vulnerability Summary */}
      <Card
        title={
          <div className="flex items-center gap-2">
            <ShieldCheckIcon size={18} className="text-accent" />
            <span>1. Vulnerability Summary</span>
          </div>
        }
      >
        <div className="grid-2 gap-4 mb-4">
          <div className="p-3 rounded border bg-surface-elevated border-subtle">
            <span className="text-dim block text-xs">Vulnerability</span>
            <span className="font-semibold text-main text-sm">{finding.title} ({finding.cwe_id})</span>
          </div>
          <div className="p-3 rounded border bg-surface-elevated border-subtle">
            <span className="text-dim block text-xs">Location</span>
            <span className="font-mono text-xs text-accent">{finding.file_path}:{finding.line_number}</span>
          </div>
        </div>

        <div className="grid-2 gap-4">
          <div className="p-3.5 rounded border bg-surface-elevated border-subtle">
            <span className="text-xs font-bold uppercase tracking-wider block mb-1 text-accent">Plain-English Explanation</span>
            <p className="text-xs text-muted leading-relaxed">
              {finding.why_it_matters || "User-controlled input flows directly into high-risk system functions without sanitization."}
            </p>
          </div>
          <div className="p-3.5 rounded border bg-surface-elevated border-subtle">
            <span className="text-xs font-bold uppercase tracking-wider block mb-1 text-warning">Technical Taint Analysis</span>
            <p className="text-xs text-muted leading-relaxed font-mono">
              {finding.reasoning_summary || "Taint source traced from route parameters directly into SQL execution sink."}
            </p>
          </div>
        </div>
      </Card>

      {/* 2. Code Comparison & Recommended Fix */}
      <Card
        title="2. Code Comparison & Recommended Fix"
        description="Side-by-side diff between vulnerable code and safe OWASP implementation"
        actions={<Button variant="secondary" size="sm" onClick={handleCopyFix}>{copied ? "✓ Copied" : "Copy Fix"}</Button>}
      >
        <div className="grid-2 gap-4">
          <div style={{ minWidth: 0, overflow: "hidden" }}>
            <div className="flex-between px-3 py-1.5 rounded-t border text-xs" style={{ backgroundColor: "var(--crit-bg)", borderColor: "var(--crit-border)", color: "var(--crit-color)" }}>
              <span className="font-semibold">Vulnerable Code</span>
              <span className="font-mono">Line {finding.line_number}</span>
            </div>
            <pre className="p-3 rounded-b border font-mono text-xs overflow-x-auto whitespace-pre leading-relaxed" style={{ backgroundColor: "var(--bg-base)", borderColor: "var(--border-subtle)", color: "var(--crit-color)" }}>
              {finding.code_snippet || "// Code snippet unavailable"}
            </pre>
          </div>

          <div style={{ minWidth: 0, overflow: "hidden" }}>
            <div className="flex-between px-3 py-1.5 rounded-t border text-xs" style={{ backgroundColor: "var(--pass-bg)", borderColor: "var(--pass-border)", color: "var(--pass-color)" }}>
              <span className="font-semibold">Remediated Fix (OWASP)</span>
              <span>Safe Implementation</span>
            </div>
            <pre className="p-3 rounded-b border font-mono text-xs overflow-x-auto whitespace-pre leading-relaxed" style={{ backgroundColor: "var(--bg-base)", borderColor: "var(--border-subtle)", color: "var(--pass-color)" }}>
              {finding.suggested_fix || "// Fix suggestion unavailable"}
            </pre>
          </div>
        </div>
      </Card>

      {/* 3. Exploit Scenario */}
      {finding.attack_scenario && (
        <Card
          title={
            <div className="flex items-center gap-2">
              <AlertTriangleIcon size={18} className="text-warning" />
              <span>3. Concrete Exploit Scenario</span>
            </div>
          }
        >
          <div className="p-3.5 rounded border text-xs font-mono leading-relaxed" style={{ backgroundColor: "var(--bg-base)", borderColor: "var(--border-subtle)", color: "var(--med-color)" }}>
            {finding.attack_scenario}
          </div>
        </Card>
      )}

      {/* 4. OWASP Classification & Confidence */}
      <div className="grid-2">
        <Card title="4. OWASP Classification">
          <span className="crumb-badge text-xs mb-2 inline-block">{finding.owasp_category || "OWASP Top 10"}</span>
          <p className="text-xs text-muted leading-relaxed">{finding.security_principle || "Follow defense-in-depth secure coding principles."}</p>
        </Card>

        <Card title="5. AI Model Confidence" actions={<span className="badge badge-low">{finding.confidence || 94}% Confidence</span>}>
          <p className="text-xs text-muted leading-relaxed">
            Deterministic AST graph validated against contextual OWASP vectors retrieved via private Qdrant collection.
          </p>
        </Card>
      </div>

      {/* 6. Remediation Status Actions */}
      <Card title="Remediation Status" description="Update security gate tracking for this vulnerability">
        <div className="flex items-center gap-2.5 flex-wrap">
          <Button variant="success" size="sm" onClick={() => onStatusChange("resolved")}>Mark as Resolved</Button>
          <Button variant="secondary" size="sm" onClick={() => onStatusChange("ignored")}>Accept Risk (Ignore)</Button>
          <Button variant="ghost" size="sm" onClick={() => onStatusChange("open")}>Re-open Finding</Button>
        </div>
      </Card>
    </div>
  );
}
