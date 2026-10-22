"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Finding } from "@/types";
import { fetchFindingById, updateFindingStatus } from "@/lib/api";
import { SeverityBadge, StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ArrowLeftIcon, GitHubIcon } from "@/components/ui/Icons";
import { FindingDetailContent } from "@/components/findings/FindingDetailContent";

export default function FindingDetailPage() {
  const params = useParams();
  const findingId = typeof params?.id === "string" ? params.id : "finding-1";
  const [finding, setFinding] = useState<Finding | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchFindingById(findingId).then((data) => {
      if (data) setFinding(data);
    });
  }, [findingId]);

  const handleStatusChange = async (newStatus: "open" | "resolved" | "ignored") => {
    if (!finding) return;
    const prevStatus = finding.status;
    setFinding({ ...finding, status: newStatus });
    const ok = await updateFindingStatus(finding.id, newStatus);
    if (ok) {
      setToastMessage(`Finding status updated to "${newStatus}" in database.`);
    } else {
      setFinding({ ...finding, status: prevStatus });
      setToastMessage(`Failed to update finding status in database.`);
    }
    setTimeout(() => setToastMessage(null), 3000);
  };

  if (!finding) {
    return (
      <div className="py-16 text-center text-muted text-xs">
        <span className="btn-spinner mr-2" />
        Loading finding details...
      </div>
    );
  }

  return (
    <div className="space-y">
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

      {/* Deep Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs flex-wrap">
        <Link
          href="/findings"
          className="text-muted hover:text-main flex items-center gap-1 font-medium"
        >
          <ArrowLeftIcon size={14} />
          <span>Security Findings</span>
        </Link>
        <span className="text-dim">/</span>
        <Link
          href={`/repositories/${finding.repository}`}
          className="text-muted hover:text-main font-mono"
        >
          {finding.repository}
        </Link>
        <span className="text-dim">/</span>
        <span className="crumb-target">{finding.title}</span>
        <span className="crumb-badge font-mono">{finding.cwe_id}</span>
      </div>

      {/* Header with Title and CTAs */}
      <div className="flex-between items-start gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2.5 mb-2 flex-wrap">
            <SeverityBadge severity={finding.severity} />
            <span className="crumb-badge font-mono">{finding.cwe_id}</span>
            <StatusBadge status={finding.status || "open"} />
            <span className="text-xs text-dim">
              {finding.detected_at || "Recently"}
            </span>
          </div>
          <h1 className="page-title mb-1">{finding.title}</h1>
          <p className="text-xs font-mono text-muted">
            {finding.repository} &bull; {finding.file_path}:{finding.line_number}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <a
            href={`https://github.com/example/${finding.repository}/blob/main/${finding.file_path}#L${finding.line_number}`}
            target="_blank"
            rel="noreferrer"
          >
            <Button variant="secondary" size="sm" icon={<GitHubIcon size={14} />}>
              Open in GitHub ↗
            </Button>
          </a>
          <Link href={`/repositories/${finding.repository}`}>
            <Button variant="ghost" size="sm">
              Repository Overview
            </Button>
          </Link>
        </div>
      </div>

      {/* Detailed Breakdown */}
      <FindingDetailContent
        finding={finding}
        onStatusChange={handleStatusChange}
      />
    </div>
  );
}
