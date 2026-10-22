"use client";

import React from "react";
import { SecurityPolicy } from "@/types";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface Props {
  policy: SecurityPolicy;
  onChange: (updated: SecurityPolicy) => void;
  onSave: () => void;
  saving: boolean;
}

export function PolicyForm({ policy, onChange, onSave, saving }: Props) {
  const update = (key: keyof SecurityPolicy, value: unknown) => {
    onChange({ ...policy, [key]: value });
  };

  return (
    <div className="space-y">
      <Card
        title="Pull Request Merge Gate Rules"
        description="Configure automated GitHub PR check run blocking conditions"
      >
        <div className="flex flex-col gap-4">
          {[
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
              desc: "Only recommend warnings by default; toggle on for zero-defect branches.",
              checked: policy.block_medium,
            },
            {
              key: "secret_detection" as const,
              title: "Shannon Entropy Analysis",
              desc: "Run algorithmic high-entropy mathematical scanning on string literals.",
              checked: policy.secret_detection,
            },
          ].map((rule) => (
            <div
              key={rule.key}
              className="flex-between py-2 border-b last:border-b-0"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              <div>
                <span className="text-xs font-semibold text-main block">
                  {rule.title}
                </span>
                <span className="text-xs text-muted">{rule.desc}</span>
              </div>
              <input
                type="checkbox"
                checked={rule.checked}
                onChange={(e) => update(rule.key, e.target.checked)}
                style={{ width: "18px", height: "18px", cursor: "pointer", accentColor: "var(--accent)" }}
              />
            </div>
          ))}
        </div>

        {/* Sliders */}
        <div
          className="pt-4 mt-4 border-t grid-2 gap-6"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <div>
            <div className="flex-between mb-2 text-xs">
              <label className="font-semibold text-main">
                Minimum PR Security Score
              </label>
              <span className="font-mono font-bold text-accent">
                {policy.min_security_score} / 100
              </span>
            </div>
            <input
              type="range"
              min="50"
              max="95"
              step="5"
              value={policy.min_security_score}
              onChange={(e) => update("min_security_score", Number(e.target.value))}
              className="w-full"
              style={{ accentColor: "var(--accent)" }}
            />
            <span className="text-[11px] text-dim block mt-1">
              PRs scoring below this threshold will be marked BLOCKED.
            </span>
          </div>

          <div>
            <div className="flex-between mb-2 text-xs">
              <label className="font-semibold text-main">
                Minimum AI Confidence to Block
              </label>
              <span className="font-mono font-bold text-accent">
                {policy.confidence_threshold}%
              </span>
            </div>
            <input
              type="range"
              min="60"
              max="99"
              step="1"
              value={policy.confidence_threshold}
              onChange={(e) => update("confidence_threshold", Number(e.target.value))}
              className="w-full"
              style={{ accentColor: "var(--accent)" }}
            />
            <span className="text-[11px] text-dim block mt-1">
              Prevents false-positive blocks when model confidence is low.
            </span>
          </div>
        </div>
      </Card>

      {/* Gate Simulation Preview & Save */}
      <Card
        title="Simulation on Recent 10 Pull Requests"
        description="Preview policy impact before saving active guardrails"
        actions={
          <Button
            variant="primary"
            size="md"
            onClick={onSave}
            loading={saving}
          >
            Save Policy Configuration
          </Button>
        }
      >
        <p className="text-xs text-muted">
          With these rules:{" "}
          <strong style={{ color: "var(--pass-color)" }}>8 would PASS</strong>,{" "}
          <strong style={{ color: "var(--crit-color)" }}>2 would be BLOCKED</strong>.
        </p>
      </Card>
    </div>
  );
}
