"use client";

import React, { useEffect, useState } from "react";
import { LogEntry } from "@/types";
import { fetchLogs } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { DataTable, Column } from "@/components/ui/DataTable";

export default function AdminLogsPage() {
  const [activeService, setActiveService] = useState<
    "main-server" | "client-server" | "rag-server"
  >("main-server");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const loadLogs = async (
    srv: "main-server" | "client-server" | "rag-server"
  ) => {
    setLoading(true);
    const data = await fetchLogs(srv, 50);
    setLogs(data);
    setLoading(false);
  };

  useEffect(() => {
    loadLogs(activeService);
  }, [activeService]);

  const columns: Column<LogEntry>[] = [
    {
      key: "timestamp",
      header: "Timestamp",
      width: "180px",
      render: (l) => (
        <span className="font-mono text-xs text-dim whitespace-nowrap">
          {l.timestamp}
        </span>
      ),
    },
    {
      key: "level",
      header: "Level",
      width: "100px",
      render: (l) => {
        let color = "var(--pass-color)";
        if (l.level === "ERROR") color = "var(--crit-color)";
        else if (l.level === "WARN") color = "var(--high-color)";
        return (
          <span
            className="font-mono font-bold text-xs"
            style={{ color }}
          >
            {l.level}
          </span>
        );
      },
    },
    {
      key: "message",
      header: "Message",
      render: (l) => (
        <span className="font-mono text-xs text-main break-all">
          {l.message}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y">
      <PageHeader
        title="System Log Streams"
        subtitle="Live Redis Streams telemetry with automatic secret redaction."
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => loadLogs(activeService)}
            loading={loading}
          >
            🔄 Refresh Stream
          </Button>
        }
      />

      <div className="flex items-center gap-2">
        {(["main-server", "client-server", "rag-server"] as const).map((s) => (
          <Button
            key={s}
            variant={activeService === s ? "primary" : "secondary"}
            size="sm"
            onClick={() => setActiveService(s)}
          >
            {s}
          </Button>
        ))}
      </div>

      <Card
        title={
          <div className="flex items-center gap-2">
            <span>Stream:</span>
            <code className="text-accent font-mono text-xs">
              log:{activeService}
            </code>
          </div>
        }
        actions={
          <span className="text-xs text-dim">
            {logs.length} entries tailing
          </span>
        }
      >
        <DataTable
          columns={columns}
          data={logs}
          keyExtractor={(l) => l.id}
          loading={loading}
          emptyMessage={`No recent log entries in stream log:${activeService}. System operating normally.`}
        />
      </Card>
    </div>
  );
}
