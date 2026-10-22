import React from "react";
import Link from "next/link";
import { Finding } from "@/types";
import { SeverityBadge, StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export interface SecurityFindingCardProps {
  finding: Finding;
  onSelect?: (finding: Finding) => void;
  compact?: boolean;
  className?: string;
}

export function SecurityFindingCard({
  finding,
  onSelect,
  compact = false,
  className = "",
}: SecurityFindingCardProps) {
  return (
    <div
      className={`card card-interactive ${className}`.trim()}
      onClick={() => onSelect && onSelect(finding)}
    >
      <div className="flex-between items-start gap-4">
        <div className="flex items-center gap-2 flex-wrap">
          <SeverityBadge severity={finding.severity} />
          {finding.cwe_id && (
            <span className="crumb-badge text-xs font-mono">
              {finding.cwe_id}
            </span>
          )}
          {finding.status && <StatusBadge status={finding.status} />}
        </div>
        <Link
          href={`/findings/${finding.id}`}
          onClick={(e) => e.stopPropagation()}
        >
          <Button variant="ghost" size="sm">
            Details →
          </Button>
        </Link>
      </div>

      <div className="mt-2.5">
        <h4 className="text-sm font-bold text-main">
          {finding.title}
        </h4>
        <div className="mt-1 flex items-center gap-2 text-xs text-muted font-mono">
          <span>{finding.file_path}</span>
          {finding.line_number && (
            <span className="text-dim">:{finding.line_number}</span>
          )}
          {finding.repository && (
            <span className="text-dim font-sans ml-2">
              in {finding.repository}
            </span>
          )}
        </div>
      </div>

      {!compact && finding.why_it_matters && (
        <p className="mt-2 text-xs text-muted line-clamp-2">
          {finding.why_it_matters}
        </p>
      )}

      {!compact && finding.code_snippet && (
        <div className="mt-3 p-2.5 rounded bg-surface-elevated border border-subtle">
          <pre className="text-xs text-rose-300 font-mono overflow-x-auto whitespace-pre-wrap">
            {finding.code_snippet.slice(0, 160)}
            {finding.code_snippet.length > 160 ? "..." : ""}
          </pre>
        </div>
      )}
    </div>
  );
}
