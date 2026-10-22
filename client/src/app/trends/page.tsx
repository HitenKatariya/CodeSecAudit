"use client";

import React, { useEffect, useState } from "react";
import { TrendsCharts } from "@/components/trends/TrendsCharts";
import { PageHeader } from "@/components/ui/PageHeader";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card } from "@/components/ui/Card";
import { AnalyticsTrends } from "@/types";
import { fetchAnalyticsTrends } from "@/lib/api";

export default function TrendsPage() {
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalyticsTrends()
      .then(setTrends)
      .finally(() => setLoading(false));
  }, []);

  const secScore = trends?.security_score ?? 100;
  const criticalCount = trends?.critical_active ?? 0;
  const passedCount = trends?.gate_verdicts?.passed_count ?? 0;
  const blockedCount = trends?.gate_verdicts?.blocked_count ?? 0;
  const passedPct = trends?.gate_verdicts?.passed_pct ?? 100;
  const blockedPct = trends?.gate_verdicts?.blocked_pct ?? 0;
  const mttr = trends?.mttr_hours ?? 0;

  return (
    <div className="space-y">
      <PageHeader
        title="Security Trends & Posture"
        subtitle="Quarterly vulnerability metrics, MTTR performance, and automated gate enforcement history."
      />

      {/* 4 KPI Cards */}
      <div className="stat-grid">
        <MetricCard
          label="Security Score"
          value={String(secScore)}
          trend={secScore >= 80 ? "Healthy" : "Needs Review"}
          trendDirection="up"
          trendPositive={secScore >= 80}
          subtitle="across monitored repositories"
        />

        <MetricCard
          label="Critical Active"
          value={`${criticalCount} Active`}
          severity={criticalCount > 0 ? "critical" : "passed"}
          subtitle={criticalCount > 0 ? "Requires remediation" : "Clean branch posture"}
        />

        <MetricCard
          label="Critical MTTR"
          value={`${mttr} hrs`}
          trend="Automated"
          trendDirection="down"
          trendPositive={true}
          subtitle="mean time to remediate"
        />

        <MetricCard
          label="Gate Enforcement"
          value={`${passedPct}%`}
          severity={passedPct >= 80 ? "passed" : "warning"}
          subtitle={`${passedCount} / ${passedCount + blockedCount} reviews passed`}
        />
      </div>

      {/* Visual Charts */}
      <TrendsCharts trends={trends} />

      {/* PR Gate Verdict Distribution & Top Remediated CWEs */}
      <div className="grid-2">
        <Card
          title="Pull Request Gate Verdicts (Active Tenant)"
          description="Distribution of PR verdicts enforced by automated policy gates"
        >
          <div className="grid-2 mb-3">
            <div
              className="p-3 rounded text-center border"
              style={{
                backgroundColor: "var(--bg-surface-elevated)",
                borderColor: "var(--border-subtle)",
              }}
            >
              <span
                className="text-xs font-semibold block"
                style={{ color: "var(--pass-color)" }}
              >
                Passed &amp; Approved
              </span>
              <span className="text-xl font-bold font-mono text-main mt-1 block">
                {passedCount} ({passedPct}%)
              </span>
            </div>

            <div
              className="p-3 rounded text-center border"
              style={{
                backgroundColor: "var(--bg-surface-elevated)",
                borderColor: "var(--border-subtle)",
              }}
            >
              <span
                className="text-xs font-semibold block"
                style={{ color: "var(--crit-color)" }}
              >
                Blocked by Policy
              </span>
              <span className="text-xl font-bold font-mono text-main mt-1 block">
                {blockedCount} ({blockedPct}%)
              </span>
            </div>
          </div>

          <p className="text-xs text-muted leading-relaxed">
            Every blocked pull request required developer remediation or
            security lead sign-off before merging, preventing {blockedCount} high-risk code changes from reaching production branches.
          </p>
        </Card>

        <Card
          title="Detected CWEs in Database"
          description="High-frequency vulnerability types resolved or identified"
        >
          <div className="flex flex-col gap-2">
            {trends?.cwe_distribution && trends.cwe_distribution.length > 0 ? (
              trends.cwe_distribution.map((item) => (
                <div
                  key={item.cwe_id}
                  className="flex-between p-2.5 rounded border text-xs"
                  style={{
                    backgroundColor: "var(--bg-surface-elevated)",
                    borderColor: "var(--border-subtle)",
                  }}
                >
                  <span className="font-mono text-main">{item.name}</span>
                  <span
                    className="font-medium font-mono"
                    style={{ color: item.color }}
                  >
                    {item.count} findings ({item.pct})
                  </span>
                </div>
              ))
            ) : (
              <div className="text-xs text-muted py-4 text-center">
                ✓ No vulnerabilities currently detected in database.
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
