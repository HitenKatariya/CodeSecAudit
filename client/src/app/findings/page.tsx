"use client";

import React, { useEffect, useState, useMemo } from "react";
import { Finding } from "@/types";
import { fetchFindings } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { FindingsTable } from "@/components/findings/FindingsTable";
import { Button } from "@/components/ui/Button";

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchFindings().then(setFindings);
  }, []);

  const criticalCount = findings.filter((f) => f.severity === "critical").length;
  const highCount = findings.filter((f) => f.severity === "high").length;
  const otherCount = findings.filter((f) => f.severity !== "critical" && f.severity !== "high").length;

  const filtered = useMemo(() => {
    return findings.filter((f) => {
      const matchSev =
        selectedSeverity === "all" || f.severity === selectedSeverity;
      const matchStat =
        selectedStatus === "all" || (f.status || "open") === selectedStatus;
      const matchSearch =
        f.title.toLowerCase().includes(search.toLowerCase()) ||
        f.cwe_id.toLowerCase().includes(search.toLowerCase()) ||
        f.file_path.toLowerCase().includes(search.toLowerCase());
      return matchSev && matchStat && matchSearch;
    });
  }, [findings, selectedSeverity, selectedStatus, search]);

  return (
    <div className="space-y">
      <PageHeader
        title="Security Findings"
        subtitle="Vulnerabilities detected by automated AST and RAG security analysis."
      />

      {/* Action Banner */}
      {criticalCount > 0 ? (
        <div className="banner-alert">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="badge badge-critical">🔴 {criticalCount} Critical</span>
              {highCount > 0 && <span className="badge badge-high">🟠 {highCount} High</span>}
              <span className="text-dim text-xs">&bull; {otherCount} Medium / Low</span>
            </div>
            <p className="text-xs text-main">
              {criticalCount} critical vulnerability issue{criticalCount === 1 ? " is" : "s are"} currently gating production merges.
            </p>
          </div>

          <Button
            variant="danger"
            size="sm"
            onClick={() => setSelectedSeverity("critical")}
          >
            Filter Critical Findings ({criticalCount})
          </Button>
        </div>
      ) : (
        <div className="p-3.5 rounded-lg border text-xs flex items-center justify-between" style={{ backgroundColor: "var(--pass-bg)", borderColor: "var(--pass-border)", color: "var(--pass-color)" }}>
          <div className="flex items-center gap-2">
            <span>🛡️</span>
            <span className="font-semibold">Zero Critical Findings: Clean security posture detected.</span>
          </div>
          <span className="text-muted text-[11px]">{findings.length} total monitored items</span>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="filter-bar flex-between">
        <div className="flex items-center gap-2.5 flex-wrap">
          <input
            type="text"
            placeholder="Search findings, CWE, files..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="form-input"
            style={{ width: "240px" }}
          />

          <div className="flex items-center gap-1">
            {["all", "critical", "high", "medium", "low"].map((sev) => (
              <Button
                key={sev}
                variant={selectedSeverity === sev ? "primary" : "secondary"}
                size="sm"
                onClick={() => setSelectedSeverity(sev)}
                className="capitalize"
              >
                {sev}
              </Button>
            ))}
          </div>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="form-input"
          >
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="ignored">Ignored</option>
          </select>
        </div>

        <span className="text-xs text-dim">
          Showing {filtered.length} of {findings.length} findings
        </span>
      </div>

      {/* Findings Table */}
      <FindingsTable findings={filtered} />
    </div>
  );
}
