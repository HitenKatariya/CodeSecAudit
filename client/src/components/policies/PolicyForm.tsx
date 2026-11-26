"use client";

import { GateStatus, PullRequest, SecurityPolicy } from "@/types";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { GateBadge } from "@/components/ui/Badge";
import { PolicyThresholdBars } from "@/components/policies/PolicyThresholdBars";

interface Props {
  policy: SecurityPolicy;
  onChange: (updated: SecurityPolicy) => void;
  onSave: () => void;
  saving: boolean;
  recentPrs?: PullRequest[];
}

export function simulateGate(pr: PullRequest, policy: SecurityPolicy): GateStatus {
  const activeFindings = (pr.findings || []).filter((f: any) => {
    const cwe = (f.cwe_id || "").toUpperCase();
    const title = (f.title || "").toLowerCase();
    const isSecret = cwe === "CWE-798" || title.includes("secret") || title.includes("hardcoded");
    return policy.secret_detection || !isSecret;
  });

  const crit = activeFindings.filter((f) => f.severity === "critical").length;
  const hi = activeFindings.filter((f) => f.severity === "high").length;
  const med = activeFindings.filter((f) => f.severity === "medium").length;
  const hasSecret = activeFindings.some(
    (f: any) => f.cwe_id === "CWE-798" || (f.title || "").toLowerCase().includes("secret")
  );
  const effectiveRisk = activeFindings.length === 0 ? 0 : pr.security_score || 0;
  const score = Math.max(0, 100 - effectiveRisk * 10);

  if (
    (policy.block_critical && crit > 0) ||
    (policy.block_secrets && hasSecret) ||
    (policy.block_high && hi > 0) ||
    (policy.block_medium && med > 0) ||
    score < policy.min_security_score
  ) {
    return "BLOCKED";
  }

  const warnThreshold = policy.warn_security_score;
  if ((warnThreshold != null && warnThreshold > policy.min_security_score && score < warnThreshold) || med > 0) {
    return "WARNING";
  }
  return "PASSED";
}

export function PolicyForm({ policy, onChange, onSave, saving, recentPrs = [] }: Props) {
  const patchPolicy = (patch: Partial<SecurityPolicy>) => onChange({ ...policy, ...patch });

  const simulated = recentPrs.map((pr) => ({ pr, gate: simulateGate(pr, policy) }));
  const blockedCount = simulated.filter((x) => x.gate === "BLOCKED").length;
  const warnCount = simulated.filter((x) => x.gate === "WARNING").length;
  const passCount = simulated.filter((x) => x.gate === "PASSED").length;

  const rules = [
    {
      key: "block_critical" as const,
      title: "Block on Critical Vulnerabilities",
      desc: "Strictly block PR merge if SQLi, RCE, or Critical CWEs are found.",
      checked: policy.block_critical,
    },
    {
      key: "block_secrets" as const,
      title: "Block on Hardcoded Secrets & Keys",
      desc: "Block PRs introducing AWS, Stripe, GitHub, or high-entropy tokens.",
      checked: policy.block_secrets,
    },
    {
      key: "block_high" as const,
      title: "Block on High Severity Vulnerabilities",
      desc: "Require fixes or security lead bypass for SSRF, broken auth, and high CVEs.",
      checked: policy.block_high,
    },
    {
      key: "block_medium" as const,
      title: "Block on Medium Severity Vulnerabilities",
      desc: "Raise non-blocking warnings by default; enable for strict branches.",
      checked: policy.block_medium,
    },
    {
      key: "secret_detection" as const,
      title: "Shannon Entropy & Secret Detection",
      desc: "Scan diffs for hardcoded API keys and credential patterns.",
      checked: policy.secret_detection,
    },
  ];

  return (
    <div className="space-y">
      <Card
        title="Pull Request Merge Gate Rules"
        description="Configure automated GitHub PR check run blocking conditions and dynamic score thresholds"
      >
        <div className="flex flex-col gap-4">
          {rules.map((rule) => (
            <div
              key={rule.key}
              className="flex-between py-2 border-b last:border-b-0"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              <div>
                <span className="text-xs font-semibold text-main block">{rule.title}</span>
                <span className="text-xs text-muted">{rule.desc}</span>
              </div>
              <input
                type="checkbox"
                checked={rule.checked}
                onChange={(e) => patchPolicy({ [rule.key]: e.target.checked })}
                style={{ width: "18px", height: "18px", cursor: "pointer", accentColor: "var(--accent)" }}
              />
            </div>
          ))}
        </div>

        <PolicyThresholdBars policy={policy} onUpdate={patchPolicy} />
      </Card>

      <Card
        title="Live Gate Simulation"
        description="Real-time impact preview across recorded pull requests before saving"
        actions={
          <Button variant="primary" size="md" onClick={onSave} loading={saving}>
            Save Policy &amp; Apply to PRs
          </Button>
        }
      >
        {recentPrs.length > 0 ? (
          <div className="space-y-3">
            <p className="text-xs text-muted">
              Evaluated {recentPrs.length} recorded PR(s):{" "}
              <strong style={{ color: "var(--pass-color)" }}>{passCount} PASSED</strong> &middot;{" "}
              <strong style={{ color: "var(--med-color)" }}>{warnCount} WARNING</strong> &middot;{" "}
              <strong style={{ color: "var(--crit-color)" }}>{blockedCount} BLOCKED</strong>
            </p>
            <div className="flex flex-wrap gap-2">
              {simulated.slice(0, 12).map(({ pr, gate }) => (
                <div
                  key={pr.id}
                  className="px-2.5 py-1.5 rounded border text-xs flex items-center gap-2"
                  style={{ borderColor: "var(--border-subtle)", backgroundColor: "var(--bg-surface-elevated)" }}
                >
                  <span className="font-mono font-semibold text-main">#{pr.pr_number}</span>
                  <span className="font-mono text-dim">{Math.max(0, Math.round(100 - pr.security_score * 10))}/100</span>
                  <GateBadge status={gate} />
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-xs text-muted">
            No pull requests synced yet. As PRs arrive or sync from GitHub, they will simulate against these gates here.
          </p>
        )}
      </Card>
    </div>
  );
}
