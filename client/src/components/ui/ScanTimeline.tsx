import React from "react";

export interface ScanTimelineEvent {
  id: string;
  stage: string;
  timestamp: string;
  status: "completed" | "in_progress" | "failed" | "pending";
  details?: string;
}

export interface ScanTimelineProps {
  events: ScanTimelineEvent[];
  className?: string;
}

export function ScanTimeline({ events, className = "" }: ScanTimelineProps) {
  const getStatusIcon = (status: ScanTimelineEvent["status"]) => {
    switch (status) {
      case "completed":
        return <span style={{ color: "var(--pass-color)" }}>●</span>;
      case "in_progress":
        return <span className="btn-spinner" style={{ width: 10, height: 10 }} />;
      case "failed":
        return <span style={{ color: "var(--crit-color)" }}>✕</span>;
      case "pending":
      default:
        return <span style={{ color: "var(--text-dim)" }}>○</span>;
    }
  };

  return (
    <div className={`flex flex-col gap-3 ${className}`.trim()}>
      {events.map((evt, idx) => {
        const isLast = idx === events.length - 1;

        return (
          <div key={evt.id} className="flex items-start gap-3 relative">
            {!isLast && (
              <div
                style={{
                  position: "absolute",
                  left: "9px",
                  top: "18px",
                  bottom: "-12px",
                  width: "2px",
                  backgroundColor: "var(--border-subtle)",
                }}
              />
            )}

            <div
              className="flex items-center justify-center shrink-0"
              style={{
                width: "20px",
                height: "20px",
                borderRadius: "50%",
                backgroundColor: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                fontSize: "10px",
                zIndex: 1,
              }}
            >
              {getStatusIcon(evt.status)}
            </div>

            <div className="flex-1 pb-1">
              <div className="flex-between">
                <span className="text-xs font-semibold text-main">
                  {evt.stage}
                </span>
                <span className="text-[11px] font-mono text-dim">
                  {evt.timestamp}
                </span>
              </div>
              {evt.details && (
                <p className="text-xs text-muted mt-0.5">{evt.details}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
