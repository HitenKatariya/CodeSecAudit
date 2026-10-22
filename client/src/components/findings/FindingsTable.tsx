"use client";

import React from "react";
import Link from "next/link";
import { Finding } from "@/types";
import { SeverityBadge, StatusBadge } from "@/components/ui/Badge";
import { DataTable, Column } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";

interface Props {
  findings: Finding[];
}

export function FindingsTable({ findings }: Props) {
  const columns: Column<Finding>[] = [
    {
      key: "severity",
      header: "Severity",
      render: (f) => <SeverityBadge severity={f.severity} />,
    },
    {
      key: "title",
      header: "Vulnerability & CWE",
      render: (f) => (
        <div>
          <Link
            href={`/findings/${f.id}`}
            className="font-medium hover:underline block"
            style={{ color: "var(--text-main)" }}
          >
            {f.title}
          </Link>
          <span className="crumb-badge text-xs font-mono">{f.cwe_id}</span>
        </div>
      ),
    },
    {
      key: "repository",
      header: "Repository",
      render: (f) => (
        <Link
          href={`/repositories/${f.repository}`}
          className="font-mono text-xs hover:underline"
          style={{ color: "var(--accent)" }}
        >
          {f.repository}
        </Link>
      ),
    },
    {
      key: "file_path",
      header: "Location",
      render: (f) => (
        <span className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>
          {f.file_path}:{f.line_number}
        </span>
      ),
    },
    {
      key: "owasp_category",
      header: "Category",
      render: (f) => (
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {f.owasp_category || "OWASP Top 10"}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (f) => <StatusBadge status={f.status || "open"} />,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (f) => (
        <Link href={`/findings/${f.id}`}>
          <Button variant="ghost" size="sm">
            Review →
          </Button>
        </Link>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={findings}
      keyExtractor={(f) => f.id}
      emptyMessage="No findings match your current filter criteria."
    />
  );
}
