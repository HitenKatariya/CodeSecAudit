"use client";

import React, { useEffect, useState } from "react";
import { ReportSummary } from "@/types";
import { fetchReportSummary } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ShieldCheckIcon, DocumentTextIcon } from "@/components/ui/Icons";

export default function ReportsPage() {
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [period, setPeriod] = useState("Current Period");

  useEffect(() => {
    fetchReportSummary().then((data) => {
      if (data) {
        setReport(data);
        setPeriod(data.period);
      }
    });
  }, []);

  const handleExport = (type: string) => {
    if (!report) return;
    if (type === "CSV") {
      const csvContent =
        "Metric,Value\n" +
        `Period,${report.period}\n` +
        `Repositories Scanned,${report.repos_scanned}\n` +
        `Pull Requests Audited,${report.prs_scanned}\n` +
        `Vulnerabilities Detected,${report.vulnerabilities_detected}\n` +
        `Critical Vulnerabilities,${report.critical_vulnerabilities}\n` +
        `Resolved / Remediated,${report.resolved_vulnerabilities}\n` +
        `Critical MTTR Hours,${report.avg_remediation_hours.critical}\n`;
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `codesec_audit_report_${period.replace(/\s+/g, "_")}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      window.print();
    }
  };

  if (!report) {
    return (
      <div className="py-16 text-center text-muted text-xs">
        <span className="btn-spinner mr-2" />
        Loading audit report from database...
      </div>
    );
  }

  const resolutionRate =
    report.vulnerabilities_detected > 0
      ? Math.round((report.resolved_vulnerabilities / report.vulnerabilities_detected) * 100)
      : 100;

  return (
    <div className="space-y">
      <PageHeader
        title="Security & Compliance Reports"
        subtitle="Executive audit summaries, remediation metrics, and compliance attestations."
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted font-mono">{period}</span>
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleExport("PDF")}
            >
              Print / Save PDF
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleExport("CSV")}
            >
              Export CSV
            </Button>
          </div>
        }
      />

      {/* Executive Summary Card */}
      <Card
        title={
          <div className="flex items-center gap-2">
            <DocumentTextIcon size={18} className="text-accent" />
            <span>Executive Audit Overview ({period})</span>
          </div>
        }
      >
        <p className="text-xs text-muted leading-relaxed mb-4">
          During {period}, CodeSecAudit AI evaluated {report.prs_scanned} pull requests across {report.repos_scanned} active microservice repositories in PostgreSQL. Automated policy gates monitored for high-risk security regressions before merging into production.
        </p>

        <div className="stat-grid">
          <div className="metric-card">
            <span className="metric-card-label">Total PRs Audited</span>
            <span className="metric-card-value">{report.prs_scanned}</span>
          </div>
          <div className="metric-card">
            <span className="metric-card-label">Vulnerabilities Detected</span>
            <span className="metric-card-value text-warning">{report.vulnerabilities_detected}</span>
          </div>
          <div className="metric-card">
            <span className="metric-card-label">Resolved / Remediated</span>
            <span className="metric-card-value text-success">{report.resolved_vulnerabilities}</span>
          </div>
          <div className="metric-card">
            <span className="metric-card-label">Resolution Rate</span>
            <span className="metric-card-value text-accent">{resolutionRate}%</span>
          </div>
        </div>
      </Card>

      {/* Compliance Framework Mapping */}
      <Card
        title={
          <div className="flex items-center gap-2">
            <ShieldCheckIcon size={18} className="text-success" />
            <span>Compliance Framework Verification</span>
          </div>
        }
      >
        <div className="grid-2">
          {[
            {
              title: "SOC 2 Type II",
              badge: "ACTIVE",
              variant: "passed" as const,
              desc: "Controls CC6.6 & CC6.7: Continuous code integrity and peer security gate verification.",
            },
            {
              title: "ISO/IEC 27001",
              badge: "ACTIVE",
              variant: "passed" as const,
              desc: "Control A.14.2: Security in development and support processes via automated SAST taint-tracking.",
            },
            {
              title: "OWASP Top 10",
              badge: "100% COVERED",
              variant: "passed" as const,
              desc: "Active rulesets verifying A01:2021 through A10:2021 with contextual private RAG explanation.",
            },
          ].map((item) => (
            <div
              key={item.title}
              className="p-4 rounded border"
              style={{
                backgroundColor: "var(--bg-surface-elevated)",
                borderColor: "var(--border-subtle)",
              }}
            >
              <div className="flex-between mb-2">
                <span className="font-semibold text-main text-sm">{item.title}</span>
                <Badge variant={item.variant}>{item.badge}</Badge>
              </div>
              <p className="text-xs text-muted leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
