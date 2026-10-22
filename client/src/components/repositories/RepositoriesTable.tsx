"use client";

import React from "react";
import Link from "next/link";
import { Repository } from "@/types";
import { RepoIcon } from "@/components/ui/Icons";
import { DataTable, Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface Props {
  repositories: Repository[];
}

export function RepositoriesTable({ repositories }: Props) {
  const columns: Column<Repository>[] = [
    {
      key: "name",
      header: "Repository",
      render: (repo) => (
        <div className="flex items-center gap-2">
          <RepoIcon className="shrink-0 text-muted" size={16} />
          <Link
            href={`/repositories/${repo.name}`}
            className="font-medium hover:underline"
            style={{ color: "var(--text-main)" }}
          >
            {repo.name}
          </Link>
        </div>
      ),
    },
    {
      key: "language",
      header: "Language",
      render: (repo) => (
        <span className="crumb-badge text-xs">{repo.language}</span>
      ),
    },
    {
      key: "security_score",
      header: "Score",
      render: (repo) => (
        <div className="flex items-center gap-1 font-mono">
          <span
            className="font-bold text-xs"
            style={{
              color:
                repo.security_score >= 85
                  ? "var(--pass-color)"
                  : repo.security_score >= 70
                  ? "var(--med-color)"
                  : "var(--crit-color)",
            }}
          >
            {repo.security_score}
          </span>
          <span className="text-[11px] text-dim">/ 100</span>
        </div>
      ),
    },
    {
      key: "vulnerabilities",
      header: "Vulnerabilities",
      render: (repo) => (
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <span className="badge badge-critical">{repo.critical_count} crit</span>
          <span className="badge badge-high">{repo.high_count} high</span>
          <span className="badge badge-medium">{repo.medium_count} med</span>
        </div>
      ),
    },
    {
      key: "last_scan",
      header: "Last Scan",
      render: (repo) => (
        <span className="text-xs" style={{ color: "var(--text-dim)" }}>
          {repo.last_scan}
        </span>
      ),
    },
    {
      key: "status",
      header: "Policy Gate",
      render: (repo) => <StatusBadge status={repo.status} />,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (repo) => (
        <Link href={`/repositories/${repo.name}`}>
          <Button variant="ghost" size="sm">
            Manage →
          </Button>
        </Link>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={repositories}
      keyExtractor={(repo) => repo.id}
      emptyMessage="No connected repositories."
    />
  );
}
